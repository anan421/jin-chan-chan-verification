#!/usr/bin/env python3
"""Independent recount for round-6 scoring (vision-1 round 6).

Re-reads testset-v5.json and the prediction files from scratch and
recomputes every number in score-v6.json with separate code (this file
imports nothing from score_v6.py). Any disagreement exits non-zero.
Also independently re-checks the round-5 reproduction gate numbers
(trial1 clean 10/20, trial2 clean 6/21).

Usage:
  python3 score_v6_verify.py [--pred-dir DIR] [--score-file FILE]
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round6-vision6-2026-11-22", "predictions")
R5_TRIAL = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-weakest-link",
    "runs", "weakest-link-vision5-2026-11-22", "trial")

FOCUS = {5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
         30, 31, 32, 36, 37, 61, 62, 63, 67, 74, 92, 93}
EXCLUDED = {7, 30}
CLEAN = FOCUS - EXCLUDED
M_SUB = {10, 11, 12, 13, 14, 15, 17, 18, 31, 37, 67, 92, 93}
Q_SUB = {5, 6, 36, 61, 74}
N_SUB = {16, 19, 32, 8, 62, 63}
CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
R5_TO_V5 = {5: 5, 6: 6, 7: 7, 8: 9, 9: 10, 10: 11, 11: 12, 12: 13, 13: 14,
            14: 15, 15: 17, 16: 18, 26: 30, 27: 31, 31: 36, 32: 37,
            53: 61, 57: 67, 64: 74, 81: 92, 82: 93}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--score-file", default=None)
    args = ap.parse_args()
    score_file = args.score_file or os.path.join(args.pred_dir, "score-v6.json")
    if not os.path.exists(score_file):
        print(f"no score file yet: {score_file}")
        sys.exit(2)
    scored = json.load(open(score_file))
    ts = json.load(open(os.path.join(BASE, "testset-v5.json")))
    truth = {q["q_id"]: q["kind"] for q in ts["questions"]}
    meta = {q["q_id"]: q for q in ts["questions"]}
    problems = []

    def check(label, got, want):
        if got != want:
            problems.append(f"{label}: verify={got} score-v6={want}")

    # ---- independent round-5 gate recount ----
    def load_trial(pat, repl=None):
        d = {}
        for fn in sorted(glob.glob(os.path.join(R5_TRIAL, pat))):
            for rec in json.load(open(fn)):
                d[R5_TO_V5[rec["q_id"]]] = rec["predicted_kind"]
        if repl:
            for rec in json.load(open(os.path.join(R5_TRIAL, repl))):
                d[R5_TO_V5[rec["q_id"]]] = rec["predicted_kind"]
        return d
    t1 = load_trial("predictions-trial1-*.json")
    t2c = load_trial("predictions-trial2-*.json",
                     repl="predictions-trial2b-S5-3-2.json")
    t1_clean_n = sum(1 for q in t1 if q != 14 and t1[q] == truth[q])
    t2_clean_n = sum(1 for q in t2c if t2c[q] == truth[q])
    check("gate trial1_clean", scored.get("reproduction_gate", {}).get("trial1_clean"),
          [t1_clean_n, 20])
    check("gate trial2_clean", scored.get("reproduction_gate", {}).get("trial2_clean"),
          [t2_clean_n, 21])
    if [t1_clean_n, 20] != [10, 20] or [t2_clean_n, 21] != [6, 21]:
        problems.append(f"gate recount itself off: trial1 {t1_clean_n}/20, "
                        f"trial2 {t2_clean_n}/21 (expected 10/20, 6/21)")

    # ---- independent round-6 recount ----
    for batch in BATCHES:
        if batch not in scored:
            continue
        got = {}
        for fn in sorted(glob.glob(os.path.join(args.pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                got[rec["q_id"]] = rec
        if set(got) != FOCUS:
            problems.append(f"{batch}: q_id set != FOCUS26")
            continue
        want = scored[batch]
        ok = lambda q: got[q]["predicted_kind"] == truth[q]
        check(f"{batch} raw_26", want["raw_26"],
              [sum(1 for q in FOCUS if ok(q)), 26])
        check(f"{batch} clean_24", want["clean_24"],
              [sum(1 for q in CLEAN if ok(q)), 24])
        check(f"{batch} correct_qids_raw", want["correct_qids_raw"],
              sorted(q for q in FOCUS if ok(q)))
        check(f"{batch} correct_qids_clean", want["correct_qids_clean"],
              sorted(q for q in CLEAN if ok(q)))
        for subset, ids, n in (("M_method_13", M_SUB, 13),
                               ("Q_no_precursor_5", Q_SUB, 5),
                               ("N_new_6", N_SUB, 6)):
            check(f"{batch} by_subset {subset}", want["by_subset"][subset],
                  [sum(1 for q in ids if ok(q)), n])
        check(f"{batch} capex_10", want["capex_10"],
              [sum(1 for q in CAPEX if ok(q)), 10])
        check(f"{batch} excluded q7", want["excluded"]["q7_bis_rule_BYTE"], ok(7))
        check(f"{batch} excluded q30", want["excluded"]["q30_datacenter_BYTE"], ok(30))
        for level in ("high", "medium", "low"):
            qs = [q for q in FOCUS if got[q].get("confidence") == level]
            check(f"{batch} confidence {level}", want["confidence"][level],
                  [sum(1 for q in qs if ok(q)), len(qs)])
        for table, keyfn in (("by_kind", lambda q: truth[q]),
                             ("by_player", lambda q: meta[q]["player"]),
                             ("by_round", lambda q: f"S{meta[q]['season']} {meta[q]['round_label']}")):
            agg = {}
            for q in CLEAN:
                k = keyfn(q)
                c, t = agg.get(k, (0, 0))
                agg[k] = (c + (1 if ok(q) else 0), t + 1)
            check(f"{batch} {table}", want[table],
                  {k: list(v) for k, v in sorted(agg.items())})
        check(f"{batch} guesses", want["guesses"],
              {str(q): got[q]["predicted_kind"] for q in sorted(FOCUS)})

    # ---- group summary recount ----
    if "group_summary" in scored:
        g = scored["group_summary"]
        c = [scored[b]["clean_24"][0] for b in ("C1", "C2", "C3")]
        e = [scored[b]["clean_24"][0] for b in ("E1", "E2")]
        check("group control_clean", g["control_clean"], c)
        check("group experiment_clean", g["experiment_clean"], e)
        check("group M_C", g["M_C"], sum(c) / 3)
        check("group M_E", g["M_E"], sum(e) / 2)
        check("group spread_S", g["spread_S"], max(c) - min(c))
        check("group M_E_minus_M_C", g["M_E_minus_M_C"], sum(e) / 2 - sum(c) / 3)
        cc = [scored[b]["capex_10"][0] for b in ("C1", "C2", "C3")]
        ee = [scored[b]["capex_10"][0] for b in ("E1", "E2")]
        check("group capex control", g["capex"]["control"], cc)
        check("group capex experiment", g["capex"]["experiment"], ee)
        check("group capex experiment_diff", g["capex"]["experiment_diff"],
              max(ee) - min(ee))
        check("group capex control_spread", g["capex"]["control_spread"],
              max(cc) - min(cc))

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
