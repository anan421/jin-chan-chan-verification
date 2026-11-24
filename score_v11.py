#!/usr/bin/env python3
"""Score round 11 (vision11): control D1-D3 (no roleplay) vs experiment
C1-C3 (baseline retest, with roleplay), on testset-v7 (215 questions).

Truth: testset-v7.json. Control predictions:
  runs/round11-vision11-2026-11-22/predictions/  predictions-D{1,2,3}-*.json
Experiment predictions (reused baseline retest, not re-run):
  runs/baseline-retest-2026-11-22/predictions/  predictions-C{1,2,3}-*.json
A guess is correct iff guessed kind == testset kind for that q_id.
Scoring uses only the kind field; fact dates (some written as integers
in control files) do not affect scoring.

REPRODUCTION GATES (run first; any failure exits non-zero, no scores):
  gate A (round-10 focus, testset-v6): C1 31, C2 31, C3 31, E1 32, E2 32 /32.
  gate B (v7 baseline retest, same logic): C1 98, C2 107, C3 95 /215.
Gate results are written to reproduce-v11.json next to the predictions
and into score-v11.json under "reproduction_gates".

Audited experiment scores: leakage exclusions from
runs/baseline-retest-2026-11-22/audit-baseline-v7.json
(leakage_exclusion.by_batch: C1 [30,31], C2 [1,30,31], C3 [30,31];
all 7 records were correct, so audited = raw minus excluded correct).
Audited totals: C1 96, C2 104, C3 93 (mean 97.67). Audited new-117:
C1 38, C2 38, C3 29 (mean 35.00). Denominator stays 215.

Audited control scores: leakage exclusions from
runs/round11-vision11-2026-11-22/audit-v11.json
(exclusions.exclude records: D1 [30], D2 [30], D3 [30,31,32];
all 5 records were correct, so audited = raw minus excluded correct).
Audited totals: D1 90, D2 94, D3 93 (mean 92.33, spread 4).
Same convention as the experiment audit: denominator stays 215 and
an excluded record counts as not correct. (audit-v11.json itself
writes the same numerators with reduced denominators, 90/214,
94/214, 93/212; the mean 92.33 is the same either way.)

GAIN CALIBERS (two numbers, both correct, different definitions):
  Caliber A ("mixed", the script's original G_audited):
    experiment audited mean minus control RAW mean.
    97.67 - 94.00 = 3.67. The control audit is not applied here.
  Caliber B ("both-audited", the report's G, primary caliber):
    experiment audited mean minus control AUDITED mean.
    97.67 - 92.33 = 5.33. Both groups use the leakage-exclusion rule.
  Difference: 5.33 - 3.67 = 1.67, exactly the control audit
    adjustment 94.00 - 92.33 = 1.67 (5 leaked control records:
    D1 q30; D2 q30; D3 q30, q31, q32).
  Both calibers are below the adoption threshold 11, so the
    conclusion is the same under either caliber: roleplay stays
    tentative. The script now outputs both calibers in every run
    (gains.G_audited for A, gains.G_both_audited for B, plus
    gain_calibers with the definitions in words).
  WARNING -- a second, different 3.67: the report's old-question
    gain (both-audited old split) is also 3.67
    (62.67 - 59.00). That is a different number from caliber A
    (97.67 - 94.00). The two 3.67 values agree by coincidence only:
    the experiment audited new-117 mean (35.00) happens to equal
    control raw total (94.00) minus control audited old mean
    (59.00). Do not read one 3.67 as the other.

Decision rules: design/experiment-vision11-round11.md. Evaluated for
the both-audited gain (primary, report caliber), the mixed audited
gain (script's original caliber, kept for backward compatibility),
and the raw gain.

Usage:
  python3 score_v11.py [--pred-dir DIR] [--exp-dir DIR] [--out FILE]
"""
import argparse
import glob
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "round11-vision11-2026-11-22", "predictions")
EXP_DIR = os.path.join(BASE, "runs", "baseline-retest-2026-11-22", "predictions")
AUDIT_PATH = os.path.join(BASE, "runs", "baseline-retest-2026-11-22",
                          "audit-baseline-v7.json")
AUDIT_CONTROL_PATH = os.path.join(BASE, "runs", "round11-vision11-2026-11-22",
                                  "audit-v11.json")
R10_BASE = os.path.join(os.path.expanduser("~"), "workspace",
                        "verification-v1-round10")
