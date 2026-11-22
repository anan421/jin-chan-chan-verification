#!/usr/bin/env python3
"""Build round-7 question files for vision-1 round 7 (forward-guidance steps,
single-rule test).

Reads:
  - runs/s5patch-round6-2026-11-22/context-all-v5.json  (per-question context)
  - runs/s5patch-round6-2026-11-22/questions/questions-S3-1-1.json (vocabulary)
  - testset-v6.json (truth; used only to check each question's round_date)
Writes (runs/round7-vision7-2026-11-22/questions/, gitignored):
  - questions-round7-S{season}-{round}.json, one per round (4 rounds,
    10 capex questions), in the same format as the v6 question files
    (round, season, round_label, round_date, round_trace_date, vocabulary,
    questions[]). Questions carry NO answer field: no kind, no event_name,
    no action, no source, and NO prev_round_kinds (the round-5 contamination
    root cause -- the builder never emits it).

Round dates:
  - File header round_date / round_trace_date = the trace round date.
  - Each question's own round_date = its prediction point from the v5
    context (== testset-v6 round_date). Questions carry a
    round_date_override (trace date + reason) where the context has one:
    S3 6-1 q14 -> 20241030, S5 1-1 q15-q18 -> each question's event date.
    S5 1-1 has no single round date: each of its 4 questions carries its
    own event date as round_date.
  - Single-round isolation: each file holds only its own round's questions.
    A predictor doing an early round must not see a later round's file.

Generator fix (round-6 report known defect #1):
  - player_last3 entries are [kind_name, date_int] pairs. The v5 context
    generator did not filter history by round date (q36 carried two
    2025-01-20/21 entries after its 2024-09-20 cutoff). This builder drops
    every player_last3 entry whose date is >= the question's round_date,
    logs how many were dropped, and asserts afterwards that every remaining
    entry is strictly before the question's round_date. player_history_counts
    are cumulative counts (no dates) and are not filtered.

Pre-issue checks (run by this script after writing; any failure exits
non-zero and fails loudly):
  1. The 4 files contain exactly the 10-ID focus set, no more, no fewer.
  2. Zero occurrences of every banned field, counted as exact JSON field
     names (recursive scan): prev_round_kinds, kind, action, action_kind,
     hp_delta, gold_delta, event_name, event_real_date, source.
     NOTE on "kind": the approved question format legitimately contains
     kind NAMES as values -- player_history_counts keys, player_last_kind,
     player_most_frequent. Those are field names of their own, not the
     field "kind", and the plan's field list requires them. The check is
     therefore on the exact field name "kind", not on the substring.
     A separate substring check asserts "prev_round" appears nowhere.
  3. Every question's round_date matches testset-v6.json exactly.
  4. Every file header round_date equals the trace round date.
  5. Every player_last3 entry date is strictly before its question's
     round_date (after the filter above).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V5 = HERE / "runs" / "s5patch-round6-2026-11-22"
OUT = HERE / "runs" / "round7-vision7-2026-11-22" / "questions"

FOCUS = {10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
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


def filter_last3(last3, round_date, qid):
    """Drop player_last3 entries dated on/after the question's round_date.

    Entries are [kind_name, date_int] pairs. Returns (kept, dropped_count).
    """
    kept = []
    dropped = 0
    for e in (last3 or []):
        d = e[1]
        if d < round_date:
            kept.append(e)
        else:
            dropped += 1
    if dropped:
        print(f"  q{qid}: dropped {dropped} stale player_last3 entries "
              f"(date >= round_date {round_date})")
    return kept, dropped


def main():
    ctx = {c["q_id"]: c
           for c in json.loads((V5 / "context-all-v5.json").read_text(encoding="utf-8"))}
    ts = json.loads((HERE / "testset-v6.json").read_text(encoding="utf-8"))
    truth = {q["q_id"]: q for q in ts["questions"]}
    vocab = json.loads(
        (V5 / "questions" / "questions-S3-1-1.json").read_text(encoding="utf-8")
    )["vocabulary"]
    assert len(vocab) == 34, f"vocabulary should be 34 kinds, got {len(vocab)}"

    missing = FOCUS - set(ctx)
    assert not missing, f"focus q_ids missing from v5 context: {sorted(missing)}"
    # Per-question round_date must match testset-v6 exactly (checked again
    # after writing, against the files on disk).
    for qid in sorted(FOCUS):
        assert ctx[qid]["date"] == truth[qid]["round_date"], (
            f"q{qid}: context date {ctx[qid]['date']} != "
            f"testset-v6 round_date {truth[qid]['round_date']}")
        assert "prev_round_kinds" not in ctx[qid], f"q{qid} carries prev_round_kinds"

    by_round = defaultdict(list)
    for qid in sorted(FOCUS):
        c = ctx[qid]
        by_round[(c["season"], c["round_label"])].append(c)
    assert len(by_round) == 4, f"expected 4 rounds, got {len(by_round)}"

    OUT.mkdir(parents=True, exist_ok=True)
    total_dropped = 0
    # Chronological round order: season, then trace date.
    for (season, rlabel) in sorted(by_round, key=lambda k: (k[0], by_round[k][0]["trace_date"])):
        cs = sorted(by_round[(season, rlabel)], key=lambda c: c["q_id"])
        trace_date = cs[0]["trace_date"]
        assert all(c["trace_date"] == trace_date for c in cs), (
            f"S{season} {rlabel}: mixed trace dates")
        questions = []
        for c in cs:
            last3, dropped = filter_last3(c["player_last3"], c["date"], c["q_id"])
            total_dropped += dropped
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
                "player_last3": last3,
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
        name = f"questions-round7-S{season}-{rlabel}.json"
        (OUT / name).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        print(f"{name}: {len(cs)} questions (q_ids {[c['q_id'] for c in cs]})")
    print(f"player_last3 stale entries dropped total: {total_dropped}")

    # ---- Pre-issue checks on the files as written ----
    all_ids = []
    counts = defaultdict(int)
    failures = []
    for f in sorted(OUT.glob("questions-round7-*.json")):
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
                    f"testset-v6 {truth[q['q_id']]['round_date']}")
            for e in q.get("player_last3") or []:
                if e[1] >= q["round_date"]:
                    failures.append(
                        f"{f.name} q{q['q_id']}: player_last3 entry {e} "
                        f"not before round_date {q['round_date']}")
    if set(all_ids) != FOCUS:
        failures.append(
            f"q_id set mismatch: missing {sorted(FOCUS - set(all_ids))}, "
            f"extra {sorted(set(all_ids) - FOCUS)}")
    if len(all_ids) != 10:
        failures.append(f"total questions {len(all_ids)} != 10")
    banned_total = {k: counts.get(k, 0) for k in sorted(BANNED_FIELDS)}
    print("banned-field counts (exact JSON field names):", banned_total)
    if any(banned_total.values()):
        failures.append(f"banned fields present: "
                        f"{ {k: v for k, v in banned_total.items() if v} }")
    print(f"rounds: {len(list(OUT.glob('questions-round7-*.json')))}, "
          f"questions: {len(all_ids)}, unique q_ids: {len(set(all_ids))}")
    if failures:
        print("PRE-ISSUE CHECKS FAILED:")
        for f_ in failures:
            print("  FAIL:", f_)
        sys.exit(1)
    print("PRE-ISSUE CHECKS PASSED: 10-ID set exact, banned fields all 0, "
          "round_dates match testset-v6, player_last3 all before round_date.")


if __name__ == "__main__":
    main()
