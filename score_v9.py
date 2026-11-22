#!/usr/bin/env python3
"""Score vision-1 round 9 (datacenter vs capex boundary, single rule).

Truth: testset-v6.json. Predictions:
  runs/round9-vision9-2026-11-22/predictions/
  predictions-{C1|C2|C3|E1|E2}-S{season}-{round}.json, one file per round,
  same record format as round 8 (q_id, player, predicted_kind, confidence,
  reasoning, facts_used, guidance_cited) plus boundary_cited for the
  experimental group (dict with step 1-5 and the place/money sentence,
  or null when the boundary rule was not used).
  Output: score-v9.json next to the predictions. Focus set is 13 questions
  only (capex q10-19 + datacenter q30-32).

REPRODUCTION GATES (run first, every time, unless --skip-reproduction):
  1. round-7 capex gate (same as score_v8.py): control C1 2, C2 1, C3 2,
     C4 2, C5 2; experiment E1 10, E2 10, E3 10 (out of 10).
  2. round-8 capex gate: re-score the round-8 batches' capex predictions
     and must reproduce the round-8 report exactly: control C1 3, C2 1,
     C3 3 (mean 2.33/10); experiment E1 10, E2 10 (out of 10).
  If either gate fails, the script exits non-zero and scores nothing.

Per batch (C1-C3, E1-E2) the output has:
  total_13, datacenter_3 (q30-32), capex_10 (q10-19),
  X = datacenter questions guessed as capex (0-3) with qids,
  Y = capex questions guessed as datacenter (0-10) with qids,
  per-player (8 players), per-round (6 rounds), per-kind (within focus),
  confidence calibration (high/medium/low correct/total),
  guidance citation (both groups now have the forward-guidance steps:
  guidance_cited present with date strictly before the round_date;
  content validity is the audit's job),
  boundary citation (experimental only, mechanical: boundary_cited present
  with a step 1-5 and a place/money sentence; content validity is the
  audit's job).
Group summary: control mean total M_TC and spread S_T over C1-C3,
  experiment mean total M_TE over E1-E2, datacenter means D_C/D_E and
  control spread S_D, capex means C_C/C_E, two-way miscall means
  X_C/X_E (spread S_X) and Y_C/Y_E, guidance citation mean G,
  boundary citation mean B, and the decision-rule inputs
  (a) M_TE - M_TC > S_T, (b) D_E >= 2 and each experiment batch D >= 2,
  (c) C_E >= 9 and each experiment batch C >= 9,
  (d) X_E <= X_C - 1 and Y_E <= 1.0, (e) B >= 80%.

Usage:
  python3 score_v9.py [--pred-dir DIR] [--out FILE] [--reproduce-only]
                      [--skip-reproduction]
  With no prediction files present yet, the script still runs the
  reproduction gates and reports "no round-9 batches yet".
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round9-vision9-2026-11-22", "predictions")
R7_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round7",
    "runs", "round7-vision7-2026-11-22", "predictions")
R8_PRED_DIR = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round8",
    "runs", "round8-vision8-2026-11-22", "predictions")

FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 30, 31, 32}
CAPEX = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}   # capex, 10 questions
DC = {30, 31, 32}                                  # datacenter, 3 questions
BATCHES = ["C1", "C2", "C3", "E1", "E2"]
CONTROL = ["C1", "C2", "C3"]
EXPERIMENT = ["E1", "E2"]
# Round-7 capex scores to reproduce (round-7 report, capex table).
R7_CAPEX_EXPECTED = {"C1": 2, "C2": 1, "C3": 2, "C4": 2, "C5": 2,
                     "E1": 10, "E2": 10, "E3": 10}
# Round-8 capex scores to reproduce (round-8 report, capex table).
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
    cited guidance actually guidance, not the event itself) is the audit's
    job; this only checks presence + date."""
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


