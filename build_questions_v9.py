#!/usr/bin/env python3
"""Build round-9 question files: filter the round-8 files to the 13 focus
questions (capex q10-19 + datacenter q30-32).

Input:  ~/workspace/verification-v1-round8/runs/round8-vision8-2026-11-22/questions/
        questions-round8-<round>.json (6 rounds, 27 questions in total).
Output: runs/round9-vision9-2026-11-22/questions/
        questions-round9-<round>.json (same 6 rounds, 13 questions in total).
Each question object is copied unchanged (round_date, round_date_override,
player history); only non-focus questions are dropped. File headers
(round/season/round_label/round_date/vocabulary) are copied unchanged.

Assertions (fail loudly, build nothing on failure):
  1. output q_id set == FOCUS (13 ids), no more, no fewer.
  2. no banned field name appears in the output files:
     prev_round_kinds, "kind":, "action":, "action_kind":, "hp_delta":,
     "gold_delta":, "event_name":, "event_real_date":, "source":
     (kind names inside vocabulary / player_last3 pairs are values, not
     fields, and are allowed).
  3. every output question's round_date matches testset-v6.json.

Usage: python3 build_questions_v9.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
R8_QDIR = os.path.join(os.path.expanduser("~"), "workspace",
                       "verification-v1-round8",
                       "runs", "round8-vision8-2026-11-22", "questions")
OUT_DIR = os.path.join(BASE, "runs", "round9-vision9-2026-11-22", "questions")

FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 30, 31, 32}
ROUNDS = ["S3-1-1", "S3-6-1", "S4-1-2", "S5-1-1", "S5-2-1", "S5-4-1"]
BANNED = ['"prev_round_kinds"', '"kind":', '"action":', '"action_kind":',
          '"hp_delta":', '"gold_delta":', '"event_name":',
          '"event_real_date":', '"source":']


def main():
    ts = json.load(open(os.path.join(BASE, "testset-v6.json")))
    truth_date = {q["q_id"]: q["round_date"] for q in ts["questions"]}
    os.makedirs(OUT_DIR, exist_ok=True)
    out_qids = []
    for r in ROUNDS:
        src = os.path.join(R8_QDIR, f"questions-round8-{r}.json")
        d = json.load(open(src))
        kept = [q for q in d["questions"] if q["q_id"] in FOCUS]
        dropped = [q["q_id"] for q in d["questions"] if q["q_id"] not in FOCUS]
        d["questions"] = kept
        out = os.path.join(OUT_DIR, f"questions-round9-{r}.json")
        with open(out, "w") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
        out_qids += [q["q_id"] for q in kept]
        print(f"{r}: kept {sorted(q['q_id'] for q in kept)} "
              f"dropped {sorted(dropped)} -> {out}")
    assert sorted(out_qids) == sorted(FOCUS), (
        f"output q_id set != FOCUS: got {sorted(out_qids)}")
    for r in ROUNDS:
        text = open(os.path.join(OUT_DIR, f"questions-round9-{r}.json")).read()
        for b in BANNED:
            assert b not in text, f"banned field {b} in questions-round9-{r}.json"
        d = json.load(open(os.path.join(OUT_DIR, f"questions-round9-{r}.json")))
        for q in d["questions"]:
            assert q["round_date"] == truth_date[q["q_id"]], (
                f"q{q['q_id']}: round_date {q['round_date']} != "
                f"testset-v6 {truth_date[q['q_id']]}")
    print(f"BUILD OK: 6 files, {len(out_qids)} focus questions, "
          f"no banned fields, round_dates match testset-v6.")


if __name__ == "__main__":
    main()
