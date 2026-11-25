#!/usr/bin/env python3
"""Score round 12, direction 2 (repair the weak new kinds).

Control C1-C3: cleaned baseline package (search boundary + forward
guidance steps + datacenter/capex boundary + roleplay, all cleaned).
Experiment E1-E3: control package + the weak-repair method file
(design/round12-weak-repair-method.md).
Same 215 questions (testset-v7). A guess is correct iff guessed kind
== testset kind for that q_id. Scoring uses only the kind field.

Splits: v7-A (108, method-selection set) and v7-B (107, scoring set),
from the testset "split" field. A-set scores are an upper bound, not
the true level: the A set was used for method selection in rounds 7-11.

LEAKAGE EXCLUSION (adoption computation):
  The Phase 4 protocol section 3.2 / 6.1 says 39 leaked questions are
  excluded from the adoption computation, and section 11.3 lists the
  leaked questions. The two do not agree: section 11.3 lists 42
  questions, and no 39-question list exists anywhere in the repo
  (see design/adoption-decision-records.md, open item 1). This script
  uses the section 11.3 list (42 questions) because it is the only
  concrete list, reports the leaked-subset scores separately, and
  records the 39-vs-42 mismatch in the output. Which list governs the
  adoption decision is for the coordinator to decide; this script
  does not decide it.
  LEAK_42 (protocol section 11.3): q0, q1, q2, q3, q4, q5, q7, q8,
  q9, q10, q11, q12, q13, q14, q15, q16, q17, q18, q19, q20, q24,
  q30, q31, q32, q35, q36, q37, q41, q42, q45, q49, q50, q61, q63,
  q67, q69, q70, q74, q78, q89, q92, q98.
  Excluded questions count as not correct; denominators stay 215
  (same convention as the round-11 audits).

McNEMAR: exact two-sided binomial test on the discordant pairs of
  each batch pair (C_i vs E_i). p < 0.05 is significant. No chi-square
  approximation, no continuity correction. Pure-python exact test
  (math.comb); no scipy dependency.

DECISION RULES (protocol section 6.1, all six, evaluated on the
leakage-excluded scores):
  (1) G > max(11, round noise band). Round noise band =
      max(control spread, experiment spread) on excluded scores.
      G equal to the band does not pass.
  (2) McNemar two-sided p < 0.05 for every batch pair C_i vs E_i.
  (3) G >= 3.
  (4) Gain from >= 2 questions; no single question > half of G.
  (5) Weakest kind does not fall: experiment weakest-kind rate >=
      control weakest-kind rate (excluded scores).
  (6) Gain is not on leaked questions: the excluded gain still
      satisfies (1)-(5). This is exactly what "excluded gain still
      satisfies conditions one to five" means, so (6) passes iff
      the excluded gain G > 0 and (1)-(5) pass on excluded scores.
  All six pass: ADOPT. G <= 0, or G_new <= 0, or gain only from
  leaked questions, or the method harms the new kinds: REMOVE.
  Otherwise: MIXED (helpful but below threshold; stays tentative).

H-W (direction-2 hypothesis, protocol section 4.2/4.3):
  The weak-repair method lifts the weakest kind rate above 50%,
  total score does not fall, weak-kind total gain > 0. Falsified if
  the weakest kind rate stays below 50%, or the total falls below
  control, or the weak-kind total gain is 0.
  WEAK_KINDS: acquisition (9), arr (13), partnership (6), math (5),
  wallstreet (4), social (8). 45 questions.

REPRODUCTION GATES (run first; any failure exits non-zero, no scores):
  gate 0 (round-10 focus, testset-v6): C1 31, C2 31, C3 31, E1 32,
    E2 32 /32. Same core logic as score_v11.py.
  gate 1 (v7 baseline retest, audited): C1 96, C2 104, C3 93 /215,
    mean 97.67. Exclusions from the round-11 audit file
    (audit-baseline-v7.json leakage_exclusion.by_batch).
  gate 2 (round-11 control, audited): D1 90, D2 94, D3 93 /215,
    mean 92.33; both-audited gain +5.33 (97.67 - 92.33).
    Exclusions from audit-v11.json exclusions.exclude.
  Gate results are written to reproduce-round12.json next to the
  predictions and into score-round12.json under
  "reproduction_gates".

Usage:
  python3 score_round12.py [--pred-dir DIR] [--out FILE]
  python3 score_round12.py --reproduce-only   (gates only, no scoring)
"""
import argparse
import glob
import json
import math
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, "runs", "round12-weak-repair-2026-11-25")
PRED_DIR = os.path.join(RUN, "predictions")
R11_BASE = os.path.join(os.path.expanduser("~"), "workspace",
                        "verification-v1-round11")
R11_BASELINE_DIR = os.path.join(R11_BASE, "runs",
                                "baseline-retest-2026-11-22", "predictions")
R11_BASELINE_AUDIT = os.path.join(R11_BASE, "runs",
                                  "baseline-retest-2026-11-22",
                                  "audit-baseline-v7.json")
R11_CONTROL_DIR = os.path.join(R11_BASE, "runs",
                               "round11-vision11-2026-11-22", "predictions")
