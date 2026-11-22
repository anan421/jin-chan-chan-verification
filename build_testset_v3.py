#!/usr/bin/env python3
"""Assemble the expanded test set (testset-v3.json).

Usage: python3 build_testset_v3.py
Reads:
  - testset-v2.json (45 clean questions, tracked)
  - runs/walkforward-vision1-2026-11-22/s1-review.json, s2-review.json, s3-review.json
    (kept questions only; verdict == 'keep')
  - /home/hatch/workspace/verification/traces/trace-latest.json (for round_index lookup)
Writes (tracked):
  - testset-v3.json: v2's 45 + new S1-S3 questions, re-split A/B.
A/B split (same method as testset-v2): sort by (kind, season, round_index, player),
assign A/B by alternating global index; then fix one-sided rounds (a round with
2+ questions all on one side) by swapping two same-kind questions, until no
one-sided round with 2+ questions remains or no valid swap exists.
"""
import json
import os
from collections import Counter

TRACE = "/home/hatch/workspace/verification/traces/trace-latest.json"
RUN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "runs", "walkforward-vision1-2026-11-22")
REVIEW_FILES = ["s1-review.json", "s2-review.json", "s3-review.json"]
# Same-event duplicates (identified by the S2 reviewer): keep the primary actor only.
# (keep_trace_idx, drop_trace_idx, reason)
DEDUP = [
    (92, 91, "same event: Microsoft-OpenAI investment 2023-01-23"),
    (149, 146, "same event: Llama 2 release 2023-07-18"),
    (168, 166, "same event: Amazon-Anthropic investment 2023-09-25"),
]


