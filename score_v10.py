#!/usr/bin/env python3
"""Score vision-1 round 10 (roleplay + forward guidance vs forward
guidance only, single rule).

Truth: testset-v6.json. Predictions:
  runs/round10-vision10-2026-11-22/predictions/
  predictions-{C1|C2|C3|E1|E2}-S{season}-{round}.json, one file per round.
  Record format: q_id, player, predicted_kind, confidence, reasoning,
  facts_used (each with date, fact, source), guidance_cited
  ({source, date, quote} or null, both groups), boundary_cited
  ({step, place_money} or null, both groups), plus for the experiment
  group only: roleplay_text, roleplay_step25 ({same, note}),
  forecast_prop, forecast_prob.
  Output: score-v10.json next to the predictions. The scored set is
  the 32 round-10 questions only.

REPRODUCTION GATES (run first, every time, unless --skip-reproduction):
  1. round-9 focus gate: re-score the round-9 batches' 13 focus
     questions (capex q10-19 + datacenter q30-32) and must reproduce
     the round-9 report exactly: control C1 10, C2 10, C3 10;
     experiment E1 12, E2 12 (out of 13).
  2. round-8 capex gate: re-score the round-8 batches' capex
     predictions and must reproduce the round-8 report exactly:
     control C1 3, C2 1, C3 3; experiment E1 10, E2 10 (out of 10).
  If either gate fails, the script exits non-zero and scores nothing.
  Gate results are also written to reproduce-v10.json next to the
  predictions (and into score-v10.json under "reproduction_gate").

Per batch (C1-C3, E1-E2) the output has:
  total_32, per prototype category (infra_capex 12, policy_regulatory 3,
  model_release 14, chip_supply 3), capex_8 (q11-19), non_capex_24,
  per-round (16 rounds), per-kind (13 kinds), per-player,
  confidence calibration (high/medium/low correct/total),
  roleplay execution (experiment only, mechanical: roleplay_text +
  roleplay_step25 + forecast_prop + forecast_prob all present),
  guidance citation (both groups: 8 capex predictions with a valid
  guidance_cited, date strictly before the round_date; content
  validity is the audit's job),
  boundary citation (both groups: 10 capex + datacenter predictions
  with boundary_cited step 1-5 and a place/money sentence; content
  validity is the audit's job),
  q7 reported separately (known hard question, expected 0 for both
  groups; a correct guess is flagged for audit, not celebrated).
Group summary: control mean total M_TC and spread S_T over C1-C3,
  experiment mean total M_TE over E1-E2, per-category means,
  non-capex means N_C/N_E, capex means C_C/C_E, roleplay mean R,
  guidance means G_C/G_E, boundary means B_C/B_E, and the
  decision-rule inputs from the design:
  (a) M_TE - M_TC > S_T, (b) M_TE > max(T_C), (c) N_E - N_C > 0,
  (d) model_E >= model_C - 1, (e) R >= 80%.
  KEEP = all five; DROP = M_TE <= M_TC or model_E < model_C - 2 or
  R < 50%; MIXED = (c)(d)(e) pass but (a) fails.

Usage:
  python3 score_v10.py [--pred-dir DIR] [--out FILE] [--reproduce-only]
                       [--skip-reproduction]
  With no prediction files present yet, the script still runs the
  reproduction gates and reports "no round-10 batches yet", writing
  reproduce-v10.json (and a gate-only score-v10.json).
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round10-vision10-2026-11-22", "predictions")
R9_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round9",
    "runs", "round9-vision9-2026-11-22", "predictions")
R8_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round8",
    "runs", "round8-vision8-2026-11-22", "predictions")

# 32 round-10 questions (design/experiment-vision10-round10.md).
FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
         36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
CAPEX = {11, 12, 13, 14, 16, 17, 18, 19}          # capex, 8 questions
NON_CAPEX = FOCUS - CAPEX                          # 24 questions
DATACENTER = {30, 31}                              # datacenter, 2 questions
CAPEX_DC = CAPEX | DATACENTER                      # 10 questions (B set)
INFRA_CAPEX = {11, 12, 13, 14, 16, 17, 18, 19, 30, 31, 36, 37}  # 12
POLICY = {6, 7, 74}                                # 3
MODEL = {20, 23, 25, 27, 45, 48, 51, 58, 70, 72, 86, 89, 93, 94}  # 14
CHIP = {61, 62, 67}                                # 3
CATEGORIES = {"infra_capex": INFRA_CAPEX, "policy_regulatory": POLICY,
              "model_release": MODEL, "chip_supply": CHIP}
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]
# Round-9 focus scores to reproduce (round-9 report, total_13).
R9_FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 30, 31, 32}
R9_TOTAL_EXPECTED = {"C1": 10, "C2": 10, "C3": 10, "E1": 12, "E2": 12}
# Round-8 capex scores to reproduce (round-8 report, capex table).
R8_CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
R8_CAPEX_EXPECTED = {"C1": 3, "C2": 1, "C3": 3, "E1": 10, "E2": 10}


def load_truth():
    ts = json.load(open(os.path.join(BASE, "testset-v6.json")))
    qs = ts["questions"] if isinstance(ts, dict) else ts
    return {q["q_id"]: q for q in qs}


def is_correct(preds, truth, qid):
    return preds[qid]["predicted_kind"] == truth[qid]["kind"]


def norm_date(d):
    """Normalize a date to int YYYYMMDD. Accepts int YYYYMMDD, string
    'YYYYMMDD', or string 'YYYY-MM-DD'. Returns None if unparseable.
    A YYYYMM-only value is NOT a full date: return None (do not invent
    a day)."""
    if isinstance(d, int):
        return d
    if isinstance(d, str):
        s = d.strip().replace("-", "")
        if len(s) == 8 and s.isdigit():
            return int(s)
    return None


def guidance_cited_ok(pred, truth, qid):
    """Mechanical citation check: guidance_cited present, with a date
    strictly before the question's round_date. Content validity (is the
    cited guidance actually guidance, not the event itself) is the
    audit's job; this only checks presence + date."""
    g = pred.get("guidance_cited")
    if not isinstance(g, dict):
        return False
    d = norm_date(g.get("date"))
    if d is None:
        return False
    return d < truth[qid]["round_date"]


