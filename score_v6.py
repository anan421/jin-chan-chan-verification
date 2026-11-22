#!/usr/bin/env python3
"""Score vision-1 round 6 (method-fix bundle experiment).

Truth: testset-v5.json. Predictions: runs/round6-vision6-2026-11-22/predictions/
  predictions-{C1|C2|C3|E1|E2}-S{season}-{round}.json, one file per round,
  same record format as round 5 (q_id, player, predicted_kind, confidence,
  reasoning, facts_used). Output: score-v6.json next to the predictions.

REPRODUCTION GATE (runs first, every time, unless --skip-reproduction):
  the same scoring logic re-scores the round-5 trial predictions
  (~/workspace/verification-v1-weakest-link/runs/weakest-link-vision5-2026-11-22/trial/)
  after mapping round-5 (testset-v3) q_ids to testset-v5 q_ids, and must
  reproduce the round-5 trial clean scores exactly:
    trial1 clean 10/20 (r5 q13 / v5 q14 excluded: audit found its facts
    describe the event itself), trial2 clean 6/21 (trial2b S5-3-2 redo).
  If it does not match exactly, the script exits non-zero and scores nothing.

Per batch (C1, C2, C3, E1, E2) the output has:
  raw-26, clean-24 (q7, q30 excluded: date-violating questions),
  per-kind (8 focus kinds), per-subset (M clean 13 / Q 5 / N 6, excluded
  reported separately), per-player (13 players), per-round (11 rounds),
  confidence calibration (high/medium/low correct/total),
  capex-10 (the 10 capex questions), excluded q7/q30 answered correctly or not.
Group summary: control mean M_C and spread S over C1-C3 clean-24,
  experiment mean M_E over E1-E2 clean-24, capex gate numbers
  (experiment 2-batch diff, control 3-batch spread, capex means),
  and the decision-rule inputs (M_E - M_C vs S, M-subset share of the gain).

Usage:
  python3 score_v6.py [--pred-dir DIR] [--out FILE] [--reproduce-only]
                      [--skip-reproduction]
  With no prediction files present yet, the script still runs the
  reproduction gate and reports "no round-6 batches yet".
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round6-vision6-2026-11-22", "predictions")
R5_TRIAL = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-weakest-link",
    "runs", "weakest-link-vision5-2026-11-22", "trial")

FOCUS = {5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
         30, 31, 32, 36, 37, 61, 62, 63, 67, 74, 92, 93}
EXCLUDED = {7, 30}            # date-violating: round date after the event
CLEAN = FOCUS - EXCLUDED      # 24 questions; the primary score
SUBSET_M = {10, 11, 12, 13, 14, 15, 17, 18, 31, 37, 67, 92, 93}  # clean 13
SUBSET_Q = {5, 6, 36, 61, 74}                                    # no-precursor 5
SUBSET_N = {16, 19, 32, 8, 62, 63}                               # new 6
CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}                 # 10
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]

# Round-5 (testset-v3) q_id -> testset-v5 q_id, verified by player/kind/round
# (design/experiment-vision6-round6.md). r5 q8 (Blackwell) -> v5 q9.
R5_TO_V5 = {5: 5, 6: 6, 7: 7, 8: 9, 9: 10, 10: 11, 11: 12, 12: 13, 13: 14,
            14: 15, 15: 17, 16: 18, 26: 30, 27: 31, 31: 36, 32: 37,
            53: 61, 57: 67, 64: 74, 81: 92, 82: 93}
R5_WEAK = sorted(R5_TO_V5)  # 21 round-5 trial questions (v3 numbering)


def load_truth():
    ts = json.load(open(os.path.join(BASE, "testset-v5.json")))
    qs = ts["questions"] if isinstance(ts, dict) else ts
    return {q["q_id"]: q for q in qs}


def is_correct(preds, truth, qid):
    return preds[qid]["predicted_kind"] == truth[qid]["kind"]


def score_preds(preds, truth, qids):
    """Core scoring logic, shared by round-6 batches and the round-5 gate.

    preds: {q_id: prediction record}. qids: the questions to score.
    Returns raw correct/total plus per-kind, per-player, per-round tables.
    """
    correct = [q for q in qids if is_correct(preds, truth, q)]
    by_kind = defaultdict(lambda: [0, 0])
    by_player = defaultdict(lambda: [0, 0])
    by_round = defaultdict(lambda: [0, 0])
    for q in qids:
        t = truth[q]
        by_kind[t["kind"]][1] += 1
        by_player[t["player"]][1] += 1
        by_round[f"S{t['season']} {t['round_label']}"][1] += 1
        if q in correct:
            by_kind[t["kind"]][0] += 1
            by_player[t["player"]][0] += 1
            by_round[f"S{t['season']} {t['round_label']}"][0] += 1
    return {
        "correct": len(correct), "total": len(qids),
        "correct_qids": sorted(correct),
        "by_kind": {k: v for k, v in sorted(by_kind.items())},
        "by_player": {k: v for k, v in sorted(by_player.items())},
        "by_round": {k: v for k, v in sorted(by_round.items())},
    }


def score_batch(preds, truth):
    """Full per-batch report for one round-6 batch (exactly the 26 focus q_ids)."""
    assert set(preds) == FOCUS, (
        f"batch q_id set != FOCUS26: missing {sorted(FOCUS - set(preds))}, "
        f"extra {sorted(set(preds) - FOCUS)}")
    raw = score_preds(preds, truth, sorted(FOCUS))
    clean = score_preds(preds, truth, sorted(CLEAN))
    out = {
        "raw_26": [raw["correct"], 26],
        "clean_24": [clean["correct"], 24],
        "correct_qids_raw": raw["correct_qids"],
        "correct_qids_clean": clean["correct_qids"],
        "by_kind": clean["by_kind"],
        "by_player": clean["by_player"],
        "by_round": clean["by_round"],
        "by_subset": {
            "M_method_13": [len([q for q in SUBSET_M if is_correct(preds, truth, q)]), 13],
            "Q_no_precursor_5": [len([q for q in SUBSET_Q if is_correct(preds, truth, q)]), 5],
            "N_new_6": [len([q for q in SUBSET_N if is_correct(preds, truth, q)]), 6],
        },
        "excluded": {
            "q7_bis_rule_BYTE": is_correct(preds, truth, 7),
            "q30_datacenter_BYTE": is_correct(preds, truth, 30),
        },
        "capex_10": [len([q for q in CAPEX if is_correct(preds, truth, q)]), 10],
        "confidence": {},
        "guesses": {str(q): preds[q]["predicted_kind"] for q in sorted(FOCUS)},
    }
    for level in ("high", "medium", "low"):
        qs = [q for q in FOCUS if preds[q].get("confidence") == level]
        out["confidence"][level] = [
            len([q for q in qs if is_correct(preds, truth, q)]), len(qs)]
    return out


def load_trial(pattern, replace=None):
    """Load round-5 trial predictions, remapped to testset-v5 q_ids."""
    preds = {}
    for f in sorted(glob.glob(os.path.join(R5_TRIAL, pattern))):
        for p in json.load(open(f)):
            preds[R5_TO_V5[p["q_id"]]] = p
    if replace:
        for p in json.load(open(os.path.join(R5_TRIAL, replace))):
            preds[R5_TO_V5[p["q_id"]]] = p
    return preds


def reproduce_round5(truth):
    """Reproduction gate: re-score the round-5 trial with this script's
    own logic. Must return trial1 clean 10/20 and trial2 clean 6/21."""
    t1 = load_trial("predictions-trial1-*.json")
    t2 = load_trial("predictions-trial2-*.json")
    t2c = load_trial("predictions-trial2-*.json",
                     replace="predictions-trial2b-S5-3-2.json")
    assert set(t1) == set(R5_TO_V5.values()), "trial1 q_id set mismatch"
    assert set(t2c) == set(R5_TO_V5.values()), "trial2-clean q_id set mismatch"
    v5_trial = sorted(R5_TO_V5.values())  # 21 questions in v5 numbering
    t1_raw = score_preds(t1, truth, v5_trial)
    t1_clean = score_preds(t1, truth, [q for q in v5_trial if q != 14])
    t2_raw = score_preds(t2, truth, v5_trial)
    t2_clean = score_preds(t2c, truth, v5_trial)
    gate = {
        "trial1_raw": [t1_raw["correct"], 21],
        "trial1_clean": [t1_clean["correct"], 20],
        "trial1_clean_excluded": [14],
        "trial2_raw": [t2_raw["correct"], 21],
        "trial2_clean": [t2_clean["correct"], 21],
    }
    print("round-5 reproduction gate:")
    print(f"  trial1 raw {t1_raw['correct']}/21, clean {t1_clean['correct']}/20 "
          f"(v5 q14 excluded)")
    print(f"  trial2 raw {t2_raw['correct']}/21, clean {t2_clean['correct']}/21 "
          f"(trial2b S5-3-2 redo)")
    ok = gate["trial1_clean"] == [10, 20] and gate["trial2_clean"] == [6, 21]
    print("  REPRODUCTION GATE:", "PASS" if ok else "FAIL")
    if not ok:
        print("  expected trial1 clean [10, 20], trial2 clean [6, 21]; "
              "fix score_v6.py before scoring round 6.")
        sys.exit(1)
    return gate


def load_batch(pred_dir, batch):
    preds = {}
    for f in sorted(glob.glob(os.path.join(pred_dir, f"predictions-{batch}-*.json"))):
        for p in json.load(open(f)):
            if p["q_id"] in preds:
                raise AssertionError(f"{batch}: duplicate prediction for q{p['q_id']}")
            preds[p["q_id"]] = p
    return preds


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
        gate = reproduce_round5(truth)
    if args.reproduce_only:
        return

    result = {"reproduction_gate": gate}
    found = []
    for batch in BATCHES:
        preds = load_batch(args.pred_dir, batch)
        if not preds:
            continue
        found.append(batch)
        result[batch] = score_batch(preds, truth)
        print(f"{batch}: raw {result[batch]['raw_26'][0]}/26, "
              f"clean {result[batch]['clean_24'][0]}/24")
    if not found:
        print("no round-6 prediction files yet; reproduction gate passed, "
              "nothing to score.")
        return
    for batch in BATCHES:
        if batch not in found:
            print(f"WARNING: batch {batch} has no prediction files; "
                  f"group summary covers only {found}.")

    scored = [b for b in CONTROL if b in result]
    exp = [b for b in EXPERIMENT if b in result]
    if len(scored) == 3 and len(exp) == 2:
        c_clean = [result[b]["clean_24"][0] for b in CONTROL]
        e_clean = [result[b]["clean_24"][0] for b in EXPERIMENT]
        m_c = sum(c_clean) / 3
        m_e = sum(e_clean) / 2
        s = max(c_clean) - min(c_clean)
        c_capex = [result[b]["capex_10"][0] for b in CONTROL]
        e_capex = [result[b]["capex_10"][0] for b in EXPERIMENT]
        m_gain = (sum(result[b]["by_subset"]["M_method_13"][0] for b in EXPERIMENT) / 2
                  - sum(result[b]["by_subset"]["M_method_13"][0] for b in CONTROL) / 3)
        gain = m_e - m_c
        result["group_summary"] = {
            "control_clean": c_clean, "M_C": m_c, "spread_S": s,
            "experiment_clean": e_clean, "M_E": m_e,
            "M_E_minus_M_C": gain,
            "win_rule_a_gain_gt_spread": gain > s,
            "win_rule_b_M_E_gt_max_C": m_e > max(c_clean),
            "win_rule_min_gain_2": gain >= 2,
            "M_subset_gain": m_gain,
            "M_subset_share_of_gain": (m_gain / gain if gain else None),
            "capex": {
                "control": c_capex,
                "control_mean": sum(c_capex) / 3,
                "control_spread": max(c_capex) - min(c_capex),
                "experiment": e_capex,
                "experiment_mean": sum(e_capex) / 2,
                "experiment_diff": max(e_capex) - min(e_capex),
                "capex_gate_pass": (max(e_capex) - min(e_capex) <= 2
                                    and sum(e_capex) / 2 >= sum(c_capex) / 3),
            },
            "v3_check": {b: result[b]["by_kind"].get("v3", [0, 0])
                         for b in EXPERIMENT},
            "Q_subset": {b: result[b]["by_subset"]["Q_no_precursor_5"]
                         for b in BATCHES if b in result},
        }
        print(f"group: M_C={m_c:.2f} S={s} M_E={m_e:.2f} gain={gain:.2f} "
              f"M-share={result['group_summary']['M_subset_share_of_gain']}")

    out_path = args.out or os.path.join(args.pred_dir, "score-v6.json")
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
