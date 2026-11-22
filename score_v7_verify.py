#!/usr/bin/env python3
"""Independent recount for round-7 scoring (vision-1 round 7).

Re-reads testset-v6.json and the prediction files from scratch and
recomputes every number in score-v7.json with separate code (this file
imports nothing from score_v7.py). Any disagreement exits non-zero.
Also independently re-checks the round-6 capex reproduction gate numbers
(C1 2, C2 5, C3 6, E1 10, E2 10).

Usage:
  python3 score_v7_verify.py [--pred-dir DIR] [--score-file FILE]
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round7-vision7-2026-11-22", "predictions")
R6_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round6",
    "runs", "round6-vision6-2026-11-22", "predictions")

FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
OLD_SUB = {10, 11, 12, 13, 14, 15, 17, 18}
NEW_SUB = {16, 19}
BATCHES = ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]
CONTROL = ["C1", "C2", "C3", "C4", "C5"]
EXPERIMENT = ["E1", "E2", "E3"]
R6_CAPEX_EXPECTED = {"C1": 2, "C2": 5, "C3": 6, "E1": 10, "E2": 10}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--score-file", default=None)
    args = ap.parse_args()
    score_file = args.score_file or os.path.join(args.pred_dir, "score-v7.json")
    if not os.path.exists(score_file):
        print(f"no score file yet: {score_file}")
        sys.exit(2)
    scored = json.load(open(score_file))
    ts = json.load(open(os.path.join(BASE, "testset-v6.json")))
    truth = {q["q_id"]: q["kind"] for q in ts["questions"]}
    meta = {q["q_id"]: q for q in ts["questions"]}
    problems = []

    def check(label, got, want):
        if got != want:
            problems.append(f"{label}: verify={got} score-v7={want}")

    # ---- independent round-6 capex gate recount ----
    def load_r6(batch):
        d = {}
        for fn in sorted(glob.glob(os.path.join(R6_PRED_DIR,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                d[rec["q_id"]] = rec["predicted_kind"]
        return d
    gate_got = {}
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        d = load_r6(b)
        gate_got[b] = sum(1 for q in FOCUS if d.get(q) == truth[q])
    check("gate round6_capex", scored.get("reproduction_gate", {}).get("round6_capex"),
          gate_got)
    if gate_got != R6_CAPEX_EXPECTED:
        problems.append(f"gate recount itself off: {gate_got} "
                        f"(expected {R6_CAPEX_EXPECTED})")

    # ---- independent round-7 recount ----
    for batch in BATCHES:
        if batch not in scored:
            continue
        got = {}
        for fn in sorted(glob.glob(os.path.join(args.pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                got[rec["q_id"]] = rec
        if set(got) != FOCUS:
            problems.append(f"{batch}: q_id set != FOCUS10")
            continue
        want = scored[batch]
        ok = lambda q: got[q]["predicted_kind"] == truth[q]
        check(f"{batch} total_10", want["total_10"],
              [sum(1 for q in FOCUS if ok(q)), 10])
        check(f"{batch} correct_qids", want["correct_qids"],
              sorted(q for q in FOCUS if ok(q)))
        check(f"{batch} by_subset OLD_designed_from_8",
              want["by_subset"]["OLD_designed_from_8"],
              [sum(1 for q in OLD_SUB if ok(q)), 8])
        check(f"{batch} by_subset NEW_v5_2", want["by_subset"]["NEW_v5_2"],
              [sum(1 for q in NEW_SUB if ok(q)), 2])
        for level in ("high", "medium", "low"):
            qs = [q for q in FOCUS if got[q].get("confidence") == level]
            check(f"{batch} confidence {level}", want["confidence"][level],
                  [sum(1 for q in qs if ok(q)), len(qs)])
        for table, keyfn in (("by_player", lambda q: meta[q]["player"]),
                             ("by_round", lambda q: f"S{meta[q]['season']} {meta[q]['round_label']}")):
            agg = {}
            for q in FOCUS:
                k = keyfn(q)
                c, t = agg.get(k, (0, 0))
                agg[k] = (c + (1 if ok(q) else 0), t + 1)
            check(f"{batch} {table}", want[table],
                  {k: list(v) for k, v in sorted(agg.items())})
        check(f"{batch} guesses", want["guesses"],
              {str(q): got[q]["predicted_kind"] for q in sorted(FOCUS)})
        if batch in EXPERIMENT:
            cited = 0
            for q in FOCUS:
                g = got[q].get("guidance_cited")
                if isinstance(g, dict) and g.get("date") is not None \
                        and g["date"] < meta[q]["round_date"]:
                    cited += 1
            check(f"{batch} guidance_citation", want["guidance_citation"],
                  [cited, 10])
        else:
            check(f"{batch} guidance_citation", want["guidance_citation"], None)

    # ---- group summary recount ----
    if "group_summary" in scored:
        g = scored["group_summary"]
        c = [scored[b]["total_10"][0] for b in CONTROL]
        e = [scored[b]["total_10"][0] for b in EXPERIMENT]
        check("group control_total", g["control_total"], c)
        check("group experiment_total", g["experiment_total"], e)
        check("group M_C", g["M_C"], sum(c) / 5)
        check("group M_E", g["M_E"], sum(e) / 3)
        check("group spread_S", g["spread_S"], max(c) - min(c))
        check("group experiment_diff", g["experiment_diff"], max(e) - min(e))
        check("group M_E_minus_M_C", g["M_E_minus_M_C"], sum(e) / 3 - sum(c) / 5)
        check("group win_rule_a_gain_gt_spread", g["win_rule_a_gain_gt_spread"],
              (sum(e) / 3 - sum(c) / 5) > (max(c) - min(c)))
        check("group win_rule_b_M_E_gt_max_C", g["win_rule_b_M_E_gt_max_C"],
              (sum(e) / 3) > max(c))
        check("group win_rule_c_exp_diff_le_1", g["win_rule_c_exp_diff_le_1"],
              (max(e) - min(e)) <= 1)
        check("group win_rule_d_min_gain_2", g["win_rule_d_min_gain_2"],
              (sum(e) / 3 - sum(c) / 5) >= 2)
        g_rates = [scored[b]["guidance_citation"][0] / 10 for b in EXPERIMENT]
        check("group guidance_citation_mean_G", g["guidance_citation_mean_G"],
              sum(g_rates) / 3)
        check("group win_rule_e_G_ge_80pct", g["win_rule_e_G_ge_80pct"],
              (sum(g_rates) / 3) >= 0.8)

    if problems:
        print("VERIFY FAILED:")
        for p in problems:
            print("  MISMATCH:", p)
        sys.exit(1)
    print(f"VERIFY PASS: score file {score_file} agrees with independent "
          f"recount on every number "
          f"(batches checked: {[b for b in BATCHES if b in scored] or 'none yet'}).")


if __name__ == "__main__":
    main()
