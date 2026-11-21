#!/usr/bin/env python3
"""Fitting layer: revealed-preference / max-margin estimation of the
payoff-model weights (average structured perceptron).

Method (design/fitting-layer.md):
  * One decision per player present in a round, inside the fit
    window. The state is chained from the trace prefix before that
    round only (backtest.chain_state: no future information).
  * Candidate kinds are the semantic kinds seen in the prefix,
    minus the kinds banned at that date (same aperture as
    backtest.py). kind_of() reads semantic_kind, falling back to
    action_kind for traces that predate the semantic layer (e.g.
    the fixture). "unknown" is a classification gap, not an
    action: it is excluded from the candidate set.
  * A move whose recorded kind is "unknown" is not a decision:
    its true kind is unknown, so it carries no supervision
    signal. It still folds into the state chain normally
    (chain_state never reads kinds) and its unknown-kind mean
    still enters the expectations of others fixed on it.
  * Expected increments exp(pid, kind) come from the prefix only
    (predict.expected_deltas / make_expectation).
  * Others are held fixed on their recorded kinds (their expected
    increments); player i tries candidate kind k. Features, with
    ranks from predict.ranks_of:
        f_hp(a)    = (hp_after)^a - (hp_before)^a   (a = 1 gives dHP,
                     exactly v1; hp_after is clamped to the rule
                     bounds in effect at the move date)
        f_gold     = dgold
        f_lever    = 1 when gold_after < 0, else 0
        f_rule     = 0 (compliance cost is 0 for every legal kind
                     in this version)
        f_pos      = rank_before - rank_after
    The utility is linear in phi = (f_hp, f_gold, -f_lever,
    -f_rule, f_pos), so u = w . phi with
    w = (w_hp, w_gold, c_lever, c_rule, w_pos). The minus signs
    on the two penalty features are folded into phi: the
    perceptron update w += eta * weight * (phi(k*) - phi(k_pred))
    is then the ordinary margin-ascent step. (A literal update on
    the raw f vector would push c_lever the wrong way.)
  * Perceptron: init at the placeholder weights (1, 1, 5, 10, 1),
    eta = 0.1, 30 epochs in time order. On a mistake the weights
    move by eta * decision_weight * (phi(k*) - phi(k_pred));
    negative components are clipped to 0 after each update; at
    the end of each epoch w is normalised to unit L2 norm (scale
    is fixed: multiplying a utility by a positive number does not
    change argmax). The reported weights are the epoch-averaged
    weights (average of the 30 end-of-epoch normalised vectors),
    renormalised to unit L2 norm.
  * Discount gamma: decision weight = gamma ** (R - r), where r
    is the decision's global round order (across seasons, from 0)
    and R is the last round order in the fit window. Recent
    evidence weighs more; gamma = 1.0 is equal weighting.
  * Grid search over alpha in {0.25, 0.5, 0.75, 1.0} and gamma in
    {0.90, 0.95, 0.98, 1.0}: the lowest (discount-weighted)
    violation rate wins (violation = recorded kind is not the
    argmax); ties go towards alpha = 1, gamma = 1 (simpler model).
  * Temperature tau: after the weights are fixed, softmax maximum
    likelihood over tau in {0.25, 0.5, 1, 2, 4, 8} (weighted
    log-likelihood of the recorded kind).
  * Uncertainty: bootstrap B = 50, resampling whole rounds
    (keeps within-round correlation), (alpha, gamma) fixed at the
    selected values, refitting w and tau each time.
  * One fit per player type (five types) plus one shared
    all-seats fit as a reference. A separate v1 projection is
    fitted with alpha = 1, gamma = 1 fixed, by the same
    perceptron flow: those are the weights predict.py /
    backtest.py (v1 linear utility) can use directly. v2 weights
    with alpha != 1 cannot be substituted into the v1 linear
    form, so the two are kept apart.
  * The first round of the trace has an empty prefix (no expected
    increments, no candidate kinds): its decisions carry no
    information and are excluded, as in backtest.py.
  * A recorded kind that is banned at its date (so not among the
    candidates) counts as a violation and takes no perceptron
    update (there is no legal contrast to learn from). This is
    what lets the machine tell good data from bad data: the
    broken fixture's banned-kind moves show up here.

Only the Python standard library is used, as in the rest of the
pipeline. This file never writes into rules/ (a fitted file must
not be mistaken for a calibrated model); all outputs go to the
given --out-dir.

Usage:
    python3 fit.py <trace.json> --payoff <payoff.json>
        [--fit-seasons 1,2,3] [--out-dir runs/fit-smoke-2026-11-21]
        [--bootstrap 50] [--seed 20261121]
        [--status auto|smoke_test|fitted] [--fit-id fit-2026-11-21-01]
Exit: 0 run completed; 2 bad input. (The verdict lives in the
report; it is not encoded in the exit code.)

--status auto (default) derives the run status from the input
trace: a trace whose moves carry no semantic_kind, or whose
filename contains "fixture", is the synthetic fixture and gets
the smoke-test notes; any other trace is treated as the real
trace and gets a real-fit note naming the trace path, schema
and semantic_kind coverage. The notes are never hard-coded to
one input: they are generated from the trace actually fitted.
"""
import argparse
import copy
import datetime
import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import predict as P  # noqa: E402
from backtest import chain_state  # noqa: E402

