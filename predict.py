#!/usr/bin/env python3
"""Prediction runner: MPE + best-response dynamics over the payoff
model, agent-claim application via the Dynamics.applyMove mirror,
fork construction (season S+1, 1 round), and re-verification
(check.py + Lean build in a temp copy of lean/).

Design decisions (from design/prediction-layer.md section 8):
 1. Solution concept: MPE + best-response dynamics.
 2. Payoff parameters: all placeholders, labelled as assumptions.
 3. Hit-rate threshold: 10 pp above the random baseline; M5
    tolerance +-10; below threshold degrades to opinion, never blocks.
 4. Prediction does not go on the page; it goes in the merged
    report's prediction chapter only.
 5. Default horizon 1 round; --horizon at most 1 season; beyond
    1 season only a symbolic reachable-set conclusion, no per-round
    actions; confidence is tiered by round (1 high, 2-7 medium,
    further low).
 6. Code covers all 18 seats; agent-claim smoke tests pilot 4 key
    seats (NVDA, Anthropic, HUAWEI, BYTE).
 7. Schema v2 is another lane's work; this file does not touch the
    schema or gate.py.
 8. Backtest: walk-forward, S1-S3 fit, S4-S5 test (see backtest.py);
    random-baseline margin 10 pp.
 9. Move is not extended (population and card pool stay in the
    finite layer; the Lean side uses only what Move determines).
10. A below-threshold hit rate is reported only; the model is not
    auto-revised.

Rule scenarios (--scenarios, rules/scenarios.json): each scenario is
a conditional branch (trigger + rule delta: banned action kinds
and/or HP bounds). Best-response dynamics run once per scenario;
no trigger probability is assigned anywhere (no data supports one).
Output is a standalone JSON file; merging into the merged report is
not wired (run.sh / merge_report.py untouched).

Feasibility mask (audit fix 5, round 5): rules/payoff-model.json
"feasible_kinds" lists, per kind, eligible_players (player keys),
one_shot and exogenous. The mask filters every candidate set before
best-response dynamics (baseline and per-scenario runs): exogenous
kinds never enter argmax, a listed kind is open only to its eligible
players, and a one_shot kind leaves a player's candidates once that
player already has a prefix move of that kind (prefix = history
available at prediction time). A kind absent from the table is open
to every player. M7 is the feasibility violation rate (share of
predictions whose kind is infeasible for that player); it is named
M7 because the audit's "M6" for this rate collides with the M6
calibration gap defined in batch 1 (round 3), which is unchanged.

Utility (per payoff-model.json v2, design/fitting-layer.md §3-4):
  u = w_hp*[(hp_after)^alpha - (hp_before)^alpha] + w_gold*dgold
      - c_lever*leverage_penalty - c_rule*compliance_cost
      + w_pos*position_term
  alpha = hp_exponent (A9); alpha = 1 is exactly v1 (linear dHP).
  At alpha = 1 the HP term uses the caller's expected dHP verbatim
  (not re-derived from clamped HPs, which would round), so v1 is
  restored bit-exactly.
  gamma = discount (A8) is read but NOT applied here: per design
  §3 it weights fitting evidence by recency (decision weight
  gamma**(R-r)); it does not discount future rewards in
  single-step prediction. Multi-step continuation discounting is
  a future extension, not this version.
  hp_after is the HP after the expected increment, clamped to the
  rule bounds; hp_before is the round-start HP. Gold stays linear.
  leverage_penalty = 1 when the expected gold result is negative,
  else 0. compliance_cost = 0 for every legal kind in this version.
  position_term = old rank - new rank after applying the expected
  increments (rank by HP desc, then gold desc).

applyMove mirror: identical to Dynamics.lean applyMove, on the
trace-level representation (string rule ids, as in check.py):
legal iff the move's player equals the state's player, the state
is not eliminated, a base rule is in effect at the move's date,
the move's rulesVersion equals that base rule's id, the kind is
not banned under the base rule or any overlay, and the gold
result is non-negative or the move is flagged liability. HP is
clamped to the rule bounds; gold is never clamped; eliminated
iff clamped HP is 0; the new state's rule is the base rule id,
date/season are the move's, liab is the move's liability.

Usage:
    python3 predict.py <trace.json> --payoff <payoff.json>
        [--horizon N] [--claims <claims.json>]
        [--gate-report <gate-report.json>]
        [--backtest-report <backtest-report.json>]
        [--scenarios <scenarios.json>]
        [--scenarios-out scenarios-report.json]
        [--out report.json] [--summary summary.txt]
Exit: 0 run completed; 2 bad input. (The verdict lives in the
report; it is not encoded in the exit code.)
"""
import argparse
import copy
import datetime
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402  (resolve_rules, penalty_value, run)

HP_SEGMENTS = [
    ("king", 90, None), ("master", 80, 89), ("diamond", 70, 79),
    ("platinum", 60, 69), ("gold", 50, 59), ("silver", 40, 49),
    ("bronze", 30, 39), ("iron", None, 29),
]

SMOKE_NOTE = ("Smoke test only, not calibration: payoff parameters "
              "are placeholders and the fixture trace must not be "
              "used for calibration.")
ASSUMPTION_NOTE = ("All payoff parameters are placeholders (status "
                   "placeholder, assumptions A1-A6, plus A7 for the "
                   "AAPL tier judgement). No parameter value carries "
                   "evidence.")


def hp_segment(hp):
    for name, lo, hi in HP_SEGMENTS:
        if (lo is None or hp >= lo) and (hi is None or hp <= hi):
            return name
    return "iron"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def sign(x):
    return (x > 0) - (x < 0)


def load_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"predict: cannot parse {what} {path}: {e}", file=sys.stderr)
        return None


def load_trace(path):
    trace = load_json(path, "trace")
    if trace is None:
        return None
    for k in ("players", "seasons", "moves", "season_state", "rankings",
              "hp_series", "card_pool", "holdings", "key_cards", "facts",
              "formulas", "rules", "meta_players", "rule_actions",
              "political_record", "trigger_links", "lobby_actions",
              "goal_checks"):
        if k not in trace:
            print(f"predict: trace missing top-level field '{k}'",
                  file=sys.stderr)
            return None
    return trace


def kind_of(m):
    """Semantic kind of a move; falls back to action_kind for traces
    that predate the semantic layer (e.g. the fixture, whose
    action_kind values already are semantic kinds). Same rule as
    backtest.kind_of; keep the two in sync."""
    return m.get("semantic_kind") or m["action_kind"]


# --- feasibility mask (audit fix 5, round 5) -------------------------
def load_feasible_kinds(payoff):
    """The feasible_kinds table from the payoff model. Returns {}
    when the payoff file predates the table: with no table every
    kind is feasible for every player (old behaviour), so old
    payoff files keep working."""
    table = payoff.get("feasible_kinds")
    return table if isinstance(table, dict) else {}


def kind_feasible(kind, pid, player_key, prefix_moves, feasible):
    """True when `kind` is a feasible action for the player with id
    `pid` (key `player_key`), judged on the prefix history
    available at prediction time. A kind absent from the table is
    feasible for every player. An exogenous kind is feasible for
    nobody: it never enters argmax (scenario input only). A listed
    kind is feasible only for its eligible_players (null means not
    applicable as a player action, as for bis_rule). A one_shot
    kind is infeasible for a player once that player already has a
    prefix move of that kind. "unknown" is never feasible here
    (classification gap, not an action); callers already exclude it
    from the kind set, so this is a backstop. This one function is
    the single source of truth for both the mask and the M7
    measurement; M7 is computed from the table and the prefix, not
    by trusting that the mask ran."""
    if kind is None or kind == "unknown":
        return False
    kinds = feasible.get("kinds") or {}
    row = kinds.get(kind)
    if row is None:
        return True
    if row.get("exogenous"):
        return False
    eligible = row.get("eligible_players")
    if eligible is not None and player_key not in eligible:
        return False
    if row.get("one_shot"):
        for m in prefix_moves:
            if kind_of(m) == kind and m.get("player") == pid:
                return False
    return True


