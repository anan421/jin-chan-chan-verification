#!/usr/bin/env python3
"""Assemble testset-v7.json: testset-v6 (98) + verified new questions from
the coverage plan (design/testset-coverage-plan.md, 119 candidates).

Usage: python3 build_testset_v7.py
Reads:
  - testset-v6.json (98 questions, tracked; q_id 0-78, 80-98, q79 absent)
  - new_questions/*.json (one file per verification agent; each has
    {"category": ..., "questions": [...], "excluded": [...]})
Writes (tracked):
  - testset-v7.json: 98 + N questions. Old 98 keep q_id / split / every
    field exactly. New questions get q_id 99+ (in (kind, event date,
    player) order), split assigned by stratified alternation over the
    new questions only (sorted by kind, season, round_index, player),
    starting with B so the final total lands near A 109 / B 108.

Round assignment (central, deterministic; overrides any hint):
  Rounds come from the trace (raw-trace-real.json): each (season,
  round_label) has a round_index and a date (round start).
  - Exact-date event (YYYYMMDD = D): assign the LAST round (by date,
    tie-break season then round_index) whose date <= D.
    round_date = that round's date.
  - Month-only event (YYYYMM): assign the LAST round whose date <
    YYYYMM01 (i.e. before that month). round_date = that round's date.
    event_real_date stays 6-digit YYYYMM; for validation it is treated
    as YYYYMM01 (the event could be any day in the month, so the
    prediction point must be on/before the 1st to guarantee no leak).
  - Year-only event (YYYY): assign the LAST round whose date < YYYY0101.
    event_real_date stays 4-digit YYYY; validation treats it as YYYY0101.

Invariants asserted:
  - Old 98 questions byte-identical in every field (except nothing).
  - New q_id unique, 99+, no renumbering.
  - round_date <= event_real_date for every question (calendar days;
    month/year-only events use the 1st-of-period rule above).
  - No duplicate (event_real_date, event_name).
  - Every kind with 2+ questions appears on both splits.
  - Split total is A 109 / B 108 (or as close as the new-question count
    allows; if fewer than 119 verify, the split is recomputed and
    reported, not forced).
"""
import glob
import json
import os
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
V6 = os.path.join(HERE, "testset-v6.json")
V7 = os.path.join(HERE, "testset-v7.json")
NEW_DIR = os.path.join(HERE, "new_questions")
TRACE = os.path.join(HERE, "raw-trace-real.json")

# --- round table from the trace -------------------------------------------
def load_rounds():
    t = json.load(open(TRACE))
    moves = t.get("moves", t if isinstance(t, list) else [])
    rounds = {}
    for m in moves:
        key = (m["season"], m["round_label"])
        if key not in rounds:
            rounds[key] = (m["round_index"], int(m["date"]))
    # sort by (date, season, round_index)
    ordered = sorted(
        ((season, label, idx, d) for (season, label), (idx, d) in rounds.items()),
        key=lambda r: (r[3], r[0], r[2]),
    )
    return ordered

ROUNDS = load_rounds()

def assign_round(event_real_date):
    """Return (season, round_label, round_date) for an event date.
    event_real_date may be YYYYMMDD (8-digit), YYYYMM (6-digit) or
    YYYY (4-digit)."""
    s = str(event_real_date)
    if len(s) == 8:
        d = int(s)
        cands = [r for r in ROUNDS if r[3] <= d]
        assert cands, "no round on/before event date %s" % s
        season, label, idx, rdate = cands[-1]
        return season, label, rdate
    if len(s) == 6:
        # month only: round must be strictly before the 1st of that month
        first = int(s + "01")
        cands = [r for r in ROUNDS if r[3] < first]
        assert cands, "no round before month %s" % s
        season, label, idx, rdate = cands[-1]
        return season, label, rdate
    if len(s) == 4:
        first = int(s + "0101")
        cands = [r for r in ROUNDS if r[3] < first]
        assert cands, "no round before year %s" % s
        season, label, idx, rdate = cands[-1]
        return season, label, rdate
    raise ValueError("bad event_real_date %r" % (event_real_date,))

