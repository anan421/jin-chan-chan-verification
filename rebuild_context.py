#!/usr/bin/env python3
"""Rebuild the per-question context for all 83 questions from the trace.

Why: the round-*-context.json files from round 2 cover only 54 questions
(the single-round redo); the other 29 (24 subset + 5 batch-D-clean) have
no context file in that format. This script rebuilds the context for all
83 from trace-latest.json + test83.json, and verifies it reproduces the
54 known rows exactly before writing anything.

NOTE: test83.json's `idx` is a STALE trace position (the within-round move
order changed when the trace was re-extracted). Matching is done by
(season, round_label, player), never by idx. Verified: 0/83 mismatches
on kind/hp_start/gold_start when matched this way.

Context fields (same shape as the round-2 round-context files):
  q_idx, trace_idx (= test83 idx, stale, kept for reference), season,
  round_label, round, date, player, hp_start, gold_start, rules_version,
  first_appearance, player_history_counts, player_most_frequent,
  player_last_kind, player_last3, prev_round_kinds.
Prefix = the player's moves in rounds strictly before this round.
Unknown kinds are excluded from history counts / last / last3 /
prev_round_kinds (verified against the known rows).
"""
import json
import sys
from collections import Counter
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs" / "forward-guidance-vision1-2026-11-22"
R2 = Path("/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22")


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    trace = json.loads((RUNS / "trace-latest.json").read_text(encoding="utf-8"))
    test83 = json.loads((RUNS / "test83.json").read_text(encoding="utf-8"))
    moves = trace["moves"]
    pid2key = {p["id"]: p["key"] for p in trace["players"]}
    key2pid = {v: k for k, v in pid2key.items()}

    # Round order by (season, round_index).
    round_keys = sorted({(m["season"], m["round_index"]) for m in moves})
    round_pos = {k: i for i, k in enumerate(round_keys)}
    # Moves grouped by (season, round_index), in trace order.
    by_round = {}
    for m in moves:
        by_round.setdefault((m["season"], m["round_index"]), []).append(m)

    built = []
    for pos, row in enumerate(test83):
        rk = (row["season"], row["round_index"])
        player = row["player"]
        pid = key2pid[player]
        # Prefix: this player's moves in strictly earlier rounds.
        prefix = [m for m in moves
                  if m["player"] == pid and (m["season"], m["round_index"]) < rk]
        prefix.sort(key=lambda m: (m["season"], m["round_index"]))
        hist = [(m["semantic_kind"], m["date"]) for m in prefix
                if m["semantic_kind"] != "unknown"]
        counts = Counter(k for k, _ in hist)
        i = round_pos[rk]
        if counts:
            # Most frequent; ties broken by earliest first appearance.
            first_seen = {}
            for j, (k, _) in enumerate(hist):
                first_seen.setdefault(k, j)
            most = max(counts, key=lambda k: (counts[k], -first_seen[k]))
            last_kind = hist[-1][0]
        else:
            most, last_kind = None, None
        # player_last3: the player's classified moves in the LAST 3 ROUNDS
        # before this round (not the last 3 moves overall). Verified
        # against the known rows: e.g. q_idx=22 ORCL S4 1-3 has the
        # moves from S3 6-1, S4 1-1, S4 1-2; q_idx=11 TSMC S4 1-1 is
        # empty because TSMC had no classified move in S3 4-1/5-1/6-1.
        last3_rounds = round_keys[max(0, i - 3):i]
        last3 = []
        for rk2 in last3_rounds:
            for m in by_round.get(rk2, []):
                if m["player"] == pid and m["semantic_kind"] != "unknown":
                    last3.append([m["semantic_kind"], m["date"]])
        # Previous round in (season, round_index) order.
        prev = None
        if i > 0:
            prev = by_round[round_keys[i - 1]]
        prev_kinds = {}
        if prev:
            for m in prev:
                if m["semantic_kind"] != "unknown":
                    prev_kinds[pid2key[m["player"]]] = m["semantic_kind"]
        built.append({
            "q_idx": pos,
            "trace_idx": row["idx"],
            "season": row["season"],
            "round_label": row["round_label"],
            "round": f"S{row['season']} {row['round_label']}",
            "date": row["date"],
            "player": player,
            "hp_start": row["hp_start"],
            "gold_start": row["gold_start"],
            "rules_version": row["rules_version"],
            "first_appearance": row["first_appearance"],
            "player_history_counts": dict(counts),
            "player_most_frequent": most,
            "player_last_kind": last_kind,
            "player_last3": last3,
            "prev_round_kinds": prev_kinds,
        })

    # Verify against the 54 known round-context rows.
    known = {}
    for path in sorted(R2.glob("round-S*-context.json")):
        for c in json.loads(path.read_text(encoding="utf-8")):
            known[c["q_idx"]] = c
    print(f"known round-context rows: {len(known)}")
    fields = ["trace_idx", "season", "round_label", "round", "date", "player",
              "hp_start", "gold_start", "rules_version", "first_appearance",
              "player_history_counts", "player_most_frequent", "player_last_kind",
              "player_last3", "prev_round_kinds"]
    mismatches = []
    for q_idx, k in sorted(known.items()):
        b = built[q_idx]
        for f in fields:
            if b[f] != k[f]:
                mismatches.append((q_idx, f, k[f], b[f]))
    print(f"mismatches vs known rows: {len(mismatches)}")
    for q_idx, f, want, got in mismatches[:20]:
        print(f"  q_idx={q_idx} field={f}: known={want!r} rebuilt={got!r}")
    if mismatches:
        fail(f"{len(mismatches)} mismatches; fix the builder before using it")
    out = RUNS / "context-all83.json"
    out.write_text(json.dumps(built, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"verified: rebuilt context matches all {len(known)} known rows exactly")
    print(f"wrote {out} ({len(built)} rows)")


if __name__ == "__main__":
    main()