def apply_feasibility_mask(candidates, feasible, prefix_moves, pmap):
    """Filter each player's candidate list through the feasible_kinds
    table, judged on the prefix history available at prediction
    time. Returns (filtered, removed) where removed maps pid to the
    kinds taken out of that player's list. Kinds absent from the
    table pass through untouched. Callers apply this before
    best-response dynamics (and before start_actions are filtered
    by candidate membership), so a filtered-out kind can never be
    a start action, a best response, or a modal prediction."""
    filtered, removed = {}, {}
    for pid, kinds in candidates.items():
        key = pmap.get(pid, {}).get("key") if isinstance(pmap, dict) \
            else None
        keep = [k for k in kinds
                if kind_feasible(k, pid, key, prefix_moves, feasible)]
        removed[pid] = [k for k in kinds if k not in keep]
        filtered[pid] = keep
    return filtered, removed


def feasibility_report(first_players, feasible, prefix_moves, pmap):
    """M7 feasibility violation rate (audit fix 5, round 5) over the
    round-1 forecast: the share of players with a modal action
    whose modal kind is infeasible for that player at prediction
    time. M7 must be 0; otherwise the M1-M5 numbers are not
    credible (the model is predicting actions the player cannot
    take). Naming: the audit calls this rate "M6", but M6 is
    already the calibration gap (batch 1, round 3), so this rate
    is M7 and M6 calibration is unchanged. Players with no modal
    action (empty candidate set) are not violations and are not
    in the denominator: no kind was predicted."""
    n_pred = 0
    violations = []
    for row in first_players:
        kind = row.get("modal_action")
        if kind is None:
            continue
        n_pred += 1
        pid = row["player"]
        key = pmap.get(pid, {}).get("key") if isinstance(pmap, dict) \
            else None
        if not kind_feasible(kind, pid, key, prefix_moves, feasible):
            violations.append({
                "player": pid, "key": key, "kind": kind,
                "modal_probability": row.get("modal_probability")})
    rate = (len(violations) / n_pred) if n_pred else 0.0
    return {"m7_violation_rate": round(rate, 6),
            "m7_violations": len(violations),
            "m7_n": n_pred,
            "m7_pass": len(violations) == 0,
            "violations": violations,
            "table_version": feasible.get("version"),
            "note": ("M7 is the share of round-1 modal predictions "
                     "whose kind is infeasible for that player "
                     "(exogenous, outside eligible_players, or a "
                     "one_shot kind the player already did in the "
                     "prefix). Named M7 because the audit's 'M6' "
                     "for this rate collides with the existing M6 "
                     "calibration gap, which is unchanged. M7 must "
                     "be 0; otherwise M1-M5 are not credible.")}


MIN_SUPPORT = 5
SHRINKAGE_K = 5


def _expectation_tables(moves):
    """Raw sums and counts behind expected_deltas / expectation_support.
    Returns {"per": {(pid, kind): [sum_dhp, sum_dgold, n]},
    "kind": {kind: [sum_dhp, sum_dgold, n]},
    "global": [sum_dhp, sum_dgold, n]}. n is the instance count in
    `moves`, the prefix available at prediction time."""
    per = defaultdict(lambda: [0, 0, 0])
    glob = defaultdict(lambda: [0, 0, 0])
    total = [0, 0, 0]
    for m in moves:
        kind = kind_of(m)
        for table, key in ((per, (m["player"], kind)),
                           (glob, kind)):
            s = table[key]
            s[0] += m["hp_delta"]
            s[1] += m["gold_delta"]
            s[2] += 1
        total[0] += m["hp_delta"]
        total[1] += m["gold_delta"]
        total[2] += 1
    return {"per": dict(per), "kind": dict(glob), "global": total}


def _shrink(raw_mean, n, prior_mean):
    """Shrinkage toward the prior mean with k = SHRINKAGE_K:
    (n * raw + k * prior) / (n + k). At n = 0 this is the prior."""
    return ((n * raw_mean[0] + SHRINKAGE_K * prior_mean[0]) / (n + SHRINKAGE_K),
            (n * raw_mean[1] + SHRINKAGE_K * prior_mean[1]) / (n + SHRINKAGE_K))


def expected_deltas(moves):
    """Return (per (player, kind), per kind) mean (dHP, dgold), with
    minimum support and shrinkage (audit fix 4, round 4).

    n is the instance count in `moves`, the prefix available at
    prediction time (the full history for a live forecast, the
    prefix before the test round in a backtest). A mean is used raw
    only when n >= MIN_SUPPORT (5); below that it is shrunk toward
    the coarser level with k = SHRINKAGE_K (5):
      expected = (n * kind_mean + k * global_mean) / (n + k).
    Hierarchy: a (player, kind) cell is shrunk toward its kind mean
    (itself already shrunk toward the global mean when the kind is
    thin); a kind mean is shrunk toward the global mean over all
    prefix moves. A kind with n < 5 therefore can no longer set a
    prediction on its own two observations: v3 (n = 2, raw dHP
    +7.0) shrinks to about +2.3 dHP on the S1-S3 prefix.

    Shrinkage, not exclusion, was chosen: excluding thin kinds
    would delete real (if weak) evidence and shrink the candidate
    set by fiat; shrinkage keeps every kind playable but pulls its
    expectation toward the global mean in proportion to how little
    supports it, so a thin kind must also win on the position term
    to be picked.

    NOT grouped by HP segment or rules version in this round: on
    the S1-S3 prefix, (player, segment, version, kind) cells number
    94 and none reaches n >= 5 (max n = 4), so that grouping could
    never be used raw and would only add shrinkage noise. See
    design/round-4-min-support.md for the counts. The grouping is
    deferred, not silently dropped.

    Same (per_mean, glob_mean) return shape as before, so existing
    callers (fit.py, ensemble.py, backtest.py) keep working and all
    use the shrunk expectations."""
    t = _expectation_tables(moves)
    n_tot = t["global"][2]
    glob_mean = ((t["global"][0] / n_tot, t["global"][1] / n_tot)
                 if n_tot else (0.0, 0.0))
    glob_shrunk = {}
    for kind, v in t["kind"].items():
        raw = (v[0] / v[2], v[1] / v[2])
        glob_shrunk[kind] = (raw if v[2] >= MIN_SUPPORT
                             else _shrink(raw, v[2], glob_mean))
    per_mean = {}
    for (pid, kind), v in t["per"].items():
        raw = (v[0] / v[2], v[1] / v[2])
        per_mean[(pid, kind)] = (raw if v[2] >= MIN_SUPPORT
                                 else _shrink(raw, v[2],
                                              glob_shrunk[kind]))
    return per_mean, glob_shrunk


def expectation_support(moves):
    """Diagnostics for the same tables expected_deltas uses: the
    global mean, and per kind / per (player, kind) cell the instance
    count n and whether its mean was shrunk. JSON-able. Same n
    definition as expected_deltas: count in `moves`, the prefix
    available at prediction time."""
    t = _expectation_tables(moves)
    n_tot = t["global"][2]
    glob_mean = ((t["global"][0] / n_tot, t["global"][1] / n_tot)
                 if n_tot else (0.0, 0.0))
    kinds = {}
    for kind, v in t["kind"].items():
        raw = (v[0] / v[2], v[1] / v[2])
        shrunk = v[2] < MIN_SUPPORT
        kinds[kind] = {
            "n": v[2],
            "raw_mean": [round(raw[0], 4), round(raw[1], 4)],
            "value": [round(x, 4) for x in
                      (_shrink(raw, v[2], glob_mean) if shrunk else raw)],
            "shrunk": shrunk}
    cells = {}
    for (pid, kind), v in t["per"].items():
        cells[f"{pid}|{kind}"] = {"n": v[2],
                                  "shrunk": v[2] < MIN_SUPPORT}
    return {"min_support": MIN_SUPPORT, "shrinkage_k": SHRINKAGE_K,
            "global_mean": [round(glob_mean[0], 4),
                            round(glob_mean[1], 4)],
            "global_n": n_tot, "kinds": kinds, "cells": cells}


