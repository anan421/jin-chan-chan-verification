#!/usr/bin/env python3
"""Build round-10 question files: filter the round-8 files to the 32
questions of vision-1 round 10 (roleplay + forward guidance vs forward
guidance only, single rule), covering the 4 prototype prediction
categories (infra_capex 12, policy_regulatory 3, model_release 14,
chip_supply 3).

Input:  ~/workspace/verification-v1-round8/runs/round8-vision8-2026-11-22/questions/
        questions-round8-<round>.json (16 rounds, 32 questions in total).
Output: runs/round10-vision10-2026-11-22/questions/
        questions-round10-<round>.json (same 16 rounds, 32 questions).
Each question object is copied unchanged (round_date,
round_date_override, player history); only non-round-10 questions are
dropped. File headers (round/season/round_label/round_date/vocabulary)
are copied unchanged.

Assertions (fail loudly, build nothing on failure):
  1. output q_id set == FOCUS (32 ids), no more, no fewer.
  2. no banned field name appears in the output files:
     prev_round_kinds, "kind":, "action":, "action_kind":, "hp_delta":,
     "gold_delta":, "event_name":, "event_real_date":, "source":
     (kind names inside vocabulary / player_last3 pairs are values, not
     fields, and are allowed).
  3. every output question's round_date matches testset-v6.json.
  4. every player_last3 record date is strictly before the question's
     round_date.

Usage: python3 build_questions_v10.py
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
R8_QDIR = os.path.join(os.path.expanduser("~"), "workspace",
                       "verification-v1-round8",
                       "runs", "round8-vision8-2026-11-22", "questions")
OUT_DIR = os.path.join(BASE, "runs", "round10-vision10-2026-11-22", "questions")

# 32 round-10 questions (design/experiment-vision10-round10.md).
FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
         36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
ROUNDS = ["S1-1-4", "S2-2-1", "S3-1-1", "S3-2-1", "S3-3-2", "S3-6-1",
          "S4-1-1", "S4-1-2", "S4-3-2", "S4-4-1", "S5-1-1", "S5-2-1",
          "S5-3-2", "S5-4-1", "S5-5-1", "S5-6-1"]
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
        out = os.path.join(OUT_DIR, f"questions-round10-{r}.json")
        with open(out, "w") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
        out_qids += [q["q_id"] for q in kept]
        print(f"{r}: kept {sorted(q['q_id'] for q in kept)} "
              f"dropped {sorted(dropped)} -> {out}")
    assert sorted(out_qids) == sorted(FOCUS), (
        f"output q_id set != FOCUS: got {sorted(out_qids)}")
    for r in ROUNDS:
        path = os.path.join(OUT_DIR, f"questions-round10-{r}.json")
        text = open(path).read()
        for b in BANNED:
            assert b not in text, f"banned field {b} in questions-round10-{r}.json"
        d = json.load(open(path))
        for q in d["questions"]:
            assert q["round_date"] == truth_date[q["q_id"]], (
                f"q{q['q_id']}: round_date {q['round_date']} != "
                f"testset-v6 {truth_date[q['q_id']]}")
            for rec in q.get("player_last3") or []:
                rec_date = rec[1]
                assert rec_date < q["round_date"], (
                    f"q{q['q_id']}: player_last3 record {rec} not strictly "
                    f"before round_date {q['round_date']}")
    print(f"BUILD OK: {len(ROUNDS)} files, {len(out_qids)} round-10 questions, "
          f"no banned fields, round_dates match testset-v6, "
          f"all player_last3 dates strictly before round_date.")


if __name__ == "__main__":
    main()