SMOKE_NOTE = ("Smoke test only, not calibration: the fixture trace "
              "must not be used for calibration. Every number in "
              "these outputs comes from fitting the fixture; none "
              "of it is a calibrated model.")
SMOKE_NOTE_ZH = ("fixture 上的冒烟拟合，不是校准：fixture 不得用于"
                 "校准。值是拟合值，不是占位值，但只拟合了合成 "
                 "fixture 数据。")


def is_fixture_trace(trace_path, trace):
    """True when the input is the synthetic fixture: its filename
    says so, or no move carries semantic_kind (the fixture
    predates the semantic layer; the real trace carries it on
    every move). Schema version does not distinguish them: both
    are schema 4."""
    if "fixture" in Path(trace_path).name:
        return True
    return not any("semantic_kind" in m
                   for m in trace.get("moves", []))


def real_note(trace_path, trace, coverage, n_decisions, fit_seasons):
    """Real-fit note, generated from the input actually fitted:
    trace path, schema, semantic_kind coverage, fit window and
    decision count. Returns (note_en, note_zh)."""
    moves = trace.get("moves", [])
    n_sem = sum(1 for m in moves if "semantic_kind" in m)
    schema = trace.get("schema_version")
    window = ",".join(f"S{s}" for s in fit_seasons)
    en = (
        f"Real fit on the real trace {trace_path} (schema "
        f"{schema}; {n_sem}/{len(moves)} moves carry "
        f"semantic_kind). Values are fitted, not placeholders. "
        f"Fit window {window} holds {n_decisions} classifiable "
        f"decisions; {coverage['unknown_moves']} unknown moves "
        f"in the window carry no supervision signal. In-sample "
        f"only; not calibration-grade on its own.")
    zh = (
        f"真实 trace {trace_path}（schema {schema}；{n_sem}/"
        f"{len(moves)} 条 move 带 semantic_kind）上的真实拟合。"
        f"值是拟合值，不是占位值。拟合窗口 {window} 有 "
        f"{n_decisions} 条可分类决策；窗口内 "
        f"{coverage['unknown_moves']} 条 unknown move 不提供监督"
        f"信号。仅样本内，不单独当校准证据。")
    return en, zh
METHOD = ("revealed preference / max-margin: average structured "
          "perceptron on prefix-only decisions, others fixed on "
          "recorded kinds, 30 epochs, eta 0.1, unit-L2 scale, "
          "discount-weighted by gamma, HP power alpha, softmax "
          "temperature by maximum likelihood, round-resampled "
          "bootstrap for uncertainty")

ALPHA_GRID = [0.25, 0.5, 0.75, 1.0]
GAMMA_GRID = [0.90, 0.95, 0.98, 1.0]
TAU_GRID = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
EPOCHS = 30
ETA = 0.1
INIT_W = (1.0, 1.0, 5.0, 10.0, 1.0)
WEIGHT_NAMES = ["w_hp", "w_gold", "c_lever", "c_rule", "w_pos"]


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def kind_of(m):
    """Semantic kind of a move; falls back to action_kind for traces
    that predate the semantic layer (e.g. the fixture, whose
    action_kind values already are semantic kinds). Same rule as
    predict.kind_of and backtest.kind_of; keep the three in sync."""
    return m.get("semantic_kind") or m["action_kind"]


def round_key(m):
    return (m["season"], m["round_index"])