def score_preds(preds, truth, qids):
    """Core scoring logic, shared by round-9 batches and the gates."""
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
    """Full per-batch report for one round-9 batch (exactly the 13 focus q_ids)."""
    assert set(preds) == set(all_qids), (
        f"batch q_id set != FOCUS13: missing {sorted(set(all_qids) - set(preds))}, "
        f"extra {sorted(set(preds) - set(all_qids))}")
    total = score_preds(preds, truth, sorted(all_qids))
    dc = score_preds(preds, truth, sorted(DC))
    capex = score_preds(preds, truth, sorted(CAPEX))
    # Two-way miscalls.
    x_qids = sorted(q for q in DC if preds[q]["predicted_kind"] == "capex")
    y_qids = sorted(q for q in CAPEX if preds[q]["predicted_kind"] == "datacenter")
    cited_g = [len([q for q in CAPEX
                    if guidance_cited_ok(preds[q], truth, q)]), 10]
    cited_b = None
    if batch in EXPERIMENT:
        cited_b = [len([q for q in sorted(all_qids)
                        if boundary_cited_ok(preds[q])]), 13]
    out = {
        "total_13": [total["correct"], 13],
        "correct_qids": total["correct_qids"],
        "datacenter_3": [dc["correct"], 3],
        "datacenter_correct_qids": dc["correct_qids"],
        "capex_10": [capex["correct"], 10],
        "capex_correct_qids": capex["correct_qids"],
        "miscall_dc_as_capex_X": len(x_qids),
        "miscall_dc_as_capex_qids": x_qids,
        "miscall_capex_as_dc_Y": len(y_qids),
        "miscall_capex_as_dc_qids": y_qids,
        "by_player": total["by_player"],
        "by_round": total["by_round"],
        "by_kind": total["by_kind"],
        "confidence": {},
        "guidance_citation": cited_g,
        "boundary_citation": cited_b,
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
    """Reproduction gates: re-score round-7 and round-8 capex with this
    script's own logic. Both must match exactly."""
    got7 = {}
    for batch in ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]:
        preds = load_batch(R7_PRED_DIR, batch)
        got7[batch] = len([q for q in CAPEX if is_correct(preds, truth, q)])
    print("round-7 capex reproduction gate:")
    for b in ["C1", "C2", "C3", "C4", "C5", "E1", "E2", "E3"]:
        print(f"  {b}: {got7[b]}/10 (expected {R7_CAPEX_EXPECTED[b]}/10)")
    ok7 = got7 == R7_CAPEX_EXPECTED
    print("  REPRODUCTION GATE (round 7):", "PASS" if ok7 else "FAIL")
    got8 = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R8_PRED_DIR, batch)
        got8[batch] = len([q for q in CAPEX if is_correct(preds, truth, q)])
    print("round-8 capex reproduction gate:")
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        print(f"  {b}: {got8[b]}/10 (expected {R8_CAPEX_EXPECTED[b]}/10)")
    ok8 = got8 == R8_CAPEX_EXPECTED
    print("  REPRODUCTION GATE (round 8):", "PASS" if ok8 else "FAIL")
    if not (ok7 and ok8):
        print("  fix score_v9.py before scoring round 9.")
        sys.exit(1)
    return {"round7_capex": got7, "round8_capex": got8}


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
        print(f"{batch}: total {result[batch]['total_13'][0]}/13 "
              f"dc {result[batch]['datacenter_3'][0]}/3 "
              f"capex {result[batch]['capex_10'][0]}/10 "
              f"X={result[batch]['miscall_dc_as_capex_X']} "
              f"Y={result[batch]['miscall_capex_as_dc_Y']}")
    if not found:
        print("no round-9 prediction files yet; reproduction gates passed, "
              "nothing to score.")
        return
    for batch in BATCHES:
        if batch not in found:
            print(f"WARNING: batch {batch} has no prediction files; "
                  f"group summary covers only {found}.")

    scored_c = [b for b in CONTROL if b in result]
    scored_e = [b for b in EXPERIMENT if b in result]
    if len(scored_c) == 3 and len(scored_e) == 2:
        c_tot = [result[b]["total_13"][0] for b in CONTROL]
        e_tot = [result[b]["total_13"][0] for b in EXPERIMENT]
        c_dc = [result[b]["datacenter_3"][0] for b in CONTROL]
        e_dc = [result[b]["datacenter_3"][0] for b in EXPERIMENT]
        c_cap = [result[b]["capex_10"][0] for b in CONTROL]
        e_cap = [result[b]["capex_10"][0] for b in EXPERIMENT]
        c_x = [result[b]["miscall_dc_as_capex_X"] for b in CONTROL]
        e_x = [result[b]["miscall_dc_as_capex_X"] for b in EXPERIMENT]
        c_y = [result[b]["miscall_capex_as_dc_Y"] for b in CONTROL]
        e_y = [result[b]["miscall_capex_as_dc_Y"] for b in EXPERIMENT]
        m_tc = sum(c_tot) / 3
        m_te = sum(e_tot) / 2
        s_t = max(c_tot) - min(c_tot)
        d_c = sum(c_dc) / 3
        d_e = sum(e_dc) / 2
        s_d = max(c_dc) - min(c_dc)
        c_c = sum(c_cap) / 3
        c_e = sum(e_cap) / 2
        x_c = sum(c_x) / 3
        x_e = sum(e_x) / 2
        s_x = max(c_x) - min(c_x)
        y_c = sum(c_y) / 3
        y_e = sum(e_y) / 2
        g_rates = [result[b]["guidance_citation"][0] / 10 for b in BATCHES]
        g_mean = sum(g_rates) / 5
        b_rates = [result[b]["boundary_citation"][0] / 13 for b in EXPERIMENT]
        b_mean = sum(b_rates) / 2
        rule_a = (m_te - m_tc) > s_t
        rule_b = d_e >= 2 and all(d >= 2 for d in e_dc)
        rule_c = c_e >= 9 and all(c >= 9 for c in e_cap)
        rule_d = (x_e <= x_c - 1) and (y_e <= 1.0)
        rule_e = b_mean >= 0.8
        keep = rule_a and rule_b and rule_c and rule_d and rule_e
        drop = (m_te <= m_tc) or (d_e < 1) or (c_e < 8) or (b_mean < 0.5)
        mixed = (not rule_a) and rule_b and rule_c and rule_d and rule_e
        result["group_summary"] = {
            "control_total": c_tot, "M_TC": m_tc, "spread_S_T": s_t,
            "experiment_total": e_tot, "M_TE": m_te,
            "M_TE_minus_M_TC": m_te - m_tc,
            "control_datacenter": c_dc, "D_C": d_c, "spread_S_D": s_d,
            "experiment_datacenter": e_dc, "D_E": d_e,
            "control_capex": c_cap, "C_C": c_c,
            "experiment_capex": e_cap, "C_E": c_e,
            "control_X": c_x, "X_C": x_c, "spread_S_X": s_x,
            "experiment_X": e_x, "X_E": x_e,
            "control_Y": c_y, "Y_C": y_c,
            "experiment_Y": e_y, "Y_E": y_e,
            "guidance_citation_rates": {b: result[b]["guidance_citation"]
                                        for b in BATCHES},
            "guidance_citation_mean_G": g_mean,
            "boundary_citation_rates": {b: result[b]["boundary_citation"]
                                        for b in EXPERIMENT},
            "boundary_citation_mean_B": b_mean,
            "rule_a_gain_gt_noise": rule_a,
            "rule_b_dc_ge_2": rule_b,
            "rule_c_capex_ge_9": rule_c,
            "rule_d_miscalls": rule_d,
            "rule_e_B_ge_80pct": rule_e,
            "KEEP_all_five": keep,
            "DROP_any": drop,
            "MIXED_helped_no_keep": mixed,
        }
        print(f"group: M_TC={m_tc:.2f} S_T={s_t} M_TE={m_te:.2f} "
              f"gain={m_te - m_tc:.2f} D_C={d_c:.2f} D_E={d_e:.2f} "
              f"C_C={c_c:.2f} C_E={c_e:.2f} X_C={x_c:.2f} X_E={x_e:.2f} "
              f"Y_C={y_c:.2f} Y_E={y_e:.2f} G={g_mean:.2f} B={b_mean:.2f} "
              f"KEEP={keep} DROP={drop} MIXED={mixed}")

    out_path = args.out or os.path.join(args.pred_dir, "score-v9.json")
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