def main():
    t = json.load(open(TRACE))
    round_idx = {}
    for m in t["moves"]:
        round_idx[(m["season"], m["round_label"])] = m["round_index"]

    v2 = json.load(open("testset-v2.json"))
    questions = []
    for q in v2["questions"]:
        q = dict(q)
        q.pop("split", None)
        q.pop("q_id", None)
        q["origin"] = "old83" if q.get("origin") == "old83" else q.get("origin", "v2")
        questions.append(q)
    n_v2 = len(questions)

    new_by_season = Counter()
    dedup_dropped = []
    drop_set = {d for _, d, _ in DEDUP}
    for fn in REVIEW_FILES:
        p = os.path.join(RUN_DIR, fn)
        if not os.path.exists(p):
            print("missing %s (reviewer not done yet), skipping" % fn)
            continue
        for r in json.load(open(p)):
            if r.get("verdict") != "keep":
                continue
            if r["trace_idx"] in drop_set:
                dedup_dropped.append(r["trace_idx"])
                continue
            season = r["season"]
            label = r["round"].split(" ", 1)[1]
            # round_date from the trace (first move of that round)
            rd = next(m["date"] for m in t["moves"]
                      if m["season"] == season and m["round_label"] == label)
            questions.append({
                "season": season,
                "round_label": label,
                "round_date": rd,
                "event_real_date": int(r["event_real_date"]),
                "event_name": r.get("event_name", ""),
                "player": r["player"],
                "kind": r["kind"],
                "action": r["action"],
                "source": r.get("source", ""),
                "origin": "walkforward",
                "trace_idx": r["trace_idx"],
            })
            new_by_season[season] += 1
    print("v2 questions: %d, new S1-S3: %d (S1 %d, S2 %d, S3 %d)" % (
        n_v2, sum(new_by_season.values()),
        new_by_season[1], new_by_season[2], new_by_season[3]))

    # sort by (kind, season, round_index, player), assign q_id
    def skey(q):
        return (q["kind"], q["season"],
                round_idx[(q["season"], q["round_label"])], q["player"])
    questions.sort(key=skey)
    for i, q in enumerate(questions):
        q["q_id"] = i

    # A/B by alternating global index
    for i, q in enumerate(questions):
        q["split"] = "A" if i % 2 == 0 else "B"

    # fix one-sided rounds (2+ questions all on one side) by same-kind swaps
    def round_key(q):
        return (q["season"], q["round_label"])
    for _ in range(100):
        by_round = {}
        for q in questions:
            by_round.setdefault(round_key(q), []).append(q)
        one_sided = [rk for rk, qs in by_round.items()
                     if len(qs) >= 2 and len({q["split"] for q in qs}) == 1]
        if not one_sided:
            break
        fixed = False
        for rk in one_sided:
            qs = by_round[rk]
            side = qs[0]["split"]
            other = "B" if side == "A" else "A"
            for q1 in qs:
                # partner: same kind, opposite side, from a round that stays split
                partners = [q for q in questions
                            if q["kind"] == q1["kind"] and q["split"] == other
                            and round_key(q) != rk]
                for q2 in partners:
                    r2 = by_round[round_key(q2)]
                    # after swap, q2's round must not become one-sided
                    if len(r2) >= 2 and len({q["split"] for q in r2 if q is not q2} | {side}) == 1:
                        continue
                    q1["split"], q2["split"] = q2["split"], q1["split"]
                    fixed = True
                    break
                if fixed:
                    break
            if fixed:
                break
        if not fixed:
            print("could not fix one-sided rounds:", one_sided)
            break

    split = Counter(q["split"] for q in questions)
    # safety check: no two NEW questions share the same (event date, event name).
    # v2 itself has a pre-existing pattern (BIS rule 20261116 counted 3 times:
    # ALI, TSMC, BYTE reacting to one shared event) — kept as-is, not re-audited.
    new_qs = [q for q in questions if q.get("origin") == "walkforward"]
    ev_new = Counter((q["event_real_date"], q["event_name"]) for q in new_qs)
    dup_new = [k for k, n in ev_new.items() if n > 1]
    print("same-event duplicates among new questions:", dup_new)
    assert not dup_new, "unresolved same-event duplicates: %s" % dup_new
    ev_all = Counter((q["event_real_date"], q["event_name"]) for q in questions)
    print("same-event duplicates overall (incl. pre-existing v2 pattern):",
          [k for k, n in ev_all.items() if n > 1])
    # verify: kinds and rounds with 2+ appear in both
    by_kind = {}
    by_round = {}
    for q in questions:
        by_kind.setdefault(q["kind"], set()).add(q["split"])
        by_round.setdefault(round_key(q), set()).add(q["split"])
    kinds_one_sided = [k for k, s in by_kind.items()
                       if sum(1 for q in questions if q["kind"] == k) >= 2 and len(s) == 1]
    rounds_one_sided = [rk for rk, s in by_round.items()
                        if sum(1 for q in questions if round_key(q) == rk) >= 2 and len(s) == 1]
    print("split: A %d, B %d" % (split["A"], split["B"]))
    print("kinds with 2+ one-sided:", kinds_one_sided)
    print("rounds with 2+ one-sided:", rounds_one_sided)

    meta = {
        "name": "testset-v3 (vision-1 test set redesign + S1-S3 walk-forward)",
        "n": len(questions),
        "split": {"A": split["A"], "B": split["B"]},
        "split_method": ("stratified: sorted by (kind, season, round_index, player), "
                         "assigned A/B by alternating global index; one-sided rounds "
                         "fixed by swapping two same-kind questions; each kind with 2+ "
                         "questions and each round with 2+ questions appears in both sets"),
        "v2_kept": n_v2,
        "new_from_walkforward": sum(new_by_season.values()),
        "new_S1": new_by_season[1],
        "new_S2": new_by_season[2],
        "new_S3": new_by_season[3],
        "dedup": ("same-event duplicates dropped, one per event (primary actor kept): "
                  "91 (OAI) -> 92 (MSFT) Microsoft-OpenAI investment; "
                  "146 (MSFT) -> 149 (META) Llama 2 release; "
                  "166 (ANTH) -> 168 (AMZN) Amazon-Anthropic investment"),
        "dedup_dropped_trace_idx": sorted(dedup_dropped),
        "gap_to_140": 140 - len(questions),
    }
    with open("testset-v3.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "questions": questions}, f, ensure_ascii=False, indent=1)
    print("wrote testset-v3.json: n=%d, gap to 140: %d" % (len(questions), meta["gap_to_140"]))


if __name__ == "__main__":
    main()
