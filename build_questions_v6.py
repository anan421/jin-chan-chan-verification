#!/usr/bin/env python3
"""Build round-6 question files for vision-1 round 6 (method-fix bundle).

Reads:
  - runs/s5patch-round6-2026-11-22/context-all-v5.json  (per-question context)
  - runs/s5patch-round6-2026-11-22/questions/questions-S3-1-1.json (vocabulary)
  - testset-v5.json (truth; used only to check each question's round_date)
Writes (runs/round6-vision6-2026-11-22/questions/, gitignored):
  - questions-round6-S{season}-{round}.json, one per round (11 rounds,
    26 focused questions), in the same format as the v5 question files
    (round, season, round_label, round_date, round_trace_date, vocabulary,
    questions[]). Questions carry NO answer field: no kind, no event_name,
    no action, no source, and NO prev_round_kinds (the round-5 contamination
    root cause -- the builder never emits it).

Round dates:
  - File header round_date / round_trace_date = the trace round date.
  - Each question's own round_date = its prediction point from the v5
    context (== testset-v5 round_date). Two questions carry a
    round_date_override (trace date + reason): S3 6-1 q14 -> 20241030,
    S4 3-2 q36 -> 20240920. S5 1-1 has no single round date: each of its
    4 questions carries its own event date as round_date.
  - Single-round isolation: each file holds only its own round's questions.
    A predictor doing an early round must not see a later round's file.

Pre-issue checks (run by this script after writing; any failure exits
non-zero and fails loudly):
  1. The 11 files contain exactly the 26-ID focus set, no more, no fewer.
  2. Zero occurrences of every banned field, counted as exact JSON field
     names (recursive scan): prev_round_kinds, kind, action, action_kind,
     hp_delta, gold_delta, event_name, event_real_date, source.
     NOTE on "kind": the approved question format legitimately contains
     kind NAMES as values -- player_history_counts keys, player_last_kind,
     player_most_frequent. Those are field names of their own, not the
     field "kind", and the plan's field list requires them. The check is
     therefore on the exact field name "kind", not on the substring.
     A separate substring check asserts "prev_round" appears nowhere.
  3. Every question's round_date matches testset-v5.json exactly.
  4. Every file header round_date equals the trace round date.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V5 = HERE / "runs" / "s5patch-round6-2026-11-22"
OUT = HERE / "runs" / "round6-vision6-2026-11-22" / "questions"

FOCUS = {5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
         30, 31, 32, 36, 37, 61, 62, 63, 67, 74, 92, 93}
BANNED_FIELDS = {"prev_round_kinds", "kind", "action", "action_kind",
                 "hp_delta", "gold_delta", "event_name", "event_real_date",
                 "source"}


def count_banned(obj, counts):
    """Recursively count exact-key occurrences of banned field names."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BANNED_FIELDS:
                counts[k] += 1
            count_banned(v, counts)
    elif isinstance(obj, list):
        for v in obj:
            count_banned(v, counts)