def support_lookup(support, pid, kind):
    """(n_kind, n_cell, shrunk) for one (player, kind) lookup against
    an expectation_support() table. shrunk is True when the value
    actually used came from a shrunk cell or a shrunk kind mean.
    A kind never seen in the prefix falls back to the global mean
    (n_kind 0, shrunk True)."""
    kinfo = support["kinds"].get(kind)
    cinfo = support["cells"].get(f"{pid}|{kind}")
    n_kind = kinfo["n"] if kinfo else 0
    n_cell = cinfo["n"] if cinfo else 0
    if cinfo is None and kinfo is None:
        return n_kind, n_cell, True
    if cinfo is not None:
        return n_kind, n_cell, bool(cinfo["shrunk"] or
                                    (kinfo and kinfo["shrunk"]))
    return n_kind, n_cell, bool(kinfo["shrunk"])


def make_expectation(per_mean, glob_mean, global_mean=None):
    """exp(pid, kind) -> (dHP, dgold). per (player, kind) first, then
    per kind, then the fallback. global_mean, when given, is the
    fallback for a kind never seen in the prefix: it is the n = 0
    limit of the shrinkage formula, (0 * kind + k * global) / k.
    When global_mean is None the fallback stays (0.0, 0.0), the old
    behaviour (callers that do not pass it are unaffected)."""
    def exp(pid, kind):
        if (pid, kind) in per_mean:
            return per_mean[(pid, kind)]
        if kind in glob_mean:
            return glob_mean[kind]
        if global_mean is not None:
            return global_mean
        return (0.0, 0.0)
    return exp


def ranks_of(state):
    """state: pid -> (hp, gold). Rank 1 is best (HP desc, gold desc,
    player id asc as deterministic tie-break)."""
    order = sorted(state, key=lambda p: (-state[p][0], -state[p][1], p))
    return {p: i + 1 for i, p in enumerate(order)}


def utility(params, hp_before, hp_after, dhp, dgold, lever, compliance,
            position):
    """v2 utility (payoff-model.json v2, design/fitting-layer.md
    §3-4): u = w_hp * [(hp_after)^alpha - (hp_before)^alpha]
    + w_gold*dgold - c_lever*lever - c_rule*compliance
    + w_pos*position. alpha = params['hp_exponent'] (default 1.0).
    hp_after is the HP after the expected increment, clamped to
    the rule bounds (the caller clamps); hp_before is the
    round-start HP. Gold stays linear. dhp is the caller's
    expected HP increment; when alpha == 1.0 the HP term uses dhp
    verbatim, so v1 is restored bit-exactly: re-deriving it as
    hp_after - hp_before would round (clamped HPs are floats) and
    could flip near-ties in best-response. When alpha != 1.0 the
    power form above is used.
    gamma = params['discount'] is read (default 1.0) but
    deliberately NOT applied: per design §3 it weights fitting
    evidence by recency (decision weight gamma**(R-r)); it does
    not discount future rewards in single-step prediction.
    Multi-step continuation discounting is a future extension."""
    alpha = params.get("hp_exponent", 1.0)
    _gamma = params.get("discount", 1.0)  # fitting recency only; see above
    if alpha == 1.0:
        f_hp = dhp
    else:
        f_hp = hp_after ** alpha - hp_before ** alpha
    return (params["w_hp"] * f_hp + params["w_gold"] * dgold
            - params["c_lever"] * lever - params["c_rule"] * compliance
            + params["w_pos"] * position)


def best_response(state, params, tau, candidates, exp, start_actions,
                  acting, hp_bounds):
    """Best-response dynamics. state: pid -> (hp, gold).
    candidates: pid -> sorted list of kinds. exp: (pid, kind) ->
    (dHP, dgold). acting: players who move this round. Returns a
    dict with actions, distributions, utilities, iterations,
    converged and cycle."""
    floor, cap = hp_bounds
    actions = {}
    for pid in acting:
        cands = candidates.get(pid, [])
        actions[pid] = start_actions.get(pid) or (cands[0] if cands else None)
    base_rank = ranks_of(state)
    converged = False
    iterations = 0
    for it in range(1, 21):
        iterations = it
        changed = False
        for pid in acting:
            others_post = {}
            for q, (hp, gold) in state.items():
                if q in acting and q != pid and actions.get(q):
                    dh, dg = exp(q, actions[q])
                    others_post[q] = (clamp(hp + dh, floor, cap),
                                      gold + dg)
                else:
                    others_post[q] = (hp, gold)
            best_kind, best_u = None, None
            for kind in candidates.get(pid, []):
                dh, dg = exp(pid, kind)
                hp2 = clamp(state[pid][0] + dh, floor, cap)
                gold2 = state[pid][1] + dg
                post = dict(others_post)
                post[pid] = (hp2, gold2)
                r = ranks_of(post)
                pos = base_rank[pid] - r[pid]
                lever = 1 if gold2 < 0 else 0
                u = utility(params, state[pid][0], hp2, dh, dg, lever,
                            0, pos)
                if best_u is None or u > best_u + 1e-12:
                    best_kind, best_u = kind, u
            if best_kind is not None and best_kind != actions[pid]:
                actions[pid] = best_kind
                changed = True
        if not changed:
            converged = True
            break
    # Final-iteration utilities -> softmax distribution per player.
    distributions, utilities, modal = {}, {}, {}
    for pid in acting:
        others_post = {}
        for q, (hp, gold) in state.items():
            if q in acting and q != pid and actions.get(q):
                dh, dg = exp(q, actions[q])
                others_post[q] = (clamp(hp + dh, floor, cap), gold + dg)
            else:
                others_post[q] = (hp, gold)
        utils = {}
        for kind in candidates.get(pid, []):
            dh, dg = exp(pid, kind)
            hp2 = clamp(state[pid][0] + dh, floor, cap)
            gold2 = state[pid][1] + dg
            post = dict(others_post)
            post[pid] = (hp2, gold2)
            r = ranks_of(post)
            utils[kind] = utility(params, state[pid][0], hp2, dh, dg,
                                  1 if gold2 < 0 else 0, 0,
                                  base_rank[pid] - r[pid])
        mx = max(utils.values()) if utils else 0.0
        weights = {k: math.exp((v - mx) / tau) if tau else
                   (1.0 if v == mx else 0.0) for k, v in utils.items()}
        total = sum(weights.values()) or 1.0
        raw_dist = {k: w / total for k, w in weights.items()}
        dist = {k: round(v, 6) for k, v in raw_dist.items()}
        modal_kind = max(dist, key=lambda k: (dist[k], k)) if dist else None
        top3 = round(sum(sorted(raw_dist.values(), reverse=True)[:3]), 6)
        distributions[pid] = dist
        utilities[pid] = {k: round(v, 6) for k, v in utils.items()}
        modal[pid] = {"action": modal_kind,
                      "probability": dist.get(modal_kind, 0.0) if modal_kind
                      else 0.0,
                      "top3_mass": top3}
    return {"actions": actions, "distributions": distributions,
            "utilities": utilities, "modal": modal,
            "iterations": iterations, "converged": converged,
            "cycle": not converged}


# --- applyMove mirror (Dynamics.lean, trace representation) --------
def normalize_move(move, players_by_key):
    """Accept camelCase or snake_case Move fields. Player may be an
    int id or a key string. Return a normalized dict or raise."""
    if not isinstance(move, dict):
        raise ValueError("move is not an object")
    def get(*names):
        for n in names:
            if n in move:
                return move[n]
        raise ValueError(f"move missing field {names[0]}")
    player = get("player")
    if isinstance(player, str):
        p = players_by_key.get(player)
        if p is None:
            raise ValueError(f"move player key unknown: {player!r}")
        player = p["id"]
    if not isinstance(player, int) or isinstance(player, bool):
        raise ValueError("move player must be an int id or a key")
    out = {
        "player": player,
        "date": int(get("date")),
        "season": int(get("season")),
        "action_kind": str(get("actionKind", "action_kind")),
        "hp_delta": int(get("hpDelta", "hp_delta")),
        "gold_delta": int(get("goldDelta", "gold_delta")),
        "liability": bool(get("liability")),
        "rules_version": str(get("rulesVersion", "rules_version")),
    }
    # Optional: keep a semantic kind when the claim carries one, so
    # kind_of() can prefer it over action_kind downstream. Absent
    # for claims written in the semantic vocabulary already (the
    # fixture), where action_kind is the semantic kind.
    sem = move.get("semanticKind", move.get("semantic_kind"))
    if sem:
        out["semantic_kind"] = str(sem)
    return out


