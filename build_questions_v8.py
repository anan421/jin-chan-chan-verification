#!/usr/bin/env python3
"""Build round-8 question files for vision-1 round 8 (forward-guidance step
as baseline, full 98-question run to measure false-capex spillover).

Reads:
  - runs/s5patch-round6-2026-11-22-context-all-v5.json (per-question context,
    copied from the round-7 worktree; built for testset-v5, 99 questions)
  - /tmp/vocab-source.json (vocabulary, 34 kinds, from a v5 question file)
  - testset-v6.json (truth; 98 questions, q79 removed, 23 round dates fixed)
Writes (runs/round8-vision8-2026-11-22/questions/, gitignored):
  - questions-round8-S{season}-{round}.json, one per round (28 rounds,
    98 questions), same format as the v7 question files
    (round, season, round_label, round_date, round_trace_date, vocabulary,
    questions[]). Questions carry NO answer field: no kind, no event_name,
    no action, no source, and NO prev_round_kinds.

Round dates:
  - File header round_date / round_trace_date = the trace round date.
  - Each question's own round_date = its prediction point from
    testset-v6 (== event date for the 23 Part-1-fixed questions).
  - round_date_override: kept from the v5 context where present
    (q0, 14, 15, 16, 17, 18, 36, 42, 43); added for the 23 Part-1-fixed
    questions (trace date + calendar days late + reason).
  - S5 1-1 has no single round date: each of its 7 questions carries its
    own event date as round_date.
  - Single-round isolation: each file holds only its own round's questions.

Generator fix (from round 7): player_last3 entries are [kind_name,
date_int] pairs. Drop every entry whose date is >= the question's
round_date (the v6 date, which for the 23 fixed questions is EARLIER
than the v5 context date, so more entries drop -- correct, history must
be before the prediction point). Log drops, assert afterwards that every
remaining entry is strictly before the question's round_date.
player_history_counts are cumulative counts (no dates), not filtered.

Pre-issue checks (run by this script after writing; any failure exits
non-zero and fails loudly):
  1. The 28 files contain exactly the 98 q_ids of testset-v6, no more,
     no fewer (q79 absent).
  2. Zero occurrences of every banned field, counted as exact JSON field
     names (recursive scan): prev_round_kinds, kind, action, action_kind,
     hp_delta, gold_delta, event_name, event_real_date, source.
     (Kind NAMES as values -- player_history_counts keys,
     player_last_kind, player_most_frequent -- are legitimate; the check
     is on the exact field name "kind", not the substring.)
     A separate substring check asserts "prev_round" appears nowhere.
  3. Every question's round_date matches testset-v6.json exactly.
  4. Every file header round_date equals the trace round date.
  5. Every player_last3 entry date is strictly before its question's
     round_date (after the filter above).
  6. The 23 Part-1-fixed questions each carry a round_date_override
     recording the old trace date and the calendar days it was late.
"""
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CTX = HERE / "runs" / "s5patch-round6-2026-11-22-context-all-v5.json"
OUT = HERE / "runs" / "round8-vision8-2026-11-22" / "questions"

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


