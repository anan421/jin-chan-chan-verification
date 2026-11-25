#!/usr/bin/env python3
"""Score round 14 (second weak-kind repair).

Control C1-C3: 4 shared method files (search boundary tightened +
forward-guidance steps + datacenter/capex boundary + roleplay).
Experiment E1-E3: the same 4 files + method-weak-repair-round14.md
(the only variable). Both groups get the same question files
(31 files, 215 questions, no forward_guidance; 14 questions carry
a numeric_history field as common background input, design 3.4).
Same 215 questions (testset-v7). A guess is correct iff guessed kind
== testset kind for that q_id. Scoring uses only the kind field.
Generic-kind guesses are counted per batch ("generic" is in the
vocabulary but is the correct kind of 0 of the 215 questions).

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
leakage-excluded scores) plus H-14 H4 as a seventh adoption gate:
  (1) G > max(11, round noise band). Round noise band =
      max(control spread, experiment spread) on excluded scores.
      G equal to the band does not pass.
  (2) McNemar two-sided p < 0.05 for every batch pair C_i vs E_i.
  (3) G >= 3.
  (4) Gain from >= 2 questions; no single question > half of G.
  (5) Weakest kind does not fall: experiment weakest-kind rate >=
      control weakest-kind rate (excluded scores). Weakest kind here
      means the weakest among the six weak kinds (round-12
      definition), NOT the weakest among all 43 kinds. The all-43
      weakest kind is reported separately and is not the decision
      input.
  (6) Gain is not on leaked questions: the excluded gain still
      satisfies (1)-(5). This is exactly what "excluded gain still
      satisfies conditions one to five" means, so (6) passes iff
      the excluded gain G > 0 and (1)-(5) pass on excluded scores.
  (H4) Side-effect gate: experiment claude mean >= control claude
      mean - 2. A larger claude drop blocks adoption even if the
      six conditions pass (design section 6.3 / 11).
  All six pass plus H4: ADOPT. G <= 0, or G_new <= 0, or gain only
  from leaked questions, or the method harms the new kinds: REMOVE.
  Otherwise: MIXED (helpful but below threshold; stays tentative).
  H4 fails on its own: NOT ADOPTED (coordinator decides tentative
  vs remove; design section 11).

H-14 (weak-repair hypothesis, written before the run; design
section 9). Four checks, all against THIS round's control group
(the input changed: both groups carry numeric_history, so the
62.00 clean baseline is reported alongside, not used as the
comparator):
  H1: experiment mean (excluded42) - control mean (excluded42)
      > max(11, this round's noise band).
  H2: experiment weak-45 mean - control weak-45 mean >= 3.
  H3: forced-step execution rates reach section 5.3 thresholds
      (total >= 90%, N-step >= 90%, T-check-row >= 90%).
  H4: experiment claude mean >= control claude mean - 2.
  Any check fails, H-14 is falsified. F3 (execution below
  threshold) means "method not executed", not "method invalid";
  the adoption decision pauses.
  WEAK_KINDS (weakest kinds, round-12 definition): acquisition (9),
  arr (13), partnership (6), math (5), wallstreet (4), social (8).
  45 questions. "Weakest kind" in decision rule (5) and in H-14
  means the weakest among these six kinds, as in round 12. The
  weakest among all 43 kinds is also reported (weakest_kind).
  Capex (10 questions, q10-q19) is reported on RAW scores only, as
  description: all 10 are in LEAK_42, so the excluded capex mean
  is 0 by construction.
  Weak-gain decomposition (design 3.5, written before the run):
  input gain = this control weak mean - 1.00 (round-13 control weak
  mean); program gain = experiment weak mean - this control weak
  mean. Input gain large + program gain small means the input
  repaired the revenue questions, not the method.

FORCED-STEP EXECUTION (design 5.2/5.3, from the rule-O five lines
in each prediction record: problem_type, weak_rule, weak_evidence,
kind + probability, confidence):
  total execution: record has all five lines present and non-empty
    (probability a number in [0, 1], confidence high/medium/low).
    Denominator 135 (45 weak questions x 3 experiment batches).
  T-check-row presence: weak_evidence contains a trigger check:
    the characters for "trigger" plus either a date or the phrase
    for "no trigger event in 30 days". Denominator 135.
  N-step execution: on the 14 numeric_history questions only,
    weak_evidence lists >= 2 dated values plus a trend word
    (up/down/flat/rise/fall/grow/trend/accelerate/decelerate).
    Denominator 42 (14 x 3 experiment batches).
  Empty lines, placeholders, and copied method-file text do not
  count as execution; the checks above require real content.
  Rule-L trigger count: records whose weak_evidence names a dated
  legal-process milestone. Guard: more than 3 such records in the
  experiment group (q186 has 3) is flagged with question numbers.
  "Follow the latest action line" template count: experiment-group
  records on the 16 claude questions whose reason contains that
  phrase; their correct rate and guessed-kind distribution are
  reported (design 6.2).
  Sentinels: q145 (round-13 experiment 0/3, control 3/3), q195
  (round-13 both groups 6/6; experiment below 2/3 means the method
  broke a guessed question), q186 (legal-process channel alone).

TRAP KINDS (design 10.6): kinds in the 48-kind vocabulary but not
  among the 43 testset kinds: open_source, ascend, compliance,
  generic, openai_mar26. Every trap guess counts as wrong. Trap
  counts are reported per batch for both groups (round-13 total
  was 174: open_source 130, ascend 24, compliance 12, generic 7,
  openai_mar26 1). Trap counts do not enter the adoption decision.

REPRODUCTION GATES (run first; any failure exits non-zero, no scores):
  gate 0 (round-10 focus, testset-v6): C1 31, C2 31, C3 31, E1 32,
    E2 32 /32. Same core logic as score_v11.py.
  gate 1 (v7 baseline retest, audited): C1 96, C2 104, C3 93 /215,
    mean 97.67. Exclusions from the round-11 audit file
    (audit-baseline-v7.json leakage_exclusion.by_batch).
  gate 2 (round-11 control, audited): D1 90, D2 94, D3 93 /215,
    mean 92.33; both-audited gain +5.33 (97.67 - 92.33).
    Exclusions from audit-v11.json exclusions.exclude.
  gate 3 (round-12 control, raw): C1 63, C2 59, C3 64 /215,
    mean 62.00 (the clean baseline under cleaned method files).
  gate 4 (round-13 control): raw C1 73, C2 70, C3 66 /215,
    mean 69.67; excluded42 C1 62, C2 61, C3 61 /215, mean 61.33.
  Gate results are written to reproduce-round14.json next to the
  predictions and into score-round14.json under
  "reproduction_gates". Gate 1's 97.67 only reproduces arithmetic
  (it was measured under leaked method files and is NOT the clean
  baseline); the clean baseline is 62.00 from gate 3.

Usage:
  python3 score_round14.py [--pred-dir DIR] [--out FILE]
  python3 score_round14.py --reproduce-only   (gates only, no scoring)
"""
import argparse
import glob
import re
import json
import math
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, "runs", "round14-weak-repair-2-2026-11-25")
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
R12_BASE = os.path.join(os.path.expanduser("~"), "workspace",
                        "verification-v1-round12")