def apply_move(rules, state, move):
    """Mirror of Dynamics.applyMove. state: {player, hp, gold,
    elim, liab, rule, date, season}. Returns (new_state, None) on
    success, (None, reason) on an illegal move."""
    base, overlays = check.resolve_rules(rules, move["date"],
                                         move["player"])
    if base is None:
        return None, "no base rule in effect at the move date"
    if move["player"] != state["player"]:
        return None, "move player does not equal state player"
    if state["elim"]:
        return None, "state is eliminated"
    if move["rules_version"] != base["rule_id"]:
        return None, (f"rulesVersion {move['rules_version']} != base "
                      f"rule {base['rule_id']} in effect at the date")
    banned = set(base["params"].get("banned_action_kinds", []))
    for ov in overlays:
        banned |= set(ov["params"].get("banned_action_kinds", []))
    kind = kind_of(move)
    if kind in banned:
        return None, (f"action kind {kind} banned under "
                      f"rule(s) in effect")
    gold2 = state["gold"] + move["gold_delta"]
    if gold2 < 0 and not move["liability"]:
        return None, "gold result negative without liability flag"
    hp2 = clamp(state["hp"] + move["hp_delta"],
                base["params"]["hp_floor"], base["params"]["hp_cap"])
    return {"player": state["player"], "hp": hp2, "gold": gold2,
            "elim": bool(hp2 == 0), "liab": move["liability"],
            "rule": base["rule_id"], "date": move["date"],
            "season": move["season"]}, None


def current_states(trace):
    """Per player: (hp_end, gold_end) of the latest season_state."""
    latest = {}
    for s in trace["season_state"]:
        pid = s["player"]
        if pid not in latest or s["season"] > latest[pid]["season"]:
            latest[pid] = s
    return {pid: (s["hp_end"], s["gold_end"]) for pid, s in latest.items()}


def last_moves(trace):
    """Per player: the last move by (season, round_index)."""
    last = {}
    for m in trace["moves"]:
        pid = m["player"]
        key = (m["season"], m["round_index"])
        if pid not in last or key > (last[pid]["season"],
                                    last[pid]["round_index"]):
            last[pid] = m
    return last


def add_days(date_int, days):
    d = datetime.date(int(str(date_int)[:4]), int(str(date_int)[4:6]),
                      int(str(date_int)[6:8]))
    return int((d + datetime.timedelta(days=days)).strftime("%Y%m%d"))


def build_fork(trace, current, lasts, modal, exp, claim_moves):
    """Build the S+1 fork trace (1 round). modal: pid -> modal kind.
    claim_moves: pid -> normalized move (overrides the modal)."""
    fork = copy.deepcopy(trace)
    last_season = max(s["season"] for s in trace["seasons"])
    new_season = last_season + 1
    last_date = max(m["date"] for m in trace["moves"])
    fork_date = add_days(last_date, 1)
    last_season_row = next(s for s in trace["seasons"]
                           if s["season"] == last_season)
    active = [pid for pid in last_season_row["active_players"]
              if current.get(pid, (0, 0))[0] > 0]
    rules = trace["rules"]
    moves, states = [], []
    for pid in active:
        hp_start, gold_start = current[pid]
        base, _ = check.resolve_rules(rules, fork_date, pid)
        if pid in claim_moves:
            mv = claim_moves[pid]
            kind, dhp, dgold = (kind_of(mv), mv["hp_delta"],
                                mv["gold_delta"])
        else:
            kind = modal[pid]["action"]
            dhp_f, dgold_f = exp(pid, kind)
            dhp, dgold = int(round(dhp_f)), int(round(dgold_f))
        last = lasts.get(pid, {})
        liability = (gold_start + dgold) < 0
        moves.append({
            "season": new_season, "round_index": 1,
            "round_label": f"{new_season}-1", "player": pid,
            "hp_delta": dhp, "gold_delta": dgold, "action_kind": kind,
            "action": kind, "date": fork_date,
            "hp_start": hp_start, "gold_start": gold_start,
            "population": last.get("population", 0),
            "win_streak": last.get("win_streak", 0),
            "roster_stars": last.get("roster_stars", 0),
            "borrowed": last.get("borrowed", 0),
            "liability": liability,
            "rules_version": base["rule_id"] if base else None,
        })
        params = base["params"]
        pen = check.penalty_value(params["leverage_penalty"],
                                  last.get("borrowed", 0))
        cur_hp = clamp(hp_start + dhp, params["hp_floor"],
                       params["hp_cap"])
        cur_gold = gold_start + dgold
        hp_end = (clamp(cur_hp - pen, params["hp_floor"],
                        params["hp_cap"])
                  if params["penalty_applies_to"] == "hp" else cur_hp)
        gold_end = (cur_gold - pen
                    if params["penalty_applies_to"] == "gold" else cur_gold)
        states.append({
            "season": new_season, "player": pid,
            "hp_start": hp_start, "gold_start": gold_start,
            "hp_end": hp_end, "gold_end": gold_end,
            "borrowed": last.get("borrowed", 0), "penalty": pen,
        })
    fork["moves"].extend(moves)
    fork["season_state"].extend(states)
    ranked = sorted(states, key=lambda s: (-s["hp_end"], -s["gold_end"],
                                           s["player"]))
    for i, s in enumerate(ranked):
        fork["rankings"].append({
            "season": new_season, "player": s["player"], "rank": i + 1,
            "hp_end": s["hp_end"], "gold_end": s["gold_end"]})
    for line in fork["hp_series"]:
        pid = line["player"]
        st = next((s for s in states if s["player"] == pid), None)
        if st is not None:
            line["points"] = list(line.get("points", [])) + [st["hp_end"]]
    base0, _ = check.resolve_rules(rules, fork_date, active[0])
    fork["seasons"].append({
        "season": new_season, "name": f"S{new_season}",
        "start_date": fork_date, "end_date": fork_date, "rounds": 1,
        "active_players": active,
        "rules_version": base0["rule_id"] if base0 else None})
    meta = dict(fork.get("meta", {}))
    fork["meta"] = dict(meta)
    fork["meta"]["page_version"] = "fork"
    fork["meta"]["fork_of"] = meta.get("page_version")
    fork["meta"]["fork_season"] = new_season
    fork["meta"]["fork_date"] = fork_date
    info = {"fork_season": new_season, "fork_date": fork_date,
            "rounds": 1, "active_players": active,
            "base_rule": base0["rule_id"] if base0 else None,
            "moves": len(moves)}
    return fork, info