R11_CONTROL_AUDIT = os.path.join(R11_BASE, "runs",
                                 "round11-vision11-2026-11-22",
                                 "audit-v11.json")
R10_BASE = os.path.join(os.path.expanduser("~"), "workspace",
                        "verification-v1-round10")
R10_PRED_DIR = os.path.join(R10_BASE, "runs", "round10-vision10-2026-11-22",
                            "predictions")

R10_FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
             36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
R10_TOTAL_EXPECTED = {"C1": 31, "C2": 31, "C3": 31, "E1": 32, "E2": 32}
V7_BASELINE_AUDITED_EXPECTED = {"C1": 96, "C2": 104, "C3": 93}
V7_R11_CONTROL_AUDITED_EXPECTED = {"D1": 90, "D2": 94, "D3": 93}
R11_GAIN_BOTH_AUDITED_EXPECTED = 5.33

CONTROL_BATCHES = ["C1", "C2", "C3"]
EXP_BATCHES = ["E1", "E2", "E3"]
MODEL_KINDS = ["claude", "chatgpt", "gemini", "r1", "v3", "tongyi",
               "llama", "kimi", "muse", "glm", "minimax"]
# New kinds named in design/experiment-vision11-round11.md.
NEW_KINDS = ["agent", "arr", "acquisition", "social", "partnership", "kimi",
             "math", "memory", "wallstreet", "talent", "video", "muse"]
# Weak kinds the round-12 repair targets (protocol section 1.3 / 4.2).
WEAK_KINDS = ["acquisition", "arr", "partnership", "math", "wallstreet",
              "social"]
# Protocol section 11.3 list (42 questions). See module docstring:
# sections 3.2/6.1 say 39, but no 39-question list exists.
LEAK_42 = [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
           19, 20, 24, 30, 31, 32, 35, 36, 37, 41, 42, 45, 49, 50, 61, 63,
           67, 69, 70, 74, 78, 89, 92, 98]


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


