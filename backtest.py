#!/usr/bin/env python3
"""Walk-forward backtest of the prediction runner (design section 5).

Fit window S1-S3, test window S4-S5; a full-range S1-S5 table is
also included, labelled in-sample, not calibration. The payoff
parameters are placeholders: there is no real fit. The report says
so: "fit = placeholder parameters, not calibrated".

Per test round only the trace prefix before that round is used
(no future information): the current state is chained per player
by the C2/C3 ledger rule (HP clamped per the rule in effect at
each move's date, gold accumulated, no season-end penalty term),
and expected deltas come from the prefix only. Expected deltas
use the minimum-support rule (audit fix 4, round 4): a kind or
(player, kind) mean is used raw only at n >= 5; below that it is
shrunk toward the coarser mean with k = 5 (see
predict.expected_deltas). The report's expectation_diagnostics
section says how many test predictions rested on a shrunk
expectation, the prediction distribution (entropy, max share,
v3 count), and the instance count behind each predicted kind.

Metrics (design section 5):
  M1 semantic-kind equality, measured on the classifiable subset
  only (records whose recorded semantic_kind is known); M2 sign of
  dHP; M3 sign of dgold; M4 next HP segment equality (segments of
  design section 3; predicted segment from the clamped HP after the
  expected increment, recorded segment from the clamped HP after the
  recorded increment); M5 |predicted dHP - recorded dHP| within
  the payoff model's m5_tolerance.
  M6 calibration (audit fix 3, round 3): the largest gap between
  the mean predicted modal probability and the actual M1 hit rate
  over probability buckets, on the classifiable subset; threshold
  M6 < 0.2. The top bucket [0.99, 1.0] holds the near-certain
  claims, including modal p = 1.0.

  Post-hoc calibration (round 9, 2026-11-21): the modal
  probabilities measured here are the calibrated ones. run_window
  passes a calibration.load_calibration() dict into
  predict.best_response(), which rescales every distribution
  through calibration.apply_calibration() -- the same single
  implementation the live forecast uses. The rescaling is
  monotone, so no modal action and no M1-M5 hit count changes;
  only the stated probabilities (and hence M6) move. The
  parameters live in rules/calibration.json, fitted on the fit
  window only (S1-S3) by fit_calibration.py; the test window is
  never used for fitting. When the file is absent, calibration
  is None and the raw probabilities are measured.

Kind layer (semantic kinds, added 2026-11-21): moves carry
semantic_kind (the substantive action thread) beside action_kind
(the round-type slug). Candidates, expectations and M1 all use the
semantic kind. "unknown" is a classification gap, not an action a
player can take: it is excluded from the candidate set and from the
M1 denominator (reported as m1_unknown_n). Traces that predate the
layer (e.g. the fixture) have no semantic_kind field; kind_of()
falls back to action_kind, so the fixture backtest is unchanged.
Random baselines sit beside every rate: M1 1/(kinds), M2/M3 50%,
M4 1/8, M5 the probability that a uniform draw from the player's
observed dHP interval lands within tolerance of the recorded dHP.
A metric counts as a signal only when it exceeds its baseline by
margin_pp (10 pp); below that it is recorded below_threshold
(opinion, never a block, and never an auto-revision trigger).

Usage:
    python3 backtest.py <trace.json> --payoff <payoff.json>
        [--out report.json] [--summary summary.txt]
Exit: 0 run completed; 2 bad input.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import calibration as CAL  # noqa: E402  (post-hoc rescaling, round 9)
import check  # noqa: E402
import predict as P  # noqa: E402  (shared best-response + helpers)

SMOKE_NOTE = ("Smoke test only, not calibration: payoff parameters "
              "are placeholders, the fit window is not a real fit, "
              "and the fixture trace must not be used for calibration.")


def chain_state(trace, prefix_moves):
    """Per-player (hp, gold) after prefix moves, C2/C3 chain without
    the season-end penalty term. Starts from each player's first
    season_state hp_start/gold_start."""
    starts = {}
    for s in trace["season_state"]:
        pid = s["player"]
        if pid not in starts or s["season"] < starts[pid][0]:
            starts[pid] = (s["season"], s["hp_start"], s["gold_start"])
    state = {pid: (v[1], v[2]) for pid, v in starts.items()}
    by_player = defaultdict(list)
    for m in prefix_moves:
        by_player[m["player"]].append(m)
    for pid, ms in by_player.items():
        hp, gold = state.get(pid, (100, 50))
        for m in sorted(ms, key=lambda x: (x["season"],
                                           x["round_index"])):
            base, _ = check.resolve_rules(trace["rules"], m["date"], pid)
            if base is None:
                continue
            hp = P.clamp(hp + m["hp_delta"],
                         base["params"]["hp_floor"],
                         base["params"]["hp_cap"])
            gold = gold + m["gold_delta"]
        state[pid] = (hp, gold)
    return state


def kind_of(m):
    """Semantic kind of a move; falls back to action_kind for traces
    that predate the semantic layer (e.g. the fixture, whose
    action_kind values already are semantic kinds)."""
    return m.get("semantic_kind") or m["action_kind"]


def semantic_expected_deltas(moves):
    """Expectation means grouped by semantic kind (per (player,
    kind) and per kind mean (dHP, dgold)). This is a direct
    delegation to predict.expected_deltas, not a second copy: the
    two must stay the same logic (round 4 found them drifting
    before), so there is one implementation. predict's version
    applies the minimum-support rule (n < 5 shrinks toward the
    coarser mean, k = 5; see predict.expected_deltas). "unknown" is
    included in the means (it is a real set of past moves) but is
    never a candidate: it is a classification gap, not an action a
    player can take."""
    return P.expected_deltas(moves)


def m5_baseline(lo, hi, recorded, tol):
    """P(uniform draw from [lo, hi] lands within tol of recorded)."""
    if hi <= lo:
        return 1.0 if abs(lo - recorded) <= tol else 0.0
    overlap = max(0, min(hi, recorded + tol) - max(lo, recorded - tol))
    return overlap / (hi - lo)


def aggregate(records):
    """records: list of dicts with m1..m5 bools and baselines b1..b5.
    M1 is measured on the classifiable subset only (records whose
    recorded semantic kind is known); "unknown" is a classification
    gap, not an action, so it is excluded from the M1 denominator
    (reported as m1_unknown_n). M2-M5 use all records.
    Return the summary table row."""
    n = len(records)
    if n == 0:
        return {"n": 0}
    row = {"n": n}
    m1_recs = [r for r in records if r.get("m1_classifiable")]
    row["m1_n"] = len(m1_recs)
    row["m1_unknown_n"] = n - len(m1_recs)
    for i in (1, 2, 3, 4, 5):
        subset = m1_recs if i == 1 else records
        if not subset:
            row[f"m{i}_hit_rate"] = None
            row[f"m{i}_baseline"] = None
            row[f"m{i}_margin_pp"] = None
            continue
        hits = sum(1 for r in subset if r[f"m{i}"])
        base = sum(r[f"b{i}"] for r in subset) / len(subset)
        row[f"m{i}_hit_rate"] = round(hits / len(subset), 4)
        row[f"m{i}_baseline"] = round(base, 4)
        row[f"m{i}_margin_pp"] = round((hits / len(subset) - base) * 100, 2)
    return row


def add_thresholds(row, margin_pp):
    below = []
    for i in (1, 2, 3, 4, 5):
        m = row.get(f"m{i}_margin_pp")
        signal = m is not None and m >= margin_pp
        row[f"m{i}_signal"] = signal
        if not signal:
            below.append(f"M{i}")
    row["below_threshold"] = below
    return row


# --- M6 calibration (audit fix 3, round 3) --------------------------
CALIBRATION_BUCKETS = [(0.0, 0.5), (0.5, 0.8), (0.8, 0.9),
                       (0.9, 0.99), (0.99, 1.0)]
M6_THRESHOLD = 0.2


def calibration(records):
    """M6: calibration of the modal probability against the realised
    M1 hit rate, on the classifiable subset only (same denominator
    as M1: records whose recorded semantic kind is known). Records
    are bucketed by modal probability; per bucket: n, mean predicted
    p, actual M1 hit rate, gap = |mean p - hit rate|. M6 is the
    largest gap over non-empty buckets. Threshold: M6 < 0.2.
    The top bucket [0.99, 1.0] is the near-certain bucket: it holds
    the p = 1.0 modal claims (a modal probability of exactly 1.0
    falls here). A model that asserts near-certainty there and hits
    0% is maximally miscalibrated: gap ~1.0. M6 is reported as its
    own pass/fail; it does not change threshold_verdict /
    below_threshold (M1-M5 keep their existing semantics)."""
    cls = [r for r in records if r.get("m1_classifiable")]
    buckets = []
    worst = 0.0
    for lo, hi in CALIBRATION_BUCKETS:
        b = [r for r in cls
             if r.get("modal_probability") is not None
             and lo <= r["modal_probability"]
             and (r["modal_probability"] < hi or hi == 1.0)]
        if not b:
            buckets.append({"bucket": f"[{lo}, {hi}]" if hi == 1.0
                            else f"[{lo}, {hi})",
                            "n": 0, "mean_predicted_p": None,
                            "actual_hit_rate": None, "gap": None})
            continue
        mean_p = sum(r["modal_probability"] for r in b) / len(b)
        hit = sum(1 for r in b if r["m1"]) / len(b)
        gap = abs(mean_p - hit)
        worst = max(worst, gap)
        buckets.append({"bucket": f"[{lo}, {hi}]" if hi == 1.0
                        else f"[{lo}, {hi})",
                        "n": len(b),
                        "mean_predicted_p": round(mean_p, 6),
                        "actual_hit_rate": round(hit, 4),
                        "gap": round(gap, 4)})
    m6 = round(worst, 4)
    return {"m6": m6, "m6_threshold": M6_THRESHOLD,
            "m6_pass": m6 < M6_THRESHOLD,
            "buckets": buckets,
            "n_classifiable": len(cls),
            "note": ("M6 is the largest |mean predicted modal "
                     "probability - actual M1 hit rate| over the "
                     "probability buckets, on the classifiable "
                     "subset (same denominator as M1). The top "
                     "bucket [0.99, 1.0] holds the near-certain "
                     "claims, including modal p = 1.0.")}


def prediction_distribution(records):
    """Distribution of predicted actions over `records`: counts,
    Shannon entropy (bits) of the modal-action distribution, the
    largest kind share, and the v3 count. Audit fix 4 measures
    concentration here: a kind with 2 instances must not decide
    hundreds of predictions, so the max share must stay below 50%
    and the v3 count must fall to the order of its real frequency
    (v3 never actually occurs in the S4-S5 test window)."""
    import math
    n = len(records)
    counts = {}
    for r in records:
        a = r["predicted_action"]
        counts[a] = counts.get(a, 0) + 1
    entropy = 0.0
    for c in counts.values():
        p = c / n if n else 0.0
        if p:
            entropy -= p * math.log2(p)
    top_kind, top_n = (max(counts.items(), key=lambda kv: kv[1])
                       if counts else (None, 0))
    return {"n": n, "counts": counts,
            "entropy_bits": round(entropy, 4),
            "max_kind": top_kind, "max_n": top_n,
            "max_share": round(top_n / n, 4) if n else 0.0,
            "v3_count": counts.get("v3", 0)}


def expectation_diagnostics(records):
    """Round-4 diagnostics over test records: how many predictions
    rested on a shrunk expectation (thin cell or thin kind, n < 5),
    the prediction distribution (counts / entropy / max share /
    v3 count), and, per predicted kind, the instance count n behind
    it at prediction time (min / max over the records where it was
    predicted; n grows as the walk-forward prefix grows)."""
    n = len(records)
    shrunk = sum(1 for r in records if r.get("predicted_kind_shrunk"))
    fallback = sum(1 for r in records
                   if r.get("predicted_kind_n", 0) == 0)
    per_kind = {}
    for r in records:
        k = r["predicted_action"]
        nk = r.get("predicted_kind_n", 0)
        e = per_kind.setdefault(k, {"records": 0, "min_n": nk,
                                    "max_n": nk})
        e["records"] += 1
        e["min_n"] = min(e["min_n"], nk)
        e["max_n"] = max(e["max_n"], nk)
    return {"min_support": P.MIN_SUPPORT, "shrinkage_k": P.SHRINKAGE_K,
            "method": ("n < 5: shrink toward the coarser mean, "
                       "expected = (n * kind_mean + k * global_mean) "
                       "/ (n + k), k = 5; n >= 5: raw mean"),
            "n": n, "shrunk_predictions": shrunk,
            "shrunk_share": round(shrunk / n, 4) if n else 0.0,
            "fallback_to_global": fallback,
            "prediction_distribution": prediction_distribution(records),
            "per_kind_n_at_prediction": per_kind}


def run_window(trace, payoff_params, tau, seasons, margin_pp, tol,
               calibration=None, include_distributions=False,
               player_types=None):
    """Predict every round in `seasons` from its prefix. Returns
    (records, per_round_meta). calibration is passed through to
    predict.best_response() (round 9): the modal probabilities in
    the records are the calibrated ones when a calibration dict is
    given, the raw ones when it is None. include_distributions
    attaches the full (calibrated) distribution to each record;
    fit_calibration.py uses it to fit on the fit window, the
    regular report leaves it off to stay lean. player_types is a
    pid -> type map (round 10): when given, each round's
    predictions use the resolved per-player reference-class prior
    from that round's walk-forward prefix (P.per_player_rates);
    when None (fit_calibration.py, which needs the raw model
    distributions) no prior is applied."""
    rules = trace["rules"]
    moves = trace["moves"]
    pmap = {p["id"]: p for p in trace["players"]}
    records = []
    for season in sorted(seasons):
        season_row = next(s for s in trace["seasons"]
                          if s["season"] == season)
        for rnd in range(1, season_row["rounds"] + 1):
            prefix = [m for m in moves
                      if (m["season"], m["round_index"]) < (season, rnd)]
            test = [m for m in moves
                    if m["season"] == season and m["round_index"] == rnd]
            if not test or not prefix:
                continue
            state = chain_state(trace, prefix)
            per_mean, glob_mean = semantic_expected_deltas(prefix)
            support = P.expectation_support(prefix)
            exp = P.make_expectation(
                per_mean, glob_mean,
                global_mean=tuple(support["global_mean"]))
            # Round 10 (fruit 4): per-player reference-class priors
            # from this round's walk-forward prefix, the same prefix
            # the expectations above come from (predict.py uses the
            # full trace for the live forecast; here the prefix grows
            # round by round). Single implementation:
            # P.per_player_rates. When player_types is None
            # (fit_calibration.py) no prior is applied.
            priors_table = (P.per_player_rates(prefix, player_types)
                            if player_types is not None else None)
            last = {}
            for m in prefix:
                pid = m["player"]
                key = (m["season"], m["round_index"])
                if pid not in last or key > (last[pid]["season"],
                                            last[pid]["round_index"]):
                    last[pid] = m
            candidates = {}
            for m in test:
                pid = m["player"]
                base, overlays = check.resolve_rules(
                    rules, m["date"], pid)
                banned = set()
                if base is not None:
                    banned |= set(base["params"].get(
                        "banned_action_kinds", []))
                for ov in overlays:
                    banned |= set(ov["params"].get(
                        "banned_action_kinds", []))
                kinds_here = [k for k in
                              sorted({kind_of(x) for x in prefix}
                                     - {"unknown"})
                              if k not in banned]
                if not kinds_here:
                    rec = kind_of(m)
                    kinds_here = ([rec] if rec != "unknown" else
                                  sorted({kind_of(x) for x in prefix}
                                         - {"unknown"}))
                candidates[pid] = kinds_here
            start = {pid: kind_of(last[pid])
                     for pid in last
                     if pid in candidates
                     and kind_of(last[pid]) in candidates[pid]}
            acting = sorted(m["player"] for m in test)
            hp_bounds = (100, 0)
            base0, _ = check.resolve_rules(rules, test[0]["date"],
                                           test[0]["player"])
            if base0 is not None:
                hp_bounds = (base0["params"]["hp_floor"],
                             base0["params"]["hp_cap"])
            # Round 10: resolve one prior per acting player from
            # this round's prefix table (own / type / global).
            prior_by_player = (
                {pid: P.resolve_prior(priors_table, pid, player_types)
                 for pid in acting}
                if priors_table is not None else None)
            res = P.best_response(state, payoff_params, tau, candidates,
                                  exp, start, acting, hp_bounds,
                                  calibration=calibration,
                                  priors=prior_by_player)
            dhp_obs = defaultdict(list)
            for m in prefix:
                dhp_obs[m["player"]].append(m["hp_delta"])
            for m in test:
                pid = m["player"]
                pred_kind = res["modal"][pid]["action"]
                pdhp, pdgold = exp(pid, pred_kind)
                n_kind, n_cell, shrunk = P.support_lookup(
                    support, pid, pred_kind)
                cur_hp, _ = state[pid]
                base_m, _ = check.resolve_rules(rules, m["date"], pid)
                lo_b = base_m["params"]["hp_floor"] if base_m else 0
                hi_b = base_m["params"]["hp_cap"] if base_m else 100
                pred_hp = P.clamp(cur_hp + pdhp, lo_b, hi_b)
                rec_hp = P.clamp(cur_hp + m["hp_delta"], lo_b, hi_b)
                obs = dhp_obs.get(pid, [m["hp_delta"]])
                rec_kind = kind_of(m)
                # Round 10 diagnostics. prior_only_guess: the mode
                # of the resolved reference-class prior for this
                # player (own / type / global hierarchy) -- fruit
                # 4's own measure: the reference class alone,
                # against the model and against the global-only
                # guess. global_only_guess: the global table's mode
                # (round 7's base-only guess; it must reproduce
                # 6/83 on this window). prior_level / prior_n: which
                # level resolved for this player at this round and
                # how many known-kind moves supported it.
                prior = (prior_by_player or {}).get(pid)
                prior_guess = (prior["table"]["mode"]
                               if prior is not None else None)
                global_guess = (priors_table["global"]["mode"]
                                if priors_table is not None else None)
                rec = {
                    "season": season, "round": rnd, "player": pid,
                    "key": pmap[pid].get("key"),
                    "predicted_action": pred_kind,
                    "recorded_action": rec_kind,
                    "prior_level": prior["level"] if prior else None,
                    "prior_n": (prior["table"]["n"]
                                if prior is not None else None),
                    "prior_only_guess": prior_guess,
                    "prior_only_hit": (prior_guess == rec_kind
                                       and rec_kind != "unknown"),
                    "global_only_guess": global_guess,
                    "global_only_hit": (global_guess == rec_kind
                                        and rec_kind != "unknown"),
                    "modal_probability": res["modal"][pid]["probability"],
                    "predicted_kind_n": n_kind,
                    "predicted_kind_n_player": n_cell,
                    "predicted_kind_shrunk": shrunk,
                    "predicted_dhp": round(pdhp, 4),
                    "recorded_dhp": m["hp_delta"],
                    "predicted_dgold": round(pdgold, 4),
                    "recorded_dgold": m["gold_delta"],
                    "m1": pred_kind == rec_kind and rec_kind != "unknown",
                    "m1_classifiable": rec_kind != "unknown",
                    "m2": P.sign(pdhp) == P.sign(m["hp_delta"]),
                    "m3": P.sign(pdgold) == P.sign(m["gold_delta"]),
                    "m4": P.hp_segment(pred_hp) == P.hp_segment(rec_hp),
                    "m5": abs(pdhp - m["hp_delta"]) <= tol,
                    "b1": 1.0 / len(candidates[pid]),
                    "b2": 0.5, "b3": 0.5, "b4": 1.0 / 8,
                    "b5": m5_baseline(min(obs), max(obs),
                                      m["hp_delta"], tol),
                }
                if include_distributions:
                    rec["distribution"] = res["distributions"][pid]
                records.append(rec)
    return records


def main(argv=None):
    ap = argparse.ArgumentParser(description="Walk-forward backtest.")
    ap.add_argument("trace")
    ap.add_argument("--payoff", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--summary", default=None)
    args = ap.parse_args(argv)

    trace = P.load_trace(args.trace)
    if trace is None:
        return 2
    payoff = P.load_json(args.payoff, "payoff model")
    if payoff is None or "parameters" not in payoff:
        print("backtest: bad payoff model file", file=sys.stderr)
        return 2
    params = {k: v["value"] for k, v in payoff["parameters"].items()}
    tau = params.get("temperature", 1.0)
    thresholds = payoff.get("thresholds", {})
    margin_pp = thresholds.get("margin_pp", 10)
    tol = thresholds.get("m5_tolerance", 10)
    # Post-hoc calibration (round 9): fitted on the fit window
    # only (S1-S3) by fit_calibration.py; parameters live in
    # rules/calibration.json. Absent file -> None -> the raw
    # probabilities are measured.
    calibration_params = CAL.load_calibration()

    seasons = sorted(s["season"] for s in trace["seasons"])
    fit_seasons = seasons[:3]
    test_seasons = seasons[3:]
    if not test_seasons:
        print("backtest: trace needs more than 3 seasons for a "
              "walk-forward test window", file=sys.stderr)
        return 2
    # Round 10 (fruit 4): pid -> player type, from the payoff
    # model's five tiers; threaded into run_window so each round's
    # priors resolve own / type / global from that round's prefix.
    type_of = {p["key"]: p["type"] for p in payoff.get("players", [])}
    player_types = {p["id"]: type_of.get(p["key"])
                    for p in trace["players"]}

    test_records = run_window(trace, params, tau, test_seasons,
                              margin_pp, tol,
                              calibration=calibration_params,
                              player_types=player_types)
    full_records = run_window(trace, params, tau, seasons,
                              margin_pp, tol,
                              calibration=calibration_params,
                              player_types=player_types)

    def tables(records):
        overall = add_thresholds(aggregate(records), margin_pp)
        by_season = {}
        for s in sorted({r["season"] for r in records}):
            by_season[f"S{s}"] = add_thresholds(
                aggregate([r for r in records if r["season"] == s]),
                margin_pp)
        by_player = {}
        for pid in sorted({r["player"] for r in records}):
            key = next(r["key"] for r in records if r["player"] == pid)
            by_player[key] = add_thresholds(
                aggregate([r for r in records if r["player"] == pid]),
                margin_pp)
        return {"overall": overall, "by_season": by_season,
                "by_player": by_player}

    test_tables = tables(test_records)
    full_tables = tables(full_records)
    below_any = bool(test_tables["overall"].get("below_threshold"))
    calib = calibration(test_records)
    test_tables["overall"]["m6_gap"] = calib["m6"]
    test_tables["overall"]["m6_pass"] = calib["m6_pass"]
    exp_diag = expectation_diagnostics(test_records)
    # Round 10 (fruit 4): reference-class-only diagnostics on the
    # test window. prior-only = the resolved prior's mode for every
    # record; global-only = the global table's mode (round 7's
    # base-only guess, same denominator as M1). Fruit 4's
    # falsification check: per-player-only does not beat
    # global-only. Level breakdown: hits by the level the prior
    # resolved at for that record.
    cls_recs = [r for r in test_records if r.get("m1_classifiable")]
    prior_hits = sum(1 for r in cls_recs if r.get("prior_only_hit"))
    global_hits = sum(1 for r in cls_recs if r.get("global_only_hit"))
    level_counts = {}
    level_hits = {}
    for r in cls_recs:
        lv = r.get("prior_level")
        level_counts[lv] = level_counts.get(lv, 0) + 1
        if r.get("prior_only_hit"):
            level_hits[lv] = level_hits.get(lv, 0) + 1
    per_player_diag = {
        "method": ("Per-player reference-class prior (round 10, "
                   "research fruit 4): each player's kind "
                   "distribution from the walk-forward prefix, "
                   "Laplace-smoothed with one pseudocount per kind, "
                   "p = (count + 1) / (N + K); the model distribution "
                   "is multiplied by the prior and renormalised. "
                   "Resolution per player: own history when its "
                   "known-kind count n >= 5 (MIN_SUPPORT, round 4), "
                   "else the same-type average when its n >= 5, else "
                   "the global average. 'unknown' moves are excluded "
                   "from counts and denominator. The prior is computed "
                   "from the trace, not stored in payoff-model.json."),
        "min_support": P.MIN_SUPPORT,
        "pseudocount": P.PER_PLAYER_PSEUDOCOUNT,
        "diagnostic": {
            "prior_only_guess": ("resolved prior mode (own / type / "
                                 "global) for every record"),
            "global_only_guess": "global table mode for every record",
            "prior_only_hits": prior_hits,
            "global_only_hits": global_hits,
            "n_classifiable": len(cls_recs),
            "prior_only_hit_rate": (round(prior_hits / len(cls_recs), 4)
                                    if cls_recs else None),
            "global_only_hit_rate": (round(global_hits / len(cls_recs),
                                           4)
                                     if cls_recs else None),
            "model_m1_hits": sum(1 for r in cls_recs if r["m1"]),
            "note": ("Prior-only hits vs global-only hits vs model M1 "
                     "hits, same denominator. Fruit 4's falsification "
                     "check: if prior-only does not beat global-only, "
                     "the reference class adds nothing over the "
                     "global average on this window.")},
        "levels": {lv: {"records": level_counts.get(lv, 0),
                        "prior_only_hits": level_hits.get(lv, 0)}
                   for lv in ("player", "type", "global")},
    }
    report = {
        "trace": args.trace,
        "payoff_model": {"version": payoff.get("version"),
                         "utility_form": payoff.get("utility_form")},
        "protocol": {
            "method": "walk-forward",
            "fit_seasons": [f"S{s}" for s in fit_seasons],
            "test_seasons": [f"S{s}" for s in test_seasons],
            "fit_note": ("Fit = placeholder parameters, not "
                         "calibrated. No real fitting was done; the "
                         "payoff parameters are placeholders (A1-A6)."),
            "prefix_rule": ("Each test round uses only the trace "
                            "prefix before that round. State is "
                            "chained per player by the C2/C3 ledger "
                            "rule (HP clamped per the rule in effect "
                            "at each move date, gold accumulated, no "
                            "season-end penalty term)."),
            "full_range_note": ("The S1-S5 full-range table is "
                                "in-sample, not calibration."),
            "kind_layer": ("Semantic kinds: candidates, expectations "
                           "and M1 use each move's semantic_kind "
                           "(substantive action thread); 'unknown' is "
                           "excluded from candidates and from the M1 "
                           "denominator (m1_unknown_n). Traces without "
                           "semantic_kind fall back to action_kind."),
        },
        "thresholds": {"margin_pp": margin_pp, "m5_tolerance": tol,
                       "below_threshold": "opinion"},
        "threshold_verdict": ("below_threshold" if below_any else "pass"),
        "below_threshold": test_tables["overall"].get("below_threshold",
                                                      []),
        "verdict": ("fail" if below_any else "pass"),
        "calibration": calib,
        "calibration_applied": {
            "applied": calibration_params is not None,
            "method": (calibration_params["method"]
                       if calibration_params else None),
            "temperature": (calibration_params["temperature"]
                            if calibration_params else None),
            "cap": (calibration_params["cap"]
                    if calibration_params else None),
            "fit_window": (calibration_params.get("fit_window")
                           if calibration_params else None),
            "fit_date": (calibration_params.get("fit_date")
                         if calibration_params else None),
            "source_file": (calibration_params.get("source_file")
                            if calibration_params else None),
            "note": ("Post-hoc rescaling (round 9): the modal "
                     "probabilities measured here are the calibrated "
                     "ones when a calibration file is present. The "
                     "rescaling is monotone, so no modal action and "
                     "no M1-M5 hit count changes; only the stated "
                     "probabilities (and hence M6) move. Parameters "
                     "were fitted on the fit window only (S1-S3); "
                     "the test window was never used for fitting."),
        },
        "expectation_diagnostics": exp_diag,
        "per_player_rates": per_player_diag,
        "tables": test_tables,
        "baselines": {f"M{i}": test_tables["overall"].get(f"m{i}_baseline")
                      for i in (1, 2, 3, 4, 5)},
        "test_window": test_tables,
        "test_records": test_records,
        "full_range": full_tables,
        "full_range_records": full_records,
        "calibration_status": "placeholder_only",
        "smoke_test_note": SMOKE_NOTE,
        "assumptions": payoff.get("assumptions", []),
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8")
    o = test_tables["overall"]
    lines = [
        f"backtest: fit={[f'S{s}' for s in fit_seasons]} "
        f"test={[f'S{s}' for s in test_seasons]} "
        f"n={o.get('n', 0)} threshold_verdict="
        f"{report['threshold_verdict']}",
        f"backtest: {SMOKE_NOTE}",
        f"backtest: M1 on {o.get('m1_n', 0)} classifiable records "
        f"({o.get('m1_unknown_n', 0)} unknown excluded)",
    ]
    for i in (1, 2, 3, 4, 5):
        lines.append(
            f"  M{i}: hit={o.get(f'm{i}_hit_rate')} "
            f"baseline={o.get(f'm{i}_baseline')} "
            f"margin_pp={o.get(f'm{i}_margin_pp')} "
            f"signal={o.get(f'm{i}_signal')}")
    top = next((b for b in calib["buckets"] if b["bucket"] == "[0.99, 1.0]"),
               None)
    lines.append(
        f"  M6: gap={calib['m6']} threshold=<{calib['m6_threshold']} "
        f"pass={calib['m6_pass']}"
        + (f" (top bucket [0.99, 1.0]: n={top['n']} "
           f"mean_p={top['mean_predicted_p']} "
           f"hit={top['actual_hit_rate']} gap={top['gap']})"
           if top and top["n"] else "")
        + (" calibration=applied "
           f"(temperature={calibration_params['temperature']} "
           f"cap={calibration_params['cap']})"
           if calibration_params else
           " calibration=none (raw probabilities)"))
    dist = exp_diag["prediction_distribution"]
    lines.append(
        f"  expectation: shrunk={exp_diag['shrunk_predictions']}/"
        f"{exp_diag['n']} (share={exp_diag['shrunk_share']}) "
        f"fallback_to_global={exp_diag['fallback_to_global']} "
        f"pred_dist={dist['counts']} entropy={dist['entropy_bits']} "
        f"bits max_share={dist['max_share']} ({dist['max_kind']}) "
        f"v3={dist['v3_count']}")
    ppd = per_player_diag["diagnostic"]
    lines.append(
        f"  per_player_rates: prior-only guess hits="
        f"{ppd['prior_only_hits']}/{ppd['n_classifiable']} "
        f"(rate={ppd['prior_only_hit_rate']}) vs global-only hits="
        f"{ppd['global_only_hits']}/{ppd['n_classifiable']} "
        f"(rate={ppd['global_only_hit_rate']}) vs model M1 hits="
        f"{ppd['model_m1_hits']}/{ppd['n_classifiable']} "
        f"levels={per_player_diag['levels']}")
    summary = "\n".join(lines)
    print(summary)
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