def build_decisions(trace, fit_seasons):
    """Decisions inside the fit window. Returns (decisions, rounds,
    skipped). decisions are dicts; rounds is the ordered list of
    (season, round) keys in the window (excluding the empty-prefix
    first round). Each decision carries its raw per-candidate
    features so that phi(alpha) can be built for any alpha."""
    moves = trace["moves"]
    rules = trace["rules"]
    type_of = {p["key"]: p["type"] for p in
               trace.get("_payoff_players", [])}  # filled by caller
    pmap = {p["id"]: p for p in trace["players"]}
    rounds = sorted({round_key(m) for m in moves
                     if m["season"] in fit_seasons})
    window_moves = [m for m in moves if m["season"] in fit_seasons]
    decisions = []
    skipped = {"empty_prefix_rounds": [], "no_base_rule": 0,
               "unknown_recorded": 0,
               "coverage": {
                   "moves_in_window": len(window_moves),
                   "classifiable_moves": sum(
                       1 for m in window_moves
                       if kind_of(m) != "unknown"),
                   "unknown_moves": sum(
                       1 for m in window_moves
                       if kind_of(m) == "unknown")}}
    r_order = {}
    for idx, rk in enumerate(rounds):
        r_order[rk] = idx
    for rk in rounds:
        season, rnd = rk
        prefix = [m for m in moves if round_key(m) < rk]
        if not prefix:
            skipped["empty_prefix_rounds"].append(
                f"S{season}R{rnd}")
            continue
        test = [m for m in moves if round_key(m) == rk]
        if not test:
            continue
        state = chain_state(trace, prefix)
        per_mean, glob_mean = P.expected_deltas(prefix)
        exp = P.make_expectation(per_mean, glob_mean)
        kinds_prefix = sorted({kind_of(m) for m in prefix}
                              - {"unknown"})
        recorded_kind = {m["player"]: kind_of(m) for m in test}
        # Others fixed on their recorded kinds (expected increments).
        others_post = {}
        for pid, (hp, gold) in state.items():
            if pid in recorded_kind:
                dh, dg = exp(pid, recorded_kind[pid])
                base_q, _ = check.resolve_rules(rules, next(
                    m["date"] for m in test if m["player"] == pid),
                    pid)
                if base_q is None:
                    others_post[pid] = (hp, gold)
                else:
                    others_post[pid] = (
                        P.clamp(hp + dh, base_q["params"]["hp_floor"],
                                base_q["params"]["hp_cap"]), gold + dg)
            else:
                others_post[pid] = (hp, gold)
        base_rank = P.ranks_of(state)
        for m in sorted(test, key=lambda x: x["player"]):
            pid = m["player"]
            base, overlays = check.resolve_rules(rules, m["date"], pid)
            if base is None:
                skipped["no_base_rule"] += 1
                continue
            if kind_of(m) == "unknown":
                # No supervision signal: the true kind is unknown.
                # The move still folds into the state chain (which
                # never reads kinds) and into others' expectations.
                skipped["unknown_recorded"] += 1
                continue
            banned = set(base["params"].get("banned_action_kinds", []))
            for ov in overlays:
                banned |= set(ov["params"].get(
                    "banned_action_kinds", []))
            candidates = [k for k in kinds_prefix if k not in banned]
            if not candidates:
                candidates = [kind_of(m)]
            hp_before, gold_before = state[pid]
            lo = base["params"]["hp_floor"]
            hi = base["params"]["hp_cap"]
            feats = []
            for kind in candidates:
                dh, dg = exp(pid, kind)
                hp_after = P.clamp(hp_before + dh, lo, hi)
                gold_after = gold_before + dg
                post = dict(others_post)
                post[pid] = (hp_after, gold_after)
                rank_after = P.ranks_of(post)[pid]
                feats.append({
                    "kind": kind,
                    "hp_after": hp_after,
                    "dgold": dg,
                    "lever": 1 if gold_after < 0 else 0,
                    "pos": base_rank[pid] - rank_after,
                })
            decisions.append({
                "season": season, "round": rnd,
                "round_order": r_order[rk],
                "player": pid, "key": pmap[pid].get("key"),
                "type": type_of.get(pmap[pid].get("key")),
                "recorded": kind_of(m),
                "recorded_in_candidates":
                    kind_of(m) in candidates,
                "candidates": candidates,
                "feats": feats,
                "hp_before": hp_before,
            })
    return decisions, rounds, skipped


def phi_of(feat, hp_before, alpha):
    """phi = (f_hp, f_gold, -f_lever, -f_rule, f_pos)."""
    return ((feat["hp_after"] ** alpha - hp_before ** alpha),
            feat["dgold"],
            -float(feat["lever"]),
            0.0,
            float(feat["pos"]))


def argmax_kind(phis, kinds, w):
    best_k, best_u = None, None
    for k, phi in zip(kinds, phis):
        u = (w[0] * phi[0] + w[1] * phi[1] + w[2] * phi[2]
             + w[3] * phi[3] + w[4] * phi[4])
        if best_u is None or u > best_u + 1e-12:
            best_k, best_u = k, u
    return best_k, best_u


def utilities(phis, w):
    return [(w[0] * phi[0] + w[1] * phi[1] + w[2] * phi[2]
             + w[3] * phi[3] + w[4] * phi[4]) for phi in phis]


def normalise(w):
    n = math.sqrt(sum(x * x for x in w))
    if n <= 0:
        return list(w)
    return [x / n for x in w]


def perceptron(decisions, alpha, gamma, r_max, epochs=EPOCHS,
               eta=ETA, init=INIT_W):
    """Average structured perceptron. decisions must already be in
    time order. Returns the epoch-averaged weights, renormalised
    to unit L2 norm."""
    phis = [[phi_of(f, d["hp_before"], alpha) for f in d["feats"]]
            for d in decisions]
    w = list(init)
    avg = [0.0] * 5
    for _ in range(epochs):
        for d, phi_list in zip(decisions, phis):
            if not d["recorded_in_candidates"]:
                continue
            kinds = d["candidates"]
            pred, _ = argmax_kind(phi_list, kinds, w)
            if pred == d["recorded"]:
                continue
            dw = gamma ** (r_max - d["round_order"])
            step = eta * dw
            i_star = kinds.index(d["recorded"])
            i_pred = kinds.index(pred)
            phi_star = phi_list[i_star]
            phi_pred = phi_list[i_pred]
            for j in range(5):
                w[j] += step * (phi_star[j] - phi_pred[j])
            for j in range(5):
                if w[j] < 0:
                    w[j] = 0.0
        w = normalise(w)
        for j in range(5):
            avg[j] += w[j]
    avg = [x / epochs for x in avg]
    return normalise(avg)


