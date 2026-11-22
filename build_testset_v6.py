#!/usr/bin/env python3
"""Assemble testset-v6.json: testset-v5 (99) minus q79, plus 23 round-date fixes.

Usage: python3 build_testset_v6.py
Reads:
  - testset-v5.json (99 questions, tracked)
Writes (tracked):
  - testset-v6.json: 98 questions, q_id NOT renumbered (0-78, 80-98;
    q79 is absent). Splits are kept as in v5 (no re-split: removing one
    B question leaves A 50 / B 48, and every kind with 2+ questions is
    still on both sides -- asserted below).

Task 1 -- remove q79 (S5 5-1, MUSK, spacex_xai, "xAI Grok 4.8 soft launch",
event 20261118). Source is only a Musk X post: no xAI official press
release, no API release, no benchmark. Gu approved removal under the
official-announcement standard. ONLY the question is removed: the S5
move (trace_idx 511) stays, trace stays 558 moves, data.json / hp / gold
are untouched.

Task 2 -- fix 23 round_date > event_real_date violations (calendar days,
never YYYYMMDD integer subtraction). Fix method, same as round-6 Part 1:
round_date := event_real_date (prediction point moves to the event day),
each fixed question carries a round_date_note. event_real_date is NOT
changed for any of the 23 (values match the round-6 design doc table,
design/experiment-vision6-round6.md, verified against v5 before fixing).
S5 1-1 questions keep their per-event dates (no single true date);
nothing is unified to one date.

S5 was re-opened by Gu's decision (a sealed season re-opened); this
test-set repair does not change any S5 move, hp or gold.
"""
import json
from collections import Counter
from datetime import date

V5 = "testset-v5.json"
V6 = "testset-v6.json"

REMOVE_QID = 79

# (q_id, player, kind, old round_date, event_real_date, days late by calendar)
DATE_FIXES = [
    (40, "MUSK", "financing", 20251201, 20250701, 153),
    (91, "ALI", "tongyi", 20250801, 20250429, 94),
    (47, "GOOG", "gemini", 20240501, 20240215, 76),
    (28, "ANTH", "claude", 20250801, 20250522, 71),
    (27, "ANTH", "claude", 20240501, 20240304, 58),
    (34, "BYTE", "doubao", 20250801, 20250611, 51),
    (48, "GOOG", "gemini", 20250801, 20250617, 45),
    (69, "HUAWEI", "pangu", 20250801, 20250620, 42),
    (41, "ORCL", "financing", 20251201, 20251023, 39),
    (54, "TCE", "hunyuan", 20250801, 20250627, 35),
    (77, "MUSK", "spacex_xai", 20240501, 20240328, 34),
    (98, "BIDU", "wenxin", 20250801, 20250630, 32),
    (76, "MUSK", "spacex_xai", 20231201, 20231104, 27),
    (29, "MUSK", "colossus", 20240701, 20240605, 26),
    (89, "ALI", "tongyi", 20240301, 20240205, 25),
    (78, "MUSK", "spacex_xai", 20250801, 20250709, 23),
    (45, "GOOG", "gemini", 20230301, 20230208, 21),
    (60, "META", "llama", 20240501, 20240418, 13),
    (85, "ORCL", "stargate", 20250801, 20250722, 10),
    (30, "BYTE", "datacenter", 20250121, 20250115, 6),
    (7, "BYTE", "bis_rule", 20261118, 20261116, 2),
    (4, "ANTH", "anthropic_ipo", 20261121, 20261120, 1),
    (88, "ALI", "tongyi", 20231201, 20231130, 1),
]