def effective_date(event_real_date):
    """Date used for the round_date <= event check: exact day if 8-digit,
    else the 1st of the month / year."""
    s = str(event_real_date)
    if len(s) == 8:
        return int(s)
    if len(s) == 6:
        return int(s + "01")
    if len(s) == 4:
        return int(s + "0101")
    raise ValueError("bad event_real_date %r" % (event_real_date,))

def cal_days(a, b):
    da = date(a // 10000, (a // 100) % 100, a % 100)
    db = date(b // 10000, (b // 100) % 100, b % 100)
    return (da - db).days

def main():
    v6 = json.load(open(V6))
    old = v6["questions"]
    assert len(old) == 98, "v6 must have 98 questions, got %d" % len(old)
    old_by_id = {q["q_id"]: q for q in old}
    assert len(old_by_id) == 98, "v6 q_id not unique"
    assert 79 not in old_by_id, "q79 must stay absent"

    # --- collect verified new questions ---
    new_raw = []
    excluded = []
    files = sorted(glob.glob(os.path.join(NEW_DIR, "*.json")))
    assert files, "no new_questions/*.json found in %s" % NEW_DIR
    for f in files:
        d = json.load(open(f))
        cat = d.get("category", os.path.basename(f))
        for q in d.get("questions", []):
            q = dict(q)
            q["_file"] = os.path.basename(f)
            q["_category"] = cat
            new_raw.append(q)
        for e in d.get("excluded", []):
            excluded.append((cat, e))
    print("collected %d verified new questions from %d files" % (len(new_raw), len(files)))
    print("excluded: %d" % len(excluded))
    for cat, e in excluded:
        print("  excluded [%s]: %s -- %s" % (cat, e.get("event_name", "?"), e.get("reason", "?")))

    # --- validate each new question's fields ---
    seen = set()
    for q in new_raw:
        for k in ("event_name", "event_real_date", "player", "kind", "action", "source"):
            assert k in q and q[k] not in (None, ""), "missing/empty %s in %s" % (k, q.get("event_name"))
        ed = str(q["event_real_date"])
        assert len(ed) in (4, 6, 8) and ed.isdigit(), "bad event_real_date %r" % (q["event_real_date"],)
        # S5 only: real date must be <= 2026-11-21
        eff = effective_date(q["event_real_date"])
        assert eff <= 20261121, "event %s date %s after S5 cutoff 2026-11-21" % (q["event_name"], ed)
        key = (q["event_real_date"], q["event_name"])
        assert key not in seen, "duplicate (event_real_date, event_name): %s" % (key,)
        seen.add(key)
        # no duplicate against old questions either
        for oq in old:
            assert not (str(oq["event_real_date"]) == ed and oq["event_name"] == q["event_name"]), \
                "new question duplicates old q%d: %s" % (oq["q_id"], q["event_name"])

    # --- assign season / round_label / round_date / q_id ---
    # sort new questions deterministically: (kind, effective date, player, event_name)
    new_raw.sort(key=lambda q: (q["kind"], effective_date(q["event_real_date"]), q["player"], q["event_name"]))
    round_idx = {(s, l): i for (s, l, i, d) in ROUNDS}
    questions = [dict(q) for q in old]
    new_qs = []
    for i, q in enumerate(new_raw):
        season, label, rdate = assign_round(q["event_real_date"])
        nq = {
            "season": season,
            "round_label": label,
            "round_date": rdate,
            "event_real_date": q["event_real_date"],
            "event_name": q["event_name"],
            "player": q["player"],
            "kind": q["kind"],
            "action": q["action"],
            "source": q["source"],
            "origin": q.get("origin", "testset-complete"),
            "q_id": 99 + i,
        }
        # sanity: round_date <= effective event date
        assert rdate <= effective_date(q["event_real_date"]), \
            "round_date %s after event %s for %s" % (rdate, q["event_real_date"], q["event_name"])
        new_qs.append(nq)
    # split: stratified alternation over new questions only, sorted by
    # (kind, season, round_index, player); start with B so the total
    # lands near A 109 / B 108 when all 119 verify.
    order = sorted(new_qs, key=lambda q: (q["kind"], q["season"], round_idx[(q["season"], q["round_label"])], q["player"]))
    for j, q in enumerate(order):
        q["split"] = "B" if j % 2 == 0 else "A"
    questions.extend(new_qs)

    # --- invariants ---
    assert len(questions) == 98 + len(new_qs), "total mismatch"
    by_id = {q["q_id"]: q for q in questions}
    assert len(by_id) == len(questions), "q_id not unique"
    # old 98 unchanged
    for q in questions[:98]:
        o = old_by_id[q["q_id"]]
        assert q == o, "old q%d changed" % q["q_id"]
    # full-set date scan (calendar days; month/year-only use 1st-of-period)
    viol = []
    for q in questions:
        rd = int(q["round_date"])
        ed = effective_date(q["event_real_date"])
        if rd > ed:
            viol.append((q["q_id"], rd, ed, cal_days(rd, ed)))
    assert not viol, "round_date after event_real_date: %s" % viol
    # every kind with 2+ questions on both splits
    by_kind = {}
    for q in questions:
        by_kind.setdefault(q["kind"], Counter())[q["split"]] += 1
    one_sided = []
    for kind, c in sorted(by_kind.items()):
        if sum(c.values()) >= 2 and (c["A"] == 0 or c["B"] == 0):
            one_sided.append((kind, dict(c)))
    if one_sided:
        # fix by swapping the last question of each one-sided kind to the other side
        for kind, c in one_sided:
            target = "A" if c["A"] == 0 else "B"
            cands = [q for q in new_qs if q["kind"] == kind]
            assert cands, "one-sided kind %s has no new question to swap" % kind
            cands[-1]["split"] = target
            print("split fix: kind %s moved one question to %s" % (kind, target))
        by_kind = {}
        for q in questions:
            by_kind.setdefault(q["kind"], Counter())[q["split"]] += 1
        for kind, c in sorted(by_kind.items()):
            if sum(c.values()) >= 2:
                assert c["A"] >= 1 and c["B"] >= 1, "kind %s still one-sided: %s" % (kind, dict(c))
    split = Counter(q["split"] for q in questions)
    print("total: %d (old 98 + new %d)" % (len(questions), len(new_qs)))
    print("split: A %d / B %d" % (split["A"], split["B"]))
    print("kinds: %d total" % len(by_kind))
    for kind in sorted(by_kind):
        print("  %-16s %3d  (A %d / B %d)" % (kind, sum(by_kind[kind].values()), by_kind[kind]["A"], by_kind[kind]["B"]))
    print("full-set date scan: 0 violations (round_date <= event, calendar days; month/year-only use 1st-of-period)")

    meta = dict(v6["meta"])
    meta.update({
        "name": "testset-v7 (testset-v6 + coverage-plan completion, 119 candidates)",
        "n": len(questions),
        "split": {"A": split["A"], "B": split["B"]},
        "gap_to_140": max(0, 140 - len(questions)),
        "new_from_coverage_plan": len(new_qs),
        "excluded_from_coverage_plan": len(excluded),
        "note": ("testset-v7 adds the verified questions from the coverage plan "
                 "(design/testset-coverage-plan.md). Old 98 questions unchanged "
                 "(q_id / split / every field). New questions get q_id 99+ and "
                 "split by stratified alternation over the new questions only. "
                 "Season / round_label / round_date are assigned centrally from "
                 "the event date (last trace round on/before the event; month- "
                 "only events use the last round before that month, year-only "
                 "the last round before that year). Month-only dates stay YYYYMM, "
                 "year-only stay YYYY; validation treats them as the 1st of the "
                 "period. No S6 events (all real dates <= 2026-11-21). "
                 "S6 pool / monitor untouched. Trace stays 558 moves."),
    })
    with open(V7, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "questions": questions}, f, ensure_ascii=False, indent=1)
    print("wrote %s: n=%d, A %d, B %d" % (V7, len(questions), split["A"], split["B"]))

if __name__ == "__main__":
    main()