def reverify(fork):
    """check.run on the fork + gen_trace_lean.py + lake build in a
    temp copy of lean/ (the .lake cache is excluded so the build is
    fresh, never vacuous). Returns a dict of both results."""
    out = {"check": {}, "lean": {}}
    try:
        r, coverage = check.run(fork)
        out["check"] = {
            "verdict": ("pass" if not r.failures and not r.gaps
                        else "insufficient_data"
                        if r.gaps and not r.failures else "fail"),
            "passed": len(r.passed), "failures": r.failures,
            "gaps": r.gaps, "coverage": coverage}
    except Exception as e:
        out["check"] = {"verdict": "error", "error": str(e)}
    try:
        tmp = Path(tempfile.mkdtemp(prefix="predict-lean-"))
        lean_tmp = tmp / "lean"
        shutil.copytree(HERE / "lean", lean_tmp,
                        ignore=shutil.ignore_patterns(".lake"))
        fork_path = tmp / "fork-trace.json"
        fork_path.write_text(json.dumps(fork, ensure_ascii=False),
                             encoding="utf-8")
        env = dict(os.environ)
        env["PATH"] = (str(Path.home() / ".elan" / "bin") + os.pathsep
                       + env.get("PATH", ""))
        gen = subprocess.run(
            [sys.executable, str(HERE / "gen_trace_lean.py"),
             str(fork_path), "--out",
             str(lean_tmp / "Verification" / "Trace.lean")],
            capture_output=True, text=True, timeout=300, env=env)
        build = None
        log_tail = ""
        if gen.returncode == 0:
            build = subprocess.run(
                ["lake", "build"], cwd=str(lean_tmp),
                capture_output=True, text=True, timeout=900, env=env)
            log_tail = (build.stdout + build.stderr)[-2000:]
        else:
            log_tail = (gen.stdout + gen.stderr)[-2000:]
        olean = lean_tmp / ".lake" / "build" / "lib" / "lean" / \
            "Verification" / "Proofs.olean"
        src = lean_tmp / "Verification" / "Proofs.lean"
        fresh = bool(olean.exists() and src.exists()
                     and olean.stat().st_mtime > src.stat().st_mtime)
        lean_ok = (gen.returncode == 0 and build is not None
                   and build.returncode == 0 and fresh)
        out["lean"] = {
            "status": "pass" if lean_ok else "fail",
            "gen_exit": gen.returncode,
            "build_exit": build.returncode if build is not None else None,
            "olean_fresh": fresh,
            "temp_dir": str(tmp),
            "log_tail": log_tail,
            "note": (".lake cache excluded from the temp copy so the "
                     "build is fresh, never vacuous."),
        }
    except Exception as e:
        out["lean"] = {"status": "error", "error": str(e)}
    return out


def confidence_tier(round_no):
    if round_no == 1:
        return "high"
    if 2 <= round_no <= 7:
        return "medium"
    return "low"


DEGENERACY_THRESHOLD = 0.5


def degeneracy_metrics(first_players):
    """Degeneracy of the round-1 forecast distribution (audit fix 3,
    round 3). degeneracy_rate is the share of players whose modal
    action probability is exactly 1.0; the run is degenerate when
    that share exceeds DEGENERACY_THRESHOLD (0.5). Distribution
    entropy is the Shannon entropy (bits) of the modal-action
    distribution across players: 0.0 bits when every player shares
    one modal action. Players with no modal action (no candidates)
    are excluded from the action counts but still count in the
    denominator (their modal probability is 0.0, never degenerate).
    A degenerate forecast asserts certainty while the backtest
    shows the same kind of modal claim hits ~0% of the time; see
    backtest.py calibration (M6)."""
    n = len(first_players)
    if n == 0:
        return {"degeneracy_rate": 0.0, "degenerate_players": 0,
                "players_total": 0, "degenerate": False,
                "threshold": DEGENERACY_THRESHOLD,
                "modal_action_entropy_bits": 0.0,
                "modal_action_counts": {}}
    deg = sum(1 for r in first_players
              if r.get("modal_probability") == 1.0)
    counts = {}
    for r in first_players:
        a = r.get("modal_action")
        if a is not None:
            counts[a] = counts.get(a, 0) + 1
    entropy = 0.0
    for c in counts.values():
        p = c / n
        entropy -= p * math.log2(p)
    rate = deg / n
    return {"degeneracy_rate": round(rate, 6),
            "degenerate_players": deg,
            "players_total": n,
            "degenerate": rate > DEGENERACY_THRESHOLD,
            "threshold": DEGENERACY_THRESHOLD,
            "modal_action_entropy_bits": round(entropy, 6),
            "modal_action_counts": counts}


# --- rule scenarios (rules/scenarios.json) --------------------------
def load_scenarios(path):
    """Load and validate a scenarios file. Returns the doc or None
    (with an error printed). A trigger probability must be null:
    no data supports any trigger probability, and an invented
    probability would enter the model as an input. A non-null
    probability is accepted only with an explicit
    probability_assumption label."""
    doc = load_json(path, "scenarios")
    if doc is None:
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("scenarios"),
                                                    list):
        print("predict: scenarios file must hold {'scenarios': [...]}",
              file=sys.stderr)
        return None
    seen = set()
    for sc in doc["scenarios"]:
        if not isinstance(sc, dict):
            print("predict: scenario is not an object", file=sys.stderr)
            return None
        sid = sc.get("id")
        if not sid or sid in seen:
            print(f"predict: scenario id missing or duplicate: {sid!r}",
                  file=sys.stderr)
            return None
        seen.add(sid)
        if sc.get("trigger_probability") is not None and not sc.get(
                "probability_assumption"):
            print(f"predict: scenario {sid} has a trigger probability "
                  "without an explicit assumption label; refusing to "
                  "invent one", file=sys.stderr)
            return None
        delta = sc.get("rule_delta")
        if not isinstance(delta, dict):
            print(f"predict: scenario {sid} has no rule_delta",
                  file=sys.stderr)
            return None
        for k in ("banned_action_kinds_add", "banned_action_kinds_remove"):
            if not isinstance(delta.get(k, []), list):
                print(f"predict: scenario {sid} rule_delta.{k} is not "
                      "a list", file=sys.stderr)
                return None
        for k in ("hp_floor", "hp_cap"):
            v = delta.get(k)
            if v is not None and (not isinstance(v, int)
                                  or isinstance(v, bool)):
                print(f"predict: scenario {sid} rule_delta.{k} is not "
                      "an int or null", file=sys.stderr)
                return None
        if not isinstance(delta.get("overlays_add", []), list):
            print(f"predict: scenario {sid} rule_delta.overlays_add "
                  "is not a list", file=sys.stderr)
            return None
    return doc


def apply_scenario_rules(rules, scenario, base_rule_id, current_date,
                         players_by_key):
    """Deep-copy the rule set and apply one scenario's delta to the
    base rule in effect (rule_id base_rule_id). Returns
    (scenario_rules, applied) where applied records what changed.
    Overlays in rule_delta.overlays_add are appended as
    player-specific rules ({players: [keys], banned_action_kinds:
    [...]}), effective from current_date; an overlay only adds
    banned kinds for those players (HP bounds still come from the
    base rule, as in apply_move)."""
    srules = copy.deepcopy(rules)
    base = next((r for r in srules if r["rule_id"] == base_rule_id
                 and r.get("applies_to_players") is None), None)
    if base is None:
        raise ValueError(f"base rule {base_rule_id} not found")
    delta = scenario.get("rule_delta", {})
    params = base["params"]
    banned = set(params.get("banned_action_kinds", []))
    added = [k for k in delta.get("banned_action_kinds_add", [])
             if k not in banned]
    removed = [k for k in delta.get("banned_action_kinds_remove", [])
               if k in banned]
    banned |= set(added)
    banned -= set(removed)
    params["banned_action_kinds"] = sorted(banned)
    floor_before, cap_before = params["hp_floor"], params["hp_cap"]
    if delta.get("hp_floor") is not None:
        params["hp_floor"] = delta["hp_floor"]
    if delta.get("hp_cap") is not None:
        params["hp_cap"] = delta["hp_cap"]
    overlays = []
    for i, ov in enumerate(delta.get("overlays_add", [])):
        pids = []
        for key in ov.get("players", []):
            p = players_by_key.get(key)
            if p is None:
                raise ValueError(f"overlay player key unknown: {key!r}")
            pids.append(p["id"])
        orule = {
            "rule_id": f"{scenario['id']}-OV-{i+1}",
            "name": ov.get("name", f"{scenario['id']} overlay {i+1}"),
            "version": scenario["id"],
            "effective_from": ov.get("effective_from", current_date),
            "effective_to": ov.get("effective_to"),
            "applies_to_players": sorted(pids),
            "trigger": scenario.get("name"),
            "trigger_type": "scenario_overlay",
            "params": dict(params, banned_action_kinds=sorted(
                set(ov.get("banned_action_kinds", [])))),
        }
        srules.append(orule)
        overlays.append(orule["rule_id"])
    applied = {
        "base_rule_id": base_rule_id,
        "scenario_rule_id": f"{base_rule_id}+{scenario['id']}",
        "banned_action_kinds_added": added,
        "banned_action_kinds_removed": removed,
        "banned_action_kinds_effective": sorted(banned),
        "hp_floor": [floor_before, params["hp_floor"]],
        "hp_cap": [cap_before, params["hp_cap"]],
        "overlays_added": overlays,
    }
    return srules, applied


