#!/usr/bin/env python3
"""Score baseline retest on testset-v7 (215 questions), 3 control batches.

Truth: testset-v7.json in this workspace root. Predictions:
  runs/baseline-retest-2026-11-22/predictions/
  predictions-{C1|C2|C3}-S{season}-{round}.json, one file per round
  (31 files per batch, 215 questions each).
  Record format (v7): top-level dict {batch, predictor, round,
  predictions: [...]}; each record has q_id, kind (guessed kind),
  confidence (high/medium/low), reason, facts, roleplay_text,
  roleplay_step25 (string), forecast_prop, forecast_prob,
  boundary_cited (string or null), guidance_cited (string or null).
  A guess is correct iff guessed kind == testset kind for that q_id.
  Guessed kinds outside the 43-kind answer set (open_source, ascend,
  generic, compliance) can never match and count as wrong.

REPRODUCTION GATE (run first, every time, unless --skip-reproduction):
  re-score the round-10 batches' 32 focus questions with this script's
  own core logic (truth: testset-v6.json in verification-v1-round10;
  predictions: runs/round10-vision10-2026-11-22/predictions/) and must
  reproduce the round-10 report exactly: control C1 31, C2 31, C3 31;
  experiment E1 32, E2 32 (out of 32). If the gate fails, the script
  exits non-zero and scores nothing. Gate results are written to
  reproduce-baseline-v7.json next to the predictions and into
  score-baseline-v7.json under "reproduction_gate".

Per batch (C1-C3) the output has:
  total_215, correct_qids, per-kind (43 kinds, [correct, total]),
  per-player ([correct, total] for every player label in the testset),
  old_98 (q_id <= 98; 98 questions, q79 withdrawn) and new_117
  (q_id >= 99; 117 questions), capex_10 (kind == capex, q10-19),
  model_release_66 (kinds claude, chatgpt, gemini, r1, v3, tongyi,
  llama, kimi, muse, glm, minimax) plus each model kind separately,
  confidence calibration (high/medium/low [correct, total] + accuracy),
  roleplay execution R (all four of roleplay_text, roleplay_step25,
  forecast_prop, forecast_prob present and well-formed, /215),
  guidance citation G (capex predictions with guidance_cited non-empty,
  /10), boundary citation B (capex + datacenter predictions with
  boundary_cited non-empty, /13).
Group summary: control totals, mean M_TC, spread S_T = max - min,
  per-kind mean correct, old/new means, capex/model means,
  confidence means, R/G/B means.

Usage:
  python3 score_baseline_v7.py [--pred-dir DIR] [--out FILE]
                               [--reproduce-only] [--skip-reproduction]
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "baseline-retest-2026-11-22", "predictions")
R10_BASE = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round10")
R10_PRED_DIR = os.path.join(
    R10_BASE, "runs", "round10-vision10-2026-11-22", "predictions")

# Round-10 focus set (design/experiment-vision10-round10.md) and the
# round-10 reported totals to reproduce.
R10_FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
             36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
R10_TOTAL_EXPECTED = {"C1": 31, "C2": 31, "C3": 31, "E1": 32, "E2": 32}

BATCHES = ["C1", "C2", "C3"]
MODEL_KINDS = ["claude", "chatgpt", "gemini", "r1", "v3", "tongyi",
               "llama", "kimi", "muse", "glm", "minimax"]


def load_truth(path):
    ts = json.load(open(path))
    qs = ts["questions"] if isinstance(ts, dict) else ts
    return {q["q_id"]: q for q in qs}


def guessed_kind(pred):
    """v7 records use 'kind'; round-10 records use 'predicted_kind'."""
    k = pred.get("kind", pred.get("predicted_kind"))
    return k


def is_correct(preds, truth, qid):
    """preds is the whole batch dict {q_id: record} (same signature as
    score_v10.py). Correct iff the guessed kind matches the testset
    kind for that q_id."""
    return guessed_kind(preds[qid]) == truth[qid]["kind"]


def non_empty(v):
    """Mechanical non-empty check for a citation field: a non-empty
    string counts; a non-empty dict counts; anything else (null,
    empty string, empty dict) does not."""
    if v is None:
        return False
    if isinstance(v, str):
        return len(v.strip()) > 0
    if isinstance(v, dict):
        return len(v) > 0
    return True


def roleplay_executed_ok(pred):
    """Mechanical roleplay-execution check: roleplay_text +
    roleplay_step25 + forecast_prop + forecast_prob all present and
    well-formed. Missing any one of the four means not executed.
    Accepts both shapes of roleplay_step25: the v7 plain string
    ("同一件" / "不是同一件" ...) and the round-10 dict
    {same, note}."""
    rt = pred.get("roleplay_text")
    if not isinstance(rt, str) or not rt.strip():
        return False
    s25 = pred.get("roleplay_step25")
    if isinstance(s25, str):
        if not s25.strip():
            return False
    elif isinstance(s25, dict):
        if "same" not in s25:
            return False
        note = s25.get("note")
        if not isinstance(note, str) or not note.strip():
            return False
    else:
        return False
    fp = pred.get("forecast_prop")
    if not isinstance(fp, str) or not fp.strip():
        return False
    prob = pred.get("forecast_prob")
    if isinstance(prob, bool) or not isinstance(prob, (int, float)):
        return False
    return 0.0 <= prob <= 1.0


def load_batch(pred_dir, batch):
    """Load one batch's predictions from its per-round files. Handles
    both the v7 dict-with-'predictions' files and the round-10
    top-level-list files."""
    preds = {}
    for f in sorted(glob.glob(os.path.join(pred_dir, f"predictions-{batch}-*.json"))):
        data = json.load(open(f))
        recs = data["predictions"] if isinstance(data, dict) else data
        for p in recs:
            if p["q_id"] in preds:
                raise AssertionError(f"{batch}: duplicate prediction for q{p['q_id']} in {f}")
            preds[p["q_id"]] = p
    return preds


def score_preds(preds, truth, qids):
    """Core scoring logic, shared by the v7 batches and the gate."""
    correct = [q for q in qids if is_correct(preds, truth, q)]
    by_player = defaultdict(lambda: [0, 0])
    by_kind = defaultdict(lambda: [0, 0])
    for q in qids:
        t = truth[q]
        by_player[t["player"]][1] += 1
        by_kind[t["kind"]][1] += 1
        if q in set(correct):
            by_player[t["player"]][0] += 1
            by_kind[t["kind"]][0] += 1
    return {
        "correct": len(correct), "total": len(qids),
        "correct_qids": sorted(correct),
        "by_player": {k: v for k, v in sorted(by_player.items())},
        "by_kind": {k: v for k, v in sorted(by_kind.items())},
    }


def score_batch(preds, truth, batch, all_qids):
    """Full per-batch report for one v7 batch (all 215 questions)."""
    assert set(preds) == set(all_qids), (
        f"batch {batch} q_id set != testset: "
        f"missing {sorted(set(all_qids) - set(preds))}, "
        f"extra {sorted(set(preds) - set(all_qids))}")
    total = score_preds(preds, truth, sorted(all_qids))
    old_qids = sorted(q for q in all_qids if q <= 98)
    new_qids = sorted(q for q in all_qids if q >= 99)
    capex_qids = sorted(q for q in all_qids if truth[q]["kind"] == "capex")
    dc_qids = sorted(q for q in all_qids if truth[q]["kind"] == "datacenter")
    model_qids = sorted(q for q in all_qids if truth[q]["kind"] in MODEL_KINDS)
    old = score_preds(preds, truth, old_qids)
    new = score_preds(preds, truth, new_qids)
    capex = score_preds(preds, truth, capex_qids)
    model = score_preds(preds, truth, model_qids)
    model_by_kind = {}
    for kind in MODEL_KINDS:
        kq = sorted(q for q in all_qids if truth[q]["kind"] == kind)
        s = score_preds(preds, truth, kq)
        model_by_kind[kind] = [s["correct"], s["total"]]
    rp_qids = sorted(q for q in sorted(all_qids)
                     if roleplay_executed_ok(preds[q]))
    cited_g = len([q for q in capex_qids
                   if non_empty(preds[q].get("guidance_cited"))])
    cited_b = len([q for q in sorted(set(capex_qids) | set(dc_qids))
                   if non_empty(preds[q].get("boundary_cited"))])
    out = {
        "total_215": [total["correct"], 215],
        "correct_qids": total["correct_qids"],
        "by_kind": total["by_kind"],
        "by_player": total["by_player"],
        "old_98": [old["correct"], len(old_qids)],
        "old_98_correct_qids": old["correct_qids"],
        "new_117": [new["correct"], len(new_qids)],
        "new_117_correct_qids": new["correct_qids"],
        "capex_10": [capex["correct"], len(capex_qids)],
        "capex_correct_qids": capex["correct_qids"],
        "capex_qids": capex_qids,
        "datacenter_qids": dc_qids,
        "model_release_66": [model["correct"], len(model_qids)],
        "model_release_correct_qids": model["correct_qids"],
        "model_release_by_kind": model_by_kind,
        "confidence": {},
        "roleplay_execution": {
            "executed": [len(rp_qids), 215],
            "rate": len(rp_qids) / 215,
            "executed_qids": rp_qids,
            "not_executed_qids": sorted(set(all_qids) - set(rp_qids)),
        },
        "guidance_citation": [cited_g, len(capex_qids)],
        "guidance_citation_rate": cited_g / len(capex_qids),
        "boundary_citation": [cited_b, len(set(capex_qids) | set(dc_qids))],
        "boundary_citation_rate": cited_b / len(set(capex_qids) | set(dc_qids)),
        "guesses": {str(q): guessed_kind(preds[q]) for q in sorted(all_qids)},
    }
    for level in ("high", "medium", "low"):
        qs = [q for q in all_qids if preds[q].get("confidence") == level]
        c = len([q for q in qs if is_correct(preds, truth, q)])
        out["confidence"][level] = {
            "correct_total": [c, len(qs)],
            "accuracy": (c / len(qs)) if qs else None,
        }
    return out


def reproduce_gate():
    """Reproduction gate: re-score the round-10 focus totals with this
    script's own core logic. Must match C1 31, C2 31, C3 31, E1 32,
    E2 32 out of 32."""
    truth10 = load_truth(os.path.join(R10_BASE, "testset-v6.json"))
    got = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R10_PRED_DIR, batch)
        assert set(preds) == R10_FOCUS, (
            f"round-10 gate: batch {batch} q_id set != FOCUS32: "
            f"missing {sorted(R10_FOCUS - set(preds))}, "
            f"extra {sorted(set(preds) - R10_FOCUS)}")
        got[batch] = len([q for q in sorted(R10_FOCUS)
                          if is_correct(preds, truth10, q)])
    print("round-10 focus reproduction gate (32 questions, testset-v6):")
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        print(f"  {b}: {got[b]}/32 (expected {R10_TOTAL_EXPECTED[b]}/32)")
    ok = got == R10_TOTAL_EXPECTED
    print("  REPRODUCTION GATE (round 10):", "PASS" if ok else "FAIL")
    if not ok:
        print("  fix score_baseline_v7.py before scoring the baseline retest.")
        sys.exit(1)
    return {"round10_focus": got, "round10_expected": R10_TOTAL_EXPECTED,
            "status": "PASS"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--reproduce-only", action="store_true")
    ap.add_argument("--skip-reproduction", action="store_true")
    args = ap.parse_args()
    truth = load_truth(os.path.join(BASE, "testset-v7.json"))
    all_qids = sorted(truth)

    gate = None
    if not args.skip_reproduction:
        gate = reproduce_gate()
        repro_path = os.path.join(args.pred_dir, "reproduce-baseline-v7.json")
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
        print(f"{batch}: total {r['total_215'][0]}/215 "
              f"old {r['old_98'][0]}/98 new {r['new_117'][0]}/117 "
              f"capex {r['capex_10'][0]}/10 "
              f"model {r['model_release_66'][0]}/66 "
              f"conf high {r['confidence']['high']['correct_total']} "
              f"med {r['confidence']['medium']['correct_total']} "
              f"low {r['confidence']['low']['correct_total']} "
              f"R={r['roleplay_execution']['executed'][0]}/215 "
              f"G={r['guidance_citation'][0]}/{r['guidance_citation'][1]} "
              f"B={r['boundary_citation'][0]}/{r['boundary_citation'][1]}")
    if not found:
        print("no baseline-retest prediction files yet; reproduction gate "
              "passed, nothing to score.")
    else:
        for batch in BATCHES:
            if batch not in found:
                print(f"WARNING: batch {batch} has no prediction files; "
                      f"group summary covers only {found}.")

    if len(found) == 3:
        c_tot = [result[b]["total_215"][0] for b in BATCHES]
        m_tc = sum(c_tot) / 3
        s_t = max(c_tot) - min(c_tot)
        kinds = sorted({q["kind"] for q in truth.values()})
        kind_means = {k: sum(result[b]["by_kind"][k][0] for b in BATCHES) / 3
                      for k in kinds}
        kind_totals = {k: result["C1"]["by_kind"][k][1] for k in kinds}
        players = sorted({q["player"] for q in truth.values()})
        player_means = {p: sum(result[b]["by_player"][p][0] for b in BATCHES) / 3
                        for p in players}
        result["group_summary"] = {
            "control_total": c_tot, "M_TC": m_tc, "spread_S_T": s_t,
            "per_kind_mean_correct": kind_means,
            "per_kind_total": kind_totals,
            "per_player_mean_correct": player_means,
            "old_98_mean": sum(result[b]["old_98"][0] for b in BATCHES) / 3,
            "new_117_mean": sum(result[b]["new_117"][0] for b in BATCHES) / 3,
            "capex_10_mean": sum(result[b]["capex_10"][0] for b in BATCHES) / 3,
            "model_release_66_mean":
                sum(result[b]["model_release_66"][0] for b in BATCHES) / 3,
            "model_release_by_kind_mean": {
                k: sum(result[b]["model_release_by_kind"][k][0]
                       for b in BATCHES) / 3 for k in MODEL_KINDS},
            "confidence_mean": {
                level: sum(result[b]["confidence"][level]["correct_total"][0]
                           for b in BATCHES) / 3
                for level in ("high", "medium", "low")},
            "confidence_total_mean": {
                level: sum(result[b]["confidence"][level]["correct_total"][1]
                           for b in BATCHES) / 3
                for level in ("high", "medium", "low")},
            "R_mean": sum(result[b]["roleplay_execution"]["rate"]
                          for b in BATCHES) / 3,
            "G_mean": sum(result[b]["guidance_citation_rate"]
                          for b in BATCHES) / 3,
            "B_mean": sum(result[b]["boundary_citation_rate"]
                          for b in BATCHES) / 3,
        }
        g = result["group_summary"]
        print(f"group: M_TC={m_tc:.2f} S_T={s_t} "
              f"old_mean={g['old_98_mean']:.2f}/98 "
              f"new_mean={g['new_117_mean']:.2f}/117 "
              f"capex_mean={g['capex_10_mean']:.2f}/10 "
              f"model_mean={g['model_release_66_mean']:.2f}/66 "
              f"R={g['R_mean']:.3f} G={g['G_mean']:.3f} B={g['B_mean']:.3f}")

    out_path = args.out or os.path.join(args.pred_dir, "score-baseline-v7.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