R10_PRED_DIR = os.path.join(R10_BASE, "runs", "round10-vision10-2026-11-22",
                            "predictions")

R10_FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
             36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
R10_TOTAL_EXPECTED = {"C1": 31, "C2": 31, "C3": 31, "E1": 32, "E2": 32}
V7_TOTAL_EXPECTED = {"C1": 98, "C2": 107, "C3": 95}

CONTROL_BATCHES = ["D1", "D2", "D3"]
EXP_BATCHES = ["C1", "C2", "C3"]
MODEL_KINDS = ["claude", "chatgpt", "gemini", "r1", "v3", "tongyi",
               "llama", "kimi", "muse", "glm", "minimax"]
# New kinds named in design/experiment-vision11-round11.md ("重点看新种类").
NEW_KINDS = ["agent", "arr", "acquisition", "social", "partnership", "kimi",
             "math", "memory", "wallstreet", "talent", "video", "muse"]


def load_truth(path):
    ts = json.load(open(path))
    qs = ts["questions"] if isinstance(ts, dict) else ts
    return {q["q_id"]: q for q in qs}


def guessed_kind(pred):
    return pred.get("kind", pred.get("predicted_kind"))


def is_correct(preds, truth, qid):
    return guessed_kind(preds[qid]) == truth[qid]["kind"]


def non_empty(v):
    if v is None:
        return False
    if isinstance(v, str):
        return len(v.strip()) > 0
    if isinstance(v, dict):
        return len(v) > 0
    return True


def roleplay_executed_ok(pred):
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
    correct = [q for q in qids if is_correct(preds, truth, q)]
    by_player = defaultdict(lambda: [0, 0])
    by_kind = defaultdict(lambda: [0, 0])
    cset = set(correct)
    for q in qids:
        t = truth[q]
        by_player[t["player"]][1] += 1
        by_kind[t["kind"]][1] += 1
        if q in cset:
            by_player[t["player"]][0] += 1
            by_kind[t["kind"]][0] += 1
    return {"correct": len(correct), "total": len(qids),
            "correct_qids": sorted(correct),
            "by_player": {k: v for k, v in sorted(by_player.items())},
            "by_kind": {k: v for k, v in sorted(by_kind.items())}}


def score_batch(preds, truth, batch, all_qids):
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


def score_batch_excluding(preds, truth, batch, all_qids, exclude_qids):
    """Audited rescore: excluded qids count as not correct, denominator
    stays 215 (same convention as audit-baseline-v7.json)."""
    kept = [q for q in sorted(all_qids) if q not in set(exclude_qids)]
    # Score on kept qids only; totals count excluded qids as not correct,
    # denominator stays 215 (same convention as audit-baseline-v7.json).
    total = score_preds(preds, truth, kept)
    old_qids = sorted(q for q in kept if q <= 98)
    new_qids = sorted(q for q in kept if q >= 99)
    capex_qids = sorted(q for q in kept if truth[q]["kind"] == "capex")
    model_qids = sorted(q for q in kept if truth[q]["kind"] in MODEL_KINDS)
    old = score_preds(preds, truth, old_qids)
    new = score_preds(preds, truth, new_qids)
    capex = score_preds(preds, truth, capex_qids)
    model = score_preds(preds, truth, model_qids)
    model_by_kind = {}
    for kind in MODEL_KINDS:
        kq = sorted(q for q in kept if truth[q]["kind"] == kind)
        s = score_preds(preds, truth, kq)
        model_by_kind[kind] = [s["correct"], s["total"]]
    out = {
        "total_215": [total["correct"], 215],
        "correct_qids": total["correct_qids"],
        "by_kind": total["by_kind"],
        "by_player": total["by_player"],
        "old_98": [old["correct"], 98],
        "old_98_correct_qids": old["correct_qids"],
        "new_117": [new["correct"], 117],
        "new_117_correct_qids": new["correct_qids"],
        "capex_10": [capex["correct"], 10],
        "capex_correct_qids": capex["correct_qids"],
        "model_release_66": [model["correct"], 66],
        "model_release_correct_qids": model["correct_qids"],
        "model_release_by_kind": model_by_kind,
        "excluded_qids": sorted(exclude_qids),
        "confidence": {},
    }
    for level in ("high", "medium", "low"):
        qs = [q for q in kept if preds[q].get("confidence") == level]
        c = len([q for q in qs if is_correct(preds, truth, q)])
        out["confidence"][level] = {
            "correct_total": [c, len(qs)],
            "accuracy": (c / len(qs)) if qs else None,
        }
    return out