def boundary_cited_ok(pred):
    """Mechanical boundary-citation check: boundary_cited present, with a
    step 1-5 and a non-empty place/money sentence. Content validity (did
    the step actually apply, is the place/money sentence true) is the
    audit's job; this only checks presence + shape."""
    b = pred.get("boundary_cited")
    if not isinstance(b, dict):
        return False
    if b.get("step") not in (1, 2, 3, 4, 5, "1", "2", "3", "4", "5"):
        return False
    s = b.get("place_money")
    return isinstance(s, str) and len(s.strip()) > 0


def roleplay_executed_ok(pred):
    """Mechanical roleplay-execution check (experiment group only):
    roleplay_text (decision-maker text) + roleplay_step25 (step-2.5
    answer, {same, note}) + forecast_prop (product-format proposition)
    + forecast_prob (0-1 probability) all present and well-formed.
    Missing any one of the four means not executed."""
    rt = pred.get("roleplay_text")
    if not isinstance(rt, str) or not rt.strip():
        return False
    s25 = pred.get("roleplay_step25")
    if not isinstance(s25, dict):
        return False
    if "same" not in s25:
        return False
    note = s25.get("note")
    if not isinstance(note, str) or not note.strip():
        return False
    fp = pred.get("forecast_prop")
    if not isinstance(fp, str) or not fp.strip():
        return False
    prob = pred.get("forecast_prob")
    if isinstance(prob, bool) or not isinstance(prob, (int, float)):
        return False
    return 0.0 <= prob <= 1.0


def score_preds(preds, truth, qids):
    """Core scoring logic, shared by round-10 batches and the gates."""
    correct = [q for q in qids if is_correct(preds, truth, q)]
    by_player = defaultdict(lambda: [0, 0])
    by_round = defaultdict(lambda: [0, 0])
    by_kind = defaultdict(lambda: [0, 0])
    for q in qids:
        t = truth[q]
        by_player[t["player"]][1] += 1
        by_round[f"S{t['season']} {t['round_label']}"][1] += 1
        by_kind[t["kind"]][1] += 1
        if q in correct:
            by_player[t["player"]][0] += 1
            by_round[f"S{t['season']} {t['round_label']}"][0] += 1
            by_kind[t["kind"]][0] += 1
    return {
        "correct": len(correct), "total": len(qids),
        "correct_qids": sorted(correct),
        "by_player": {k: v for k, v in sorted(by_player.items())},
        "by_round": {k: v for k, v in sorted(by_round.items())},
        "by_kind": {k: v for k, v in sorted(by_kind.items())},
    }


