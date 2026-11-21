"""Build per-round question context files (no answers) from trace-latest.json,
and validate the builder by reproducing the existing search-first context files.

Key: join test83 questions to trace moves by (season, round_label, player) --
test83 'idx' is the OLD trace position and 39/83 do not match the new trace.

Usage: python3 build_contexts.py
Writes: runs/theme-person-round3-2026-11-22/context-S<season>-<label>.json (13 files)
"""
import json, os, glob
from collections import Counter

SRC = "/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22"
OUT = "/home/hatch/workspace/verification-r3-theme/runs/theme-person-round3-2026-11-22"

trace = json.load(open(os.path.join(SRC, "trace-latest.json")))
moves = trace["moves"]
players = {p["id"]: p["key"] for p in trace["players"]}
key2id = {v: k for k, v in players.items()}
test83 = json.load(open(os.path.join(SRC, "test83.json")))

# move lookup by (season, round_label, player_key)
move_pos = {}
for i, m in enumerate(moves):
    move_pos[(m["season"], m["round_label"], players[m["player"]])] = i

round_order = []
for m in moves:
    k = (m["season"], m["round_label"])
    if k not in round_order:
        round_order.append(k)

def prev_round_key(season, label):
    i = round_order.index((season, label))
    return round_order[i - 1] if i > 0 else None

def build_item(qi, q):
    p = move_pos[(q["season"], q["round_label"], q["player"])]
    m = moves[p]
    pid = m["player"]
    pkey = players[pid]
    hist = [mm for mm in moves[:p] if mm["player"] == pid and mm.get("semantic_kind") not in (None, "unknown")]
    counts = Counter(mm["semantic_kind"] for mm in hist)
    most = counts.most_common(1)[0][0] if counts else None
    last_kind = hist[-1]["semantic_kind"] if hist else None
    # last3: the player's action kind in each of the last 3 rounds before this
    # round (one per round, chronological); rounds with unknown kind skipped.
    # (Validated: reproduces all 59 existing context items exactly.)
    cur = round_order.index((q["season"], q["round_label"]))
    last3 = []
    for rk in round_order[max(0, cur - 3):cur]:
        for mm in moves:
            if (mm["season"], mm["round_label"]) == rk and mm["player"] == pid:
                if mm.get("semantic_kind") not in (None, "unknown"):
                    last3.append([mm["semantic_kind"], mm["date"]])
                break
    pk = prev_round_key(q["season"], q["round_label"])
    prev = {}
    if pk:
        for mm in moves:
            if (mm["season"], mm["round_label"]) == pk and mm.get("semantic_kind") not in (None, "unknown"):
                prev[players[mm["player"]]] = mm["semantic_kind"]
    return {
        "q_idx": qi,
        "trace_idx": p,
        "season": q["season"],
        "round_label": q["round_label"],
        "round": "S%d %s" % (q["season"], q["round_label"]),
        "date": q["date"],
        "player": pkey,
        "hp_start": q["hp_start"],
        "gold_start": q["gold_start"],
        "rules_version": q["rules_version"],
        "first_appearance": q["first_appearance"],
        "player_history_counts": dict(counts),
        "player_most_frequent": most,
        "player_last_kind": last_kind,
        "player_last3": last3,
        "prev_round_kinds": prev,
    }

FIELDS = ["player_history_counts", "player_most_frequent", "player_last_kind",
          "player_last3", "prev_round_kinds", "hp_start", "gold_start",
          "rules_version", "first_appearance", "date", "player"]

def validate():
    existing = {}
    for f in glob.glob(os.path.join(SRC, "round-*-context.json")):
        for it in json.load(open(f)):
            existing[it["q_idx"]] = it
    b = json.load(open(os.path.join(SRC, "batchD_S5_late-context.json")))
    for it in b:
        existing.setdefault(it["q_idx"], it)
    mismatch = Counter()
    examples = {}
    bad_items = 0
    for qi, q in enumerate(test83):
        if qi not in existing:
            continue
        got = build_item(qi, q)
        exp = existing[qi]
        item_bad = False
        for field in FIELDS:
            if got[field] != exp[field]:
                mismatch[field] += 1
                examples.setdefault(field, (qi, exp[field], got[field]))
                item_bad = True
        bad_items += item_bad
    print("existing context items:", len(existing))
    print("mismatches by field:")
    for f, n in mismatch.most_common():
        print(" ", f, n, " e.g. q_idx", examples[f][0], "expected", examples[f][1], "got", examples[f][2])
    print("mismatched items:", bad_items, "/", len(existing))
    return bad_items

if __name__ == "__main__":
    bad = validate()
    os.makedirs(OUT, exist_ok=True)
    by_round = {}
    for qi, q in enumerate(test83):
        by_round.setdefault((q["season"], q["round_label"]), []).append(build_item(qi, q))
    for (s, lab), items in sorted(by_round.items()):
        fn = os.path.join(OUT, "context-S%d-%s.json" % (s, lab))
        json.dump(items, open(fn, "w"), ensure_ascii=False, indent=1)
        print("wrote", fn, len(items), "items")
    print("validation mismatched items:", bad)