R12_CONTROL_DIR = os.path.join(R12_BASE, "runs",
                               "round12-weak-repair-2026-11-25", "predictions")
R13_BASE = os.path.join(os.path.expanduser("~"), "workspace",
                        "verification-v1-round13")
R13_CONTROL_DIR = os.path.join(R13_BASE, "runs",
                               "round13-a1b2-2026-11-25", "predictions")
R10_PRED_DIR = os.path.join(R10_BASE, "runs", "round10-vision10-2026-11-22",
                            "predictions")

R10_FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
             36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
R10_TOTAL_EXPECTED = {"C1": 31, "C2": 31, "C3": 31, "E1": 32, "E2": 32}
V7_BASELINE_AUDITED_EXPECTED = {"C1": 96, "C2": 104, "C3": 93}
V7_R11_CONTROL_AUDITED_EXPECTED = {"D1": 90, "D2": 94, "D3": 93}
R11_GAIN_BOTH_AUDITED_EXPECTED = 5.33
R12_CONTROL_EXPECTED = {"C1": 63, "C2": 59, "C3": 64}
R13_CONTROL_RAW_EXPECTED = {"C1": 73, "C2": 70, "C3": 66}
R13_CONTROL_EXCL_EXPECTED = {"C1": 62, "C2": 61, "C3": 61}

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
# Questions carrying a numeric_history field (design 3.4): arr q121-q133
# plus wallstreet q213.
NUMERIC_QIDS = list(range(121, 134)) + [213]
# Kinds in the 48-kind vocabulary but not among the 43 testset kinds.
TRAP_KINDS = ["open_source", "ascend", "compliance", "generic",
              "openai_mar26"]
