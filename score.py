"""Score the theme-person round-3 predictions against the 83-question answers.

Usage: python3 score.py
Reads:  test83.json (answers, from the search-first lane -- coordinator only),
        predictions-S<season>-<label>.json (13 files, one per round)
        predictions-full83.json (search-first lane, for the paired comparison)
Writes: runs/theme-person-round3-2026-11-22/scored-theme-person.json
"""
import json, os, glob
from collections import Counter

RUN = "/home/hatch/workspace/verification-r3-theme/runs/theme-person-round3-2026-11-22"
SRC = "/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22"
KINDS = ["anthropic_ipo", "ascend", "bis_rule", "blackwell", "capex", "chatgpt",
         "claude", "colossus", "doubao", "doubao_price_war", "energy", "financing",
         "gemini", "huang_resign", "hunyuan", "llama", "megaspeed", "msft_invest",
         "musk_table", "open_source", "overseas_rental", "pangu", "r1", "sec_probe",
         "spacex_xai", "stargate", "tongyi", "v3", "wenxin"]

test83 = json.load(open(os.path.join(SRC, "test83.json")))
answers = {i: q["kind"] for i, q in enumerate(test83)}

preds = {}
for f in sorted(glob.glob(os.path.join(RUN, "predictions-S*.json"))):
    for p in json.load(open(f)):
        assert p["q_idx"] not in preds, "duplicate q_idx %s" % p["q_idx"]
        assert p["predicted_kind"] in KINDS, "bad kind %s" % p["predicted_kind"]
        preds[p["q_idx"]] = p
print("predicted:", len(preds), "/ 83")
missing = [i for i in range(83) if i not in preds]
print("missing q_idx:", missing)

records = []
for i, q in enumerate(test83):
    p = preds.get(i)
    rec = {
        "q_idx": i, "season": q["season"], "round_label": q["round_label"],
        "player": q["player"], "date": q["date"],
        "actual_kind": q["kind"], "first_appearance": q["first_appearance"],
        "predicted_kind": p["predicted_kind"] if p else None,
        "confidence": p.get("confidence") if p else None,
        "theme": p.get("theme") if p else None,
        "role": p.get("role") if p else None,
        "correct": bool(p and p["predicted_kind"] == q["kind"]),
    }
    records.append(rec)

n = sum(r["correct"] for r in records)
print("theme-person score: %d/83 (%.1f%%)" % (n, 100.0 * n / 83))

# per-round
print("\nper round:")
for (s, lab) in sorted(set((r["season"], r["round_label"]) for r in records)):
    rs = [r for r in records if (r["season"], r["round_label"]) == (s, lab)]
    c = sum(r["correct"] for r in rs)
    print("  S%d %s: %d/%d" % (s, lab, c, len(rs)))

# first appearance vs repeat
for name, subset in [("first-appearance kind", [r for r in records if r["first_appearance"]]),
                     ("repeat kind", [r for r in records if not r["first_appearance"]])]:
    c = sum(r["correct"] for r in subset)
    print("%s: %d/%d" % (name, c, len(subset)))

# confidence
print("\nconfidence:")
for conf in ["high", "medium", "low"]:
    rs = [r for r in records if r["confidence"] == conf]
    if rs:
        print("  %s: %d/%d (%.0f%%)" % (conf, sum(r["correct"] for r in rs), len(rs),
              100.0 * sum(r["correct"] for r in rs) / len(rs)))

# paired comparison vs search-first (60/83)
sf = json.load(open(os.path.join(SRC, "predictions-full83.json")))
sf_correct = {x.get("q_idx", x.get("idx")): bool(x["correct"]) for x in sf}
both = theme_only = sf_only = neither = 0
for r in records:
    a = r["correct"]
    b = sf_correct.get(r["q_idx"], False)
    if a and b: both += 1
    elif a and not b: theme_only += 1
    elif (not a) and b: sf_only += 1
    else: neither += 1
print("\npaired vs search-first (60/83): both correct %d, theme-only %d, search-first-only %d, both wrong %d" % (both, theme_only, sf_only, neither))
print("net change vs search-first: %+d" % (theme_only - sf_only))

# the two target error groups
print("\ntarget groups:")
for (s, lab) in [(4, "1-2"), (5, "3-2")]:
    rs = [r for r in records if (r["season"], r["round_label"]) == (s, lab)]
    print("  S%d %s:" % (s, lab))
    for r in rs:
        mark = "OK " if r["correct"] else "MISS"
        sf_mark = "sf-OK" if sf_correct.get(r["q_idx"]) else "sf-MISS"
        print("    %s %s: pred %-14s actual %-14s (%s)" % (mark, r["player"], r["predicted_kind"], r["actual_kind"], sf_mark))

json.dump({"score": n, "records": records,
           "paired": {"both": both, "theme_only": theme_only, "sf_only": sf_only, "neither": neither}},
          open(os.path.join(RUN, "scored-theme-person.json"), "w"), ensure_ascii=False, indent=1)
print("\nwrote scored-theme-person.json")