def violation_rate(decisions, alpha, w, gamma, r_max):
    """Discount-weighted share of decisions where the recorded kind
    is not the argmax (a banned recorded kind always counts).
    Returns (weighted_rate, unweighted_rate, n)."""
    num = den = 0.0
    bad = 0
    for d in decisions:
        dw = gamma ** (r_max - d["round_order"])
        den += dw
        if not d["recorded_in_candidates"]:
            num += dw
            bad += 1
            continue
        phi_list = [phi_of(f, d["hp_before"], alpha)
                    for f in d["feats"]]
        pred, _ = argmax_kind(phi_list, d["candidates"], w)
        if pred != d["recorded"]:
            num += dw
            bad += 1
    n = len(decisions)
    return (num / den if den else 0.0,
            bad / n if n else 0.0, n)


def placeholder_violation(decisions, r_max):
    """Violation rate of the placeholder init weights (1, 1, 5, 10,
    1) at alpha = 1, gamma = 1 (their native v1 form). Argmax is
    invariant to positive scaling, so the unnormalised init is
    comparable with the unit-L2 fitted weights."""
    vr, vr_u, n = violation_rate(decisions, 1.0, list(INIT_W), 1.0,
                                 r_max)
    return {"violation_rate": round(vr, 6),
            "violation_rate_unweighted": round(vr_u, 6), "n": n}


def select_tau(decisions, alpha, w, gamma, r_max, tau_grid=TAU_GRID):
    """Softmax maximum likelihood of the recorded kind, weighted
    by the discount weights. Decisions whose recorded kind is
    banned are excluded (no probability is defined for them).
    Returns (best_tau, best_mean_loglik, table)."""
    table = []
    for tau in tau_grid:
        num = den = 0.0
        for d in decisions:
            if not d["recorded_in_candidates"]:
                continue
            phi_list = [phi_of(f, d["hp_before"], alpha)
                        for f in d["feats"]]
            utils = utilities(phi_list, w)
            i_star = d["candidates"].index(d["recorded"])
            mx = max(utils)
            logsum = mx + math.log(sum(
                math.exp((u - mx) / tau) for u in utils))
            ll = utils[i_star] / tau - logsum
            dw = gamma ** (r_max - d["round_order"])
            num += dw * ll
            den += dw
        mean_ll = num / den if den else float("-inf")
        table.append({"tau": tau,
                      "weighted_mean_loglik": round(mean_ll, 6)})
    best = max(table, key=lambda row: row["weighted_mean_loglik"])
    return best["tau"], best["weighted_mean_loglik"], table


def fit_group(decisions, r_max, alpha_grid=ALPHA_GRID,
              gamma_grid=GAMMA_GRID):
    """Grid search + tau for one group of decisions. Returns a
    dict with weights, alpha, gamma, tau, violation rates and the
    full grid."""
    grid = []
    for alpha in alpha_grid:
        for gamma in gamma_grid:
            w = perceptron(decisions, alpha, gamma, r_max)
            vr, vr_u, _ = violation_rate(decisions, alpha, w,
                                         gamma, r_max)
            grid.append({"alpha": alpha, "gamma": gamma,
                         "violation_rate": round(vr, 6),
                         "violation_rate_unweighted": round(vr_u, 6),
                         "weights": {name: round(v, 6) for name, v
                                     in zip(WEIGHT_NAMES, w)}})
    best = min(grid, key=lambda row: (
        row["violation_rate"],
        (1.0 - row["alpha"]) + (1.0 - row["gamma"])))
    alpha, gamma = best["alpha"], best["gamma"]
    w = [best["weights"][name] for name in WEIGHT_NAMES]
    tau, mean_ll, tau_table = select_tau(decisions, alpha, w,
                                         gamma, r_max)
    vr, vr_u, n = violation_rate(decisions, alpha, w, gamma, r_max)
    return {"alpha": alpha, "gamma": gamma, "temperature": tau,
            "weights": {name: round(v, 6) for name, v
                        in zip(WEIGHT_NAMES, w)},
            "violation_rate": round(vr, 6),
            "violation_rate_unweighted": round(vr_u, 6),
            "n": n, "mean_loglik": round(mean_ll, 6),
            "tau_grid": tau_table, "grid": grid}