# Round-13 control weak-45 mean, used only for the design-3.5
# input-gain decomposition (not a comparator for H-14).
R13_CONTROL_WEAK_MEAN = 1.00


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


DATE_PATTERNS = (re.compile(r"\d{4}-\d{2}-\d{2}"),
                 re.compile(r"\d{8}"),
                 re.compile(r"\d{4}年\d{1,2}月\d{1,2}日"),
                 re.compile(r"\d{4}年\d{1,2}月"))
TREND_WORDS = ("涨", "跌", "持平", "上升", "下降", "增长", "减少", "趋势",
               "加速", "减速")


def _dates_in(text):
    """Distinct date strings in a text (full dates + YYYYMM months)."""
    found = set()
    rest = text
    for pat in DATE_PATTERNS[:3]:
        for m in pat.findall(rest):
            found.add(m)
        rest = pat.sub(" ", rest)
    for m in re.findall(r"(?<!\d)\d{6}(?!\d)", rest):
        found.add(m)
    return found


def _non_empty_str(v):
    return isinstance(v, str) and bool(v.strip())


def rule_o_complete(pred):
    """All five rule-O lines present and non-empty (design 5.2)."""
    if not _non_empty_str(pred.get("problem_type")):
        return False
    if not _non_empty_str(pred.get("weak_rule")):
        return False
    if not _non_empty_str(pred.get("weak_evidence")):
        return False
    if not _non_empty_str(pred.get("kind")):
        return False
    prob = pred.get("probability")
    if isinstance(prob, bool) or not isinstance(prob, (int, float)):
        return False
    if not 0.0 <= prob <= 1.0:
        return False
    return pred.get("confidence") in ("high", "medium", "low")


def has_trigger_line(pred):
    """weak_evidence carries a trigger check (design 5.2).

    The check line names a trigger event (the characters for
    "trigger" plus a date) or states there was no trigger event
    in 30 days. A legal-process-only line does not count.
    """
    ev = pred.get("weak_evidence")
    if not _non_empty_str(ev):
        return False
    if "触发" not in ev:
        return False
    return bool(_dates_in(ev)) or ("30 天内无触发事件" in ev)


def n_step_executed(pred):
    """N-step execution on a numeric_history question (design 5.2).

    weak_evidence lists >= 2 dated values plus a trend word.
    Placeholders and copied method text have no dates, so they fail.
    """
    ev = pred.get("weak_evidence")
    if not _non_empty_str(ev):
        return False
    if len(_dates_in(ev)) < 2:
        return False
    return any(w in ev for w in TREND_WORDS)


