#!/usr/bin/env python3
"""Score vision-1 round 8 (forward-guidance step as baseline, full 98).

Truth: testset-v6.json. Predictions: runs/round8-vision8-2026-11-22/predictions/
  predictions-{C1|C2|C3|E1|E2}-S{season}-{round}.json, one file per round,
  same record format as round 7 (q_id, player, predicted_kind, confidence,
  reasoning, facts_used) plus guidance_cited for the experimental group.
  Output: score-v8.json next to the predictions.

REPRODUCTION GATE (runs first, every time, unless --skip-reproduction):
  the same scoring logic re-scores the round-7 batches' capex predictions
  (~/workspace/verification-v1-round7/runs/round7-vision7-2026-11-22/predictions/)
  and must reproduce the round-7 capex scores exactly:
    control C1 2, C2 1, C3 2, C4 2, C5 2; experiment E1 10, E2 10, E3 10
    (out of 10).
  If it does not match exactly, the script exits non-zero and scores nothing.

Per batch (C1-C3, E1-E2) the output has:
  total-98 (all 98 questions; clean == total, no exclusions),
  capex-10 (q10-19), non-capex-88, false-capex F (non-capex questions
  guessed as capex) with F broken down by the TRUE kind of the question,
  per-subset (OLD 89 / NEW 9), per-player (18 players), per-round
  (28 rounds), per-kind (34 kinds), confidence calibration
  (high/medium/low correct/total), guidance citation rate (experimental
  only, mechanical: guidance_cited present with date strictly before the
  round_date; content validity is the audit's job, and the audit's
  verified rate is authoritative).
Group summary: control mean total M_TC and spread S_T over C1-C3,
  experiment mean total M_TE over E1-E2, control/experiment mean
  false-capex F_C/F_E and control spread S_F, experiment mean capex
  subset C_E, guidance citation mean G, and the decision-rule inputs
  (a) M_TE > M_TC, (b) F_E - F_C <= S_F, (c) C_E >= 9, (d) G >= 80%.

Usage:
  python3 score_v8.py [--pred-dir DIR] [--out FILE] [--reproduce-only]
                      [--skip-reproduction]
  With no prediction files present yet, the script still runs the
  reproduction gate and reports "no round-8 batches yet".
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round8-vision8-2026-11-22", "predictions")
R7_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round7",
    "runs", "round7-vision7-2026-11-22", "predictions")

CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}   # capex, 10 questions
NEW_SUB = {8, 16, 19, 24, 32, 43, 44, 49, 63}      # v5 new: 9
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]
# Round-7 capex scores to reproduce (round-7 report, capex table).
R7_CAPEX_EXPECTED = {"C1": 2, "C2": 1, "C3": 2, "C4": 2, "C5": 2,
                     "E1": 10, "E2": 10, "E3": 10}


def load_truth():
    ts = json.load(open(os.path.join(BASE, "testset-v6.json")))
    qs = ts["questions"] if isinstance(ts, dict) else ts
    return {q["q_id"]: q for q in qs}


def is_correct(preds, truth, qid):
    return preds[qid]["predicted_kind"] == truth[qid]["kind"]


def norm_date(d):
    """Normalize a date to int YYYYMMDD. Accepts int YYYYMMDD, string
    'YYYYMMDD', or string 'YYYY-MM-DD'. Returns None if unparseable."""
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
    cited guidance actually guidance, not the event itself) is the audit's
    job; this only checks presence + date."""
    g = pred.get("guidance_cited")
    if not isinstance(g, dict):
        return False
    d = norm_date(g.get("date"))
    if d is None:
        return False
    return d < truth[qid]["round_date"]


