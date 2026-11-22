#!/usr/bin/env python3
"""Build the per-question context for all 88 questions from the trace.

Adapted from the forward-guidance rebuild_context.py (same shapes, same
rules). Inputs are in this worktree: testset-v3.json + raw-trace-real.json.
The trace body is verified identical to the new post-fix trace (moves and
players equal; only the source sha differs), so the old data.json in this
branch does not affect the context.

Context fields (same shape as the round-2 round-context files):
  q_id, trace_idx, season, round_label, round, date, player, hp_start,
  gold_start, rules_version, first_appearance, player_history_counts,
  player_most_frequent, player_last_kind, player_last3, prev_round_kinds.
Prefix = the player's moves in rounds strictly before this round.
Unknown kinds are excluded from history counts / last / last3 /
prev_round_kinds (same rule as rebuild_context.py).
first_appearance is game level (verified 0/83 against the known rows):
the answer kind has never appeared in any strictly earlier round, by
any player. "First round of kind" is the earliest round where either
the trace has a move with that semantic_kind or a test-set question
has that kind (the test set reclassified 11 moves).

Verification (fail loudly):
  - old83 questions (39): every context field must match
    context-all83.json from the forward-guidance worktree, matched by
    (season, round_label, player).
  - walkforward questions (43): the count of all trace moves strictly
    before this round must equal prefixes.json prefix_n.
  - every question's round_date must equal its trace move date.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs" / "baseline88-2026-11-22"
GUIDANCE_RUNS = Path("/home/hatch/workspace/verification-v1-guidance/runs/forward-guidance-vision1-2026-11-22")
WALKFORWARD_RUNS = Path("/home/hatch/workspace/verification-v1-walkforward/runs/walkforward-vision1-2026-11-22")


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    trace = json.loads((ROOT / "raw-trace-real.json").read_text(encoding="utf-8"))
    testset = json.loads((ROOT / "testset-v3.json").read_text(encoding="utf-8"))
    questions = testset["questions"]
    moves = trace["moves"]
    pid2key = {p["id"]: p["key"] for p in trace["players"]}
    key2pid = {v: k for k, v in pid2key.items()}

    round_keys = sorted({(m["season"], m["round_index"]) for m in moves})
    round_pos = {k: i for i, k in enumerate(round_keys)}
    by_round = {}
    for m in moves:
        by_round.setdefault((m["season"], m["round_index"]), []).append(m)
    # Move lookup by (season, round_label, player key).
    move_by_key = {}
    for m in moves:
        move_by_key[(m["season"], m["round_label"], pid2key[m["player"]])] = m
    # first_appearance (game level, verified 0/83 against the known rows):
    # the answer kind has never appeared in any strictly earlier round,
    # by any player. "First round of kind" is the earliest round where
    # either the trace has a move with that semantic_kind or a test-set
    # question has that kind (the test set reclassified 11 moves: 10
    # unknown -> a kind, 1 blackwell -> tongyi).
    kind_first_round = {}
    for m in moves:
        if m["semantic_kind"] == "unknown":
            continue
        rk = (m["season"], m["round_index"])
        k = m["semantic_kind"]
        if k not in kind_first_round or rk < kind_first_round[k]:
            kind_first_round[k] = rk
    round_index_of = {(m["season"], m["round_label"]): m["round_index"] for m in moves}
    for q in questions:
        rk = (q["season"], round_index_of[(q["season"], q["round_label"])])
        k = q["kind"]
        if k not in kind_first_round or rk < kind_first_round[k]:
            kind_first_round[k] = rk

    built = []
    for q in questions:
        q_id = q["q_id"]
        rk_label = (q["season"], q["round_label"])
        player = q["player"]
        pid = key2pid[player]
        mv = move_by_key.get((q["season"], q["round_label"], player))
        if mv is None:
            fail(f"q_id={q_id}: no trace move for {rk_label} {player}")
        if mv["date"] != q["round_date"]:
            fail(f"q_id={q_id}: round_date {q['round_date']} != trace date {mv['date']}")
        rk = (q["season"], mv["round_index"])
        prefix = [m for m in moves
                  if m["player"] == pid and (m["season"], m["round_index"]) < rk]
        prefix.sort(key=lambda m: (m["season"], m["round_index"]))
        hist = [(m["semantic_kind"], m["date"]) for m in prefix
                if m["semantic_kind"] != "unknown"]
        counts = Counter(k for k, _ in hist)
        i = round_pos[rk]
        if counts:
            first_seen = {}
            for j, (k, _) in enumerate(hist):
                first_seen.setdefault(k, j)
            most = max(counts, key=lambda k: (counts[k], -first_seen[k]))
            last_kind = hist[-1][0]
        else:
            most, last_kind = None, None
        last3_rounds = round_keys[max(0, i - 3):i]
        last3 = []
        for rk2 in last3_rounds:
            for m in by_round.get(rk2, []):
                if m["player"] == pid and m["semantic_kind"] != "unknown":
                    last3.append([m["semantic_kind"], m["date"]])
        prev = None
        if i > 0:
            prev = by_round[round_keys[i - 1]]
        prev_kinds = {}
        if prev:
            for m in prev:
                if m["semantic_kind"] != "unknown":
                    prev_kinds[pid2key[m["player"]]] = m["semantic_kind"]
        built.append({
            "q_id": q_id,
            "trace_idx": q.get("old_q_idx"),
            "season": q["season"],
            "round_label": q["round_label"],
            "round": f"S{q['season']} {q['round_label']}",
            "date": q["round_date"],
            "player": player,
            "hp_start": mv["hp_start"],
            "gold_start": mv["gold_start"],
            "rules_version": mv["rules_version"],
            "first_appearance": kind_first_round[q["kind"]] == rk,
            "player_history_counts": dict(counts),
            "player_most_frequent": most,
            "player_last_kind": last_kind,
            "player_last3": last3,
            "prev_round_kinds": prev_kinds,
            "_prefix_all_n": sum(1 for m in moves
                                 if (m["season"], m["round_index"]) < rk),
        })

    # Verify old83 rows against context-all83.json.
    known83 = json.loads((GUIDANCE_RUNS / "context-all83.json").read_text(encoding="utf-8"))
    known_by_key = {(c["season"], c["round_label"], c["player"]): c for c in known83}
    fields = ["date", "hp_start", "gold_start", "rules_version",
              "first_appearance", "player_history_counts",
              "player_most_frequent", "player_last_kind", "player_last3",
              "prev_round_kinds"]
    mismatches = []
    n_old = 0
    for b in built:
        q = questions[b["q_id"]]
        if q["origin"] != "old83":
            continue
        n_old += 1
        k = known_by_key.get((b["season"], b["round_label"], b["player"]))
        if k is None:
            mismatches.append((b["q_id"], "missing-known", None, None))
            continue
        for f in fields:
            if b[f] != k[f]:
                mismatches.append((b["q_id"], f, k[f], b[f]))
    print(f"old83 questions checked: {n_old}, mismatches: {len(mismatches)}")
    for q_id, f, want, got in mismatches[:20]:
        print(f"  q_id={q_id} field={f}: known={want!r} rebuilt={got!r}")

    # Verify walkforward prefix counts against prefixes.json.
    prefixes = json.loads((WALKFORWARD_RUNS / "prefixes.json").read_text(encoding="utf-8"))
    pref_by_qid = {p["q_id"]: p for p in prefixes}
    n_wf = 0
    wf_bad = []
    for b in built:
        q = questions[b["q_id"]]
        if q["origin"] != "walkforward":
            continue
        n_wf += 1
        # prefixes.json q_id is the walkforward-local id; match by
        # (season, round, player) instead.
        cand = [p for p in prefixes
                if p["season"] == b["season"] and p["round"] == b["round"]
                and p["player"] == b["player"]]
        if len(cand) != 1:
            wf_bad.append((b["q_id"], "prefix-match", len(cand)))
            continue
        if cand[0]["prefix_n"] != b["_prefix_all_n"]:
            wf_bad.append((b["q_id"], "prefix_n", cand[0]["prefix_n"], b["_prefix_all_n"]))
    print(f"walkforward questions checked: {n_wf}, prefix mismatches: {len(wf_bad)}")
    for row in wf_bad[:20]:
        print(f"  {row}")

    if mismatches or wf_bad:
        fail("verification failed; fix the builder before using it")

    for b in built:
        del b["_prefix_all_n"]
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / "context-all88.json"
    out.write_text(json.dumps(built, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"verified: context matches all {n_old} old83 rows and {n_wf} walkforward prefix counts")
    print(f"wrote {out} ({len(built)} rows)")


if __name__ == "__main__":
    main()