def forecast_rounds(state, params, tau, candidates, exp, start_actions,
                    acting, hp_bounds, horizon, cap_rounds, pmap):
    """Best-response dynamics, round by round. Shared by the
    baseline run and the per-scenario runs. Returns (forecast,
    effective_horizon). Forecast rows carry the round, the
    round-tiered confidence, convergence, and per-player
    distributions / modal actions / expected deltas."""
    effective_horizon = min(horizon, cap_rounds)
    forecast = []
    round_state = dict(state)
    round_start = dict(start_actions)
    acting_now = list(acting)
    for rnd in range(1, effective_horizon + 1):
        res = best_response(round_state, params, tau, candidates, exp,
                            round_start, acting_now, hp_bounds)
        forecast.append({
            "round": rnd, "confidence": confidence_tier(rnd),
            "iterations": res["iterations"],
            "converged": res["converged"], "cycle": res["cycle"],
            "players": [{
                "player": pid, "key": pmap[pid].get("key"),
                "name": pmap[pid].get("name"),
                "distribution": res["distributions"].get(pid, {}),
                "modal_action": res["modal"][pid]["action"],
                "modal_probability": res["modal"][pid]["probability"],
                "top3_mass": res["modal"][pid]["top3_mass"],
                "expected_delta": list(exp(pid, res["modal"][pid]["action"]))
                if res["modal"][pid]["action"] else [0.0, 0.0],
            } for pid in acting_now]})
        if rnd < effective_horizon:
            nxt = {}
            for pid in round_state:
                if pid in acting_now and res["modal"][pid]["action"]:
                    dh, dg = exp(pid, res["modal"][pid]["action"])
                    hp2 = clamp(round_state[pid][0] + dh, *hp_bounds)
                    nxt[pid] = (hp2, round_state[pid][1] + dg)
                else:
                    nxt[pid] = round_state[pid]
            round_state = nxt
            round_start = dict(res["actions"])
            acting_now = sorted(pid for pid in acting_now
                                if round_state[pid][0] > 0)
    return forecast, effective_horizon