def fit_group_fixed(decisions, r_max, alpha=1.0, gamma=1.0):
    """Same perceptron flow with (alpha, gamma) fixed: the v1
    projection."""
    w = perceptron(decisions, alpha, gamma, r_max)
    tau, mean_ll, tau_table = select_tau(decisions, alpha, w,
                                         gamma, r_max)
    vr, vr_u, n = violation_rate(decisions, alpha, w, gamma, r_max)
    return {"alpha": alpha, "gamma": gamma, "temperature": tau,
            "weights": {name: round(v, 6) for name, v
                        in zip(WEIGHT_NAMES, w)},
            "violation_rate": round(vr, 6),
            "violation_rate_unweighted": round(vr_u, 6),
            "n": n, "mean_loglik": round(mean_ll, 6),
            "tau_grid": tau_table}


def _quantile(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (
        pos - lo)


def bootstrap(decisions, alpha, gamma, r_max, b_count, seed):
    """Round-resampled bootstrap: whole rounds drawn with
    replacement, original time order and original discount
    weights kept. Refit w and tau each time. Returns the
    distribution summary per weight plus tau."""
    rounds = sorted({(d["season"], d["round"]) for d in decisions})
    by_round = defaultdict(list)
    for d in decisions:
        by_round[(d["season"], d["round"])].append(d)
    rng = random.Random(seed)
    w_samples = defaultdict(list)
    tau_samples = []
    for _ in range(b_count):
        drawn = [rng.choice(rounds) for _ in rounds]
        sample = []
        for rk in sorted(drawn):
            sample.extend(by_round[rk])
        # Keep time order (stable sort by round order).
        sample.sort(key=lambda d: d["round_order"])
        w = perceptron(sample, alpha, gamma, r_max)
        tau, _, _ = select_tau(sample, alpha, w, gamma, r_max)
        for name, v in zip(WEIGHT_NAMES, w):
            w_samples[name].append(v)
        tau_samples.append(tau)
    summary = {}
    for name in WEIGHT_NAMES:
        vals = sorted(w_samples[name])
        mean = sum(vals) / len(vals) if vals else 0.0
        var = (sum((v - mean) ** 2 for v in vals) / len(vals)
               if vals else 0.0)
        summary[name] = {
            "mean": round(mean, 6),
            "std": round(math.sqrt(var), 6),
            "p5": round(_quantile(vals, 0.05), 6),
            "p95": round(_quantile(vals, 0.95), 6),
            "zero_fraction": round(
                sum(1 for v in vals if v == 0.0) / len(vals), 4)
            if vals else 0.0,
        }
    tvals = sorted(tau_samples)
    tmean = sum(tvals) / len(tvals) if tvals else 0.0
    tvar = (sum((v - tmean) ** 2 for v in tvals) / len(tvals)
            if tvals else 0.0)
    summary["temperature"] = {
        "mean": round(tmean, 6), "std": round(math.sqrt(tvar), 6),
        "p5": round(_quantile(tvals, 0.05), 6),
        "p95": round(_quantile(tvals, 0.95), 6),
        "zero_fraction": 0.0,
    }
    return {"B": b_count, "unit": "round",
            "seed": seed, "weights": summary}


def weights_block(fit, status="fitted"):
    """A parameters block (global or per type) for a fitted payoff
    file, from one group's fit dict."""
    w = fit["weights"]
    return {
        "w_hp": {"value": w["w_hp"], "status": status,
                 "assumption": "A1",
                 "meaning": "weight on HP change"},
        "w_gold": {"value": w["w_gold"], "status": status,
                   "assumption": "A2",
                   "meaning": "weight on gold change"},
        "c_lever": {"value": w["c_lever"], "status": status,
                    "assumption": "A3",
                    "meaning": ("leverage penalty coefficient; "
                                "penalty is 1 when the expected "
                                "gold result is negative, else 0")},
        "c_rule": {"value": w["c_rule"], "status": status,
                   "assumption": "A4",
                   "meaning": ("compliance cost coefficient; cost "
                               "is 0 for every legal action kind "
                               "in this version (no priced legal "
                               "action is evidenced)")},
        "w_pos": {"value": w["w_pos"], "status": status,
                  "assumption": "A5",
                  "meaning": ("weight on ranking-position change "
                              "(old rank minus new rank after "
                              "applying expected increments)")},
        "temperature": {"value": fit["temperature"],
                        "status": status, "assumption": "A6",
                        "meaning": ("softmax temperature tau over "
                                    "candidate-action utilities")},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Payoff-model fitter.")
    ap.add_argument("trace")
    ap.add_argument("--payoff", required=True)
    ap.add_argument("--fit-seasons", default="1,2,3")
    ap.add_argument("--out-dir",
                    default="runs/fit-smoke-2026-11-21")
    ap.add_argument("--bootstrap", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--status", default="auto",
                    choices=["auto", "smoke_test", "fitted"],
                    help="auto (default): derive from the input "
                         "trace; smoke_test: fixture notes; "
                         "fitted: real-trace notes")
    ap.add_argument("--fit-id", default=None,
                    help="e.g. fit-2026-11-21-01; recorded in the "
                         "fit block when given")
    args = ap.parse_args(argv)

    try:
        fit_seasons = [int(s) for s in
                       args.fit_seasons.split(",") if s.strip()]
    except ValueError:
        print("fit: --fit-seasons must be comma-separated ints",
              file=sys.stderr)
        return 2
    if not fit_seasons:
        print("fit: --fit-seasons is empty", file=sys.stderr)
        return 2

    trace = P.load_trace(args.trace)
    if trace is None:
        return 2
    payoff = P.load_json(args.payoff, "payoff model")
    if payoff is None or "parameters" not in payoff:
        print("fit: bad payoff model file", file=sys.stderr)
        return 2
    players = payoff.get("players", [])
    if not players:
        print("fit: payoff model has no players", file=sys.stderr)
        return 2
    type_of = {p["key"]: p["type"] for p in players}
    type_label = {}
    for t, row in payoff.get("player_types", {}).items():
        type_label[t] = row.get("label_zh", t)
    trace["_payoff_players"] = players
    seasons_in_trace = sorted(s["season"] for s in trace["seasons"])
    if any(s not in seasons_in_trace for s in fit_seasons):
        print(f"fit: fit seasons {fit_seasons} not all in trace "
              f"seasons {seasons_in_trace}", file=sys.stderr)
        return 2

    decisions, rounds, skipped = build_decisions(trace, fit_seasons)
    if not decisions:
        print("fit: no decisions in the fit window", file=sys.stderr)
        return 2
    r_max = max(d["round_order"] for d in decisions)
    fit_date = datetime.date.today().isoformat()
    trace_hash = sha256_file(args.trace)

    # --- run status and notes: derived from the input trace ------
    # (never hard-coded to one input). Auto mode: fixture input
    # gets smoke-test notes; real-trace input gets a real-fit note
    # naming the trace path, schema and semantic_kind coverage.
    is_fixture = is_fixture_trace(args.trace, trace)
    if args.status == "auto":
        run_status = "smoke_test" if is_fixture else "fitted"
    else:
        run_status = args.status
    if run_status == "fitted":
        note_en, note_zh = real_note(
            args.trace, trace, skipped["coverage"], len(decisions),
            fit_seasons)
    else:
        note_en, note_zh = SMOKE_NOTE, SMOKE_NOTE_ZH

    # --- fits: one per player type + one shared reference --------
    groups = {}
    for t in sorted({d["type"] for d in decisions}):
        sub = [d for d in decisions if d["type"] == t]
        groups[t] = sub
    shared = decisions
    group_fits = {}
    for t, sub in sorted(groups.items()):
        fit = fit_group(sub, r_max)
        fit["bootstrap"] = bootstrap(sub, fit["alpha"],
                                     fit["gamma"], r_max,
                                     args.bootstrap, args.seed)
        fit["players"] = sorted({d["key"] for d in sub})
        fit["label_zh"] = type_label.get(t, t)
        group_fits[t] = fit
    shared_fit = fit_group(shared, r_max)
    shared_fit["bootstrap"] = bootstrap(
        shared, shared_fit["alpha"], shared_fit["gamma"], r_max,
        args.bootstrap, args.seed)
    shared_fit["players"] = sorted({d["key"] for d in shared})
    shared_fit["label_zh"] = "all seats (shared reference)"

    # --- v1 projection: alpha = 1, gamma = 1 fixed ---------------
    v1_groups = {}
    for t, sub in sorted(groups.items()):
        v1_groups[t] = fit_group_fixed(sub, r_max)
    v1_shared = fit_group_fixed(shared, r_max)
    v1_shared["bootstrap"] = bootstrap(
        shared, 1.0, 1.0, r_max, args.bootstrap, args.seed)

    # --- placeholder comparison (adoption rule input) -------------
    # The fitted v2 model goes live only if its fit-window
    # violation rate is no higher than the placeholder weights'
    # rate on the same decisions. This file only records the
    # comparison; it never writes into rules/.
    placeholder_shared = placeholder_violation(shared, r_max)
    placeholder_groups = {
        t: placeholder_violation(sub, r_max)
        for t, sub in sorted(groups.items())}
    adoption_meets = (shared_fit["violation_rate"]
                      <= placeholder_shared["violation_rate"])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fit_window = {
        "seasons": fit_seasons,
        "rounds": len(rounds),
        "round_labels": [f"S{s}R{r}" for s, r in rounds],
        "decisions": len(decisions),
        "skipped_empty_prefix_rounds":
            skipped["empty_prefix_rounds"],
        "skipped_no_base_rule": skipped["no_base_rule"],
        "skipped_unknown_recorded": skipped["unknown_recorded"],
        "coverage": skipped["coverage"],
    }

    # --- fit-report.json ------------------------------------------
    report = {
        "status": run_status,
        "method": METHOD,
        "trace": args.trace,
        "trace_sha256": trace_hash,
        "trace_schema": trace.get("schema_version"),
        "is_fixture_trace": is_fixture,
        "payoff_model": args.payoff,
        "payoff_version": payoff.get("version"),
        "fit_id": args.fit_id,
        "fit_date": fit_date,
        **({"smoke_test_note": SMOKE_NOTE} if run_status == "smoke_test"
           else {"real_fit_note": note_en,
                 "real_fit_note_zh": note_zh}),
        "fit_window": fit_window,
        "fit_seasons": fit_seasons,
        "n_decisions": len(decisions),
        "perceptron": {"eta": ETA, "epochs": EPOCHS,
                       "init": list(INIT_W),
                       "average": "epoch-averaged weights, "
                                  "renormalised to unit L2 norm",
                       "clip": "negative components clipped to 0 "
                               "after each update",
                       "normalisation": "unit L2 norm at the end "
                                        "of each epoch"},
        "alpha_grid": ALPHA_GRID,
        "gamma_grid": GAMMA_GRID,
        "tau_grid": TAU_GRID,
        "selection_rule": ("lowest discount-weighted violation "
                           "rate; ties towards alpha = 1, "
                           "gamma = 1"),
        "groups": group_fits,
        "shared": shared_fit,
        "v1_projection": {
            "method": ("same perceptron flow with alpha = 1, "
                       "gamma = 1 fixed; usable directly by "
                       "predict.py / backtest.py (v1 linear "
                       "utility)"),
            "shared": v1_shared,
            "groups": v1_groups,
        },
        "placeholder_comparison": {
            "placeholder_weights": list(INIT_W),
            "alpha": 1.0,
            "gamma": 1.0,
            "note": ("Placeholder evaluated in its native v1 form "
                     "(alpha = 1, gamma = 1); argmax is "
                     "scale-invariant, so the unnormalised init "
                     "compares with the unit-L2 fitted weights. "
                     "The v1 projection shares this form, so its "
                     "comparison is apples-to-apples; the v2 "
                     "shared fit uses its own selected "
                     "(alpha, gamma)."),
            "shared": placeholder_shared,
            "groups": placeholder_groups,
            "fitted_shared_violation_rate":
                shared_fit["violation_rate"],
            "v1_projection_shared_violation_rate":
                v1_shared["violation_rate"],
        },
        "adoption_rule": ("Adopt the fitted v2 model into "
                          "rules/payoff-model.json only if its "
                          "fit-window violation rate is no higher "
                          "than the placeholder weights' rate on "
                          "the same decisions."),
        "adoption_recommendation": {
            "meets_rule": adoption_meets,
            "fitted_shared_violation_rate":
                shared_fit["violation_rate"],
            "placeholder_violation_rate":
                placeholder_shared["violation_rate"],
            "note": ("Recommendation only. This file never writes "
                     "into rules/; the worker applies the rule and "
                     "records the outcome separately."),
        },
        "notes": [
            "Fit-window violation rate is an in-sample metric. "
            "It is not calibration. The real check is backtest.py "
            "run with payoff-model-fitted-v1.json on the hold-out "
            "window (S4-S5): M1-M5 against the random baselines.",
            "c_rule is not identified in this version: f_rule = 0 "
            "for every legal kind, so its gradient is always 0 "
            "and it only moves through normalisation.",
            "v2 weights with alpha != 1 cannot be substituted "
            "into the v1 linear utility; the v1 projection is a "
            "separate fit, not a conversion.",
            "Bootstrap resamples whole rounds (B = %d, seed %d); "
            "decision discount weights keep their original "
            "round-order values." % (args.bootstrap, args.seed),
        ],
    }
    (out_dir / "fit-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # --- shared fit block (used by both fitted payoff files) ------
    def fit_block(fit, alpha_gamma_note):
        boot = fit["bootstrap"]["weights"]
        block = {
            "status": run_status,
            "method": METHOD,
            "trace": args.trace,
            "trace_sha256": trace_hash,
            "trace_schema": trace.get("schema_version"),
            "is_fixture_trace": is_fixture,
            "fit_seasons": fit_seasons,
            "n_decisions": fit["n"],
            "violation_rate": fit["violation_rate"],
            "violation_rate_unweighted":
                fit["violation_rate_unweighted"],
            "alpha": fit["alpha"],
            "gamma": fit["gamma"],
            "temperature": fit["temperature"],
            "alpha_gamma_note": alpha_gamma_note,
            "bootstrap": {
                "B": fit["bootstrap"]["B"],
                "unit": fit["bootstrap"]["unit"],
                "seed": fit["bootstrap"]["seed"],
                "weights": {name: boot[name] for name in
                            WEIGHT_NAMES},
            },
            "fit_date": fit_date,
            "note": note_en,
            "note_zh": note_zh,
        }
        if args.fit_id:
            block["fit_id"] = args.fit_id
        return block

    # --- payoff-model-fitted.json (v2 structure) ------------------
    fitted_v2 = copy.deepcopy(payoff)
    fitted_v2["status"] = run_status
    if run_status == "fitted":
        # First real fit: version + 1 (design/fitting-layer.md §7).
        fitted_v2["version"] = payoff.get("version", 2) + 1
    fitted_v2["note"] = note_en
    fitted_v2["note_zh"] = note_zh
    fitted_v2["parameters"] = weights_block(shared_fit)
    fitted_v2["parameters"]["discount"] = {
        "value": shared_fit["gamma"], "status": "fitted",
        "assumption": "A8",
        "meaning": ("recency weighting exponent in fitting: "
                    "decision weight gamma ** (R - r); "
                    "gamma = 1.0 is equal weighting"),
    }
    fitted_v2["parameters"]["hp_exponent"] = {
        "value": shared_fit["alpha"], "status": "fitted",
        "assumption": "A9",
        "meaning": ("HP value power exponent: f_hp = "
                    "(hp_after)^alpha - (hp_before)^alpha; "
                    "alpha = 1.0 is linear, i.e. v1"),
    }
    for t, row in fitted_v2.get("player_types", {}).items():
        gf = group_fits.get(t)
        if gf is None:
            continue
        row["parameters"] = {
            "w_hp": gf["weights"]["w_hp"],
            "w_gold": gf["weights"]["w_gold"],
            "c_lever": gf["weights"]["c_lever"],
            "c_rule": gf["weights"]["c_rule"],
            "w_pos": gf["weights"]["w_pos"],
            "temperature": gf["temperature"],
            "discount": gf["gamma"],
            "hp_exponent": gf["alpha"],
        }
    fitted_v2["fit"] = fit_block(
        shared_fit,
        "v2 fit: alpha and gamma selected by grid search; "
        "predict.py (v1) ignores discount and hp_exponent until "
        "it adopts the v2 utility form.")
    (out_dir / "payoff-model-fitted.json").write_text(
        json.dumps(fitted_v2, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # --- payoff-model-fitted-v1.json (v1 structure) ---------------
    fitted_v1 = copy.deepcopy(payoff)
    fitted_v1["version"] = 1
    fitted_v1["status"] = run_status
    fitted_v1["utility_form"] = (
        "u = w_hp * dHP + w_gold * dgold - c_lever * "
        "leverage_penalty - c_rule * compliance_cost + w_pos * "
        "position_term")
    fitted_v1["assumptions"] = [
        a for a in payoff.get("assumptions", [])
        if a.get("id") in ("A1", "A2", "A3", "A4", "A5", "A6", "A7")]
    fitted_v1["note"] = (
        note_en + " v1 projection: alpha = 1, gamma = 1 fixed. "
        "Directly usable by predict.py / backtest.py (v1 linear "
        "utility).")
    fitted_v1["note_zh"] = (
        note_zh + " v1 投影：α = 1、γ = 1 固定。可直接供 "
        "predict.py / backtest.py（v1 线性效用）使用。")
    fitted_v1["parameters"] = weights_block(v1_shared)
    for t, row in fitted_v1.get("player_types", {}).items():
        gf = v1_groups.get(t)
        if gf is None:
            continue
        row["parameters"] = {
            "w_hp": gf["weights"]["w_hp"],
            "w_gold": gf["weights"]["w_gold"],
            "c_lever": gf["weights"]["c_lever"],
            "c_rule": gf["weights"]["c_rule"],
            "w_pos": gf["weights"]["w_pos"],
            "temperature": gf["temperature"],
        }
    for key in ("discount", "hp_exponent"):
        fitted_v1["parameters"].pop(key, None)
    fitted_v1.pop("status_vocabulary", None)
    fitted_v1["fit"] = fit_block(
        v1_shared,
        "v1 projection: alpha = 1, gamma = 1 fixed, same "
        "perceptron flow; the weights are directly usable by "
        "predict.py / backtest.py.")
    (out_dir / "payoff-model-fitted-v1.json").write_text(
        json.dumps(fitted_v1, ensure_ascii=False, indent=2),
        encoding="utf-8")

    lines = [
        f"fit: status={run_status} trace={args.trace} "
        f"fit_seasons={fit_seasons} n={len(decisions)} "
        f"rounds={len(rounds)}",
        f"fit: shared alpha={shared_fit['alpha']} "
        f"gamma={shared_fit['gamma']} tau={shared_fit['temperature']} "
        f"violation={shared_fit['violation_rate']} "
        f"weights={shared_fit['weights']}",
        f"fit: v1 projection (shared) tau={v1_shared['temperature']} "
        f"violation={v1_shared['violation_rate']} "
        f"weights={v1_shared['weights']}",
    ]
    for t in sorted(group_fits):
        gf = group_fits[t]
        lines.append(
            f"  fit: {t} n={gf['n']} alpha={gf['alpha']} "
            f"gamma={gf['gamma']} tau={gf['temperature']} "
            f"violation={gf['violation_rate']} "
            f"weights={gf['weights']}")
    lines.append(f"fit: {note_en}")
    lines.append(f"fit: wrote {out_dir}/fit-report.json, "
                 f"payoff-model-fitted.json, "
                 f"payoff-model-fitted-v1.json")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