def score_batch(preds, truth, batch, all_qids):
    """Full per-batch report for one round-10 batch (exactly the 32 focus q_ids)."""
    assert set(preds) == set(all_qids), (
        f"batch q_id set != FOCUS32: missing {sorted(set(all_qids) - set(preds))}, "
        f"extra {sorted(set(preds) - set(all_qids))}")
    total = score_preds(preds, truth, sorted(all_qids))
    cats = {name: score_preds(preds, truth, sorted(qs))
            for name, qs in CATEGORIES.items()}
    capex = score_preds(preds, truth, sorted(CAPEX))
    non_capex = score_preds(preds, truth, sorted(NON_CAPEX))
    cited_g = [len([q for q in CAPEX
                    if guidance_cited_ok(preds[q], truth, q)]), 8]
    cited_b = [len([q for q in sorted(CAPEX_DC)
                    if boundary_cited_ok(preds[q])]), 10]
    rp = None
    if batch in EXPERIMENT:
        rp_qids = sorted(q for q in sorted(all_qids)
                         if roleplay_executed_ok(preds[q]))
        rp = {"executed": [len(rp_qids), 32],
              "executed_qids": rp_qids,
              "not_executed_qids": sorted(set(all_qids) - set(rp_qids))}
    out = {
        "total_32": [total["correct"], 32],
        "correct_qids": total["correct_qids"],
        "infra_capex_12": [cats["infra_capex"]["correct"], 12],
        "infra_capex_correct_qids": cats["infra_capex"]["correct_qids"],
        "policy_regulatory_3": [cats["policy_regulatory"]["correct"], 3],
        "policy_regulatory_correct_qids": cats["policy_regulatory"]["correct_qids"],
        "model_release_14": [cats["model_release"]["correct"], 14],
        "model_release_correct_qids": cats["model_release"]["correct_qids"],
        "chip_supply_3": [cats["chip_supply"]["correct"], 3],
        "chip_supply_correct_qids": cats["chip_supply"]["correct_qids"],
        "capex_8": [capex["correct"], 8],
        "capex_correct_qids": capex["correct_qids"],
        "non_capex_24": [non_capex["correct"], 24],
        "non_capex_correct_qids": non_capex["correct_qids"],
        "by_player": total["by_player"],
        "by_round": total["by_round"],
        "by_kind": total["by_kind"],
        "confidence": {},
        "roleplay_execution": rp,
        "guidance_citation": cited_g,
        "boundary_citation": cited_b,
        "q7_separate": {
            "correct": is_correct(preds, truth, 7),
            "predicted_kind": preds[7]["predicted_kind"],
            "note": "q7 is a known hard question (no precursor before the "
                    "round); expected 0 for both groups. A correct guess "
                    "must be audited for leakage before any celebration.",
        },
        "guesses": {str(q): preds[q]["predicted_kind"] for q in sorted(all_qids)},
    }
    for level in ("high", "medium", "low"):
        qs = [q for q in all_qids if preds[q].get("confidence") == level]
        out["confidence"][level] = [
            len([q for q in qs if is_correct(preds, truth, q)]), len(qs)]
    return out


def load_batch(pred_dir, batch):
    preds = {}
    for f in sorted(glob.glob(os.path.join(pred_dir, f"predictions-{batch}-*.json"))):
        for p in json.load(open(f)):
            if p["q_id"] in preds:
                raise AssertionError(f"{batch}: duplicate prediction for q{p['q_id']}")
            preds[p["q_id"]] = p
    return preds