def mean(xs):
    return sum(xs) / len(xs)


def group_summary(batches_scores, batches):
    kinds = sorted({k for b in batches for k in batches_scores[b]["by_kind"]})
    players = sorted({p for b in batches for p in batches_scores[b]["by_player"]})
    tot = [batches_scores[b]["total_215"][0] for b in batches]
    conf_pool = {}
    for level in ("high", "medium", "low"):
        c = sum(batches_scores[b]["confidence"][level]["correct_total"][0] for b in batches)
        n = sum(batches_scores[b]["confidence"][level]["correct_total"][1] for b in batches)
        conf_pool[level] = {"correct_total": [c, n],
                            "accuracy": (c / n) if n else None}
    return {
        "totals": tot, "mean": mean(tot), "spread": max(tot) - min(tot),
        "per_kind_mean_correct": {
            k: mean([batches_scores[b]["by_kind"][k][0] for b in batches]) for k in kinds},
        "per_kind_total": {k: batches_scores[batches[0]]["by_kind"][k][1] for k in kinds},
        "per_player_mean_correct": {
            p: mean([batches_scores[b]["by_player"][p][0] for b in batches]) for p in players},
        "per_player_total": {p: batches_scores[batches[0]]["by_player"][p][1] for p in players},
        "old_98_mean": mean([batches_scores[b]["old_98"][0] for b in batches]),
        "new_117_mean": mean([batches_scores[b]["new_117"][0] for b in batches]),
        "capex_10_mean": mean([batches_scores[b]["capex_10"][0] for b in batches]),
        "model_release_66_mean": mean([batches_scores[b]["model_release_66"][0] for b in batches]),
        "model_release_by_kind_mean": {
            k: mean([batches_scores[b]["model_release_by_kind"][k][0] for b in batches])
            for k in MODEL_KINDS},
        "confidence_pooled": conf_pool,
        "confidence_mean_correct": {
            level: mean([batches_scores[b]["confidence"][level]["correct_total"][0] for b in batches])
            for level in ("high", "medium", "low")},
        "guidance_citation_mean_rate": mean([batches_scores[b]["guidance_citation_rate"] for b in batches]),
        "boundary_citation_mean_rate": mean([batches_scores[b]["boundary_citation_rate"] for b in batches]),
        "roleplay_execution_mean_rate": mean([batches_scores[b]["roleplay_execution"]["rate"] for b in batches]),
    }


def audited_group_summary(aud, batches, raw_ref, truth):
    """Group summary for audited rescoring (totals/old/new/capex/model/
    per-kind/per-player/pooled confidence). Same fields as the old
    inline experiment-audited summary; used for both groups so the
    two calibers are computed by the same code. Denominator stays
    215: an excluded record counts as not correct."""
    tot = [aud[b]["total_215"][0] for b in batches]
    kinds = sorted({q["kind"] for q in truth.values()})
    players = sorted({q["player"] for q in truth.values()})
    conf_pool = {}
    for level in ("high", "medium", "low"):
        c = sum(aud[b]["confidence"][level]["correct_total"][0] for b in batches)
        n = sum(aud[b]["confidence"][level]["correct_total"][1] for b in batches)
        conf_pool[level] = {"correct_total": [c, n],
                            "accuracy": (c / n) if n else None}
    return {
        "totals": tot, "mean": mean(tot), "spread": max(tot) - min(tot),
        "old_98_mean": mean([aud[b]["old_98"][0] for b in batches]),
        "new_117_mean": mean([aud[b]["new_117"][0] for b in batches]),
        "capex_10_mean": mean([aud[b]["capex_10"][0] for b in batches]),
        "model_release_66_mean": mean([aud[b]["model_release_66"][0] for b in batches]),
        "per_kind_mean_correct": {
            k: mean([aud[b]["by_kind"].get(k, [0, 0])[0] for b in batches]) for k in kinds},
        "per_kind_total": {k: raw_ref[batches[0]]["by_kind"][k][1] for k in kinds},
        "per_player_mean_correct": {
            p: mean([aud[b]["by_player"].get(p, [0, 0])[0] for b in batches]) for p in players},
        "confidence_pooled": conf_pool,
    }


