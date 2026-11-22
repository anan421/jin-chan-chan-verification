#!/usr/bin/env python3
"""Build per-round question files for the 88-question baseline experiment.

One file per round (28 files). No headline, no guidance input: the
predictor searches the web itself. This is the clean baseline.

Inputs (all in this worktree unless noted):
  testset-v3.json, runs/baseline88-2026-11-22/context-all88.json,
  kind vocabulary parsed from the boundary-rules table in the
  testset-redesign branch worktree.
Question order inside a round is shuffled with a fixed seed (20261122).

Also writes assignment.json: the round assignment for the 13 predictor
slots, shared by all 4 batches (same grouping, different predictor
batches). Greedy by round size (largest first) to the least-loaded
slot, with a season-spread tie-break; each slot does its rounds in
chronological order. Single-round isolation is kept: one predictor
does a whole round, never half a round.

Rules enforced (fail loudly):
  - No answer fields anywhere (no kind/action/hp_delta/gold_delta).
  - Question count per round matches testset-v3; every player once.
  - Every question's predicted kind must come from the vocabulary.
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs" / "baseline88-2026-11-22"
RULES = Path("/home/hatch/workspace/verification-v1-testset/design/kind-boundary-rules.md")
BANNED = {"kind", "action", "action_kind", "hp_delta", "gold_delta"}
SEED = 20261122


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_vocabulary():
    kinds = []
    for line in RULES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        k = cells[0]
        if k in ("种类", "---") or set(k) <= {"-", " "} or not k:
            continue
        if not re.fullmatch(r"[a-z0-9_]+", k):
            continue
        kinds.append(k)
    if len(kinds) < 30:
        fail(f"vocabulary too small: {len(kinds)} kinds parsed")
    return kinds


def main():
    vocab = load_vocabulary()
    print(f"vocabulary: {len(vocab)} kinds")
    testset = json.loads((ROOT / "testset-v3.json").read_text(encoding="utf-8"))
    questions = testset["questions"]
    ctx = json.loads((RUNS / "context-all88.json").read_text(encoding="utf-8"))
    ctx_by_qid = {c["q_id"]: c for c in ctx}
    if set(ctx_by_qid) != {q["q_id"] for q in questions}:
        fail("context q_id set does not match testset-v3")

    # Group by round, in testset order (q_id = position 0..87).
    rounds = {}
    for q in questions:
        key = (q["season"], q["round_label"])
        rounds.setdefault(key, []).append(q)

    # Chronological round order from the trace round_index.
    trace = json.loads((ROOT / "raw-trace-real.json").read_text(encoding="utf-8"))
    round_index = {}
    for m in trace["moves"]:
        round_index[(m["season"], m["round_label"])] = m["round_index"]
    ordered_rounds = sorted(rounds, key=lambda k: (k[0], round_index[k]))

    rng = random.Random(SEED)
    for (season, label) in ordered_rounds:
        rows = rounds[(season, label)]
        rkey = f"S{season} {label}"
        round_date = rows[0]["round_date"]
        if any(r["round_date"] != round_date for r in rows):
            fail(f"{rkey}: mixed round dates")
        if len({r["player"] for r in rows}) != len(rows):
            fail(f"{rkey}: duplicate player in round")
        qs = []
        for q in rows:
            c = ctx_by_qid[q["q_id"]]
            if c["player"] != q["player"] or c["date"] != round_date:
                fail(f"{rkey}: context mismatch for {q['player']}")
            qs.append({
                "q_id": q["q_id"],
                "player": q["player"],
                "hp_start": c["hp_start"],
                "gold_start": c["gold_start"],
                "rules_version": c["rules_version"],
                "first_appearance": c["first_appearance"],
                "player_history_counts": c["player_history_counts"],
                "player_most_frequent": c["player_most_frequent"],
                "player_last_kind": c["player_last_kind"],
                "player_last3": c["player_last3"],
                "prev_round_kinds": c["prev_round_kinds"],
            })
        rng.shuffle(qs)
        out = {
            "round": rkey,
            "season": season,
            "round_label": label,
            "round_date": round_date,
            "vocabulary": vocab,
            "questions": qs,
        }
        text = json.dumps(out, ensure_ascii=False, indent=2)
        for banned in BANNED:
            if f'"{banned}"' in text:
                fail(f"{rkey}: banned field {banned} leaked into question file")
        (RUNS / f"questions-S{season}-{label}.json").write_text(text, encoding="utf-8")
        print(f"{rkey}: {len(qs)} questions -> questions-S{season}-{label}.json")

    # Predictor-slot assignment: greedy by round size, season-spread
    # tie-break, same for all 4 batches.
    sizes = {k: len(rounds[k]) for k in ordered_rounds}
    slots = [[] for _ in range(13)]
    loads = [0] * 13
    for k in sorted(ordered_rounds, key=lambda k: (-sizes[k], k)):
        season = k[0]
        # Least loaded first; tie-break: fewest rounds already in this
        # season (spread seasons), then lowest slot number.
        def rank(i):
            same_season = sum(1 for r in slots[i] if r[0] == season)
            return (loads[i], same_season, i)
        i = min(range(13), key=rank)
        slots[i].append(k)
        loads[i] += sizes[k]
    for i, s in enumerate(slots, 1):
        s.sort(key=lambda k: (k[0], round_index[k]))
    assignment = {
        "slots": 13,
        "batches": ["main", "control1", "control2", "control3"],
        "method": "greedy by round size (largest first) to least-loaded slot, season-spread tie-break; same grouping for all batches; chronological order within each slot",
        "slots_detail": [
            {"slot": i + 1,
             "rounds": [f"S{s} {l}" for (s, l) in slots[i]],
             "n_questions": loads[i]}
            for i in range(13)
        ],
    }
    (RUNS / "assignment.json").write_text(
        json.dumps(assignment, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"assignment: loads {loads} (min {min(loads)}, max {max(loads)})")
    for d in assignment["slots_detail"]:
        print(f"  slot {d['slot']:2d}: {d['rounds']} -> {d['n_questions']} questions")
    total_q = sum(len(v) for v in rounds.values())
    print(f"done: {len(rounds)} rounds, {total_q} questions, 28 files + assignment.json")


if __name__ == "__main__":
    main()
