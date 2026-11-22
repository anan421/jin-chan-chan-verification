#!/usr/bin/env python3
"""Extract S1-S3 moves from the trace into a review file.

Usage: python3 extract_s1_s3.py
Reads  ~/workspace/verification/traces/trace-latest.json (main repo, single source).
Writes runs/walkforward-vision1-2026-11-22/s1_s3_review.json (gitignored review evidence).
Deterministic: records ordered by trace position.
"""
import json
import os

TRACE = "/home/hatch/workspace/verification/traces/trace-latest.json"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "runs", "walkforward-vision1-2026-11-22")
OUT = os.path.join(OUT_DIR, "s1_s3_review.json")


def main():
    t = json.load(open(TRACE))
    pmap = {p["id"]: p["key"] for p in t["players"]}
    records = []
    for i, m in enumerate(t["moves"]):
        if m["season"] not in (1, 2, 3):
            continue
        records.append({
            "trace_idx": i,
            "season": m["season"],
            "round_index": m["round_index"],
            "round_label": m["round_label"],
            "round_date": m["date"],
            "player": pmap[m["player"]],
            "action": m["action"],
            "action_kind": m["action_kind"],
            "semantic_kind": m["semantic_kind"],
        })
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
    n_class = sum(1 for r in records if r["semantic_kind"] != "unknown")
    print("wrote %s" % OUT)
    print("total %d, classified %d, unknown %d" % (
        len(records), n_class, len(records) - n_class))
    for s in (1, 2, 3):
        sub = [r for r in records if r["season"] == s]
        print("S%d: %d" % (s, len(sub)))


if __name__ == "__main__":
    main()