def run_scenarios(scenarios_doc, trace, params, tau, state, exp,
                  start_actions, acting, cap_rounds, horizon, pmap,
                  players_by_key, rules, max_date, base_rule_id,
                  base_first, feasible=None):
    """Best-response dynamics under each rule scenario. Returns
    {"scenarios": [...], "comparison": {...}}. Shared inputs (state,
    expectations, start actions) come from the baseline run; only
    the candidate sets and HP bounds change per scenario. No trigger
    probability is assigned anywhere: scenarios are conditional
    branches, not a distribution. The feasibility mask (audit fix 5)
    applies inside each scenario run too, judged on the full
    history, before start actions are filtered by candidate
    membership."""
    # "unknown" is a classification gap, not an action a player can
    # take; it is excluded from the candidate set (same rule as
    # backtest.py: candidates = prefix kinds - {"unknown"}), so it
    # cannot absorb softmax probability mass.
    all_kinds = sorted({kind_of(m) for m in trace["moves"]} - {"unknown"})
    base_modal = {row["player"]: row["modal_action"]
                  for row in base_first}
    base_dist = {row["player"]: row["distribution"]
                 for row in base_first}
    base_id = scenarios_doc.get("base_scenario_id", "SC-BASE")
    runs = []
    for sc in scenarios_doc["scenarios"]:
        srules, applied = apply_scenario_rules(
            rules, sc, base_rule_id, max_date, players_by_key)
        candidates = {}
        for p in trace["players"]:
            pid = p["id"]
            base, overlays = check.resolve_rules(srules, max_date, pid)
            banned = set(base["params"].get("banned_action_kinds", []))
            for ov in overlays:
                banned |= set(ov["params"].get("banned_action_kinds", []))
            candidates[pid] = [k for k in all_kinds if k not in banned]
        candidates, _scenario_mask = apply_feasibility_mask(
            candidates, feasible or {}, trace["moves"], pmap)
        hp_bounds = (applied["hp_floor"][1], applied["hp_cap"][1])
        s_start = {pid: a for pid, a in start_actions.items()
                   if a in candidates.get(pid, [])}
        forecast, effective = forecast_rounds(
            state, params, tau, candidates, exp, s_start, acting,
            hp_bounds, horizon, cap_rounds, pmap)
        changed, max_shift = [], 0.0
        if forecast:
            for row in forecast[0]["players"]:
                pid = row["player"]
                if row["modal_action"] != base_modal.get(pid):
                    changed.append(pid)
                bd = base_dist.get(pid, {})
                for k in set(bd) | set(row["distribution"]):
                    d = abs(row["distribution"].get(k, 0.0)
                            - bd.get(k, 0.0))
                    if d > max_shift:
                        max_shift = d
        is_base = sc["id"] == base_id
        # Observable bound check: apply the round-1 modal actions to
        # the current state under this scenario's HP bounds and
        # record the resulting HPs. A bound that never bites is
        # reported as such (it still ran; it just did not change any
        # modal action on this trace).
        post_hp, clamped = {}, []
        if forecast:
            for row in forecast[0]["players"]:
                pid = row["player"]
                if row["modal_action"]:
                    dh, _dg = exp(pid, row["modal_action"])
                    raw = state[pid][0] + dh
                    hp2 = clamp(raw, *hp_bounds)
                    post_hp[pmap[pid].get("key")] = hp2
                    if hp2 != raw:
                        clamped.append(pmap[pid].get("key"))
        runs.append({
            "id": sc["id"], "name": sc["name"],
            "name_en": sc.get("name_en"),
            "trigger": sc.get("trigger", {}),
            "watchlist_ids": sc.get("trigger", {}).get("watchlist_ids",
                                                        []),
            "justification": sc.get("justification"),
            "trigger_probability": sc.get("trigger_probability"),
            "probability_note": sc.get("probability_note"),
            "rule_delta_applied": applied,
            "confidence": "baseline" if is_base else "conditional",
            "confidence_note": (
                "Baseline branch: no rule change assumed. Round "
                "confidence tiers follow the design (round 1 high, "
                "rounds 2-7 medium, further low); the branch itself "
                "carries no trigger probability."
                if is_base else
                "Conditional branch: the forecast holds only if the "
                "trigger fires. No trigger probability is assigned "
                "(no data); the branch is not a probability weight. "
                "Round confidence tiers as in the design."),
            "effective_horizon": effective,
            "forecast_rounds": forecast,
            "hp_after_round1": {
                "hp": post_hp, "clamped_players": clamped,
                "max_hp": max(post_hp.values()) if post_hp else None},
            "modal_changes_vs_baseline": {
                "count": len(changed),
                "players": [pmap[pid].get("key") for pid in changed]},
            "max_distribution_shift_vs_baseline": round(max_shift, 6),
        })
    comparison = {"players": [], "modal_change_counts": {}}
    for pid in sorted(pmap):
        row = {"player": pid, "key": pmap[pid].get("key"),
               "name": pmap[pid].get("name"), "modal_by_scenario": {},
               "changed_across_scenarios": False}
        seen = set()
        for run in runs:
            f0 = run["forecast_rounds"][0] \
                if run["forecast_rounds"] else None
            m = None
            if f0 is not None:
                prow = next((r for r in f0["players"]
                             if r["player"] == pid), None)
                m = prow["modal_action"] if prow else None
            row["modal_by_scenario"][run["id"]] = m
            seen.add(m)
        row["changed_across_scenarios"] = len(seen) > 1
        comparison["players"].append(row)
    for run in runs:
        comparison["modal_change_counts"][run["id"]] = \
            run["modal_changes_vs_baseline"]["count"]
    return {"scenarios": runs, "comparison": comparison}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prediction runner.")
    ap.add_argument("trace")
    ap.add_argument("--payoff", required=True)
    ap.add_argument("--horizon", type=int, default=1)
    ap.add_argument("--claims", default=None)
    ap.add_argument("--gate-report", default=None)
    ap.add_argument("--backtest-report", default=None)
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--scenarios-out", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--summary", default=None)
    args = ap.parse_args(argv)

    if args.horizon < 1:
        print("predict: --horizon must be >= 1", file=sys.stderr)
        return 2
    trace = load_trace(args.trace)
    if trace is None:
        return 2
    payoff = load_json(args.payoff, "payoff model")
    if payoff is None or "parameters" not in payoff:
        print("predict: bad payoff model file", file=sys.stderr)
        return 2
    params = {k: v["value"] for k, v in payoff["parameters"].items()}
    tau = params.get("temperature", 1.0)
    type_of = {p["key"]: p["type"] for p in payoff.get("players", [])}
    players = trace["players"]
    pmap = {p["id"]: p for p in players}
    players_by_key = {p["key"]: p for p in players}
    rules = trace["rules"]
    moves = trace["moves"]
    if not moves or not players:
        print("predict: trace has no moves or no players", file=sys.stderr)
        return 2

    max_date = max(m["date"] for m in moves)
    base_now, _ = check.resolve_rules(rules, max_date, players[0]["id"])
    if base_now is None:
        print("predict: no base rule in effect at the latest date",
              file=sys.stderr)
        return 2
    hp_bounds = (base_now["params"]["hp_floor"],
                 base_now["params"]["hp_cap"])
    current = current_states(trace)
    lasts = last_moves(trace)
    # "unknown" excluded: classification gap, not a playable kind
    # (same rule as backtest.py). Candidates below derive from this
    # set, so start_actions (filtered by candidates membership)
    # can never hold an "unknown" start either.
    all_kinds = sorted({kind_of(m) for m in moves} - {"unknown"})
    candidates = {}
    for p in players:
        pid = p["id"]
        _, overlays = check.resolve_rules(rules, max_date, pid)
        banned = set(base_now["params"].get("banned_action_kinds", []))
        for ov in overlays:
            banned |= set(ov["params"].get("banned_action_kinds", []))
        candidates[pid] = [k for k in all_kinds if k not in banned]
    # Feasibility mask (audit fix 5, round 5): filter before
    # best-response dynamics, judged on the full history (the live
    # prefix). start_actions below is filtered by candidate
    # membership, so a masked-out kind can never be a start action.
    feasible = load_feasible_kinds(payoff)
    candidates, mask_removed = apply_feasibility_mask(
        candidates, feasible, moves, pmap)
    per_mean, glob_mean = expected_deltas(moves)
    support = expectation_support(moves)
    exp = make_expectation(per_mean, glob_mean,
                           global_mean=tuple(support["global_mean"]))
    start_actions = {pid: kind_of(lasts[pid])
                     for pid in lasts if kind_of(lasts[pid])
                     in candidates.get(pid, [])}
    acting = sorted(pid for pid in pmap if current.get(pid, (0, 0))[0] > 0)
    state = {pid: current[pid] for pid in pmap}

    # --- best-response dynamics, round by round ----------------------
    cap_rounds = max(s["rounds"] for s in trace["seasons"])
    effective_horizon = min(args.horizon, cap_rounds)
    beyond = None
    if args.horizon > cap_rounds:
        beyond = {
            "requested_horizon": args.horizon,
            "cap_rounds_one_season": cap_rounds,
            "conclusion": ("Beyond one season no per-round actions "
                           "are given. Only a symbolic reachable-set "
                           "conclusion applies (see symbolic.py): the "
                           "reachable set is the attractor set of the "
                           "symbolic transfer graph under the rule "
                           "version in effect; confidence low."),
            "confidence": "low"}
    forecast, effective_horizon = forecast_rounds(
        state, params, tau, candidates, exp, start_actions, acting,
        hp_bounds, args.horizon, cap_rounds, pmap)
    first = forecast[0]
    modal = {row["player"]: {"action": row["modal_action"]}
             for row in first["players"]}
    # Degeneracy guard (audit fix 3, round 3): how much of the
    # round-1 forecast collapses onto p = 1.0 modal actions, and how
    # concentrated the modal actions are across players.
    degeneracy = degeneracy_metrics(first["players"])
    # Feasibility (audit fix 5, round 5): M7 over the round-1 modal
    # predictions, judged on the full history. mask_removed lists
    # the kinds the mask took out of each player's candidate set.
    feasibility = feasibility_report(first["players"], feasible, moves,
                                     pmap)
    feasibility["mask_removed"] = {
        pmap[pid].get("key"): kinds for pid, kinds in
        mask_removed.items() if kinds}
    # Expectation diagnostics (audit fix 4, round 4): how many of
    # the round-1 modal predictions rest on a shrunk expectation
    # (thin cell or thin kind, n < 5) rather than a raw mean, and
    # the instance count behind each predicted kind.
    exp_round1 = {"n_players": len(first["players"]),
                  "shrunk_predictions": 0, "fallback_to_global": 0,
                  "per_kind_n": {}}
    for row in first["players"]:
        kind = row["modal_action"]
        if kind is None:
            continue
        n_kind, _n_cell, shrunk = support_lookup(support, row["player"],
                                                 kind)
        if shrunk:
            exp_round1["shrunk_predictions"] += 1
        if kind not in support["kinds"]:
            exp_round1["fallback_to_global"] += 1
        exp_round1["per_kind_n"][kind] = n_kind
    exp_round1["shrunk_share"] = round(
        exp_round1["shrunk_predictions"] / exp_round1["n_players"], 4) \
        if exp_round1["n_players"] else 0.0
    expectation_diag = {
        "min_support": MIN_SUPPORT, "shrinkage_k": SHRINKAGE_K,
        "method": ("n < 5: shrink toward the coarser mean, "
                   "expected = (n * kind_mean + k * global_mean) "
                   "/ (n + k), k = 5; n >= 5: raw mean"),
        "global_mean": support["global_mean"],
        "global_n": support["global_n"],
        "kinds": support["kinds"],
        "round1": exp_round1}

    # --- rule scenarios -----------------------------------------------
    scenarios_output = None
    scenarios_out_path = None
    if args.scenarios:
        scenarios_doc = load_scenarios(args.scenarios)
        if scenarios_doc is None:
            return 2
        # Validate banned kinds against the trace kind set (typo
        # guard: a kind that never appears in the trace cannot be
        # pruned from any candidate set).
        for sc in scenarios_doc["scenarios"]:
            delta = sc.get("rule_delta", {})
            for k in (delta.get("banned_action_kinds_add", [])
                      + delta.get("banned_action_kinds_remove", [])):
                if k not in all_kinds:
                    print(f"predict: scenario {sc['id']} bans unknown "
                          f"kind {k!r} (not in the trace kind set)",
                          file=sys.stderr)
                    return 2
        body = run_scenarios(
            scenarios_doc, trace, params, tau, state, exp, start_actions,
            acting, cap_rounds, args.horizon, pmap, players_by_key,
            rules, max_date, base_now["rule_id"], first["players"],
            feasible)
        scenarios_output = {
            "version": 1,
            "trace": args.trace,
            "payoff_model": {"version": payoff.get("version"),
                             "utility_form": payoff.get("utility_form")},
            "horizon": args.horizon,
            "base_rule": base_now["rule_id"],
            "current_date": max_date,
            "scenarios_file": args.scenarios,
            "base_scenario_id": scenarios_doc.get("base_scenario_id",
                                                  "SC-BASE"),
            "calibration_status": "placeholder_only",
            "smoke_test_note": SMOKE_NOTE,
            "trigger_probability_note": (
                "No scenario trigger probability is assigned anywhere: "
                "no data supports any trigger probability. Scenarios "
                "are conditional branches, not a probability "
                "distribution."),
            **body,
        }
        scenarios_out_path = args.scenarios_out
        if scenarios_out_path is None:
            scenarios_out_path = (
                str(Path(args.out).parent / "scenarios-report.json")
                if args.out else "scenarios-report.json")
        Path(scenarios_out_path).write_text(
            json.dumps(scenarios_output, ensure_ascii=False, indent=2),
            encoding="utf-8")

    # --- agent claims -------------------------------------------------
    applied_claims = []
    claim_moves = {}
    gate_verdicts = {}
    gate_note = None
    if args.gate_report:
        gate = load_json(args.gate_report, "gate report")
        if gate is None:
            return 2
        for c in gate.get("claims", []):
            gate_verdicts[c.get("claim_id")] = c.get("verdict")
    if args.claims:
        claims_doc = load_json(args.claims, "claims")
        if claims_doc is None:
            return 2
        claims = (claims_doc.get("claims") if isinstance(claims_doc, dict)
                  else claims_doc)
        if not isinstance(claims, list):
            print("predict: claims file must hold a list or "
                  "{'claims': [...]}", file=sys.stderr)
            return 2
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if claim.get("kind") != "propose_action":
                continue
            cid = claim.get("claim_id")
            move = claim.get("move")
            if move is None:
                continue
            if args.gate_report:
                gv = gate_verdicts.get(cid)
                if gv != "pass":
                    applied_claims.append({
                        "claim_id": cid, "result": "skipped_gate",
                        "reason": f"gate verdict is {gv!r}, not 'pass'"})
                    continue
            else:
                gate_note = ("No --gate-report given: propose_action "
                             "claims were applied ungated; this is a "
                             "smoke-test path only.")
            try:
                mv = normalize_move(move, players_by_key)
            except ValueError as e:
                applied_claims.append({
                    "claim_id": cid, "result": "refuted_by_transition",
                    "reason": f"move does not parse: {e}"})
                continue
            pid = mv["player"]
            if pid in claim_moves:
                applied_claims.append({
                    "claim_id": cid, "player": pid,
                    "result": "skipped_gate",
                    "reason": "another applied claim already covers "
                              "this player"})
                continue
            st = {"player": pid, "hp": current[pid][0],
                  "gold": current[pid][1],
                  "elim": current[pid][0] == 0, "liab": False,
                  "rule": base_now["rule_id"], "date": max_date,
                  "season": max(s["season"] for s in trace["seasons"])}
            new_state, reason = apply_move(rules, st, mv)
            if new_state is None:
                applied_claims.append({
                    "claim_id": cid, "player": pid, "move": mv,
                    "result": "refuted_by_transition",
                    "reason": "被转移关系反驳: " + reason})
            else:
                claim_moves[pid] = mv
                applied_claims.append({
                    "claim_id": cid, "player": pid, "move": mv,
                    "result": "applied",
                    "new_state": new_state,
                    "reason": "applyMove returned a state"})

    # --- fork + re-verification ---------------------------------------
    fork, fork_info = build_fork(trace, current, lasts, modal, exp,
                                 claim_moves)
    reverify_result = reverify(fork)

    # --- backtest threshold (only when a report is supplied) ----------
    backtest_below = False
    backtest_note = None
    if args.backtest_report:
        bt = load_json(args.backtest_report, "backtest report")
        if bt is None:
            return 2
        backtest_below = (bt.get("threshold_verdict") == "below_threshold"
                          or bool(bt.get("below_threshold")))
        backtest_note = (f"backtest threshold_verdict="
                         f"{bt.get('threshold_verdict')}")
    any_refuted = any(c["result"] == "refuted_by_transition"
                      for c in applied_claims)
    check_bad = reverify_result["check"].get("verdict") != "pass"
    lean_bad = reverify_result["lean"].get("status") != "pass"
    verdict = ("fail" if (any_refuted or check_bad or lean_bad
                          or backtest_below) else "pass")

    assumptions = list(payoff.get("assumptions", []))
    report = {
        "trace": args.trace,
        "payoff_model": {"version": payoff.get("version"),
                         "utility_form": payoff.get("utility_form")},
        "horizon": args.horizon,
        "horizon_default": payoff.get("thresholds", {}).get(
            "horizon_default", 1),
        "effective_horizon": effective_horizon,
        "horizon_cap_one_season_rounds": cap_rounds,
        "beyond_horizon": beyond,
        "current_rule": base_now["rule_id"],
        "current_date": max_date,
        "players": [{
            "player": row["player"], "key": row["key"],
            "name": row["name"],
            "type": type_of.get(row["key"]),
            "current_hp": current[row["player"]][0],
            "current_gold": current[row["player"]][1],
            "distribution": row["distribution"],
            "modal_action": row["modal_action"],
            "modal_probability": row["modal_probability"],
            "top3_mass": row["top3_mass"],
            "expected_delta_modal": row["expected_delta"],
        } for row in first["players"]],
        "forecast_rounds": forecast,
        "degeneracy": degeneracy,
        "feasibility": feasibility,
        "expectation": expectation_diag,
        "best_response": {"iterations": first["iterations"],
                          "converged": first["converged"],
                          "cycle": first["cycle"]},
        "assumptions": assumptions,
        "assumption_note": ASSUMPTION_NOTE,
        "calibration_status": "placeholder_only",
        "smoke_test_note": SMOKE_NOTE,
        "applied_claims": applied_claims,
        "gate_note": gate_note,
        "fork": fork_info,
        "reverification": reverify_result,
        "backtest": {"report": args.backtest_report,
                     "below_threshold": backtest_below,
                     "note": backtest_note},
        "verdict": verdict,
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8")
    lines = [
        f"predict: verdict={verdict} horizon={args.horizon} "
        f"effective={effective_horizon} rule={base_now['rule_id']} "
        f"converged={first['converged']} iterations={first['iterations']}",
        f"predict: degeneracy_rate={degeneracy['degeneracy_rate']} "
        f"({degeneracy['degenerate_players']}/"
        f"{degeneracy['players_total']} players p=1.0) "
        f"degenerate={degeneracy['degenerate']} "
        f"modal_action_entropy_bits="
        f"{degeneracy['modal_action_entropy_bits']}",
        f"predict: feasibility M7={feasibility['m7_violation_rate']} "
        f"({feasibility['m7_violations']}/{feasibility['m7_n']} "
        f"violations) pass={feasibility['m7_pass']} "
        f"mask_removed={feasibility['mask_removed']}",
        f"predict: expectation min_support={MIN_SUPPORT} k="
        f"{SHRINKAGE_K} shrunk_predictions="
        f"{exp_round1['shrunk_predictions']}/"
        f"{exp_round1['n_players']} "
        f"(share={exp_round1['shrunk_share']}) per_kind_n="
        f"{exp_round1['per_kind_n']}",
        f"predict: {SMOKE_NOTE}",
    ]
    for row in first["players"]:
        lines.append(
            f"  {row['key']} modal={row['modal_action']} "
            f"p={row['modal_probability']} top3={row['top3_mass']}")
    for c in applied_claims:
        lines.append(f"  claim {c.get('claim_id')}: {c['result']} "
                     f"{c.get('reason', '')}")
    if scenarios_output is not None:
        lines.append(f"predict: scenarios -> {scenarios_out_path}")
        for run in scenarios_output["scenarios"]:
            lines.append(
                f"  scenario {run['id']}: confidence={run['confidence']} "
                f"modal_changes_vs_baseline="
                f"{run['modal_changes_vs_baseline']['count']} "
                f"max_shift="
                f"{run['max_distribution_shift_vs_baseline']}")
    lines.append(
        f"predict: reverify check="
        f"{reverify_result['check'].get('verdict')} lean="
        f"{reverify_result['lean'].get('status')}")
    if backtest_note:
        lines.append(f"predict: {backtest_note}")
    summary = "\n".join(lines)
    print(summary)
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