def cal_days(a, b):
    """Calendar days from b to a (a, b are YYYYMMDD ints)."""
    da = date(a // 10000, (a // 100) % 100, a % 100)
    db = date(b // 10000, (b // 100) % 100, b % 100)
    return (da - db).days


def fmt(d):
    return "%04d-%02d-%02d" % (d // 10000, (d // 100) % 100, d % 100)


def main():
    v5 = json.load(open(V5))
    questions = v5["questions"]
    assert len(questions) == 99, "v5 must have 99 questions, got %d" % len(questions)
    by_id = {q["q_id"]: q for q in questions}
    assert len(by_id) == 99, "v5 q_id not unique"

    # --- Task 1: remove q79 ---
    q79 = by_id[REMOVE_QID]
    assert q79["player"] == "MUSK" and q79["kind"] == "spacex_xai", "q79 identity mismatch"
    assert q79["split"] == "B" and int(q79["event_real_date"]) == 20261118, "q79 mismatch"
    assert q79["season"] == 5 and q79["round_label"] == "5-1", "q79 round mismatch"
    assert q79["trace_idx"] == 511, "q79 trace_idx mismatch"
    assert "X" in q79["source"] and "无 xAI 官方新闻稿" in q79["source"], "q79 source mismatch"
    print("remove q79: %s %s %s event %s (split B, trace_idx 511)" % (
        q79["player"], q79["kind"], q79["event_name"], q79["event_real_date"]))
    kept = [dict(q) for q in questions if q["q_id"] != REMOVE_QID]
    assert len(kept) == 98
    assert sorted(q["q_id"] for q in kept) == list(range(0, 79)) + list(range(80, 99)), \
        "q_id renumbered or wrong set"
    kept_by_id = {q["q_id"]: q for q in kept}

    # --- Task 2: 23 date fixes ---
    for (qid, player, kind, old_rd, ev, days) in DATE_FIXES:
        q = kept_by_id[qid]
        assert q["player"] == player and q["kind"] == kind, \
            "date-fix target mismatch at q_id %d" % qid
        assert int(q["round_date"]) == old_rd, \
            "q%d round_date %s != expected %s" % (qid, q["round_date"], old_rd)
        assert int(q["event_real_date"]) == ev, \
            "q%d event_real_date %s != expected %s" % (qid, q["event_real_date"], ev)
        assert cal_days(old_rd, ev) == days, \
            "q%d calendar days %d != expected %d (never YYYYMMDD subtraction)" % (
                qid, cal_days(old_rd, ev), days)
        assert "round_date_note" not in q or not q.get("round_date_note"), \
            "q%d already has a round_date_note" % qid
        q["round_date"] = ev
        day_word = "day" if days == 1 else "days"
        q["round_date_note"] = (
            "Round 7 (2026-11-22): round date was %d %s AFTER the event "
            "(%s) by calendar days; prediction point must be on/before the "
            "event date, so round_date = event date %s." % (
                days, day_word, fmt(ev), ev))
        print("date fix: q%d %s %s round_date %s -> %s (%d calendar days)" % (
            qid, player, kind, old_rd, ev, days))

    # --- invariants ---
    split = Counter(q["split"] for q in kept)
    assert split == {"A": 50, "B": 48}, "split must be A 50 / B 48, got %s" % dict(split)
    # no other field changed vs v5 except round_date / round_date_note on the 23
    for q in kept:
        old = by_id[q["q_id"]]
        for k, v in old.items():
            if k in ("round_date", "round_date_note"):
                continue
            assert q.get(k) == v, "q%d field %s changed" % (q["q_id"], k)
    # every kind with 2+ questions still appears on both sides
    by_kind = {}
    for q in kept:
        by_kind.setdefault(q["kind"], Counter())[q["split"]] += 1
    for kind, c in sorted(by_kind.items()):
        if sum(c.values()) >= 2:
            assert c["A"] >= 1 and c["B"] >= 1, \
                "kind %s one-sided after removal: %s" % (kind, dict(c))
    sx = sorted((q["q_id"], q["split"]) for q in kept if q["kind"] == "spacex_xai")
    assert sx == [(75, "B"), (76, "A"), (77, "B"), (78, "A")], \
        "spacex_xai must be q75(B) q76(A) q77(B) q78(A), got %s" % sx
    # full-set date scan: round_date must be on/before event_real_date, calendar days
    viol = [(q["q_id"], cal_days(int(q["round_date"]), int(q["event_real_date"])))
            for q in kept if int(q["round_date"]) > int(q["event_real_date"])]
    assert not viol, "round_date after event_real_date remains: %s" % viol
    for q in kept:
        assert cal_days(int(q["round_date"]), int(q["event_real_date"])) <= 0
    print("split: A %d / B %d" % (split["A"], split["B"]))
    print("spacex_xai: %s" % sx)
    print("full-set date scan: 0 violations (round_date <= event_real_date, calendar days)")

    meta = dict(v5["meta"])
    meta.update({
        "name": "testset-v6 (testset-v5 minus q79, 23 round-date fixes)",
        "n": 98,
        "split": {"A": 50, "B": 48},
        "gap_to_140": 42,
        "removed_q79": ("q79 S5 5-1 MUSK spacex_xai 'xAI Grok 4.8 soft launch' "
                        "20261118 removed 2026-11-22: source is only a Musk X post, "
                        "no xAI official press release, no API release, no benchmark; "
                        "removed under the official-announcement standard approved by Gu. "
                        "S5 move (trace_idx 511) untouched; trace stays 558 moves; "
                        "no renumbering (q79 absent, q_id 0-78, 80-98)."),
        "date_fixes_round7": ("23 questions: round_date set to event_real_date "
                              "(prediction point on the event day). Longest 153 days "
                              "(q40 MUSK financing); shortest 1 day (q4, q88). "
                              "Calendar days throughout, never YYYYMMDD subtraction. "
                              "Each fixed question carries round_date_note. "
                              "q7 and q30 were already excluded from the round-6 clean "
                              "score but their dates are fixed here. "
                              "S5 1-1 keeps per-event dates (no single true date)."),
        "note": ("S5 re-opened by Gu's decision (a sealed season re-opened); "
                 "this repair changes no S5 move, hp or gold. Trace stays 558 moves. "
                 "v5 note kept: A/B splits are re-derived in v5, so v5 splits differ "
                 "from v4 splits; v6 keeps v5 splits (one B question removed)."),
    })
    with open(V6, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "questions": kept}, f, ensure_ascii=False, indent=1)
    print("wrote %s: n=%d, A %d, B %d, gap to 140: %d" % (
        V6, len(kept), split["A"], split["B"], meta["gap_to_140"]))


if __name__ == "__main__":
    main()