def score_preds(preds, truth, qids):
    """Core scoring logic, shared by round-8 batches and the round-7 gate.

    preds: {q_id: prediction record}. qids: the questions to score.
    Returns raw correct/total plus per-player, per-round and per-kind tables.
    """
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
    """Full per-batch report for one round-8 batch (exactly the 98 q_ids)."""
    assert set(preds) == set(all_qids), (
        f"batch q_id set != ALL98: missing {sorted(set(all_qids) - set(preds))}, "
        f"extra {sorted(set(preds) - set(all_qids))}")
    non_capex = [q for q in sorted(all_qids) if q not in CAPEX]
    total = score_preds(preds, truth, sorted(all_qids))
    capex = score_preds(preds, truth, sorted(CAPEX))
    noncap = score_preds(preds, truth, non_capex)
    # False capex: non-capex questions guessed as capex.
    false_qids = [q for q in non_capex
                  if preds[q]["predicted_kind"] == "capex"]
    false_by_kind = defaultdict(int)
    for q in false_qids:
        false_by_kind[truth[q]["kind"]] += 1
    cited = None
    if batch in EXPERIMENT:
        cited = [len([q for q in CAPEX
                      if guidance_cited_ok(preds[q], truth, q)]), 10]
    out = {
        "total_98": [total["correct"], 98],
        "correct_qids": total["correct_qids"],
        "capex_10": [capex["correct"], 10],
        "capex_correct_qids": capex["correct_qids"],
        "noncapex_88": [noncap["correct"], 88],
        "false_capex_F": len(false_qids),
        "false_capex_qids": sorted(false_qids),
        "false_capex_by_true_kind": dict(sorted(false_by_kind.items())),
        "by_player": total["by_player"],
        "by_round": total["by_round"],
        "by_kind": total["by_kind"],
        "by_subset": {
            "OLD_89": [len([q for q in all_qids if q not in NEW_SUB
                            and is_correct(preds, truth, q)]), 89],
            "NEW_v5_9": [len([q for q in NEW_SUB if is_correct(preds, truth, q)]), 9],
        },
        "confidence": {},
        "guidance_citation": cited,
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


def reproduce_round7_capex(truth):
    """Reproduction gate: re-score the round-7 batches' capex predictions
    with this script's own logic. Must return C1 2, C2 1, C3 2, C4 2, C5 2,
    E1 10, E2 10, E3 10."""
    got = {}
    for batch in ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]:
        preds = load_batch(R7_PRED_DIR, batch)
        got[batch] = len([q for q in CAPEX if is_correct(preds, truth, q)])
    print("round-7 capex reproduction gate:")
    for b in ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]:
        print(f"  {b}: {got[b]}/10 (expected {R7_CAPEX_EXPECTED[b]}/10)")
    ok = got == R7_CAPEX_EXPECTED
    print("  REPRODUCTION GATE:", "PASS" if ok else "FAIL")
    if not ok:
        print("  expected C1 2, C2 1, C3 2, C4 2, C5 2, E1 10, E2 10, E3 10; "
              "fix score_v8.py before scoring round 8.")
        sys.exit(1)
    return {"round7_capex": got}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--reproduce-only", action="store_true")
    ap.add_argument("--skip-reproduction", action="store_true")
    args = ap.parse_args()
    truth = load_truth()
    all_qids = sorted(truth)

    gate = None
    if not args.skip_reproduction:
        gate = reproduce_round7_capex(truth)
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
        print(f"{batch}: total {result[batch]['total_98'][0]}/98 "
              f"capex {result[batch]['capex_10'][0]}/10 "
              f"noncapex {result[batch]['noncapex_88'][0]}/88 "
              f"false-capex F={result[batch]['false_capex_F']}")
    if not found:
        print("no round-8 prediction files yet; reproduction gate passed, "
              "nothing to score.")
        return
    for batch in BATCHES:
        if batch not in found:
            print(f"WARNING: batch {batch} has no prediction files; "
                  f"group summary covers only {found}.")

    scored_c = [b for b in CONTROL if b in result]
    scored_e = [b for b in EXPERIMENT if b in result]
    if len(scored_c) == 3 and len(scored_e) == 2:
        c_tot = [result[b]["total_98"][0] for b in CONTROL]
        e_tot = [result[b]["total_98"][0] for b in EXPERIMENT]
        c_f = [result[b]["false_capex_F"] for b in CONTROL]
        e_f = [result[b]["false_capex_F"] for b in EXPERIMENT]
        c_cap = [result[b]["capex_10"][0] for b in CONTROL]
        e_cap = [result[b]["capex_10"][0] for b in EXPERIMENT]
        m_tc = sum(c_tot) / 3
        m_te = sum(e_tot) / 2
        s_t = max(c_tot) - min(c_tot)
        f_c = sum(c_f) / 3
        f_e = sum(e_f) / 2
        s_f = max(c_f) - min(c_f)
        c_e = sum(e_cap) / 2
        g_rates = [result[b]["guidance_citation"][0] / 10 for b in EXPERIMENT]
        g_mean = sum(g_rates) / 2
        keep_a = m_te > m_tc
        keep_b = (f_e - f_c) <= s_f
        keep_c = c_e >= 9
        keep_d = g_mean >= 0.8
        result["group_summary"] = {
            "control_total": c_tot, "M_TC": m_tc, "spread_S_T": s_t,
            "experiment_total": e_tot, "M_TE": m_te,
            "M_TE_minus_M_TC": m_te - m_tc,
            "control_false_capex": c_f, "F_C": f_c, "spread_S_F": s_f,
            "experiment_false_capex": e_f, "F_E": f_e,
            "F_E_minus_F_C": f_e - f_c,
            "control_capex": c_cap, "experiment_capex": e_cap, "C_E": c_e,
            "guidance_citation_rates": {b: result[b]["guidance_citation"]
                                        for b in EXPERIMENT},
            "guidance_citation_mean_G": g_mean,
            "rule_a_M_TE_gt_M_TC": keep_a,
            "rule_b_spillover_within_noise": keep_b,
            "rule_c_C_E_ge_9": keep_c,
            "rule_d_G_ge_80pct": keep_d,
            "KEEP_all_four": keep_a and keep_b and keep_c and keep_d,
            "DROP_any": (not keep_a) or (c_e < 8) or (not keep_d),
            "RESTRICT_guard": keep_a and (not keep_b) and keep_c and keep_d,
        }
        print(f"group: M_TC={m_tc:.2f} S_T={s_t} M_TE={m_te:.2f} "
              f"gain={m_te - m_tc:.2f} F_C={f_c:.2f} S_F={s_f} F_E={f_e:.2f} "
              f"C_E={c_e:.1f} G={g_mean:.2f} "
              f"KEEP={result['group_summary']['KEEP_all_four']} "
              f"DROP={result['group_summary']['DROP_any']} "
              f"GUARD={result['group_summary']['RESTRICT_guard']}")

    out_path = args.out or os.path.join(args.pred_dir, "score-v8.json")
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