def reproduce_gates():
    truth10 = load_truth(os.path.join(R10_BASE, "testset-v6.json"))
    got10 = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R10_PRED_DIR, batch)
        assert set(preds) == R10_FOCUS, f"round-10 gate: batch {batch} set != FOCUS32"
        got10[batch] = len([q for q in sorted(R10_FOCUS)
                            if is_correct(preds, truth10, q)])
    ok10 = got10 == R10_TOTAL_EXPECTED
    print("gate A round-10 focus (32q, testset-v6):",
          {b: f"{got10[b]}/32 (exp {R10_TOTAL_EXPECTED[b]})" for b in got10},
          "PASS" if ok10 else "FAIL")

    truth7 = load_truth(os.path.join(BASE, "testset-v7.json"))
    all_qids = sorted(truth7)
    got7 = {}
    for batch in EXP_BATCHES:
        preds = load_batch(EXP_DIR, batch)
        got7[batch] = score_batch(preds, truth7, batch, all_qids)["total_215"][0]
    ok7 = got7 == V7_TOTAL_EXPECTED
    print("gate B v7 baseline retest (215q, testset-v7):",
          {b: f"{got7[b]}/215 (exp {V7_TOTAL_EXPECTED[b]})" for b in got7},
          "PASS" if ok7 else "FAIL")
    if not (ok10 and ok7):
        print("REPRODUCTION GATE FAILED: fix score_v11.py before scoring.")
        sys.exit(1)
    return {"gate_A_round10_focus": {"got": got10, "expected": R10_TOTAL_EXPECTED,
                                     "status": "PASS"},
            "gate_B_v7_baseline_retest": {"got": got7, "expected": V7_TOTAL_EXPECTED,
                                          "status": "PASS"}}