def mcnemar_exact_two_sided(b, c):
    """Exact two-sided McNemar p value on discordant counts b and c.

    Under the null the discordant pairs split 50/50. Two-sided p =
    2 * P(Bin(n, 0.5) <= min(b, c)), capped at 1. n = b + c.
    n = 0 (no discordant pair) gives p = 1.0.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


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


def split_qids(truth, all_qids, split):
    return sorted(q for q in all_qids if truth[q]["split"] == split)


def score_batch(preds, truth, batch, all_qids):
    assert set(preds) == set(all_qids), (
        f"batch {batch} q_id set != testset: "
        f"missing {sorted(set(all_qids) - set(preds))}, "
        f"extra {sorted(set(preds) - set(all_qids))}")
    total = score_preds(preds, truth, sorted(all_qids))
    old_qids = sorted(q for q in all_qids if q <= 98)
    new_qids = sorted(q for q in all_qids if q >= 99)
    a_qids = split_qids(truth, all_qids, "A")
    b_qids = split_qids(truth, all_qids, "B")
    weak_qids = sorted(q for q in all_qids if truth[q]["kind"] in WEAK_KINDS)
    capex_qids = sorted(q for q in all_qids if truth[q]["kind"] == "capex")
    dc_qids = sorted(q for q in all_qids if truth[q]["kind"] == "datacenter")
    model_qids = sorted(q for q in all_qids if truth[q]["kind"] in MODEL_KINDS)
    old = score_preds(preds, truth, old_qids)
    new = score_preds(preds, truth, new_qids)
    spa = score_preds(preds, truth, a_qids)
    spb = score_preds(preds, truth, b_qids)
    weak = score_preds(preds, truth, weak_qids)
    capex = score_preds(preds, truth, capex_qids)
    model = score_preds(preds, truth, model_qids)
    weak_by_kind = {}
    for kind in WEAK_KINDS:
        kq = sorted(q for q in all_qids if truth[q]["kind"] == kind)
        s = score_preds(preds, truth, kq)
        weak_by_kind[kind] = [s["correct"], s["total"]]
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
        "split_A_108": [spa["correct"], len(a_qids)],
        "split_A_108_correct_qids": spa["correct_qids"],
        "split_B_107": [spb["correct"], len(b_qids)],
        "split_B_107_correct_qids": spb["correct_qids"],
        "weak_45": [weak["correct"], len(weak_qids)],
        "weak_45_correct_qids": weak["correct_qids"],
        "weak_by_kind": weak_by_kind,
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
    """Rescore with excluded qids counted as not correct, denominator
    stays 215 (same convention as the round-11 audits)."""
    kept = [q for q in sorted(all_qids) if q not in set(exclude_qids)]
    total = score_preds(preds, truth, kept)
    old_qids = sorted(q for q in kept if q <= 98)
    new_qids = sorted(q for q in kept if q >= 99)
    a_qids = sorted(q for q in kept if truth[q]["split"] == "A")
    b_qids = sorted(q for q in kept if truth[q]["split"] == "B")
    weak_qids = sorted(q for q in kept if truth[q]["kind"] in WEAK_KINDS)
    capex_qids = sorted(q for q in kept if truth[q]["kind"] == "capex")
    model_qids = sorted(q for q in kept if truth[q]["kind"] in MODEL_KINDS)
    old = score_preds(preds, truth, old_qids)
    new = score_preds(preds, truth, new_qids)
    spa = score_preds(preds, truth, a_qids)
    spb = score_preds(preds, truth, b_qids)
    weak = score_preds(preds, truth, weak_qids)
    capex = score_preds(preds, truth, capex_qids)
    model = score_preds(preds, truth, model_qids)
    weak_by_kind = {}
    for kind in WEAK_KINDS:
        kq = sorted(q for q in kept if truth[q]["kind"] == kind)
        s = score_preds(preds, truth, kq)
        weak_by_kind[kind] = [s["correct"], s["total"]]
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
        "split_A_108": [spa["correct"], 108],
        "split_A_108_correct_qids": spa["correct_qids"],
        "split_B_107": [spb["correct"], 107],
        "split_B_107_correct_qids": spb["correct_qids"],
        "weak_45": [weak["correct"], 45],
        "weak_45_correct_qids": weak["correct_qids"],
        "weak_by_kind": weak_by_kind,
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


def score_subset(preds, truth, qids):
    """Score on a subset only (leaked-subset report). Denominator is
    the subset size. Used for the leaked-question subset report."""
    return score_preds(preds, truth, sorted(qids))


def mean(xs):
    return sum(xs) / len(xs)


def weakest_kind(by_kind_mean, by_kind_total):
    """Kind(s) with the lowest correct rate. Returns (kinds, rate)."""
    rates = {k: (by_kind_mean[k] / by_kind_total[k]) for k in by_kind_total}
    low = min(rates.values())
    return sorted(k for k, r in rates.items() if r == low), low


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
    per_kind_mean = {k: mean([batches_scores[b]["by_kind"][k][0] for b in batches])
                     for k in kinds}
    per_kind_total = {k: batches_scores[batches[0]]["by_kind"][k][1] for k in kinds}
    wk, wk_rate = weakest_kind(per_kind_mean, per_kind_total)
    wk_weak_mean = {k: mean([batches_scores[b]["weak_by_kind"][k][0] for b in batches])
                    for k in WEAK_KINDS}
    wk_weak_total = {k: batches_scores[batches[0]]["weak_by_kind"][k][1] for k in WEAK_KINDS}
    wk_w, wk_w_rate = weakest_kind(wk_weak_mean, wk_weak_total)
    return {
        "totals": tot, "mean": mean(tot), "spread": max(tot) - min(tot),
        "per_kind_mean_correct": per_kind_mean,
        "per_kind_total": per_kind_total,
        "per_player_mean_correct": {
            p: mean([batches_scores[b]["by_player"][p][0] for b in batches]) for p in players},
        "per_player_total": {p: batches_scores[batches[0]]["by_player"][p][1] for p in players},
        "old_98_mean": mean([batches_scores[b]["old_98"][0] for b in batches]),
        "new_117_mean": mean([batches_scores[b]["new_117"][0] for b in batches]),
        "split_A_108_mean": mean([batches_scores[b]["split_A_108"][0] for b in batches]),
        "split_B_107_mean": mean([batches_scores[b]["split_B_107"][0] for b in batches]),
        "weak_45_mean": mean([batches_scores[b]["weak_45"][0] for b in batches]),
        "weak_by_kind_mean": {
            k: mean([batches_scores[b]["weak_by_kind"][k][0] for b in batches])
            for k in WEAK_KINDS},
        "weak_by_kind_total": {k: batches_scores[batches[0]]["weak_by_kind"][k][1]
                               for k in WEAK_KINDS},
        "weakest_kind": wk, "weakest_kind_rate": wk_rate,
        "weakest_weak_kind": wk_w, "weakest_weak_kind_rate": wk_w_rate,
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
    """Group summary for an exclusion rescore. Denominators stay 215 /
    108 / 107 / 45: an excluded record counts as not correct."""
    tot = [aud[b]["total_215"][0] for b in batches]
    kinds = sorted({q["kind"] for q in truth.values()})
    players = sorted({q["player"] for q in truth.values()})
    conf_pool = {}
    for level in ("high", "medium", "low"):
        c = sum(aud[b]["confidence"][level]["correct_total"][0] for b in batches)
        n = sum(aud[b]["confidence"][level]["correct_total"][1] for b in batches)
        conf_pool[level] = {"correct_total": [c, n],
                            "accuracy": (c / n) if n else None}
    per_kind_mean = {k: mean([aud[b]["by_kind"].get(k, [0, 0])[0] for b in batches])
                     for k in kinds}
    per_kind_total = {k: raw_ref[batches[0]]["by_kind"][k][1] for k in kinds}
    wk, wk_rate = weakest_kind(per_kind_mean, per_kind_total)
    wk_weak_mean = {k: mean([aud[b]["weak_by_kind"][k][0] for b in batches])
                    for k in WEAK_KINDS}
    wk_weak_total = {k: raw_ref[batches[0]]["weak_by_kind"][k][1] for k in WEAK_KINDS}
    wk_w, wk_w_rate = weakest_kind(wk_weak_mean, wk_weak_total)
    return {
        "totals": tot, "mean": mean(tot), "spread": max(tot) - min(tot),
        "old_98_mean": mean([aud[b]["old_98"][0] for b in batches]),
        "new_117_mean": mean([aud[b]["new_117"][0] for b in batches]),
        "split_A_108_mean": mean([aud[b]["split_A_108"][0] for b in batches]),
        "split_B_107_mean": mean([aud[b]["split_B_107"][0] for b in batches]),
        "weak_45_mean": mean([aud[b]["weak_45"][0] for b in batches]),
        "weak_by_kind_mean": {
            k: mean([aud[b]["weak_by_kind"][k][0] for b in batches])
            for k in WEAK_KINDS},
        "weak_by_kind_total": {k: raw_ref[batches[0]]["weak_by_kind"][k][1]
                               for k in WEAK_KINDS},
        "weakest_kind": wk, "weakest_kind_rate": wk_rate,
        "weakest_weak_kind": wk_w, "weakest_weak_kind_rate": wk_w_rate,
        "capex_10_mean": mean([aud[b]["capex_10"][0] for b in batches]),
        "model_release_66_mean": mean([aud[b]["model_release_66"][0] for b in batches]),
        "per_kind_mean_correct": per_kind_mean,
        "per_kind_total": per_kind_total,
        "per_player_mean_correct": {
            p: mean([aud[b]["by_player"].get(p, [0, 0])[0] for b in batches]) for p in players},
        "confidence_pooled": conf_pool,
    }


def reproduce_gates():
    """Gates 0-2. Any failure exits non-zero."""
    truth10 = load_truth(os.path.join(R10_BASE, "testset-v6.json"))
    got10 = {}
    for batch in ["C1", "C2", "C3", "E1", "E2"]:
        preds = load_batch(R10_PRED_DIR, batch)
        assert set(preds) == R10_FOCUS, f"round-10 gate: batch {batch} set != FOCUS32"
        got10[batch] = len([q for q in sorted(R10_FOCUS)
                            if is_correct(preds, truth10, q)])
    ok10 = got10 == R10_TOTAL_EXPECTED
    print("gate 0 round-10 focus (32q, testset-v6):",
          {b: f"{got10[b]}/32 (exp {R10_TOTAL_EXPECTED[b]})" for b in got10},
          "PASS" if ok10 else "FAIL")

    truth7 = load_truth(os.path.join(BASE, "testset-v7.json"))
    all_qids = sorted(truth7)
    audit = json.load(open(R11_BASELINE_AUDIT))
    excl = audit["leakage_exclusion"]["by_batch"]
    got7 = {}
    for batch in ["C1", "C2", "C3"]:
        preds = load_batch(R11_BASELINE_DIR, batch)
        got7[batch] = score_batch_excluding(
            preds, truth7, batch, all_qids, excl[batch])["total_215"][0]
    ok7 = got7 == V7_BASELINE_AUDITED_EXPECTED
    print("gate 1 v7 baseline retest audited (215q):",
          {b: f"{got7[b]}/215 (exp {V7_BASELINE_AUDITED_EXPECTED[b]})" for b in got7},
          "PASS" if ok7 else "FAIL")

    audit_ctrl = json.load(open(R11_CONTROL_AUDIT))
    excl_ctrl = {"D1": [], "D2": [], "D3": []}
    for rec in audit_ctrl["exclusions"]["exclude"]:
        excl_ctrl[rec["batch"]].append(rec["q_id"])
    got11 = {}
    for batch in ["D1", "D2", "D3"]:
        preds = load_batch(R11_CONTROL_DIR, batch)
        got11[batch] = score_batch_excluding(
            preds, truth7, batch, all_qids, excl_ctrl[batch])["total_215"][0]
    ok11 = got11 == V7_R11_CONTROL_AUDITED_EXPECTED
    print("gate 2 round-11 control audited (215q):",
          {b: f"{got11[b]}/215 (exp {V7_R11_CONTROL_AUDITED_EXPECTED[b]})" for b in got11},
          "PASS" if ok11 else "FAIL")
    m_base = mean(list(got7.values()))
    m_ctrl = mean(list(got11.values()))
    gain = round(m_base - m_ctrl, 2)
    ok_gain = abs(gain - R11_GAIN_BOTH_AUDITED_EXPECTED) < 0.01
    print(f"gate 2 gain both-audited: {m_base:.2f} - {m_ctrl:.2f} = {gain:.2f} "
          f"(exp {R11_GAIN_BOTH_AUDITED_EXPECTED}) "
          f"{'PASS' if ok_gain else 'FAIL'}")
    ok = ok10 and ok7 and ok11 and ok_gain
    if not ok:
        print("REPRODUCTION GATE FAILED: fix score_round12.py before scoring.")
        sys.exit(1)
    return {"gate_0_round10_focus": {"got": got10,
                                     "expected": R10_TOTAL_EXPECTED,
                                     "status": "PASS"},
            "gate_1_v7_baseline_retest_audited": {
                "got": got7, "expected": V7_BASELINE_AUDITED_EXPECTED,
                "mean": m_base, "status": "PASS"},
            "gate_2_round11_control_audited": {
                "got": got11, "expected": V7_R11_CONTROL_AUDITED_EXPECTED,
                "mean": m_ctrl, "status": "PASS"},
            "gate_2_gain_both_audited": {
                "got": gain, "expected": R11_GAIN_BOTH_AUDITED_EXPECTED,
                "status": "PASS"}}


def evaluate_decision_rules(G, G_new, S_TC, S_TE, contrib, wk_rate_exp,
                            wk_rate_ctrl, G_leak_only):
    """Protocol section 6.1, six conditions, on leakage-excluded scores.

    contrib: {q_id: net contribution (e_frac - c_frac)} on excluded
      scores. wk_rate_exp / wk_rate_ctrl: weakest-kind rates.
    G_leak_only: gain measured on the leaked subset alone.
    """
    noise_band = max(S_TC, S_TE)
    threshold = max(11, noise_band)
    pos_qs = sorted(q for q, c in contrib.items() if c > 0)
    max_c = max(contrib.values()) if contrib else 0.0
    a = G > threshold
    # (2) is filled in by the caller from the per-pair McNemar p values.
    c3 = G >= 3
    d = (len(pos_qs) >= 2) and (max_c < G / 2)  # coordinator 2026-11-25: literal reading; the old "G <= 0" short-circuit made (4) pass vacuously when there is no gain at all
    e = wk_rate_exp >= wk_rate_ctrl
    f = G > 0  # excluded gain survives: (1)-(5) are already on excluded scores
    return {
        "(1) G > max(11, round noise band)": {
            "value": f"G={G:.2f} vs threshold max(11, max({S_TC},{S_TE}))={threshold}",
            "pass": bool(a)},
        "(3) G >= 3": {"value": f"G={G:.2f}", "pass": bool(c3)},
        "(4) gain from >=2 questions, no single question > half of gain": {
            "value": (f"positive-contribution questions={len(pos_qs)} {pos_qs[:20]}"
                      f"{'...' if len(pos_qs) > 20 else ''}; max single contribution={max_c:.2f}"
                      f"; G/2={G / 2:.2f}"),
            "pass": bool(d)},
        "(5) weakest kind does not fall": {
            "value": f"exp weakest rate={wk_rate_exp:.3f} vs control weakest rate={wk_rate_ctrl:.3f}",
            "pass": bool(e)},
        "(6) gain not on leaked questions (excluded gain survives)": {
            "value": f"excluded G={G:.2f}; leaked-subset-only gain={G_leak_only:.2f}",
            "pass": bool(f)},
        "noise_band": noise_band, "threshold": threshold,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
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
        repro_path = os.path.join(run_root, "reproduce-round12.json")
        os.makedirs(args.pred_dir, exist_ok=True)
        with open(repro_path, "w") as fh:
            json.dump(gates, fh, indent=2, ensure_ascii=False)
        print(f"wrote {repro_path}")
    if args.reproduce_only:
        return

    result = {"reproduction_gates": gates}
    leak_note = {
        "protocol_sections_3_2_and_6_1_count": 39,
        "protocol_section_11_3_list_count": len(LEAK_42),
        "list_used": "section 11.3 (42 questions)",
        "list": sorted(LEAK_42),
        "mismatch": "Sections 3.2/6.1 say 39 leaked questions, section 11.3 "
                    "lists 42, and no 39-question list exists in the repo. "
                    "The 39-question version cannot be computed. Which list "
                    "governs the adoption decision is for the coordinator "
                    "to decide; this script does not decide it.",
        "leak_in_split_B": len([q for q in LEAK_42 if truth[q]["split"] == "B"]),
        "leak_in_split_A": len([q for q in LEAK_42 if truth[q]["split"] == "A"]),
    }
    result["leakage_exclusion_note"] = leak_note

    # --- control batches C1-C3 (raw) ---
    control = {}
    control_preds = {}
    found_ctrl = []
    for batch in CONTROL_BATCHES:
        preds = load_batch(args.pred_dir, batch)
        if not preds:
            print(f"{batch}: no prediction files yet")
            continue
        found_ctrl.append(batch)
        control_preds[batch] = preds
        control[batch] = score_batch(preds, truth, batch, all_qids)
        r = control[batch]
        print(f"{batch}: total {r['total_215'][0]}/215 old {r['old_98'][0]}/98 "
              f"new {r['new_117'][0]}/117 A {r['split_A_108'][0]}/108 "
              f"B {r['split_B_107'][0]}/107 weak {r['weak_45'][0]}/45 "
              f"capex {r['capex_10'][0]}/10 model {r['model_release_66'][0]}/66")
    result["control"] = control
    if found_ctrl:
        result["control_group"] = group_summary(control, found_ctrl)

    # --- experiment batches E1-E3 (raw) ---
    exp_raw = {}
    exp_preds = {}
    found_exp = []
    for batch in EXP_BATCHES:
        preds = load_batch(args.pred_dir, batch)
        if not preds:
            print(f"{batch}: no prediction files yet")
            continue
        found_exp.append(batch)
        exp_preds[batch] = preds
        exp_raw[batch] = score_batch(preds, truth, batch, all_qids)
        r = exp_raw[batch]
        print(f"{batch}: total {r['total_215'][0]}/215 old {r['old_98'][0]}/98 "
              f"new {r['new_117'][0]}/117 A {r['split_A_108'][0]}/108 "
              f"B {r['split_B_107'][0]}/107 weak {r['weak_45'][0]}/45 "
              f"capex {r['capex_10'][0]}/10 model {r['model_release_66'][0]}/66")
    result["experiment_raw"] = exp_raw
    if found_exp:
        result["experiment_raw_group"] = group_summary(exp_raw, found_exp)

    if len(found_ctrl) != 3 or len(found_exp) != 3:
        print(f"incomplete: control {found_ctrl}, experiment {found_exp}. "
              "Group comparisons, gains, paired tables and decision rules "
              "need all 6 batches; wrote partial scores only.")
        out_path = args.out or os.path.join(
            os.path.dirname(os.path.normpath(args.pred_dir)), "score-round12.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
        print(f"wrote {out_path}")
        return

    # --- leakage-excluded rescore (42-list, adoption computation) ---
    ctrl_aud = {}
    for batch in CONTROL_BATCHES:
        ctrl_aud[batch] = score_batch_excluding(
            control_preds[batch], truth, batch, all_qids, LEAK_42)
    result["control_excluded42"] = ctrl_aud
    result["control_excluded42_group"] = audited_group_summary(
        ctrl_aud, CONTROL_BATCHES, control, truth)
    exp_aud = {}
    for batch in EXP_BATCHES:
        exp_aud[batch] = score_batch_excluding(
            exp_preds[batch], truth, batch, all_qids, LEAK_42)
    result["experiment_excluded42"] = exp_aud
    result["experiment_excluded42_group"] = audited_group_summary(
        exp_aud, EXP_BATCHES, exp_raw, truth)

    # --- leaked-subset scores (reported separately, never in the verdict) ---
    leak_sub = {"control": {}, "experiment": {}}
    for batch in CONTROL_BATCHES:
        s = score_subset(control_preds[batch], truth, LEAK_42)
        leak_sub["control"][batch] = {"correct": s["correct"], "total": len(LEAK_42),
                                      "correct_qids": s["correct_qids"]}
    for batch in EXP_BATCHES:
        s = score_subset(exp_preds[batch], truth, LEAK_42)
        leak_sub["experiment"][batch] = {"correct": s["correct"], "total": len(LEAK_42),
                                         "correct_qids": s["correct_qids"]}
    leak_sub["control_mean"] = mean([leak_sub["control"][b]["correct"] for b in CONTROL_BATCHES])
    leak_sub["experiment_mean"] = mean([leak_sub["experiment"][b]["correct"] for b in EXP_BATCHES])
    leak_sub["gain_on_leaked_only"] = leak_sub["experiment_mean"] - leak_sub["control_mean"]
    result["leaked_subset_scores"] = leak_sub

    cg = result["control_group"]
    cg_aud = result["control_excluded42_group"]
    eg_raw = result["experiment_raw_group"]
    eg_aud = result["experiment_excluded42_group"]
    M_TC = cg["mean"]; S_TC = cg["spread"]
    M_TC_aud = cg_aud["mean"]; S_TC_aud = cg_aud["spread"]
    M_TE_raw = eg_raw["mean"]; S_TE_raw = eg_raw["spread"]
    M_TE_aud = eg_aud["mean"]; S_TE_aud = eg_aud["spread"]

    gains = {
        "G_raw": M_TE_raw - M_TC,
        "M_TE_raw": M_TE_raw, "M_TC": M_TC,
        "G_excluded42": M_TE_aud - M_TC_aud,
        "M_TE_excluded42": M_TE_aud, "M_TC_excluded42": M_TC_aud,
        "G_new_raw": eg_raw["new_117_mean"] - cg["new_117_mean"],
        "G_new_excluded42": eg_aud["new_117_mean"] - cg_aud["new_117_mean"],
        "G_old_raw": eg_raw["old_98_mean"] - cg["old_98_mean"],
        "G_old_excluded42": eg_aud["old_98_mean"] - cg_aud["old_98_mean"],
        "G_A_raw": eg_raw["split_A_108_mean"] - cg["split_A_108_mean"],
        "G_A_excluded42": eg_aud["split_A_108_mean"] - cg_aud["split_A_108_mean"],
        "G_B_raw": eg_raw["split_B_107_mean"] - cg["split_B_107_mean"],
        "G_B_excluded42": eg_aud["split_B_107_mean"] - cg_aud["split_B_107_mean"],
        "G_weak_raw": eg_raw["weak_45_mean"] - cg["weak_45_mean"],
        "G_weak_excluded42": eg_aud["weak_45_mean"] - cg_aud["weak_45_mean"],
        "G_leaked_only": leak_sub["gain_on_leaked_only"],
        "S_TC": S_TC, "S_TE_raw": S_TE_raw, "S_TE_excluded42": S_TE_aud,
        "M_TC_excluded42_old": cg_aud["old_98_mean"],
        "M_TC_excluded42_new": cg_aud["new_117_mean"],
        "weak_by_kind_gain_excluded42": {
            k: eg_aud["weak_by_kind_mean"][k] - cg_aud["weak_by_kind_mean"][k]
            for k in WEAK_KINDS},
        "weak_by_kind_gain_raw": {
            k: eg_raw["weak_by_kind_mean"][k] - cg["weak_by_kind_mean"][k]
            for k in WEAK_KINDS},
    }
    result["gains"] = gains

    # --- paired results per question (batch pairs C_i vs E_i) ---
    paired_raw_pairs = []
    paired_aud_pairs = []
    per_question = []
    for i, (cb, eb) in enumerate(zip(CONTROL_BATCHES, EXP_BATCHES)):
        cp, ep = control_preds[cb], exp_preds[eb]
        both = e_only = c_only = neither = 0
        both_a = e_only_a = c_only_a = neither_a = 0
        for q in all_qids:
            cc = is_correct(cp, truth, q)
            ec = is_correct(ep, truth, q)
            ec_a = ec and (q not in set(LEAK_42))
            cc_a = cc and (q not in set(LEAK_42))
            if ec and cc:
                both += 1
            elif ec and not cc:
                e_only += 1
            elif cc and not ec:
                c_only += 1
            else:
                neither += 1
            if ec_a and cc_a:
                both_a += 1
            elif ec_a and not cc_a:
                e_only_a += 1
            elif cc_a and not ec_a:
                c_only_a += 1
            else:
                neither_a += 1
        paired_raw_pairs.append({"pair": f"{cb}-vs-{eb}", "both": both,
                                 "exp_only": e_only, "control_only": c_only,
                                 "neither": neither,
                                 "mcnemar_exact_two_sided_p":
                                     mcnemar_exact_two_sided(e_only, c_only)})
        paired_aud_pairs.append({"pair": f"{cb}-vs-{eb}", "both": both_a,
                                 "exp_only": e_only_a, "control_only": c_only_a,
                                 "neither": neither_a,
                                 "mcnemar_exact_two_sided_p":
                                     mcnemar_exact_two_sided(e_only_a, c_only_a)})
    def avg_pairs(pairs):
        return {k: mean([p[k] for p in pairs]) for k in ("both", "exp_only", "control_only", "neither")}
    for q in all_qids:
        e_n = sum(1 for b in EXP_BATCHES if is_correct(exp_preds[b], truth, q))
        e_n_a = sum(1 for b in EXP_BATCHES
                    if is_correct(exp_preds[b], truth, q) and q not in set(LEAK_42))
        c_n = sum(1 for b in CONTROL_BATCHES if is_correct(control_preds[b], truth, q))
        c_n_a = sum(1 for b in CONTROL_BATCHES
                    if is_correct(control_preds[b], truth, q) and q not in set(LEAK_42))
        per_question.append({
            "q_id": q, "kind": truth[q]["kind"], "player": truth[q]["player"],
            "event_name": truth[q]["event_name"], "new_question": q >= 99,
            "new_kind": truth[q]["kind"] in NEW_KINDS,
            "weak_kind": truth[q]["kind"] in WEAK_KINDS,
            "leaked_q": q in set(LEAK_42),
            "split": truth[q]["split"],
            "exp_correct_batches": e_n, "exp_correct_batches_excluded42": e_n_a,
            "control_correct_batches": c_n,
            "control_correct_batches_excluded42": c_n_a,
            "net_contrib_raw": e_n / 3 - c_n / 3,
            "net_contrib_excluded42": e_n_a / 3 - c_n_a / 3,
        })
    result["paired"] = {
        "per_batch_pair_raw": paired_raw_pairs,
        "per_batch_pair_excluded42": paired_aud_pairs,
        "average_raw": avg_pairs(paired_raw_pairs),
        "average_excluded42": avg_pairs(paired_aud_pairs),
        "per_question": per_question,
    }
    mcnemar_p = [p["mcnemar_exact_two_sided_p"] for p in paired_aud_pairs]
    result["mcnemar"] = {
        "method": "exact two-sided binomial test on discordant pairs, "
                  "per batch pair C_i vs E_i, on leakage-excluded scores",
        "per_pair_excluded42": {p["pair"]: p["mcnemar_exact_two_sided_p"]
                                for p in paired_aud_pairs},
        "per_pair_raw": {p["pair"]: p["mcnemar_exact_two_sided_p"]
                         for p in paired_raw_pairs},
        "all_pairs_significant_0.05": all(p < 0.05 for p in mcnemar_p),
    }

    # --- decision rules (protocol section 6.1, excluded scores) ---
    contrib_excl = {p["q_id"]: p["net_contrib_excluded42"] for p in per_question}
    G = gains["G_excluded42"]
    G_new = gains["G_new_excluded42"]
    rules = evaluate_decision_rules(
        G, G_new, S_TC_aud, S_TE_aud, contrib_excl,
        eg_aud["weakest_kind_rate"], cg_aud["weakest_kind_rate"],
        leak_sub["gain_on_leaked_only"])
    rules["(2) McNemar two-sided p < 0.05 for every batch pair"] = {
        "value": ("per-pair p (excluded42): "
                  + ", ".join(f"{p['pair']}={p['mcnemar_exact_two_sided_p']:.4f}"
                              for p in paired_aud_pairs)),
        "pass": bool(result["mcnemar"]["all_pairs_significant_0.05"])}
    # Gain on the new kinds (protocol section 6.2 discard condition:
    # the method harms the new kinds). New-kind total gain, excluded42.
    new_kind_gain_excl = sum(
        eg_aud["per_kind_mean_correct"][k] - cg_aud["per_kind_mean_correct"][k]
        for k in NEW_KINDS)
    gains["G_newkinds_excluded42"] = new_kind_gain_excl
    result["gains"] = gains
    conds = [rules[k]["pass"] for k in rules if isinstance(rules[k], dict) and "pass" in rules[k]]
    adopt = all(conds)
    # Discard (protocol section 6.2): gain 0 or negative, or new-kind
    # gain 0 or negative, or the gain was only on leaked questions
    # (raw gain > 0 but excluded gain <= 0), or the method harms the
    # new kinds (new-kind gain < 0).
    remove = (G <= 0) or (G_new <= 0) or (gains["G_raw"] > 0 and G <= 0) \
        or (new_kind_gain_excl < 0)
    if adopt:
        verdict = "ADOPT (weak-repair method verified into baseline)"
    elif remove:
        verdict = "REMOVE (weak-repair method out of baseline)"
    else:
        verdict = "MIXED (helpful but below adoption threshold; stays tentative)"
    rules["adopt_all_six"] = bool(adopt)
    rules["remove_any"] = bool(remove)
    rules["verdict"] = verdict
    result["decision_rules"] = rules

    # --- H-W (direction-2 hypothesis, protocol sections 4.2/4.3) ---
    # "Weakest kind" here means the weakest among the six weak kinds
    # ("在弱项种类上把最弱一项的命中率提到 50% 以上"), not the
    # weakest among all 43 kinds. That is weakest_weak_kind_rate.
    exp_weakest_rate = eg_aud["weakest_weak_kind_rate"]
    hw = {
        "weakest_weak_kind_exp": eg_aud["weakest_weak_kind"],
        "weakest_weak_kind_rate_exp": exp_weakest_rate,
        "weakest_weak_kind_ctrl": cg_aud["weakest_weak_kind"],
        "weakest_weak_kind_rate_ctrl": cg_aud["weakest_weak_kind_rate"],
        "weak_kind_rate_ge_50pct": bool(exp_weakest_rate >= 0.5),
        "total_not_falling": bool(M_TE_aud >= M_TC_aud),
        "weak_total_gain_gt_0": bool(gains["G_weak_excluded42"] > 0),
        "falsified": bool(exp_weakest_rate < 0.5 or M_TE_aud < M_TC_aud
                          or gains["G_weak_excluded42"] <= 0),
    }
    hw["hypothesis_H_W"] = ("SUPPORTED" if not hw["falsified"] else "FALSIFIED")
    result["hypothesis_H_W"] = hw

    # --- per-kind comparison table ---
    kinds = sorted({q["kind"] for q in truth.values()})
    kind_table = {}
    for k in kinds:
        kind_table[k] = {
            "total": cg["per_kind_total"][k],
            "control_mean": cg["per_kind_mean_correct"][k],
            "control_by_batch": [control[b]["by_kind"][k][0] for b in CONTROL_BATCHES],
            "control_mean_excluded42": cg_aud["per_kind_mean_correct"][k],
            "exp_mean_raw": eg_raw["per_kind_mean_correct"][k],
            "exp_by_batch_raw": [exp_raw[b]["by_kind"][k][0] for b in EXP_BATCHES],
            "exp_mean_excluded42": eg_aud["per_kind_mean_correct"][k],
            "gain_mean_excluded42": eg_aud["per_kind_mean_correct"][k] - cg_aud["per_kind_mean_correct"][k],
            "gain_mean_raw": eg_raw["per_kind_mean_correct"][k] - cg["per_kind_mean_correct"][k],
            "weak_kind": k in WEAK_KINDS,
            "new_kind": k in NEW_KINDS,
        }
    result["kind_comparison"] = kind_table

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.normpath(args.pred_dir)), "score-round12.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")
    print(f"control: {[control[b]['total_215'][0] for b in CONTROL_BATCHES]} "
          f"M_TC={M_TC:.2f} S_TC={S_TC} A_mean={cg['split_A_108_mean']:.2f} "
          f"B_mean={cg['split_B_107_mean']:.2f} weak_mean={cg['weak_45_mean']:.2f}")
    print(f"experiment raw: {[exp_raw[b]['total_215'][0] for b in EXP_BATCHES]} "
          f"M_TE_raw={M_TE_raw:.2f} S_TE_raw={S_TE_raw}")
    print(f"control excluded42: {cg_aud['totals']} M={M_TC_aud:.2f} S={S_TC_aud}")
    print(f"experiment excluded42: {eg_aud['totals']} M={M_TE_aud:.2f} S={S_TE_aud}")
    print(f"G_raw={gains['G_raw']:.2f} G_excluded42={G:.2f} "
          f"G_new_excluded42={G_new:.2f} G_weak_excluded42={gains['G_weak_excluded42']:.2f} "
          f"G_B_excluded42={gains['G_B_excluded42']:.2f} "
          f"G_leaked_only={leak_sub['gain_on_leaked_only']:.2f}")
    print("McNemar per-pair p (excluded42):",
          {p["pair"]: round(p["mcnemar_exact_two_sided_p"], 4) for p in paired_aud_pairs})
    print("decision (section 6.1, excluded42):", verdict)
    print("H-W:", hw["hypothesis_H_W"])


if __name__ == "__main__":
    main()
