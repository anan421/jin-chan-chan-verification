#!/usr/bin/env python3
"""Independent recount for round-8 scoring (vision-1 round 8).

Re-reads testset-v6.json and the prediction files from scratch and
recomputes every number in score-v8.json with separate code (this file
imports nothing from score_v8.py). Any disagreement exits non-zero.
Also independently re-checks the round-7 capex reproduction gate numbers
(C1 2, C2 1, C3 2, C4 2, C5 2, E1 10, E2 10, E3 10).

Usage:
  python3 score_v8_verify.py [--pred-dir DIR] [--score-file FILE]
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round8-vision8-2026-11-22", "predictions")
R7_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round7",
    "runs", "round7-vision7-2026-11-22", "predictions")

CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
NEW_SUB = {8, 16, 19, 24, 32, 43, 44, 49, 63}
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]
R7_CAPEX_EXPECTED = {"C1": 2, "C2": 1, "C3": 2, "C4": 2, "C5": 2,
                     "E1": 10, "E2": 10, "E3": 10}


def norm_date(d):
    if isinstance(d, int):
        return d
    if isinstance(d, str):
        s = d.strip().replace("-", "")
        if len(s) == 8 and s.isdigit():
            return int(s)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--score-file", default=None)
    args = ap.parse_args()
    score_file = args.score_file or os.path.join(args.pred_dir, "score-v8.json")
    if not os.path.exists(score_file):
        print(f"no score file yet: {score_file}")
        sys.exit(2)
    scored = json.load(open(score_file))
    ts = json.load(open(os.path.join(BASE, "testset-v6.json")))
    truth = {q["q_id"]: q["kind"] for q in ts["questions"]}
    meta = {q["q_id"]: q for q in ts["questions"]}
    ALL = set(truth)
    NONCAPEX = [q for q in sorted(ALL) if q not in CAPEX]
    problems = []

    def check(label, got, want):
        if got != want:
            problems.append(f"{label}: verify={got} score-v8={want}")

    # ---- independent round-7 capex gate recount ----
    def load_r7(batch):
        d = {}
        for fn in sorted(glob.glob(os.path.join(R7_PRED_DIR,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                d[rec["q_id"]] = rec["predicted_kind"]
        return d
    gate_got = {}
    for b in ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]:
        d = load_r7(b)
        gate_got[b] = sum(1 for q in CAPEX if d.get(q) == truth[q])
    check("gate round7_capex", scored.get("reproduction_gate", {}).get("round7_capex"),
          gate_got)
    if gate_got != R7_CAPEX_EXPECTED:
        problems.append(f"gate recount itself off: {gate_got} "
                        f"(expected {R7_CAPEX_EXPECTED})")

    # ---- independent round-8 recount ----
    for batch in BATCHES:
        if batch not in scored:
            continue
        got = {}
        for fn in sorted(glob.glob(os.path.join(args.pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                got[rec["q_id"]] = rec
        if set(got) != ALL:
            problems.append(f"{batch}: q_id set != ALL98")
            continue
        want = scored[batch]
        ok = lambda q: got[q]["predicted_kind"] == truth[q]
        check(f"{batch} total_98", want["total_98"],
              [sum(1 for q in ALL if ok(q)), 98])
        check(f"{batch} correct_qids", want["correct_qids"],
              sorted(q for q in ALL if ok(q)))
        check(f"{batch} capex_10", want["capex_10"],
              [sum(1 for q in CAPEX if ok(q)), 10])
        check(f"{batch} capex_correct_qids", want["capex_correct_qids"],
              sorted(q for q in CAPEX if ok(q)))
        check(f"{batch} noncapex_88", want["noncapex_88"],
              [sum(1 for q in NONCAPEX if ok(q)), 88])
        false_qids = sorted(q for q in NONCAPEX
                            if got[q]["predicted_kind"] == "capex")
        check(f"{batch} false_capex_F", want["false_capex_F"], len(false_qids))
        check(f"{batch} false_capex_qids", want["false_capex_qids"], false_qids)
        fbk = {}
        for q in false_qids:
            fbk[truth[q]] = fbk.get(truth[q], 0) + 1
        check(f"{batch} false_capex_by_true_kind",
              want["false_capex_by_true_kind"], dict(sorted(fbk.items())))
        check(f"{batch} by_subset OLD_89", want["by_subset"]["OLD_89"],
              [sum(1 for q in ALL if q not in NEW_SUB and ok(q)), 89])
        check(f"{batch} by_subset NEW_v5_9", want["by_subset"]["NEW_v5_9"],
              [sum(1 for q in NEW_SUB if ok(q)), 9])
        for level in ("high", "medium", "low"):
            qs = [q for q in ALL if got[q].get("confidence") == level]
            check(f"{batch} confidence {level}", want["confidence"][level],
                  [sum(1 for q in qs if ok(q)), len(qs)])
        for table, keyfn in (("by_player", lambda q: meta[q]["player"]),
                             ("by_round", lambda q: f"S{meta[q]['season']} {meta[q]['round_label']}"),
                             ("by_kind", lambda q: meta[q]["kind"])):
            agg = {}
            for q in ALL:
                k = keyfn(q)
                c, t = agg.get(k, (0, 0))
                agg[k] = (c + (1 if ok(q) else 0), t + 1)
            check(f"{batch} {table}", want[table],
                  {k: list(v) for k, v in sorted(agg.items())})
        check(f"{batch} guesses", want["guesses"],
              {str(q): got[q]["predicted_kind"] for q in sorted(ALL)})
        if batch in EXPERIMENT:
            cited = 0
            for q in CAPEX:
                g = got[q].get("guidance_cited")
                gd = norm_date(g.get("date")) if isinstance(g, dict) else None
                if gd is not None and gd < meta[q]["round_date"]:
                    cited += 1
            check(f"{batch} guidance_citation", want["guidance_citation"],
                  [cited, 10])
        else:
            check(f"{batch} guidance_citation", want["guidance_citation"], None)

    # ---- group summary recount ----
    if "group_summary" in scored:
        g = scored["group_summary"]
        c = [scored[b]["total_98"][0] for b in CONTROL]
        e = [scored[b]["total_98"][0] for b in EXPERIMENT]
        cf = [scored[b]["false_capex_F"] for b in CONTROL]
        ef = [scored[b]["false_capex_F"] for b in EXPERIMENT]
        ecap = [scored[b]["capex_10"][0] for b in EXPERIMENT]
        check("group control_total", g["control_total"], c)
        check("group experiment_total", g["experiment_total"], e)
        check("group M_TC", g["M_TC"], sum(c) / 3)
        check("group M_TE", g["M_TE"], sum(e) / 2)
        check("group spread_S_T", g["spread_S_T"], max(c) - min(c))
        check("group M_TE_minus_M_TC", g["M_TE_minus_M_TC"], sum(e) / 2 - sum(c) / 3)
        check("group control_false_capex", g["control_false_capex"], cf)
        check("group experiment_false_capex", g["experiment_false_capex"], ef)
        check("group F_C", g["F_C"], sum(cf) / 3)
        check("group F_E", g["F_E"], sum(ef) / 2)
        check("group spread_S_F", g["spread_S_F"], max(cf) - min(cf))
        check("group F_E_minus_F_C", g["F_E_minus_F_C"],
              sum(ef) / 2 - sum(cf) / 3)
        check("group C_E", g["C_E"], sum(ecap) / 2)
        g_rates = [scored[b]["guidance_citation"][0] / 10 for b in EXPERIMENT]
        check("group guidance_citation_mean_G", g["guidance_citation_mean_G"],
              sum(g_rates) / 2)
        check("group rule_a", g["rule_a_M_TE_gt_M_TC"], (sum(e) / 2) > (sum(c) / 3))
        check("group rule_b", g["rule_b_spillover_within_noise"],
              (sum(ef) / 2 - sum(cf) / 3) <= (max(cf) - min(cf)))
        check("group rule_c", g["rule_c_C_E_ge_9"], (sum(ecap) / 2) >= 9)
        check("group rule_d", g["rule_d_G_ge_80pct"], (sum(g_rates) / 2) >= 0.8)

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
