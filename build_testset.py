"""Build testset-v2.json from the two reviews.

Inputs (runs/testset-redesign-vision1-2026-11-22/):
  old83-review.json       worker 1: keep/drop per old question + event_real_date + source
  unknown151-review.json  worker 2: 6 candidates from the unknown pool
  event_dates.json        round-5 date-fix table (event_name per old q_idx)
  test83.json             original 83 questions (round_date, action text)

Rules (coordinator decisions):
  - Old kept 40, minus q58 (duplicate of q65: same event, same player,
    same kind, Bloomberg 2026-11-17 Aolani loan report) -> 39.
  - New candidates: all 6 kept. ALI/TCE real dates after the round date
    are fine: the real date is the fact cutoff (round-5 precedent).
  - Total 45. No padding to 140 (honest count).
  - A/B split: stratified by kind, alternating within kind by
    (round, player) order; totals balanced to within 1.
"""
import json
from collections import Counter, defaultdict

RUNS = "runs/testset-redesign-vision1-2026-11-22"

def load(name):
    with open(f"{RUNS}/{name}", encoding="utf-8") as f:
        return json.load(f)

old_review = load("old83-review.json")
test83 = load("test83.json")
unknown = load("unknown151-review.json")
event_dates = {e["q_idx"]: e for e in load("event_dates.json")}

# --- old 83: keep 40, drop q58 as duplicate of q65 ---
DROP_DUP = {58}
questions = []
for r in old_review:
    if r["verdict"] != "keep":
        continue
    q = r["q_idx"]
    if q in DROP_DUP:
        continue
    t = test83[q]
    ed = event_dates.get(q, {})
    questions.append({
        "season": t["season"],
        "round_label": t["round_label"],
        "round_date": t["date"],
        "event_real_date": int(r["event_real_date"]),
        "event_name": ed.get("event_name") or t["action"],
        "player": t["player"],
        "kind": t["kind"],
        "action": t["action"],
        "source": r.get("source", ""),
        "origin": "old83",
        "old_q_idx": q,
    })

# --- new 6 from the unknown pool ---
# round_date: look up the round date from test83 by (season, round_label)
round_date = {}
for t in test83:
    round_date[(t["season"], t["round_label"])] = t["date"]
# S4 rounds not in test83 keep their round dates from the trace; fall back:
# S4 1-2 -> 20250121, S4 4-1 -> 20250801 (test83 round dates)
for c in unknown["candidates"]:
    key = (c["season"], c["round"])
    questions.append({
        "season": c["season"],
        "round_label": c["round"],
        "round_date": round_date.get(key),
        "event_real_date": int(c["event_real_date"]),
        "event_name": c["action"],
        "player": c["player"],
        "kind": c["kind"],
        "action": c["action"],
        "source": c.get("source", ""),
        "origin": "new",
        "old_q_idx": None,
    })

print("total questions:", len(questions))
print("origins:", Counter(q["origin"] for q in questions))
print("kinds:", Counter(q["kind"] for q in questions).most_common())
print("rounds:", Counter(f"S{q['season']} {q['round_label']}" for q in questions).most_common())
assert len(questions) == 45, len(questions)
assert all(q["round_date"] is not None for q in questions), "missing round_date"
assert all(q["event_real_date"] for q in questions), "missing event_real_date"

# --- A/B split: stratified by kind and round ---
# Sort by (kind, round, player), assign A/B by alternating global index.
# Each kind with 2+ questions and each round with 2+ questions should end
# up in both sets. If a round is one-sided, swap two same-kind questions
# (kind counts unchanged; donor round keeps >=1 in its set).
questions.sort(key=lambda q: (q["kind"], q["round_label"], q["player"]))
for i, q in enumerate(questions):
    q["split"] = "A" if i % 2 == 0 else "B"

def round_counts():
    rc = defaultdict(Counter)
    for q in questions:
        rc[f"S{q['season']} {q['round_label']}"][q["split"]] += 1
    return rc