def execution_stats(preds, truth, all_qids):
    """Per-batch forced-step counts on the 45 weak questions."""
    weak_qids = sorted(q for q in all_qids if truth[q]["kind"] in WEAK_KINDS)
    num_qids = sorted(q for q in weak_qids if q in NUMERIC_QIDS)
    total_exec = sum(1 for q in weak_qids if rule_o_complete(preds[q]))
    trig = sum(1 for q in weak_qids if has_trigger_line(preds[q]))
    n_exec = sum(1 for q in num_qids if n_step_executed(preds[q]))
    l_qids = sorted(q for q in all_qids
                    if _non_empty_str(preds[q].get("weak_evidence"))
                    and "里程碑" in preds[q]["weak_evidence"])
    return {
        "weak_total_exec": [total_exec, len(weak_qids)],
        "weak_trigger_present": [trig, len(weak_qids)],
        "numeric_n_exec": [n_exec, len(num_qids)],
        "legal_milestone_records": [len(l_qids), len(all_qids)],
        "legal_milestone_qids": l_qids,
    }


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
    claude_qids = sorted(q for q in all_qids if truth[q]["kind"] == "claude")
    claude = score_preds(preds, truth, claude_qids)
    trap_counts = {k: len([q for q in all_qids
                           if guessed_kind(preds[q]) == k])
                   for k in TRAP_KINDS}
    exec_stats = execution_stats(preds, truth, all_qids)
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
    generic_qids = sorted(q for q in sorted(all_qids)
                          if guessed_kind(preds[q]) == "generic")
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
        "claude_16": [claude["correct"], len(claude_qids)],
        "claude_correct_qids": claude["correct_qids"],
        "claude_qids": claude_qids,
        "trap_counts": trap_counts,
        "trap_total": [sum(trap_counts.values()), 215],
        "weak_repair_execution": exec_stats,
        "capex_qids": capex_qids,
        "datacenter_qids": dc_qids,
        "model_release_66": [model["correct"], len(model_qids)],
        "model_release_correct_qids": model["correct_qids"],
        "model_release_by_kind": model_by_kind,
        "generic_guesses": [len(generic_qids), 215],
        "generic_qids": generic_qids,
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
    claude_qids = sorted(q for q in kept if truth[q]["kind"] == "claude")
    claude = score_preds(preds, truth, claude_qids)
    trap_counts = {k: len([q for q in kept
                           if guessed_kind(preds[q]) == k])
                   for k in TRAP_KINDS}
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
    generic_qids = sorted(q for q in kept
                          if guessed_kind(preds[q]) == "generic")
    out = {
        "total_215": [total["correct"], 215],
        "correct_qids": total["correct_qids"],
        "by_kind": total["by_kind"],
        "by_player": total["by_player"],
        "generic_guesses": [len(generic_qids), 215],
        "generic_qids": generic_qids,
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
        "claude_16": [claude["correct"], 16],
        "claude_correct_qids": claude["correct_qids"],
        "trap_counts": trap_counts,
        "trap_total": [sum(trap_counts.values()), 215],
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
        "claude_16_mean": mean([batches_scores[b]["claude_16"][0] for b in batches]),
        "trap_total_mean": mean([batches_scores[b]["trap_total"][0] for b in batches]),
        "trap_by_kind_mean": {
            k: mean([batches_scores[b]["trap_counts"][k] for b in batches])
            for k in TRAP_KINDS},
        "model_release_66_mean": mean([batches_scores[b]["model_release_66"][0] for b in batches]),
        "model_release_by_kind_mean": {
            k: mean([batches_scores[b]["model_release_by_kind"][k][0] for b in batches])
            for k in MODEL_KINDS},
        "confidence_pooled": conf_pool,
        "confidence_mean_correct": {
            level: mean([batches_scores[b]["confidence"][level]["correct_total"][0] for b in batches])
            for level in ("high", "medium", "low")},
        "generic_guesses_mean": mean([batches_scores[b]["generic_guesses"][0] for b in batches]),
        "generic_guesses_by_batch": [batches_scores[b]["generic_guesses"][0] for b in batches],
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
        "claude_16_mean": mean([aud[b]["claude_16"][0] for b in batches]),
        "trap_total_mean": mean([aud[b]["trap_total"][0] for b in batches]),
        "trap_by_kind_mean": {
            k: mean([aud[b]["trap_counts"][k] for b in batches])
            for k in TRAP_KINDS},
        "model_release_66_mean": mean([aud[b]["model_release_66"][0] for b in batches]),
        "generic_guesses_mean": mean([aud[b]["generic_guesses"][0] for b in batches]),
        "generic_guesses_by_batch": [aud[b]["generic_guesses"][0] for b in batches],
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
    # gate 3: round-12 control, raw scores (clean baseline 62.00).
    got12 = {}
    for batch in ["C1", "C2", "C3"]:
        preds = load_batch(R12_CONTROL_DIR, batch)
        got12[batch] = score_batch(preds, truth7, batch, all_qids)["total_215"][0]
    ok12 = got12 == R12_CONTROL_EXPECTED
    print("gate 3 round-12 control raw (215q):",
          {b: f"{got12[b]}/215 (exp {R12_CONTROL_EXPECTED[b]})" for b in got12},
          "PASS" if ok12 else "FAIL")

    # gate 4: round-13 control, raw and leakage-excluded scores.
    got13_raw = {}
    got13_excl = {}
    for batch in ["C1", "C2", "C3"]:
        preds = load_batch(R13_CONTROL_DIR, batch)
        got13_raw[batch] = score_batch(
            preds, truth7, batch, all_qids)["total_215"][0]
        got13_excl[batch] = score_batch_excluding(
            preds, truth7, batch, all_qids, LEAK_42)["total_215"][0]
    ok13_raw = got13_raw == R13_CONTROL_RAW_EXPECTED
    ok13_excl = got13_excl == R13_CONTROL_EXCL_EXPECTED
    print("gate 4 round-13 control raw (215q):",
          {b: f"{got13_raw[b]}/215 (exp {R13_CONTROL_RAW_EXPECTED[b]})" for b in got13_raw},
          "PASS" if ok13_raw else "FAIL")
    print("gate 4 round-13 control excluded42 (215q):",
          {b: f"{got13_excl[b]}/215 (exp {R13_CONTROL_EXCL_EXPECTED[b]})" for b in got13_excl},
          "PASS" if ok13_excl else "FAIL")

    m_base = mean(list(got7.values()))
    m_ctrl = mean(list(got11.values()))
    gain = round(m_base - m_ctrl, 2)
    ok_gain = abs(gain - R11_GAIN_BOTH_AUDITED_EXPECTED) < 0.01
    print(f"gate 2 gain both-audited: {m_base:.2f} - {m_ctrl:.2f} = {gain:.2f} "
          f"(exp {R11_GAIN_BOTH_AUDITED_EXPECTED}) "
          f"{'PASS' if ok_gain else 'FAIL'}")
    ok = ok10 and ok7 and ok11 and ok_gain and ok12 and ok13_raw and ok13_excl
    if not ok:
        print("REPRODUCTION GATE FAILED: fix score_round14.py before scoring.")
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
                "status": "PASS"},
            "gate_3_round12_control_raw": {
                "got": got12, "expected": R12_CONTROL_EXPECTED,
                "mean": mean(list(got12.values())), "status": "PASS"},
            "gate_4_round13_control_raw": {
                "got": got13_raw, "expected": R13_CONTROL_RAW_EXPECTED,
                "mean": mean(list(got13_raw.values())), "status": "PASS"},
            "gate_4_round13_control_excluded42": {
                "got": got13_excl, "expected": R13_CONTROL_EXCL_EXPECTED,
                "mean": mean(list(got13_excl.values())), "status": "PASS"}}


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
        repro_path = os.path.join(run_root, "reproduce-round14.json")
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
    result["clean_baseline"] = {
        "mean": 62.00,
        "note": "Round-12 control mean under cleaned method files. "
                "97.67 was measured under leaked method files and is "
                "not the clean baseline. Reproduction gates only "
                "reproduce arithmetic; they do not treat 97.67 as "
                "the clean baseline.",
    }

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
            os.path.dirname(os.path.normpath(args.pred_dir)), "score-round14.json")
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
        eg_aud["weakest_weak_kind_rate"], cg_aud["weakest_weak_kind_rate"],
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
    # Seventh adoption gate (design 11): H4 side-effect gate.
    claude_exp = eg_aud["claude_16_mean"]
    claude_ctrl = cg_aud["claude_16_mean"]
    h4_pass = bool(claude_exp >= claude_ctrl - 2)
    rules["(H4) claude side-effect gate: exp claude mean >= control claude mean - 2"] = {
        "value": f"exp claude mean={claude_exp:.2f} vs control claude mean={claude_ctrl:.2f} "
                 f"(floor {claude_ctrl - 2:.2f})",
        "pass": h4_pass}
    conds = [rules[k]["pass"] for k in rules if isinstance(rules[k], dict) and "pass" in rules[k]]
    adopt = all(conds)
    # Discard (protocol section 6.2): gain 0 or negative, or new-kind
    # gain 0 or negative, or the gain was only on leaked questions
    # (raw gain > 0 but excluded gain <= 0), or the method harms the
    # new kinds (new-kind gain < 0).
    remove = (G <= 0) or (G_new <= 0) or (gains["G_raw"] > 0 and G <= 0) \
        or (new_kind_gain_excl < 0)
    if adopt:
        verdict = "ADOPT (weak-repair-round14 method verified into baseline)"
    elif not h4_pass:
        verdict = ("NOT ADOPTED (H4 side-effect gate failed: claude drop > 2; "
                   "coordinator decides tentative vs remove)")
    elif remove:
        verdict = "REMOVE (weak-repair-round14 method out of baseline)"
    else:
        verdict = "MIXED (helpful but below adoption threshold; stays tentative)"
    rules["adopt_all_six"] = bool(all(
        rules[k]["pass"] for k in rules
        if isinstance(rules[k], dict) and "pass" in rules[k]
        and not k.startswith("(H4)")))
    rules["adopt_all_six_plus_H4"] = bool(adopt)
    rules["remove_any"] = bool(remove)
    rules["verdict"] = verdict
    result["decision_rules"] = rules

    # --- forced-step execution (design 5.2/5.3, experiment group) ---
    weak_qids = sorted(q for q in all_qids if truth[q]["kind"] in WEAK_KINDS)
    exp_exec = {"per_batch": {}, "pooled": {}}
    tot_exec = tot_trig = 0
    tot_n_exec = 0
    for b in EXP_BATCHES:
        es = exp_raw[b]["weak_repair_execution"]
        exp_exec["per_batch"][b] = es
        tot_exec += es["weak_total_exec"][0]
        tot_trig += es["weak_trigger_present"][0]
        tot_n_exec += es["numeric_n_exec"][0]
    exp_exec["pooled"] = {
        "total_exec": [tot_exec, 135],
        "total_exec_rate": tot_exec / 135,
        "total_exec_threshold": 0.90,
        "total_exec_pass": bool(tot_exec / 135 >= 0.90),
        "n_exec": [tot_n_exec, 42],
        "n_exec_rate": tot_n_exec / 42,
        "n_exec_threshold": 0.90,
        "n_exec_pass": bool(tot_n_exec / 42 >= 0.90),
        "trigger_present": [tot_trig, 135],
        "trigger_rate": tot_trig / 135,
        "trigger_threshold": 0.90,
        "trigger_pass": bool(tot_trig / 135 >= 0.90),
    }
    exp_exec["all_three_pass"] = bool(
        exp_exec["pooled"]["total_exec_pass"]
        and exp_exec["pooled"]["n_exec_pass"]
        and exp_exec["pooled"]["trigger_pass"])
    # Control-group execution (same counters; control records carry no
    # weak_* fields, so this is expected to be 0 and is reported only).
    ctrl_exec = {"per_batch": {}}
    for b in CONTROL_BATCHES:
        ctrl_exec["per_batch"][b] = control[b]["weak_repair_execution"]
    result["forced_step_execution"] = {
        "experiment": exp_exec, "control": ctrl_exec,
        "denominators": {"total_and_trigger": 135, "n_step": 42},
        "note": "Total execution = all five rule-O lines present. "
                "T-check-row = trigger check present in weak_evidence. "
                "N-step = >=2 dated values + trend word in weak_evidence "
                "on the 14 numeric_history questions. Thresholds 90% "
                "(design 5.3)."}
    # Rule-L trigger guard: more than 3 milestone records in the
    # experiment group is flagged (q186 has 3 records).
    l_all = sorted({q for b in EXP_BATCHES
                    for q in exp_raw[b]["weak_repair_execution"]["legal_milestone_qids"]})
    l_count = sum(exp_raw[b]["weak_repair_execution"]["legal_milestone_records"][0]
                  for b in EXP_BATCHES)
    result["forced_step_execution"]["legal_milestone_guard"] = {
        "experiment_records": l_count, "limit": 3,
        "over_trigger": bool(l_count > 3), "qids": l_all}
    # "Follow the latest action line" template (design 6.2): experiment
    # group, 16 claude questions, 48 records.
    claude_qids = sorted(q for q in all_qids if truth[q]["kind"] == "claude")
    tmpl_recs = []
    for b in EXP_BATCHES:
        for q in claude_qids:
            if "顺最近动作线" in (exp_preds[b][q].get("reason") or ""):
                tmpl_recs.append((b, q))
    tmpl_correct = sum(1 for b, q in tmpl_recs
                       if is_correct(exp_preds[b], truth, q))
    tmpl_guess_dist = {}
    for b, q in tmpl_recs:
        g = guessed_kind(exp_preds[b][q])
        tmpl_guess_dist[g] = tmpl_guess_dist.get(g, 0) + 1
    result["claude_template_audit"] = {
        "template_records": len(tmpl_recs), "denominator": 48,
        "template_rate": len(tmpl_recs) / 48,
        "template_correct": tmpl_correct,
        "template_correct_rate": (tmpl_correct / len(tmpl_recs)) if tmpl_recs else None,
        "template_guessed_kind_distribution": tmpl_guess_dist,
        "mechanism_supported": bool(len(tmpl_recs) >= 12 and tmpl_recs
                                    and tmpl_correct / len(tmpl_recs) < 0.50),
        "mechanism_note": "Supported iff >= 12 template records (25% of 48) "
                          "AND their correct rate < 50% (design 6.3)."}
    # Sentinels (design 6.3/6.4, section 7): q145, q195, q186.
    def _sentinel(qid):
        return {
            "control_correct_batches": sum(
                1 for b in CONTROL_BATCHES if is_correct(control_preds[b], truth, qid)),
            "experiment_correct_batches": sum(
                1 for b in EXP_BATCHES if is_correct(exp_preds[b], truth, qid)),
            "denominator": 3}
    sent = {"q145": _sentinel(145), "q195": _sentinel(195), "q186": _sentinel(186)}
    sent["q145_mechanism_reproduced"] = bool(
        sent["q145"]["experiment_correct_batches"] == 0
        and sent["q145"]["control_correct_batches"] >= 2)
    sent["q145_sentinel_cleared"] = bool(
        sent["q145"]["experiment_correct_batches"] >= 1)
    sent["q195_broken"] = bool(sent["q195"]["experiment_correct_batches"] < 2)
    result["sentinels"] = sent

    # --- H-14 (weak-repair hypothesis, design section 9) ---
    # Comparator is THIS round's control group, not 62.00: the input
    # changed (numeric_history on both groups). 62.00 and 61.33 are
    # reported alongside for reference only.
    CLEAN_BASELINE = 62.00
    h14_threshold = max(11, max(S_TC_aud, S_TE_aud))
    h1_gain = M_TE_aud - M_TC_aud
    h2_weak_gain = eg_aud["weak_45_mean"] - cg_aud["weak_45_mean"]
    h3_exec = exp_exec["all_three_pass"]
    h4_claude_ok = bool(eg_aud["claude_16_mean"] >= cg_aud["claude_16_mean"] - 2)
    input_gain_weak = cg["weak_45_mean"] - R13_CONTROL_WEAK_MEAN
    program_gain_weak = h2_weak_gain
    h14 = {
        "comparator": "this round's control group (input changed: "
                      "numeric_history on both groups)",
        "clean_baseline_62_reference": CLEAN_BASELINE,
        "round13_control_excluded42_mean_reference": 61.33,
        "experiment_mean_excluded42": M_TE_aud,
        "control_mean_excluded42": M_TC_aud,
        "H1_gain_excluded42": h1_gain,
        "H1_threshold_max_11_round_noise_band": h14_threshold,
        "H1_pass": bool(h1_gain > h14_threshold),
        "H2_weak_gain": h2_weak_gain,
        "H2_threshold": 3,
        "H2_pass": bool(h2_weak_gain >= 3),
        "weak_by_kind_gain_excluded42": gains["weak_by_kind_gain_excluded42"],
        "weak_by_kind_gain_raw": gains["weak_by_kind_gain_raw"],
        "weak_gain_decomposition_design_3_5": {
            "input_gain_weak": input_gain_weak,
            "input_gain_note": "control weak mean - 1.00 (round-13 control weak mean)",
            "program_gain_weak": program_gain_weak,
            "program_gain_note": "experiment weak mean - control weak mean",
            "interpretation": "Input gain large + program gain small means "
                              "the input repaired the revenue questions, "
                              "not the method. The field itself is not "
                              "adopted by this round."},
        "H3_execution_pass": h3_exec,
        "H3_detail": exp_exec["pooled"],
        "H4_claude_exp_mean": eg_aud["claude_16_mean"],
        "H4_claude_ctrl_mean": cg_aud["claude_16_mean"],
        "H4_pass": h4_claude_ok,
        "claude_16_mean_exp_raw": eg_raw["claude_16_mean"],
        "claude_16_mean_ctrl_raw": cg["claude_16_mean"],
        "capex_10_mean_exp_raw": eg_raw["capex_10_mean"],
        "capex_10_mean_ctrl_raw": cg["capex_10_mean"],
        "capex_10_mean_exp_excluded42": eg_aud["capex_10_mean"],
        "capex_10_mean_ctrl_excluded42": cg_aud["capex_10_mean"],
        "capex_check_note": "All 10 capex questions are in LEAK_42, so the "
            "excluded42 capex mean is 0 by construction. Capex is "
            "reported on raw means, description only (design 8).",
        "trap_counts_mean_exp_raw": eg_raw["trap_total_mean"],
        "trap_counts_mean_ctrl_raw": cg["trap_total_mean"],
        "trap_by_kind_mean_exp_raw": eg_raw["trap_by_kind_mean"],
        "trap_by_kind_mean_ctrl_raw": cg["trap_by_kind_mean"],
        "trap_round13_total_reference": 174,
        "trap_note": "Trap kinds (open_source, ascend, compliance, generic, "
                     "openai_mar26) are all wrong by construction. Trap "
                     "counts do not enter the adoption decision (design 10.6).",
        "weakest_weak_kind_exp": eg_aud["weakest_weak_kind"],
        "weakest_weak_kind_rate_exp": eg_aud["weakest_weak_kind_rate"],
        "weakest_weak_kind_ctrl": cg_aud["weakest_weak_kind"],
        "weakest_weak_kind_rate_ctrl": cg_aud["weakest_weak_kind_rate"],
        "weakest_kind_all43_exp": eg_aud["weakest_kind"],
        "weakest_kind_all43_rate_exp": eg_aud["weakest_kind_rate"],
        "weakest_kind_all43_ctrl": cg_aud["weakest_kind"],
        "weakest_kind_all43_rate_ctrl": cg_aud["weakest_kind_rate"],
        "falsified": bool(h1_gain <= h14_threshold
                          or h2_weak_gain < 3
                          or not h3_exec
                          or not h4_claude_ok),
        "falsified_by": [name for name, ok in (
            ("F1 gain not over noise band", h1_gain > h14_threshold),
            ("F2 weak gain < 3", h2_weak_gain >= 3),
            ("F3 execution below threshold", h3_exec),
            ("F4 claude drop > 2", h4_claude_ok)) if not ok],
    }
    h14["hypothesis_H_14"] = ("SUPPORTED" if not h14["falsified"] else "FALSIFIED")
    h14["execution_verdict_wording"] = (
        "method not executed (decision pauses)" if not h3_exec
        else "method executed")
    result["hypothesis_H_14"] = h14

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
        os.path.dirname(os.path.normpath(args.pred_dir)), "score-round14.json")
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
    print("decision (section 6.1 + H4, excluded42):", verdict)
    print("H-14:", h14["hypothesis_H_14"], "falsified_by:", h14["falsified_by"])
    print(f"H-14 detail: H1 gain={h1_gain:.2f} vs threshold={h14_threshold} "
          f"H2 weak_gain={h2_weak_gain:.2f} H3 exec={h3_exec} H4 claude_ok={h4_claude_ok} "
          f"input_gain_weak={input_gain_weak:.2f} program_gain_weak={program_gain_weak:.2f}")
    print(f"execution: total={tot_exec}/135={tot_exec/135:.3f} "
          f"N={tot_n_exec}/42={tot_n_exec/42:.3f} T={tot_trig}/135={tot_trig/135:.3f} "
          f"L_records={l_count} template={len(tmpl_recs)}/48")
    print(f"claude: exp_mean={eg_aud['claude_16_mean']:.2f} ctrl_mean={cg_aud['claude_16_mean']:.2f} "
          f"trap_exp_mean={eg_raw['trap_total_mean']:.2f} trap_ctrl_mean={cg['trap_total_mean']:.2f}")


if __name__ == "__main__":
    main()
