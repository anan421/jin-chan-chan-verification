#!/usr/bin/env python3
"""Independent recount for round-9 scoring (vision-1 round 9).

Re-reads testset-v6.json and the prediction files from scratch and
recomputes every number in score-v9.json with separate code (this file
imports nothing from score_v9.py). Any disagreement exits non-zero.
Also independently re-checks both reproduction gates (round-7 capex
C1 2, C2 1, C3 2, C4 2, C5 2, E1 10, E2 10, E3 10; round-8 capex
C1 3, C2 1, C3 3, E1 10, E2 10).

Usage:
  python3 score_v9_verify.py [--pred-dir DIR] [--score-file FILE]
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round9-vision9-2026-11-22", "predictions")
R7_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round7",
    "runs", "round7-vision7-2026-11-22", "predictions")
R8_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round8",
    "runs", "round8-vision8-2026-11-22", "predictions")

FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 30, 31, 32}
CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
DC = {30, 31, 32}
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]
R7_CAPEX_EXPECTED = {"C1": 2, "C2": 1, "C3": 2, "C4": 2, "C5": 2,
                     "E1": 10, "E2": 10, "E3": 10}
R8_CAPEX_EXPECTED = {"C1": 3, "C2": 1, "C3": 3, "E1": 10, "E2": 10}


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
    score_file = args.score_file or os.path.join(args.pred_dir, "score-v9.json")
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
            problems.append(f"{label}: verify={got} score-v9={want}")

    # ---- independent gate recounts ----
    def load_kinds(pred_dir, batch):
        d = {}
        for fn in sorted(glob.glob(os.path.join(pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                d[rec["q_id"]] = rec["predicted_kind"]
        return d

    gate7 = {}
    for b in ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]:
        d = load_kinds(R7_PRED_DIR, b)
        gate7[b] = sum(1 for q in CAPEX if d.get(q) == truth[q])
    check("gate round7_capex", scored.get("reproduction_gate", {}).get("round7_capex"),
          gate7)
    if gate7 != R7_CAPEX_EXPECTED:
        problems.append(f"gate7 recount itself off: {gate7} "
                        f"(expected {R7_CAPEX_EXPECTED})")
    gate8 = {}
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        d = load_kinds(R8_PRED_DIR, b)
        gate8[b] = sum(1 for q in CAPEX if d.get(q) == truth[q])
    check("gate round8_capex", scored.get("reproduction_gate", {}).get("round8_capex"),
          gate8)
    if gate8 != R8_CAPEX_EXPECTED:
        problems.append(f"gate8 recount itself off: {gate8} "
                        f"(expected {R8_CAPEX_EXPECTED})")

    # ---- independent round-9 recount ----
    for batch in BATCHES:
        if batch not in scored:
            continue
        got = {}
        for fn in sorted(glob.glob(os.path.join(args.pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                got[rec["q_id"]] = rec
        if set(got) != FOCUS:
            problems.append(f"{batch}: q_id set != FOCUS13")
            continue
        want = scored[batch]
        ok = lambda q: got[q]["predicted_kind"] == truth[q]
        check(f"{batch} total_13", want["total_13"],
              [sum(1 for q in FOCUS if ok(q)), 13])
        check(f"{batch} correct_qids", want["correct_qids"],
              sorted(q for q in FOCUS if ok(q)))
        check(f"{batch} datacenter_3", want["datacenter_3"],
              [sum(1 for q in DC if ok(q)), 3])
        check(f"{batch} datacenter_correct_qids", want["datacenter_correct_qids"],
              sorted(q for q in DC if ok(q)))
        check(f"{batch} capex_10", want["capex_10"],
              [sum(1 for q in CAPEX if ok(q)), 10])
        check(f"{batch} capex_correct_qids", want["capex_correct_qids"],
              sorted(q for q in CAPEX if ok(q)))
        x_qids = sorted(q for q in DC if got[q]["predicted_kind"] == "capex")
        y_qids = sorted(q for q in CAPEX if got[q]["predicted_kind"] == "datacenter")
        check(f"{batch} miscall_X", want["miscall_dc_as_capex_X"], len(x_qids))
        check(f"{batch} miscall_X_qids", want["miscall_dc_as_capex_qids"], x_qids)
        check(f"{batch} miscall_Y", want["miscall_capex_as_dc_Y"], len(y_qids))
        check(f"{batch} miscall_Y_qids", want["miscall_capex_as_dc_qids"], y_qids)
        for level in ("high", "medium", "low"):
            qs = [q for q in FOCUS if got[q].get("confidence") == level]
            check(f"{batch} confidence {level}", want["confidence"][level],
                  [sum(1 for q in qs if ok(q)), len(qs)])
        for table, keyfn in (("by_player", lambda q: meta[q]["player"]),
                             ("by_round", lambda q: f"S{meta[q]['season']} {meta[q]['round_label']}"),
                             ("by_kind", lambda q: meta[q]["kind"])):
            agg = {}
            for q in FOCUS:
                k = keyfn(q)
                c, t = agg.get(k, (0, 0))
                agg[k] = (c + (1 if ok(q) else 0), t + 1)
            check(f"{batch} {table}", want[table],
                  {k: list(v) for k, v in sorted(agg.items())})
        check(f"{batch} guesses", want["guesses"],
              {str(q): got[q]["predicted_kind"] for q in sorted(FOCUS)})
        cited_g = 0
        for q in CAPEX:
            g = got[q].get("guidance_cited")
            gd = norm_date(g.get("date")) if isinstance(g, dict) else None
            if gd is not None and gd < meta[q]["round_date"]:
                cited_g += 1
        check(f"{batch} guidance_citation", want["guidance_citation"],
              [cited_g, 10])
        if batch in EXPERIMENT:
            cited_b = 0
            for q in FOCUS:
                b = got[q].get("boundary_cited")
                if isinstance(b, dict) and b.get("step") in (
                        1, 2, 3, 4, 5, "1", "2", "3", "4", "5"):
                    s = b.get("place_money")
                    if isinstance(s, str) and len(s.strip()) > 0:
                        cited_b += 1
            check(f"{batch} boundary_citation", want["boundary_citation"],
                  [cited_b, 13])
        else:
            check(f"{batch} boundary_citation", want["boundary_citation"], None)

    # ---- group summary recount ----
    if "group_summary" in scored:
        g = scored["group_summary"]
        c = [scored[b]["total_13"][0] for b in CONTROL]
        e = [scored[b]["total_13"][0] for b in EXPERIMENT]
        cdc = [scored[b]["datacenter_3"][0] for b in CONTROL]
        edc = [scored[b]["datacenter_3"][0] for b in EXPERIMENT]
        ccap = [scored[b]["capex_10"][0] for b in CONTROL]
        ecap = [scored[b]["capex_10"][0] for b in EXPERIMENT]
        cx = [scored[b]["miscall_dc_as_capex_X"] for b in CONTROL]
        ex = [scored[b]["miscall_dc_as_capex_X"] for b in EXPERIMENT]
        cy = [scored[b]["miscall_capex_as_dc_Y"] for b in CONTROL]
        ey = [scored[b]["miscall_capex_as_dc_Y"] for b in EXPERIMENT]
        check("group control_total", g["control_total"], c)
        check("group experiment_total", g["experiment_total"], e)
        check("group M_TC", g["M_TC"], sum(c) / 3)
        check("group M_TE", g["M_TE"], sum(e) / 2)
        check("group spread_S_T", g["spread_S_T"], max(c) - min(c))
        check("group M_TE_minus_M_TC", g["M_TE_minus_M_TC"], sum(e) / 2 - sum(c) / 3)
        check("group D_C", g["D_C"], sum(cdc) / 3)
        check("group D_E", g["D_E"], sum(edc) / 2)
        check("group spread_S_D", g["spread_S_D"], max(cdc) - min(cdc))
        check("group C_C", g["C_C"], sum(ccap) / 3)
        check("group C_E", g["C_E"], sum(ecap) / 2)
        check("group X_C", g["X_C"], sum(cx) / 3)
        check("group X_E", g["X_E"], sum(ex) / 2)
        check("group spread_S_X", g["spread_S_X"], max(cx) - min(cx))
        check("group Y_C", g["Y_C"], sum(cy) / 3)
        check("group Y_E", g["Y_E"], sum(ey) / 2)
        g_rates = [scored[b]["guidance_citation"][0] / 10 for b in BATCHES]
        check("group guidance_citation_mean_G", g["guidance_citation_mean_G"],
              sum(g_rates) / 5)
        b_rates = [scored[b]["boundary_citation"][0] / 13 for b in EXPERIMENT]
        check("group boundary_citation_mean_B", g["boundary_citation_mean_B"],
              sum(b_rates) / 2)
        check("group rule_a", g["rule_a_gain_gt_noise"],
              (sum(e) / 2 - sum(c) / 3) > (max(c) - min(c)))
        check("group rule_b", g["rule_b_dc_ge_2"],
              (sum(edc) / 2 >= 2) and all(d >= 2 for d in edc))
        check("group rule_c", g["rule_c_capex_ge_9"],
              (sum(ecap) / 2 >= 9) and all(v >= 9 for v in ecap))
        check("group rule_d", g["rule_d_miscalls"],
              (sum(ex) / 2 <= sum(cx) / 3 - 1) and (sum(ey) / 2 <= 1.0))
        check("group rule_e", g["rule_e_B_ge_80pct"], sum(b_rates) / 2 >= 0.8)

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
