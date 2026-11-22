#!/usr/bin/env python3
"""Independent recount for round-10 scoring (vision-1 round 10).

Re-reads testset-v6.json and the prediction files from scratch and
recomputes every number in score-v10.json with separate code (this file
imports nothing from score_v10.py). Any disagreement exits non-zero.
Also independently re-checks both reproduction gates (round-9 focus
totals C1 10, C2 10, C3 10, E1 12, E2 12 out of 13; round-8 capex
C1 3, C2 1, C3 3, E1 10, E2 10 out of 10).

Usage:
  python3 score_v10_verify.py [--pred-dir DIR] [--score-file FILE]
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round10-vision10-2026-11-22", "predictions")
R9_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round9",
    "runs", "round9-vision9-2026-11-22", "predictions")
R8_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round8",
    "runs", "round8-vision8-2026-11-22", "predictions")

FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
         36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
CAPEX = {11, 12, 13, 14, 16, 17, 18, 19}
NON_CAPEX = FOCUS - CAPEX
CAPEX_DC = CAPEX | {30, 31}
INFRA = {11, 12, 13, 14, 16, 17, 18, 19, 30, 31, 36, 37}
POLICY = {6, 7, 74}
MODEL = {20, 23, 25, 27, 45, 48, 51, 58, 70, 72, 86, 89, 93, 94}
CHIP = {61, 62, 67}
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]
R9_FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 30, 31, 32}
R9_TOTAL_EXPECTED = {"C1": 10, "C2": 10, "C3": 10, "E1": 12, "E2": 12}
R8_CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
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
    score_file = args.score_file or os.path.join(args.pred_dir, "score-v10.json")
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
            problems.append(f"{label}: verify={got} score-v10={want}")

    # ---- independent gate recounts ----
    def load_kinds(pred_dir, batch):
        d = {}
        for fn in sorted(glob.glob(os.path.join(pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                d[rec["q_id"]] = rec["predicted_kind"]
        return d

    gate9 = {}
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        d = load_kinds(R9_PRED_DIR, b)
        gate9[b] = sum(1 for q in R9_FOCUS if d.get(q) == truth[q])
    check("gate round9_focus",
          scored.get("reproduction_gate", {}).get("round9_focus"), gate9)
    if gate9 != R9_TOTAL_EXPECTED:
        problems.append(f"gate9 recount itself off: {gate9} "
                        f"(expected {R9_TOTAL_EXPECTED})")
    gate8 = {}
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        d = load_kinds(R8_PRED_DIR, b)
        gate8[b] = sum(1 for q in R8_CAPEX if d.get(q) == truth[q])
    check("gate round8_capex",
          scored.get("reproduction_gate", {}).get("round8_capex"), gate8)
    if gate8 != R8_CAPEX_EXPECTED:
        problems.append(f"gate8 recount itself off: {gate8} "
                        f"(expected {R8_CAPEX_EXPECTED})")

    # ---- independent round-10 recount ----
    for batch in BATCHES:
        if batch not in scored:
            continue
        got = {}
        for fn in sorted(glob.glob(os.path.join(args.pred_dir,
                                                f"predictions-{batch}-*.json"))):
            for rec in json.load(open(fn)):
                got[rec["q_id"]] = rec
        if set(got) != FOCUS:
            problems.append(f"{batch}: q_id set != FOCUS32")
            continue
        want = scored[batch]
        ok = lambda q: got[q]["predicted_kind"] == truth[q]

        def sub(qs):
            n = sum(1 for q in qs if ok(q))
            return [n, len(qs)], sorted(q for q in qs if ok(q))

        check(f"{batch} total_32", want["total_32"], sub(FOCUS)[0])
        check(f"{batch} correct_qids", want["correct_qids"], sub(FOCUS)[1])
        for label, qs, total in (("infra_capex_12", INFRA, 12),
                                 ("policy_regulatory_3", POLICY, 3),
                                 ("model_release_14", MODEL, 14),
                                 ("chip_supply_3", CHIP, 3),
                                 ("capex_8", CAPEX, 8),
                                 ("non_capex_24", NON_CAPEX, 24)):
            sub_n, sub_q = sub(qs)
            check(f"{batch} {label}", want[label], sub_n)
        # correct-qid lists (explicit keys)
        check(f"{batch} infra_capex_correct_qids",
              want["infra_capex_correct_qids"], sub(INFRA)[1])
        check(f"{batch} policy_regulatory_correct_qids",
              want["policy_regulatory_correct_qids"], sub(POLICY)[1])
        check(f"{batch} model_release_correct_qids",
              want["model_release_correct_qids"], sub(MODEL)[1])
        check(f"{batch} chip_supply_correct_qids",
              want["chip_supply_correct_qids"], sub(CHIP)[1])
        check(f"{batch} capex_correct_qids",
              want["capex_correct_qids"], sub(CAPEX)[1])
        check(f"{batch} non_capex_correct_qids",
              want["non_capex_correct_qids"], sub(NON_CAPEX)[1])
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
        # guidance citation: 8 capex, date strictly before round_date
        cited_g = 0
        for q in CAPEX:
            g = got[q].get("guidance_cited")
            gd = norm_date(g.get("date")) if isinstance(g, dict) else None
            if gd is not None and gd < meta[q]["round_date"]:
                cited_g += 1
        check(f"{batch} guidance_citation", want["guidance_citation"],
              [cited_g, 8])
        # boundary citation: 10 capex + datacenter, step 1-5 + place/money
        cited_b = 0
        for q in CAPEX_DC:
            b = got[q].get("boundary_cited")
            if isinstance(b, dict) and b.get("step") in (
                    1, 2, 3, 4, 5, "1", "2", "3", "4", "5"):
                s = b.get("place_money")
                if isinstance(s, str) and len(s.strip()) > 0:
                    cited_b += 1
        check(f"{batch} boundary_citation", want["boundary_citation"],
              [cited_b, 10])
        # roleplay execution (experiment only): all four fields present
        if batch in EXPERIMENT:
            exec_qids = []
            for q in sorted(FOCUS):
                r = got[q]
                rt = r.get("roleplay_text")
                s25 = r.get("roleplay_step25")
                fp = r.get("forecast_prop")
                prob = r.get("forecast_prob")
                good = (isinstance(rt, str) and rt.strip()
                        and isinstance(s25, dict) and "same" in s25
                        and isinstance(s25.get("note"), str)
                        and s25["note"].strip()
                        and isinstance(fp, str) and fp.strip()
                        and isinstance(prob, (int, float))
                        and not isinstance(prob, bool)
                        and 0.0 <= prob <= 1.0)
                if good:
                    exec_qids.append(q)
            check(f"{batch} roleplay_execution",
                  want["roleplay_execution"],
                  {"executed": [len(exec_qids), 32],
                   "executed_qids": exec_qids,
                   "not_executed_qids": sorted(FOCUS - set(exec_qids))})
        else:
            check(f"{batch} roleplay_execution",
                  want["roleplay_execution"], None)
        # q7 separate
        check(f"{batch} q7_separate correct",
              want["q7_separate"]["correct"], ok(7))
        check(f"{batch} q7_separate predicted_kind",
              want["q7_separate"]["predicted_kind"], got[7]["predicted_kind"])

    # ---- group summary recount ----
    if "group_summary" in scored:
        g = scored["group_summary"]
        c = [scored[b]["total_32"][0] for b in CONTROL]
        e = [scored[b]["total_32"][0] for b in EXPERIMENT]
        check("group control_total", g["control_total"], c)
        check("group experiment_total", g["experiment_total"], e)
        check("group M_TC", g["M_TC"], sum(c) / 3)
        check("group M_TE", g["M_TE"], sum(e) / 2)
        check("group spread_S_T", g["spread_S_T"], max(c) - min(c))
        check("group M_TE_minus_M_TC", g["M_TE_minus_M_TC"],
              sum(e) / 2 - sum(c) / 3)
        for name, key in (("infra", "infra_capex_12"),
                          ("policy", "policy_regulatory_3"),
                          ("model", "model_release_14"),
                          ("chip", "chip_supply_3")):
            check(f"group {name}_C", g[f"{name}_C"],
                  sum(scored[b][key][0] for b in CONTROL) / 3)
            check(f"group {name}_E", g[f"{name}_E"],
                  sum(scored[b][key][0] for b in EXPERIMENT) / 2)
        check("group N_C", g["N_C"],
              sum(scored[b]["non_capex_24"][0] for b in CONTROL) / 3)
        check("group N_E", g["N_E"],
              sum(scored[b]["non_capex_24"][0] for b in EXPERIMENT) / 2)
        check("group N_E_minus_N_C", g["N_E_minus_N_C"],
              sum(scored[b]["non_capex_24"][0] for b in EXPERIMENT) / 2
              - sum(scored[b]["non_capex_24"][0] for b in CONTROL) / 3)
        check("group C_C", g["C_C"],
              sum(scored[b]["capex_8"][0] for b in CONTROL) / 3)
        check("group C_E", g["C_E"],
              sum(scored[b]["capex_8"][0] for b in EXPERIMENT) / 2)
        r_mean = sum(scored[b]["roleplay_execution"]["executed"][0] / 32
                     for b in EXPERIMENT) / 2
        check("group R_mean", g["R_mean"], r_mean)
        check("group G_C", g["G_C"],
              sum(scored[b]["guidance_citation"][0] / 8 for b in CONTROL) / 3)
        check("group G_E", g["G_E"],
              sum(scored[b]["guidance_citation"][0] / 8 for b in EXPERIMENT) / 2)
        check("group B_C", g["B_C"],
              sum(scored[b]["boundary_citation"][0] / 10 for b in CONTROL) / 3)
        check("group B_E", g["B_E"],
              sum(scored[b]["boundary_citation"][0] / 10 for b in EXPERIMENT) / 2)
        m_tc, m_te = sum(c) / 3, sum(e) / 2
        s_t = max(c) - min(c)
        model_c = sum(scored[b]["model_release_14"][0] for b in CONTROL) / 3
        model_e = sum(scored[b]["model_release_14"][0] for b in EXPERIMENT) / 2
        n_c = sum(scored[b]["non_capex_24"][0] for b in CONTROL) / 3
        n_e = sum(scored[b]["non_capex_24"][0] for b in EXPERIMENT) / 2
        rule_a = (m_te - m_tc) > s_t
        rule_b = m_te > max(c)
        rule_c = (n_e - n_c) > 0
        rule_d = model_e >= model_c - 1
        rule_e = r_mean >= 0.8
        check("group rule_a", g["rule_a_gain_gt_noise"], rule_a)
        check("group rule_b", g["rule_b_M_TE_gt_max_control"], rule_b)
        check("group rule_c", g["rule_c_non_capex_gain_gt_0"], rule_c)
        check("group rule_d", g["rule_d_model_not_hurt_gt_1"], rule_d)
        check("group rule_e", g["rule_e_R_ge_80pct"], rule_e)
        check("group KEEP", g["KEEP_all_five"],
              rule_a and rule_b and rule_c and rule_d and rule_e)
        check("group DROP", g["DROP_any"],
              (m_te <= m_tc) or (model_e < model_c - 2) or (r_mean < 0.5))
        check("group MIXED", g["MIXED_helped_no_keep"],
              (not rule_a) and rule_c and rule_d and rule_e)

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