def main():
    ctx = {c["q_id"]: c
           for c in json.loads((V5 / "context-all-v5.json").read_text(encoding="utf-8"))}
    ts = json.loads((HERE / "testset-v5.json").read_text(encoding="utf-8"))
    truth = {q["q_id"]: q for q in ts["questions"]}
    vocab = json.loads(
        (V5 / "questions" / "questions-S3-1-1.json").read_text(encoding="utf-8")
    )["vocabulary"]
    assert len(vocab) == 34, f"vocabulary should be 34 kinds, got {len(vocab)}"

    missing = FOCUS - set(ctx)
    assert not missing, f"focus q_ids missing from v5 context: {sorted(missing)}"
    # Per-question round_date must match testset-v5 exactly (checked again
    # after writing, against the files on disk).
    for qid in sorted(FOCUS):
        assert ctx[qid]["date"] == truth[qid]["round_date"], (
            f"q{qid}: context date {ctx[qid]['date']} != "
            f"testset-v5 round_date {truth[qid]['round_date']}")
        assert "prev_round_kinds" not in ctx[qid], f"q{qid} carries prev_round_kinds"

    by_round = defaultdict(list)
    for qid in sorted(FOCUS):
        c = ctx[qid]
        by_round[(c["season"], c["round_label"])].append(c)
    assert len(by_round) == 11, f"expected 11 rounds, got {len(by_round)}"

    OUT.mkdir(parents=True, exist_ok=True)
    # Chronological round order: season, then trace date.
    for (season, rlabel) in sorted(by_round, key=lambda k: (k[0], by_round[k][0]["trace_date"])):
        cs = sorted(by_round[(season, rlabel)], key=lambda c: c["q_id"])
        trace_date = cs[0]["trace_date"]
        assert all(c["trace_date"] == trace_date for c in cs), (
            f"S{season} {rlabel}: mixed trace dates")
        questions = []
        for c in cs:
            q = {
                "q_id": c["q_id"],
                "player": c["player"],
                "round_date": c["date"],
                "hp_start": c["hp_start"],
                "gold_start": c["gold_start"],
                "rules_version": c["rules_version"],
                "first_appearance": c["first_appearance"],
                "player_history_counts": c["player_history_counts"],
                "player_most_frequent": c["player_most_frequent"],
                "player_last_kind": c["player_last_kind"],
                "player_last3": c["player_last3"],
            }
            if c.get("round_date_override") is not None:
                q["round_date_override"] = c["round_date_override"]
            questions.append(q)
        out = {
            "round": f"S{season} {rlabel}",
            "season": season,
            "round_label": rlabel,
            "round_date": trace_date,
            "round_trace_date": trace_date,
            "vocabulary": vocab,
            "questions": questions,
        }
        name = f"questions-round6-S{season}-{rlabel}.json"
        (OUT / name).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        print(f"{name}: {len(cs)} questions (q_ids {[c['q_id'] for c in cs]})")

    # ---- Pre-issue checks on the files as written ----
    all_ids = []
    counts = defaultdict(int)
    failures = []
    for f in sorted(OUT.glob("questions-round6-*.json")):
        text = f.read_text(encoding="utf-8")
        data = json.loads(text)
        if data["round_date"] != data["round_trace_date"]:
            failures.append(f"{f.name}: header round_date != round_trace_date")
        if "prev_round" in text:
            failures.append(f"{f.name}: contains 'prev_round' substring")
        count_banned(data, counts)
        for q in data["questions"]:
            all_ids.append(q["q_id"])
            if q["round_date"] != truth[q["q_id"]]["round_date"]:
                failures.append(
                    f"{f.name} q{q['q_id']}: round_date {q['round_date']} != "
                    f"testset-v5 {truth[q['q_id']]['round_date']}")
    if set(all_ids) != FOCUS:
        failures.append(
            f"q_id set mismatch: missing {sorted(FOCUS - set(all_ids))}, "
            f"extra {sorted(set(all_ids) - FOCUS)}")
    if len(all_ids) != 26:
        failures.append(f"total questions {len(all_ids)} != 26")
    banned_total = {k: counts.get(k, 0) for k in sorted(BANNED_FIELDS)}
    print("banned-field counts (exact JSON field names):", banned_total)
    if any(banned_total.values()):
        failures.append(f"banned fields present: "
                        f"{ {k: v for k, v in banned_total.items() if v} }")
    print(f"rounds: {len(list(OUT.glob('questions-round6-*.json')))}, "
          f"questions: {len(all_ids)}, unique q_ids: {len(set(all_ids))}")
    if failures:
        print("PRE-ISSUE CHECKS FAILED:")
        for f_ in failures:
            print("  FAIL:", f_)
        sys.exit(1)
    print("PRE-ISSUE CHECKS PASSED: 26-ID set exact, banned fields all 0, "
          "round_dates match testset-v5.")


if __name__ == "__main__":
    main()