def d8(n):
    return date(n // 10000, (n // 100) % 100, n % 100)


def filter_last3(last3, round_date, qid):
    """Drop player_last3 entries dated on/after the question's round_date."""
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
           for c in json.loads(CTX.read_text(encoding="utf-8"))}
    ts = json.loads((HERE / "testset-v6.json").read_text(encoding="utf-8"))
    truth = {q["q_id"]: q for q in ts["questions"]}
    vocab = json.loads(
        Path("/tmp/vocab-source.json").read_text(encoding="utf-8")
    )["vocabulary"]
    assert len(vocab) == 34, f"vocabulary should be 34 kinds, got {len(vocab)}"
    assert len(truth) == 98, f"testset-v6 should be 98, got {len(truth)}"
    assert 79 not in truth, "q79 should be removed in testset-v6"

    missing = set(truth) - set(ctx)
    assert not missing, f"v6 q_ids missing from v5 context: {sorted(missing)}"
    for qid in sorted(truth):
        assert "prev_round_kinds" not in ctx[qid], f"q{qid} carries prev_round_kinds"

    # The 23 Part-1-fixed questions: context date (old trace date) != v6
    # round_date (event date). Their question round_date is the v6 date;
    # the override records the old date and how many calendar days late.
    fixed = {}
    for qid in sorted(truth):
        if ctx[qid]["date"] != truth[qid]["round_date"]:
            late = (d8(ctx[qid]["date"]) - d8(truth[qid]["round_date"])).days
            assert late > 0, f"q{qid}: v6 date not earlier than context date"
            fixed[qid] = late
    print(f"Part-1-fixed questions (context date -> v6 event date): {len(fixed)}")
    assert len(fixed) == 23, f"expected 23 fixed, got {len(fixed)}"

    by_round = defaultdict(list)
    for qid in sorted(truth):
        c = ctx[qid]
        by_round[(c["season"], c["round_label"])].append(c)
    assert len(by_round) == 28, f"expected 28 rounds, got {len(by_round)}"

    OUT.mkdir(parents=True, exist_ok=True)
    total_dropped = 0
    for (season, rlabel) in sorted(by_round, key=lambda k: (k[0], by_round[k][0]["trace_date"])):
        cs = sorted(by_round[(season, rlabel)], key=lambda c: c["q_id"])
        trace_date = cs[0]["trace_date"]
        assert all(c["trace_date"] == trace_date for c in cs), (
            f"S{season} {rlabel}: mixed trace dates")
        questions = []
        for c in cs:
            qid = c["q_id"]
            rdate = truth[qid]["round_date"]
            last3, dropped = filter_last3(c["player_last3"], rdate, qid)
            total_dropped += dropped
            q = {
                "q_id": qid,
                "player": c["player"],
                "round_date": rdate,
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
            elif qid in fixed:
                q["round_date_override"] = {
                    "trace_date": c["trace_date"],
                    "reason": (
                        f"Part 1 testset-v6 fixed round date from "
                        f"{c['date']} to event date {rdate} "
                        f"({fixed[qid]} calendar days late); "
                        f"prediction point = event date."
                    ),
                }
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
        name = f"questions-round8-S{season}-{rlabel}.json"
        (OUT / name).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        print(f"{name}: {len(cs)} questions (q_ids {[c['q_id'] for c in cs]})")
    print(f"player_last3 stale entries dropped total: {total_dropped}")

    # ---- Pre-issue checks on the files as written ----
    all_ids = []
    counts = defaultdict(int)
    failures = []
    for f in sorted(OUT.glob("questions-round8-*.json")):
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
            if q["q_id"] in fixed and "round_date_override" not in q:
                failures.append(
                    f"{f.name} q{q['q_id']}: fixed question missing "
                    f"round_date_override")
    if set(all_ids) != set(truth):
        failures.append(
            f"q_id set mismatch: missing {sorted(set(truth) - set(all_ids))}, "
            f"extra {sorted(set(all_ids) - set(truth))}")
    if len(all_ids) != 98:
        failures.append(f"total questions {len(all_ids)} != 98")
    banned_total = {k: counts.get(k, 0) for k in sorted(BANNED_FIELDS)}
    print("banned-field counts (exact JSON field names):", banned_total)
    if any(banned_total.values()):
        failures.append(f"banned fields present: "
                        f"{ {k: v for k, v in banned_total.items() if v} }")
    print(f"rounds: {len(list(OUT.glob('questions-round8-*.json')))}, "
          f"questions: {len(all_ids)}, unique q_ids: {len(set(all_ids))}")
    if failures:
        print("PRE-ISSUE CHECKS FAILED:")
        for f_ in failures:
            print("  FAIL:", f_)
        sys.exit(1)
    print("PRE-ISSUE CHECKS PASSED: 98-ID set exact, banned fields all 0, "
          "round_dates match testset-v6, player_last3 all before round_date, "
          "23 fixed questions carry round_date_override.")


if __name__ == "__main__":
    main()