def evaluate_decision_rules(G, G_new, S_TD, S_TE, contrib):
    """contrib: {q_id: net contribution (e_frac - d_frac)} for audited/raw
    pairing. Returns per-condition verdicts."""
    pos_qs = sorted(q for q, c in contrib.items() if c > 0)
    max_c = max(contrib.values()) if contrib else 0.0
    a = G > max(S_TD, S_TE)
    b = G >= 3
    c = G_new > 0
    d = (len(pos_qs) >= 2) and (G <= 0 or max_c < G / 2)
    adopt = a and b and c and d
    remove = (G <= 0) or (G_new <= 0)
    mixed = (G > 0) and (G_new > 0) and not (a and b)
    if adopt:
        verdict = "ADOPT (roleplay verified into baseline)"
    elif remove:
        verdict = "REMOVE (roleplay out of baseline)"
    elif mixed:
        verdict = "MIXED (helpful but below adoption threshold; stays tentative)"
    else:
        verdict = "MIXED-OTHER (G>0, G_new>0, (a)/(b) pass but (d) fails; stays tentative)"
    return {
        "(a) G > max(S_TD,S_TE)": {"value": f"G={G:.2f} vs max({S_TD},{S_TE})={max(S_TD, S_TE)}",
                                   "pass": bool(a)},
        "(b) G >= 3": {"value": f"G={G:.2f}", "pass": bool(b)},
        "(c) G_new > 0": {"value": f"G_new={G_new:.2f}", "pass": bool(c)},
        "(d) gain from >=2 questions, no single question > half of gain": {
            "value": (f"positive-contribution questions={len(pos_qs)} {pos_qs[:20]}"
                      f"{'...' if len(pos_qs) > 20 else ''}; max single contribution={max_c:.2f}"
                      f"; G/2={G / 2:.2f}"),
            "pass": bool(d)},
        "adopt_all_four": bool(adopt),
        "remove_any": bool(remove),
        "mixed": bool(mixed),
        "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--exp-dir", default=EXP_DIR)
    ap.add_argument("--out", default=None)
    ap.add_argument("--reproduce-only", action="store_true")
    ap.add_argument("--skip-reproduction", action="store_true")
    args = ap.parse_args()
    truth = load_truth(os.path.join(BASE, "testset-v7.json"))
    all_qids = sorted(truth)

    gates = None
    if not args.skip_reproduction:
        gates = reproduce_gates()
        run_root = os.path.dirname(os.path.normpath(args.pred_dir))
        repro_path = os.path.join(run_root, "reproduce-v11.json")
        os.makedirs(args.pred_dir, exist_ok=True)
        with open(repro_path, "w") as fh:
            json.dump(gates, fh, indent=2, ensure_ascii=False)
        print(f"wrote {repro_path}")
    if args.reproduce_only:
        return

    result = {"reproduction_gates": gates}

    # --- control batches D1-D3 ---
    control = {}
    control_preds = {}
    for batch in CONTROL_BATCHES:
        preds = load_batch(args.pred_dir, batch)
        control_preds[batch] = preds
        control[batch] = score_batch(preds, truth, batch, all_qids)
        r = control[batch]
        print(f"{batch}: total {r['total_215'][0]}/215 old {r['old_98'][0]}/98 "
              f"new {r['new_117'][0]}/117 capex {r['capex_10'][0]}/10 "
              f"model {r['model_release_66'][0]}/66 "
              f"conf high {r['confidence']['high']['correct_total']} "
              f"med {r['confidence']['medium']['correct_total']} "
              f"low {r['confidence']['low']['correct_total']} "
              f"R={r['roleplay_execution']['executed'][0]}/215 "
              f"G={r['guidance_citation'][0]}/{r['guidance_citation'][1]} "
              f"B={r['boundary_citation'][0]}/{r['boundary_citation'][1]}")
    result["control"] = control
    result["control_group"] = group_summary(control, CONTROL_BATCHES)

    # --- experiment batches C1-C3, raw (same logic) ---
    exp_raw = {}
    exp_preds = {}
    for batch in EXP_BATCHES:
        preds = load_batch(args.exp_dir, batch)
        exp_preds[batch] = preds
        exp_raw[batch] = score_batch(preds, truth, batch, all_qids)
    result["experiment_raw"] = exp_raw
    result["experiment_raw_group"] = group_summary(exp_raw, EXP_BATCHES)

    # --- experiment batches, audited (leakage exclusion) ---
    audit = json.load(open(AUDIT_PATH))
    excl = audit["leakage_exclusion"]["by_batch"]
    exp_aud = {}
    for batch in EXP_BATCHES:
        exp_aud[batch] = score_batch_excluding(
            exp_preds[batch], truth, batch, all_qids, excl[batch])
    result["experiment_audited"] = exp_aud
    result["experiment_audited_group"] = audited_group_summary(
        exp_aud, EXP_BATCHES, exp_raw, truth)
    result["experiment_audited_group"]["excluded_by_batch"] = excl

    # --- control batches, audited (leakage exclusion, same convention) ---
    # audit-v11.json has no leakage_exclusion.by_batch key; the
    # exclusions live in exclusions.exclude records (batch + q_id).
    audit_ctrl = json.load(open(AUDIT_CONTROL_PATH))
    excl_ctrl = {b: [] for b in CONTROL_BATCHES}
    for rec in audit_ctrl["exclusions"]["exclude"]:
        excl_ctrl[rec["batch"]].append(rec["q_id"])
    ctrl_aud = {}
    for batch in CONTROL_BATCHES:
        ctrl_aud[batch] = score_batch_excluding(
            control_preds[batch], truth, batch, all_qids, excl_ctrl[batch])
    result["control_audited"] = ctrl_aud
    result["control_audited_group"] = audited_group_summary(
        ctrl_aud, CONTROL_BATCHES, control, truth)
    result["control_audited_group"]["excluded_by_batch"] = excl_ctrl

    cg = result["control_group"]
    cg_aud = result["control_audited_group"]
    eg_raw = result["experiment_raw_group"]
    eg_aud = result["experiment_audited_group"]
    M_TD = cg["mean"]; S_TD = cg["spread"]
    M_TD_aud = cg_aud["mean"]; S_TD_aud = cg_aud["spread"]
    M_TE_raw = eg_raw["mean"]; S_TE_raw = eg_raw["spread"]
    M_TE_aud = eg_aud["mean"]; S_TE_aud = eg_aud["spread"]

    # --- gains: both calibers, every run ---
    # Caliber A ("mixed", original G_audited): experiment audited
    #   minus control RAW. 97.67 - 94.00 = 3.67.
    # Caliber B ("both-audited", report G, primary): experiment
    #   audited minus control AUDITED. 97.67 - 92.33 = 5.33.
    # Difference B - A = 1.67 = control audit adjustment
    #   (94.00 - 92.33). Old keys are kept unchanged.
    gains = {
        "G_raw": M_TE_raw - M_TD,
        "M_TE_raw": M_TE_raw, "M_TD": M_TD,
        "G_audited": M_TE_aud - M_TD,
        "M_TE_audited": M_TE_aud,
        "G_new_raw": eg_raw["new_117_mean"] - cg["new_117_mean"],
        "M_TE_new_raw": eg_raw["new_117_mean"], "M_TD_new": cg["new_117_mean"],
        "G_new_audited": eg_aud["new_117_mean"] - cg["new_117_mean"],
        "M_TE_new_audited": eg_aud["new_117_mean"],
        "G_old_raw": eg_raw["old_98_mean"] - cg["old_98_mean"],
        "G_old_audited": eg_aud["old_98_mean"] - cg["old_98_mean"],
        "S_TD": S_TD, "S_TE_raw": S_TE_raw, "S_TE_audited": S_TE_aud,
        "M_TD_audited": M_TD_aud, "S_TD_audited": S_TD_aud,
        "M_TD_old_audited": cg_aud["old_98_mean"],
        "M_TD_new_audited": cg_aud["new_117_mean"],
        "G_both_audited": M_TE_aud - M_TD_aud,
        "G_mixed_audited_exp_raw_control": M_TE_aud - M_TD,
        "G_new_both_audited": eg_aud["new_117_mean"] - cg_aud["new_117_mean"],
        "G_old_both_audited": eg_aud["old_98_mean"] - cg_aud["old_98_mean"],
        "G_new_mixed": eg_aud["new_117_mean"] - cg["new_117_mean"],
        "G_old_mixed": eg_aud["old_98_mean"] - cg["old_98_mean"],
    }
    result["gains"] = gains
    result["gain_calibers"] = {
        "caliber_A_mixed": {
            "name": "G_audited (script original)",
            "definition": "Experiment audited mean minus control RAW mean. "
                          "Only the experiment group gets leakage exclusion.",
            "formula": "M_TE_audited - M_TD = 97.67 - 94.00",
            "value": gains["G_audited"],
            "experiment": {"batches": ["C1", "C2", "C3"], "audited_totals": [96, 104, 93],
                           "mean": M_TE_aud, "excluded": excl},
            "control": {"batches": ["D1", "D2", "D3"], "raw_totals": [91, 95, 96],
                        "mean": M_TD, "excluded": "none (raw)"},
        },
        "caliber_B_both_audited": {
            "name": "G_both_audited (report G, primary caliber)",
            "definition": "Experiment audited mean minus control AUDITED mean. "
                          "Both groups use the leakage-exclusion rule.",
            "formula": "M_TE_audited - M_TD_audited = 97.67 - 92.33",
            "value": gains["G_both_audited"],
            "experiment": {"batches": ["C1", "C2", "C3"], "audited_totals": [96, 104, 93],
                           "mean": M_TE_aud, "excluded": excl},
            "control": {"batches": ["D1", "D2", "D3"], "audited_totals": [90, 94, 93],
                        "mean": M_TD_aud, "excluded": excl_ctrl},
        },
        "difference_B_minus_A": gains["G_both_audited"] - gains["G_audited"],
        "difference_source": "Control audit adjustment M_TD - M_TD_audited "
                             "= 94.00 - 92.33 = 1.67 (5 leaked control records: "
                             "D1 q30; D2 q30; D3 q30, q31, q32).",
        "primary_caliber": "caliber_B_both_audited",
        "conclusion_note": "Both calibers are below the adoption threshold 11 "
                           "(max noise spread), so the conclusion is the same "
                           "under either caliber: roleplay stays tentative.",
        "warning_second_3_67": "The report's old-question gain (both-audited "
            "old split, 62.67 - 59.00) is also 3.67, but it is a different "
            "number from caliber A (97.67 - 94.00). The two 3.67 values "
            "agree by coincidence only. Do not read one 3.67 as the other.",
    }

    # --- paired results per question (batch pairs D_i vs C_i) ---
    paired_raw_pairs = []
    paired_aud_pairs = []
    paired_both_aud_pairs = []
    per_question = []
    for i, (db, eb) in enumerate(zip(CONTROL_BATCHES, EXP_BATCHES)):
        dp, ep = control_preds[db], exp_preds[eb]
        both = e_only = d_only = neither = 0
        both_a = e_only_a = d_only_a = neither_a = 0
        both_b = e_only_b = d_only_b = neither_b = 0
        for q in all_qids:
            dc = is_correct(dp, truth, q)
            ec = is_correct(ep, truth, q)
            ec_a = ec and (q not in set(excl[eb]))
            dc_a = dc and (q not in set(excl_ctrl[db]))
            if ec and dc:
                both += 1
            elif ec and not dc:
                e_only += 1
            elif dc and not ec:
                d_only += 1
            else:
                neither += 1
            if ec_a and dc:
                both_a += 1
            elif ec_a and not dc:
                e_only_a += 1
            elif dc and not ec_a:
                d_only_a += 1
            else:
                neither_a += 1
            if ec_a and dc_a:
                both_b += 1
            elif ec_a and not dc_a:
                e_only_b += 1
            elif dc_a and not ec_a:
                d_only_b += 1
            else:
                neither_b += 1
        paired_raw_pairs.append({"pair": f"{db}-vs-{eb}", "both": both,
                                 "exp_only": e_only, "control_only": d_only,
                                 "neither": neither})
        paired_aud_pairs.append({"pair": f"{db}-vs-{eb}", "both": both_a,
                                 "exp_only": e_only_a, "control_only": d_only_a,
                                 "neither": neither_a})
        paired_both_aud_pairs.append({"pair": f"{db}-vs-{eb}", "both": both_b,
                                      "exp_only": e_only_b, "control_only": d_only_b,
                                      "neither": neither_b})
    def avg_pairs(pairs):
        return {k: mean([p[k] for p in pairs]) for k in ("both", "exp_only", "control_only", "neither")}
    for q in all_qids:
        e_n = sum(1 for b in EXP_BATCHES if is_correct(exp_preds[b], truth, q))
        e_n_a = sum(1 for b in EXP_BATCHES
                    if is_correct(exp_preds[b], truth, q) and q not in set(excl[b]))
        d_n = sum(1 for b in CONTROL_BATCHES if is_correct(control_preds[b], truth, q))
        d_n_a = sum(1 for b in CONTROL_BATCHES
                    if is_correct(control_preds[b], truth, q) and q not in set(excl_ctrl[b]))
        per_question.append({
            "q_id": q, "kind": truth[q]["kind"], "player": truth[q]["player"],
            "event_name": truth[q]["event_name"], "new_question": q >= 99,
            "new_kind": truth[q]["kind"] in NEW_KINDS,
            "exp_correct_batches": e_n, "exp_correct_batches_audited": e_n_a,
            "control_correct_batches": d_n,
            "control_correct_batches_audited": d_n_a,
            "net_contrib_raw": e_n / 3 - d_n / 3,
            "net_contrib_audited": e_n_a / 3 - d_n / 3,
            "net_contrib_both_audited": e_n_a / 3 - d_n_a / 3,
        })
    result["paired"] = {
        "per_batch_pair_raw": paired_raw_pairs,
        "per_batch_pair_audited": paired_aud_pairs,
        "per_batch_pair_both_audited": paired_both_aud_pairs,
        "average_raw": avg_pairs(paired_raw_pairs),
        "average_audited": avg_pairs(paired_aud_pairs),
        "average_both_audited": avg_pairs(paired_both_aud_pairs),
        "per_question": per_question,
    }

    # --- decision rules (both-audited primary, mixed audited kept, raw also) ---
    contrib_aud = {p["q_id"]: p["net_contrib_audited"] for p in per_question}
    contrib_raw = {p["q_id"]: p["net_contrib_raw"] for p in per_question}
    contrib_both = {p["q_id"]: p["net_contrib_both_audited"] for p in per_question}
    result["decision_rules"] = {
        "audited_primary": evaluate_decision_rules(
            gains["G_audited"], gains["G_new_audited"], S_TD, S_TE_aud, contrib_aud),
        "both_audited": evaluate_decision_rules(
            gains["G_both_audited"], gains["G_new_both_audited"],
            S_TD_aud, S_TE_aud, contrib_both),
        "raw": evaluate_decision_rules(
            gains["G_raw"], gains["G_new_raw"], S_TD, S_TE_raw, contrib_raw),
    }

    # --- roleplay harms: experiment wrong, control right, on new kinds ---
    harm_strict = [p for p in per_question
                   if p["new_kind"] and p["exp_correct_batches_audited"] == 0
                   and p["control_correct_batches"] >= 1]
    harm_any = [p for p in per_question
                if p["new_kind"] and p["net_contrib_audited"] < 0]
    harm_new_q = [p for p in per_question
                  if p["new_question"] and p["exp_correct_batches_audited"] == 0
                  and p["control_correct_batches"] >= 1]
    result["roleplay_harms"] = {
        "new_kinds_definition": NEW_KINDS,
        "strict_exp0_control_ge1_new_kind": [
            {k: p[k] for k in ("q_id", "kind", "player", "event_name",
                               "exp_correct_batches_audited", "control_correct_batches")}
            for p in harm_strict],
        "any_net_negative_new_kind": [
            {k: p[k] for k in ("q_id", "kind", "player", "event_name",
                               "exp_correct_batches_audited", "control_correct_batches",
                               "net_contrib_audited")}
            for p in harm_any],
        "strict_exp0_control_ge1_new_question_q_ge_99": [
            {k: p[k] for k in ("q_id", "kind", "player", "event_name",
                               "exp_correct_batches_audited", "control_correct_batches")}
            for p in harm_new_q],
        "counts": {"strict_new_kind": len(harm_strict),
                   "any_net_negative_new_kind": len(harm_any),
                   "strict_new_question": len(harm_new_q)},
    }

    # --- per-kind comparison table ---
    kinds = sorted({q["kind"] for q in truth.values()})
    kind_table = {}
    for k in kinds:
        kind_table[k] = {
            "total": cg["per_kind_total"][k],
            "control_mean": cg["per_kind_mean_correct"][k],
            "control_by_batch": [control[b]["by_kind"][k][0] for b in CONTROL_BATCHES],
            "exp_mean_raw": eg_raw["per_kind_mean_correct"][k],
            "exp_by_batch_raw": [exp_raw[b]["by_kind"][k][0] for b in EXP_BATCHES],
            "exp_mean_audited": eg_aud["per_kind_mean_correct"][k],
            "gain_mean_audited": eg_aud["per_kind_mean_correct"][k] - cg["per_kind_mean_correct"][k],
            "gain_mean_raw": eg_raw["per_kind_mean_correct"][k] - cg["per_kind_mean_correct"][k],
            "new_kind": k in NEW_KINDS,
        }
    result["kind_comparison"] = kind_table

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.normpath(args.pred_dir)), "score-v11.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")
    print(f"control: {[control[b]['total_215'][0] for b in CONTROL_BATCHES]} "
          f"M_TD={M_TD:.2f} S_TD={S_TD} old_mean={cg['old_98_mean']:.2f} "
          f"new_mean={cg['new_117_mean']:.2f}")
    print(f"experiment raw: {[exp_raw[b]['total_215'][0] for b in EXP_BATCHES]} "
          f"M_TE_raw={M_TE_raw:.2f} S_TE_raw={S_TE_raw} new_mean={eg_raw['new_117_mean']:.2f}")
    print(f"experiment audited: {eg_aud['totals']} M_TE_aud={M_TE_aud:.2f} "
          f"S_TE_aud={S_TE_aud} new_mean={eg_aud['new_117_mean']:.2f}")
    print(f"control audited: {[ctrl_aud[b]['total_215'][0] for b in CONTROL_BATCHES]} "
          f"M_TD_aud={M_TD_aud:.2f} S_TD_aud={S_TD_aud} "
          f"old_mean={cg_aud['old_98_mean']:.2f} new_mean={cg_aud['new_117_mean']:.2f}")
    print(f"G_raw={gains['G_raw']:.2f} G_audited(mixed)={gains['G_audited']:.2f} "
          f"G_both_audited={gains['G_both_audited']:.2f} "
          f"(B-A={gains['G_both_audited'] - gains['G_audited']:.2f} = control audit "
          f"adjustment {M_TD:.2f}-{M_TD_aud:.2f}) "
          f"G_new_both_audited={gains['G_new_both_audited']:.2f} "
          f"G_old_both_audited={gains['G_old_both_audited']:.2f}")
    print("decision (both-audited, report caliber):", result["decision_rules"]["both_audited"]["verdict"])
    print("decision (audited/mixed):", result["decision_rules"]["audited_primary"]["verdict"])
    print("decision (raw):", result["decision_rules"]["raw"]["verdict"])


if __name__ == "__main__":
    main()
