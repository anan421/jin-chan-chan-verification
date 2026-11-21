"""Score round 5 (date fix) against search-first (60/83).

Steps:
1. Reproduce search-first 60/83 from predictions-full83.json + test83.json.
2. Score the date-fix predictions (13 per-round files merged).
3. Cross-tab per question: both correct / only new correct / only
   search-first correct / both wrong.
4. Break down by round and by cutoff changed/unchanged (event_dates.json),
   and by loosened vs tightened.
5. Mechanical date check: any fact in facts_used dated after the question's
   event_real_date is a violation (reported, not silently dropped).

Writes: runs/date-fix-round5-2026-11-22/scored-date-fix.json
        runs/date-fix-round5-2026-11-22/score-summary.json
"""
import json, os, glob, re
from collections import Counter, defaultdict

RUNDIR = "/home/hatch/workspace/verification-r5-date/runs/date-fix-round5-2026-11-22"
SRC = "/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22"

test83 = json.load(open(os.path.join(RUNDIR, "test83.json")))
# NOTE: test83 "idx" is the OLD trace position (326-557), not the question
# index. The question index is the POSITION in test83.json (0-82), which is
# what predictions-full83.json ("idx"/"q_idx") and the date-fix predictors
# ("q_idx") use. Join on position.
answers = {i: q for i, q in enumerate(test83)}
event_dates = {r["q_idx"]: r for r in json.load(open(os.path.join(RUNDIR, "event_dates.json")))}

# 1. reproduce search-first
sf = json.load(open(os.path.join(SRC, "predictions-full83.json")))
sf_pred = {}
for p in sf:
    idx = p.get("idx", p.get("q_idx"))
    assert idx is not None, p
    sf_pred[idx] = p["predicted_kind"]
sf_scored = json.load(open(os.path.join(SRC, "scored-full83.json")))
sf_correct_file = sum(1 for p in sf_scored if p.get("correct"))
sf_correct = sum(1 for idx, q in answers.items() if sf_pred.get(idx) == q["kind"])
print("search-first correct (recomputed):", sf_correct, "/ 83")
print("search-first correct (scored file):", sf_correct_file, "/ 83")
assert sf_correct == sf_correct_file == 60, "reproduction failed"

# 2. merge date-fix predictions
new_pred = {}
for fn in glob.glob(os.path.join(RUNDIR, "predictions-S*.json")):
    for p in json.load(open(fn)):
        assert p["q_idx"] not in new_pred, f"dup q_idx {p['q_idx']}"
        new_pred[p["q_idx"]] = p
print("date-fix predictions loaded:", len(new_pred))
assert len(new_pred) == 83, "missing predictions"
assert set(new_pred) == set(answers), "q_idx mismatch"

# 3. score
scored = []
for idx, q in answers.items():
    p = new_pred[idx]
    ed = event_dates[idx]
    scored.append({
        "q_idx": idx,
        "round": f"S{q['season']} {q['round_label']}",
        "player": q["player"],
        "actual_kind": q["kind"],
        "search_first_kind": sf_pred[idx],
        "search_first_correct": sf_pred[idx] == q["kind"],
        "date_fix_kind": p["predicted_kind"],
        "date_fix_correct": p["predicted_kind"] == q["kind"],
        "confidence": p.get("confidence"),
        "cutoff_changed": ed["changed"],
        "round_date": ed["round_date"],
        "event_real_date": ed["event_real_date"],
        "loosened": ed["changed"] and ed["event_real_date"] > ed["round_date"],
        "tightened": ed["changed"] and ed["event_real_date"] < ed["round_date"],
        "facts_used": p.get("facts_used", []),
        "reasoning": p.get("reasoning", ""),
    })
new_correct = sum(1 for s in scored if s["date_fix_correct"])
print("date-fix correct:", new_correct, "/ 83")

# cross-tab
ct = Counter()
for s in scored:
    ct[(s["search_first_correct"], s["date_fix_correct"])] += 1
print("both correct:", ct[(True, True)])
print("only date-fix correct:", ct[(False, True)])
print("only search-first correct:", ct[(True, False)])
print("both wrong:", ct[(False, False)])

# breakdown by round
by_round = defaultdict(lambda: [0, 0, 0, 0])  # sf, new, n, changed
for s in scored:
    r = by_round[s["round"]]
    r[0] += s["search_first_correct"]
    r[1] += s["date_fix_correct"]
    r[2] += 1
    r[3] += s["cutoff_changed"]
print("\nby round (search-first / date-fix / n / cutoff-changed):")
for r in sorted(by_round):
    print(f"  {r:8s} {by_round[r][0]:2d} / {by_round[r][1]:2d} / {by_round[r][2]:2d} / {by_round[r][3]:2d}")

# breakdown by cutoff group
for name, pred in [("cutoff changed (30)", lambda s: s["cutoff_changed"]),
                   ("cutoff unchanged (53)", lambda s: not s["cutoff_changed"]),
                   ("loosened (18)", lambda s: s["loosened"]),
                   ("tightened (12)", lambda s: s["tightened"])]:
    g = [s for s in scored if pred(s)]
    print(f"{name}: search-first {sum(s['search_first_correct'] for s in g)}/{len(g)}, "
          f"date-fix {sum(s['date_fix_correct'] for s in g)}/{len(g)}")

json.dump(scored, open(os.path.join(RUNDIR, "scored-date-fix.json"), "w"),
          ensure_ascii=False, indent=1)

# 5. mechanical date check on facts_used
def parse_date(d):
    if d is None:
        return None
    s = str(d).strip()
    if s.startswith("<") or s.startswith(">"):
        return None
    m = re.match(r"^(\d{4})[-/]?(\d{2})[-/]?(\d{2})", s)
    if not m:
        return None
    return int(m.group(1) + m.group(2) + m.group(3))

violations = []
for s in scored:
    erd = s["event_real_date"]
    for f in s["facts_used"]:
        fd = parse_date(f.get("date"))
        if fd is not None and fd > erd:
            violations.append({
                "q_idx": s["q_idx"], "round": s["round"], "player": s["player"],
                "event_real_date": erd, "fact_date": fd,
                "fact": f.get("fact"), "source": f.get("source"),
            })
print("\nfacts dated after the question's event_real_date:", len(violations))
for v in violations:
    print(f"  q{v['q_idx']} {v['round']} {v['player']}: fact {v['fact_date']} > cutoff {v['event_real_date']}: {str(v['fact'])[:100]}")

summary = {
    "search_first": sf_correct,
    "date_fix": new_correct,
    "n": 83,
    "both_correct": ct[(True, True)],
    "only_date_fix": ct[(False, True)],
    "only_search_first": ct[(True, False)],
    "both_wrong": ct[(False, False)],
    "date_violations": len(violations),
    "by_round": {r: {"search_first": v[0], "date_fix": v[1], "n": v[2], "cutoff_changed": v[3]}
                 for r, v in sorted(by_round.items())},
}
json.dump(summary, open(os.path.join(RUNDIR, "score-summary.json"), "w"),
          ensure_ascii=False, indent=1)
json.dump(violations, open(os.path.join(RUNDIR, "date-violations.json"), "w"),
          ensure_ascii=False, indent=1)
print("\nwrote scored-date-fix.json, score-summary.json, date-violations.json")