# Fix one-sided rounds (2+ questions, all in one set).
# Pass 1: swap two same-kind questions (kind counts unchanged; donor round
# keeps >=1 in its set). Pass 2: if a round's questions are all singleton
# kinds, flip one to the other set (a singleton kind is whole in one set
# by definition, so flipping it breaks no kind balance).
kind_n = Counter(q["kind"] for q in questions)
for _ in range(20):
    rc = round_counts()
    one_sided = [r for r, c in rc.items() if sum(c.values()) >= 2 and (c["A"] == 0 or c["B"] == 0)]
    if not one_sided:
        break
    fixed_any = False
    for rnd in one_sided:
        in_round = [q for q in questions if f"S{q['season']} {q['round_label']}" == rnd]
        if all(Counter(q["split"] for q in in_round)[q["split"]] == len(in_round) for q in in_round):
            pass
        big = in_round[0]["split"]
        small = "B" if big == "A" else "A"
        swapped = False
        for q in in_round:
            if kind_n[q["kind"]] < 2:
                continue
            for q2 in questions:
                if q2["kind"] != q["kind"] or q2["split"] != small:
                    continue
                r2 = f"S{q2['season']} {q2['round_label']}"
                if r2 == rnd:
                    continue
                if rc[r2][small] >= 2:
                    q["split"], q2["split"] = small, big
                    swapped = True
                    fixed_any = True
                    break
            if swapped:
                break
        if swapped:
            continue
        # Pass 2: flip a singleton-kind question in this round.
        for q in in_round:
            if kind_n[q["kind"]] == 1:
                q["split"] = small
                fixed_any = True
                break
    if not fixed_any:
        break

for i, q in enumerate(questions):
    q["q_id"] = i
print("split counts:", Counter(q["split"] for q in questions))
# verify stratification
by_kind2 = defaultdict(list)
for q in questions:
    by_kind2[q["kind"]].append(q)
for kind, qs in sorted(by_kind2.items()):
    s2 = Counter(q["split"] for q in qs)
    flag = "" if len(qs) < 2 or (s2["A"] > 0 and s2["B"] > 0) else "  <-- SINGLETON, one set only"
    print(f"  kind {kind:>15} n={len(qs):>2} A={s2['A']} B={s2['B']}{flag}")
rb = defaultdict(Counter)
for q in questions:
    rb[f"S{q['season']} {q['round_label']}"][q["split"]] += 1
for rnd, s2 in sorted(rb.items()):
    flag = "" if sum(s2.values()) < 2 or (s2["A"] > 0 and s2["B"] > 0) else "  <-- ONE-SIDED"
    print(f"  round {rnd:>8} n={sum(s2.values()):>2} A={s2['A']} B={s2['B']}{flag}")
bad = [r for r, c in rb.items() if sum(c.values()) >= 2 and (c["A"] == 0 or c["B"] == 0)]
bad += [k for k, qs in by_kind2.items() if len(qs) >= 2 and (Counter(q["split"] for q in qs)["A"] == 0 or Counter(q["split"] for q in qs)["B"] == 0)]
assert not bad, f"one-sided multi groups remain: {bad}"

with open("testset-v2.json", "w", encoding="utf-8") as f:
    json.dump({
        "meta": {
            "name": "testset-v2 (vision-1 test set redesign)",
            "n": len(questions),
            "split": {"A": Counter(q["split"] for q in questions)["A"], "B": Counter(q["split"] for q in questions)["B"]},
            "split_method": "stratified: sorted by (kind, round, player), assigned A/B by alternating global index; one-sided rounds fixed by swapping two same-kind questions; each kind with 2+ questions and each round with 2+ questions appears in both sets",
            "old83_kept": 39,
            "old83_dropped": 43,
            "dedup": "q58 dropped as duplicate of q65 (same event, player, kind: Bloomberg 2026-11-17 Aolani loan)",
            "new_from_unknown": 6,
            "gap_to_140": 140 - len(questions),
        },
        "questions": questions,
    }, f, ensure_ascii=False, indent=2)
print("wrote testset-v2.json")
