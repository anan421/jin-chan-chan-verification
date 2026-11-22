#!/usr/bin/env python3
"""Score vision-1 round 7 (forward-guidance steps, single-rule test).

Truth: testset-v6.json. Predictions: runs/round7-vision7-2026-11-22/predictions/
  predictions-{C1|C2|C3|C4|C5|E1|E2|E3}-S{season}-{round}.json, one file per
  round, same record format as round 6 (q_id, player, predicted_kind,
  confidence, reasoning, facts_used) plus guidance_cited for the
  experimental group. Output: score-v7.json next to the predictions.

REPRODUCTION GATE (runs first, every time, unless --skip-reproduction):
  the same scoring logic re-scores the round-6 batches' capex predictions
  (~/workspace/verification-v1-round6/runs/round6-vision6-2026-11-22/predictions/)
  and must reproduce the round-6 capex scores exactly:
    control C1 2, C2 5, C3 6; experiment E1 10, E2 10 (out of 10).
  If it does not match exactly, the script exits non-zero and scores nothing.
  (Capex kinds are identical in testset-v5 and testset-v6; Part 1 changed
  no kind, only withdrew q79 and fixed round dates.)

Per batch (C1-C5, E1-E3) the output has:
  total-10 (all 10 capex questions; clean == total, no exclusions),
  per-subset (OLD 8 / NEW 2), per-player (8 players), per-round (4 rounds),
  confidence calibration (high/medium/low correct/total),
  guidance citation rate (experimental only, mechanical: guidance_cited
  present with date strictly before the round_date; content validity is
  the audit's job, and the audit's verified rate is authoritative).
Group summary: control mean M_C and spread S over C1-C5, experiment mean
  M_E over E1-E3, experiment stability, and the decision-rule inputs
  (a) M_E - M_C > S, (b) M_E > max(C), (c) experiment diff <= 1,
  (d) M_E - M_C >= 2, (e) mean guidance citation rate >= 80%.

Usage:
  python3 score_v7.py [--pred-dir DIR] [--out FILE] [--reproduce-only]
                      [--skip-reproduction]
  With no prediction files present yet, the script still runs the
  reproduction gate and reports "no round-7 batches yet".
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round7-vision7-2026-11-22", "predictions")
R6_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round6",
    "runs", "round6-vision6-2026-11-22", "predictions")

FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}   # capex, 10 questions
CLEAN = FOCUS                                       # no exclusions
OLD_SUB = {10, 11, 12, 13, 14, 15, 17, 18}         # rule designed from these: 8
NEW_SUB = {16, 19}                                  # v5 new: 2
BATCHES = ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]
CONTROL = ["C1", "C2", "C3", "C4", "C5"]
EXPERIMENT = ["E1", "E2", "E3"]
# Round-6 capex scores to reproduce (round-6 report, capex table).
R6_CAPEX_EXPECTED = {"C1": 2, "C2": 5, "C3": 6, "E1": 10, "E2": 10}


def load_truth():
    ts = json.load(open(os.path.join(BASE, "testset-v6.json")))
    qs = ts["questions"] if isinstance(ts, dict) else ts
    return {q["q_id"]: q for q in qs}


def is_correct(preds, truth, qid):
    return preds[qid]["predicted_kind"] == truth[qid]["kind"]


def guidance_cited_ok(pred, truth, qid):
    """Mechanical citation check: guidance_cited present, with a date
    strictly before the question's round_date. Content validity (is the
    cited guidance actually guidance, not the event itself) is the audit's
    job; this only checks presence + date."""
    g = pred.get("guidance_cited")
    if not isinstance(g, dict):
        return False
    d = g.get("date")
    if d is None:
        return False
    return d < truth[qid]["round_date"]


def score_preds(preds, truth, qids):
    """Core scoring logic, shared by round-7 batches and the round-6 gate.

    preds: {q_id: prediction record}. qids: the questions to score.
    Returns raw correct/total plus per-player and per-round tables.
    """
    correct = [q for q in qids if is_correct(preds, truth, q)]
    by_player = defaultdict(lambda: [0, 0])
    by_round = defaultdict(lambda: [0, 0])
    for q in qids:
        t = truth[q]
        by_player[t["player"]][1] += 1
        by_round[f"S{t['season']} {t['round_label']}"][1] += 1
        if q in correct:
            by_player[t["player"]][0] += 1
            by_round[f"S{t['season']} {t['round_label']}"][0] += 1
    return {
        "correct": len(correct), "total": len(qids),
        "correct_qids": sorted(correct),
        "by_player": {k: v for k, v in sorted(by_player.items())},
        "by_round": {k: v for k, v in sorted(by_round.items())},
    }


def score_batch(preds, truth, batch):
    """Full per-batch report for one round-7 batch (exactly the 10 capex q_ids)."""
    assert set(preds) == FOCUS, (
        f"batch q_id set != FOCUS10: missing {sorted(FOCUS - set(preds))}, "
        f"extra {sorted(set(preds) - FOCUS)}")
    total = score_preds(preds, truth, sorted(FOCUS))
    cited = None
    if batch in EXPERIMENT:
        cited = [len([q for q in FOCUS
                      if guidance_cited_ok(preds[q], truth, q)]), 10]
    out = {
        "total_10": [total["correct"], 10],
        "correct_qids": total["correct_qids"],
        "by_player": total["by_player"],
        "by_round": total["by_round"],
        "by_subset": {
            "OLD_designed_from_8": [len([q for q in OLD_SUB if is_correct(preds, truth, q)]), 8],
            "NEW_v5_2": [len([q for q in NEW_SUB if is_correct(preds, truth, q)]), 2],
        },
        "confidence": {},
        "guidance_citation": cited,
        "guesses": {str(q): preds[q]["predicted_kind"] for q in sorted(FOCUS)},
    }
    for level in ("high", "medium", "low"):
        qs = [q for q in FOCUS if preds[q].get("confidence") == level]
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


def reproduce_round6_capex(truth):
    """Reproduction gate: re-score the round-6 batches' capex predictions
    with this script's own logic. Must return C1 2, C2 5, C3 6, E1 10, E2 10."""
    got = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R6_PRED_DIR, batch)
        got[batch] = len([q for q in FOCUS if is_correct(preds, truth, q)])
    print("round-6 capex reproduction gate:")
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        print(f"  {b}: {got[b]}/10 (expected {R6_CAPEX_EXPECTED[b]}/10)")
    ok = got == R6_CAPEX_EXPECTED
    print("  REPRODUCTION GATE:", "PASS" if ok else "FAIL")
    if not ok:
        print("  expected C1 2, C2 5, C3 6, E1 10, E2 10; "
              "fix score_v7.py before scoring round 7.")
        sys.exit(1)
    return {"round6_capex": got}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--reproduce-only", action="store_true")
    ap.add_argument("--skip-reproduction", action="store_true")
    args = ap.parse_args()
    truth = load_truth()

    gate = None
    if not args.skip_reproduction:
        gate = reproduce_round6_capex(truth)
    if args.reproduce_only:
        return

    result = {"reproduction_gate": gate}
    found = []
    for batch in BATCHES:
        preds = load_batch(args.pred_dir, batch)
        if not preds:
            continue
        found.append(batch)
        result[batch] = score_batch(preds, truth, batch)
        print(f"{batch}: total {result[batch]['total_10'][0]}/10")
    if not found:
        print("no round-7 prediction files yet; reproduction gate passed, "
              "nothing to score.")
        return
    for batch in BATCHES:
        if batch not in found:
            print(f"WARNING: batch {batch} has no prediction files; "
                  f"group summary covers only {found}.")

    scored_c = [b for b in CONTROL if b in result]
    scored_e = [b for b in EXPERIMENT if b in result]
    if len(scored_c) == 5 and len(scored_e) == 3:
        c_tot = [result[b]["total_10"][0] for b in CONTROL]
        e_tot = [result[b]["total_10"][0] for b in EXPERIMENT]
        m_c = sum(c_tot) / 5
        m_e = sum(e_tot) / 3
        s = max(c_tot) - min(c_tot)
        e_diff = max(e_tot) - min(e_tot)
        gain = m_e - m_c
        g_rates = [result[b]["guidance_citation"][0] / 10 for b in EXPERIMENT]
        g_mean = sum(g_rates) / 3
        result["group_summary"] = {
            "control_total": c_tot, "M_C": m_c, "spread_S": s,
            "experiment_total": e_tot, "M_E": m_e,
            "experiment_diff": e_diff,
            "M_E_minus_M_C": gain,
            "win_rule_a_gain_gt_spread": gain > s,
            "win_rule_b_M_E_gt_max_C": m_e > max(c_tot),
            "win_rule_c_exp_diff_le_1": e_diff <= 1,
            "win_rule_d_min_gain_2": gain >= 2,
            "guidance_citation_rates": {b: result[b]["guidance_citation"]
                                        for b in EXPERIMENT},
            "guidance_citation_mean_G": g_mean,
            "win_rule_e_G_ge_80pct": g_mean >= 0.8,
            "win_all": (gain > s and m_e > max(c_tot) and e_diff <= 1
                        and gain >= 2 and g_mean >= 0.8),
            "new_subset_q16_q19": {
                b: result[b]["by_subset"]["NEW_v5_2"] for b in BATCHES if b in result},
            "old_subset": {
                b: result[b]["by_subset"]["OLD_designed_from_8"] for b in BATCHES if b in result},
        }
        print(f"group: M_C={m_c:.2f} S={s} M_E={m_e:.2f} gain={gain:.2f} "
              f"exp_diff={e_diff} G={g_mean:.2f} "
              f"win={result['group_summary']['win_all']}")

    out_path = args.out or os.path.join(args.pred_dir, "score-v7.json")
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