def reproduce_gates(truth):
    """Reproduction gates: re-score round-9 focus totals and round-8
    capex with this script's own logic. Both must match exactly."""
    got9 = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R9_PRED_DIR, batch)
        assert set(preds) == R9_FOCUS, (
            f"round-9 gate: batch {batch} q_id set != FOCUS13")
        got9[batch] = len([q for q in R9_FOCUS if is_correct(preds, truth, q)])
    print("round-9 focus reproduction gate:")
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        print(f"  {b}: {got9[b]}/13 (expected {R9_TOTAL_EXPECTED[b]}/13)")
    ok9 = got9 == R9_TOTAL_EXPECTED
    print("  REPRODUCTION GATE (round 9):", "PASS" if ok9 else "FAIL")
    got8 = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R8_PRED_DIR, batch)
        got8[batch] = len([q for q in R8_CAPEX if is_correct(preds, truth, q)])
    print("round-8 capex reproduction gate:")
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        print(f"  {b}: {got8[b]}/10 (expected {R8_CAPEX_EXPECTED[b]}/10)")
    ok8 = got8 == R8_CAPEX_EXPECTED
    print("  REPRODUCTION GATE (round 8):", "PASS" if ok8 else "FAIL")
    if not (ok9 and ok8):
        print("  fix score_v10.py before scoring round 10.")
        sys.exit(1)
    return {"round9_focus": got9, "round8_capex": got8,
            "round9_expected": R9_TOTAL_EXPECTED,
            "round8_expected": R8_CAPEX_EXPECTED,
            "status": "PASS"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--reproduce-only", action="store_true")
    ap.add_argument("--skip-reproduction", action="store_true")
    args = ap.parse_args()
    truth = load_truth()
    all_qids = sorted(FOCUS)

    gate = None
    if not args.skip_reproduction:
        gate = reproduce_gates(truth)
        repro_path = os.path.join(args.pred_dir, "reproduce-v10.json")
        os.makedirs(args.pred_dir, exist_ok=True)
        with open(repro_path, "w") as fh:
            json.dump(gate, fh, indent=2, ensure_ascii=False)
        print(f"wrote {repro_path}")
    if args.reproduce_only:
        return

    result = {"reproduction_gate": gate}
    found = []
    for batch in BATCHES:
        preds = load_batch(args.pred_dir, batch)
        if not preds:
            continue
        found.append(batch)
        result[batch] = score_batch(preds, truth, batch, all_qids)
        r = result[batch]
        print(f"{batch}: total {r['total_32'][0]}/32 "
              f"infra {r['infra_capex_12'][0]}/12 "
              f"policy {r['policy_regulatory_3'][0]}/3 "
              f"model {r['model_release_14'][0]}/14 "
              f"chip {r['chip_supply_3'][0]}/3 "
              f"capex {r['capex_8'][0]}/8 non-capex {r['non_capex_24'][0]}/24 "
              f"G={r['guidance_citation'][0]}/8 "
              f"B={r['boundary_citation'][0]}/10"
              + (f" R={r['roleplay_execution']['executed'][0]}/32"
                 if r["roleplay_execution"] else ""))
    if not found:
        print("no round-10 prediction files yet; reproduction gates passed, "
              "nothing to score.")
    else:
        for batch in BATCHES:
            if batch not in found:
                print(f"WARNING: batch {batch} has no prediction files; "
                      f"group summary covers only {found}.")

    scored_c = [b for b in CONTROL if b in result]
    scored_e = [b for b in EXPERIMENT if b in result]
    if len(scored_c) == 3 and len(scored_e) == 2:
        c_tot = [result[b]["total_32"][0] for b in CONTROL]
        e_tot = [result[b]["total_32"][0] for b in EXPERIMENT]
        m_tc = sum(c_tot) / 3
        m_te = sum(e_tot) / 2
        s_t = max(c_tot) - min(c_tot)
        cat_means = {}
        for name, key in (("infra_capex", "infra_capex_12"),
                          ("policy_regulatory", "policy_regulatory_3"),
                          ("model_release", "model_release_14"),
                          ("chip_supply", "chip_supply_3")):
            cat_means[f"{name}_C"] = sum(result[b][key][0] for b in CONTROL) / 3
            cat_means[f"{name}_E"] = sum(result[b][key][0] for b in EXPERIMENT) / 2
        n_c = sum(result[b]["non_capex_24"][0] for b in CONTROL) / 3
        n_e = sum(result[b]["non_capex_24"][0] for b in EXPERIMENT) / 2
        c_c = sum(result[b]["capex_8"][0] for b in CONTROL) / 3
        c_e = sum(result[b]["capex_8"][0] for b in EXPERIMENT) / 2
        r_rates = [result[b]["roleplay_execution"]["executed"][0] / 32
                   for b in EXPERIMENT]
        r_mean = sum(r_rates) / 2
        g_c = sum(result[b]["guidance_citation"][0] / 8 for b in CONTROL) / 3
        g_e = sum(result[b]["guidance_citation"][0] / 8 for b in EXPERIMENT) / 2
        b_c = sum(result[b]["boundary_citation"][0] / 10 for b in CONTROL) / 3
        b_e = sum(result[b]["boundary_citation"][0] / 10 for b in EXPERIMENT) / 2
        rule_a = (m_te - m_tc) > s_t
        rule_b = m_te > max(c_tot)
        rule_c = (n_e - n_c) > 0
        rule_d = cat_means["model_release_E"] >= cat_means["model_release_C"] - 1
        rule_e = r_mean >= 0.8
        keep = rule_a and rule_b and rule_c and rule_d and rule_e
        drop = (m_te <= m_tc) or \
               (cat_means["model_release_E"] < cat_means["model_release_C"] - 2) or \
               (r_mean < 0.5)
        mixed = (not rule_a) and rule_c and rule_d and rule_e
        result["group_summary"] = {
            "control_total": c_tot, "M_TC": m_tc, "spread_S_T": s_t,
            "experiment_total": e_tot, "M_TE": m_te,
            "M_TE_minus_M_TC": m_te - m_tc,
            "infra_C": cat_means["infra_capex_C"],
            "infra_E": cat_means["infra_capex_E"],
            "policy_C": cat_means["policy_regulatory_C"],
            "policy_E": cat_means["policy_regulatory_E"],
            "model_C": cat_means["model_release_C"],
            "model_E": cat_means["model_release_E"],
            "chip_C": cat_means["chip_supply_C"],
            "chip_E": cat_means["chip_supply_E"],
            "N_C": n_c, "N_E": n_e, "N_E_minus_N_C": n_e - n_c,
            "C_C": c_c, "C_E": c_e,
            "roleplay_execution_rates": {b: result[b]["roleplay_execution"]
                                         for b in EXPERIMENT},
            "R_mean": r_mean,
            "guidance_citation_rates": {b: result[b]["guidance_citation"]
                                        for b in BATCHES},
            "G_C": g_c, "G_E": g_e,
            "boundary_citation_rates": {b: result[b]["boundary_citation"]
                                        for b in BATCHES},
            "B_C": b_c, "B_E": b_e,
            "rule_a_gain_gt_noise": rule_a,
            "rule_b_M_TE_gt_max_control": rule_b,
            "rule_c_non_capex_gain_gt_0": rule_c,
            "rule_d_model_not_hurt_gt_1": rule_d,
            "rule_e_R_ge_80pct": rule_e,
            "KEEP_all_five": keep,
            "DROP_any": drop,
            "MIXED_helped_no_keep": mixed,
        }
        print(f"group: M_TC={m_tc:.2f} S_T={s_t} M_TE={m_te:.2f} "
              f"gain={m_te - m_tc:.2f} "
              f"infra_C={cat_means['infra_capex_C']:.2f} "
              f"infra_E={cat_means['infra_capex_E']:.2f} "
              f"policy_C={cat_means['policy_regulatory_C']:.2f} "
              f"policy_E={cat_means['policy_regulatory_E']:.2f} "
              f"model_C={cat_means['model_release_C']:.2f} "
              f"model_E={cat_means['model_release_E']:.2f} "
              f"chip_C={cat_means['chip_supply_C']:.2f} "
              f"chip_E={cat_means['chip_supply_E']:.2f} "
              f"N_C={n_c:.2f} N_E={n_e:.2f} C_C={c_c:.2f} C_E={c_e:.2f} "
              f"R={r_mean:.2f} G_C={g_c:.2f} G_E={g_e:.2f} "
              f"B_C={b_c:.2f} B_E={b_e:.2f} "
              f"KEEP={keep} DROP={drop} MIXED={mixed}")

    out_path = args.out or os.path.join(args.pred_dir, "score-v10.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
