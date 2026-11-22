#!/usr/bin/env python3
"""Build per-round predictor question files for testset-v5 (99 questions).

This is the fixed question-file builder for round 6. It replaces the
build_context88.py + build_questions88.py pair from the baseline88 /
weakest-link worktrees, with ONE change (round-5 report item 7):

  The `prev_round_kinds` field is REMOVED -- at the context builder, not
  just at the emitter. The field carried the previous round's kinds for
  all players, so a predictor holding next round's file could read this
  round's kinds in advance (the S5 3-2 contamination in round 5: the
  second batch saw S5 3-2's kinds in the S5 4-1 file's prev_round_kinds
  and its q5/q6 answers had to be discarded and re-run).

  What stays: the player's OWN history (player_history_counts,
  player_most_frequent, player_last_kind, player_last3) -- that is the
  player's own past, not the round's answer. What goes: any field that
  names another round's kinds. The per-round files are also issued one
  round at a time (single-round isolation was already the rule; the leak
  came from the field, not from batching).

  Rounds are still issued separately per round (one file per round, 31
  files); no file names any other round's kinds.

Inputs (all in this worktree):
  testset-v5.json, traces/trace-latest.json (new trace, 558 moves),
  design/kind-boundary-rules.md (vocabulary).
Writes (runs/s5patch-round6-2026-11-22/, gitignored):
  - context-all-v5.json: per-question context (no prev_round_kinds).
  - questions/ questions-S{season}-{round}.json, one per round.
    Each question carries its own round_date (prediction point). The file
    header carries round_date = the trace round date; where they differ
    (the 8 date-fixed questions + the new SFTB question), the question
    also carries round_date_override {trace_date, reason}.
Question order inside a round is shuffled with a fixed seed (20261122),
same as the baseline88 builder.

Rules enforced (fail loudly):
  - No answer fields anywhere (no kind/action/hp_delta/gold_delta).
  - No prev_round_kinds anywhere (the field must not appear at all).
  - Question count per round matches testset-v5; every player once.
  - Every NEW or DATE-FIXED question's round_date is on/before its event
    date (hard fail otherwise). The older test set has 23 pre-existing
    violations of that rule (up to 500 days); they are counted and listed
    as warnings, not fixed here -- the round-6 task fixed only q13,
    S5 1-1 and q31. See the patch report.
  - Context date (prediction point) equals the question's round_date;
    for unchanged questions it also equals the trace move date.
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs" / "s5patch-round6-2026-11-22"
OUT_DIR = RUN_DIR / "questions"
RULES = ROOT / "design" / "kind-boundary-rules.md"
BANNED = {"kind", "action", "action_kind", "hp_delta", "gold_delta",
          "prev_round_kinds"}
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vocab = load_vocabulary()
    print(f"vocabulary: {len(vocab)} kinds")
    testset = json.loads((ROOT / "testset-v5.json").read_text(encoding="utf-8"))
    questions = testset["questions"]
    assert len(questions) == 99, "testset-v5 must have 99 questions"
    trace = json.loads((ROOT / "traces" / "trace-latest.json").read_text(encoding="utf-8"))
    moves = trace["moves"]
    assert len(moves) == 558
    pid2key = {p["id"]: p["key"] for p in trace["players"]}
    key2pid = {v: k for k, v in pid2key.items()}

    round_keys = sorted({(m["season"], m["round_index"]) for m in moves})
    round_pos = {k: i for i, k in enumerate(round_keys)}
    by_round = {}
    for m in moves:
        by_round.setdefault((m["season"], m["round_index"]), []).append(m)
    move_by_key = {}
    for m in moves:
        move_by_key[(m["season"], m["round_label"], pid2key[m["player"]])] = m
    round_index_of = {(m["season"], m["round_label"]): m["round_index"] for m in moves}

    # first_appearance (game level, same rule as build_context88.py).
    kind_first_round = {}
    for m in moves:
        if m["semantic_kind"] == "unknown":
            continue
        rk = (m["season"], m["round_index"])
        k = m["semantic_kind"]
        if k not in kind_first_round or rk < kind_first_round[k]:
            kind_first_round[k] = rk
    for q in questions:
        rk = (q["season"], round_index_of[(q["season"], q["round_label"])])
        k = q["kind"]
        if k not in kind_first_round or rk < kind_first_round[k]:
            kind_first_round[k] = rk

    built_ctx = []
    for q in questions:
        q_id = q["q_id"]
        player = q["player"]
        pid = key2pid[player]
        mv = move_by_key.get((q["season"], q["round_label"], player))
        if mv is None:
            fail(f"q_id={q_id}: no trace move for {q['season']} {q['round_label']} {player}")
        if int(q["round_date"]) > int(q["event_real_date"]):
            # Strict rule (round date must be on/before the event date)
            # applies to the questions this round fixed or added. The older
            # test set has 23 pre-existing violations of the same rule
            # (round_date after event date, up to 500 days: v5 q40); the
            # round-6 task fixed only the three named in the round-5 report
            # (q13, S5 1-1, q31). Those are left as known limitations, counted
            # and listed here, not silently blessed -- see the patch report.
            if q.get("round_date_note") or q.get("origin") == "s5patch-round6":
                fail(f"q_id={q_id}: round_date {q['round_date']} after event date {q['event_real_date']}")
            print(f"  WARNING pre-existing date violation (not fixed this round): "
                  f"q_id={q_id} {q['season']} {q['round_label']} {q['player']} "
                  f"{q['kind']} round {q['round_date']} event {q['event_real_date']}", file=sys.stderr)
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
        entry = {
            "q_id": q_id,
            "trace_idx": q.get("trace_idx"),
            "season": q["season"],
            "round_label": q["round_label"],
            "round": f"S{q['season']} {q['round_label']}",
            "date": q["round_date"],
            "trace_date": mv["date"],
            "player": player,
            "hp_start": mv["hp_start"],
            "gold_start": mv["gold_start"],
            "rules_version": mv["rules_version"],
            "first_appearance": kind_first_round[q["kind"]] == rk,
            "player_history_counts": dict(counts),
            "player_most_frequent": most,
            "player_last_kind": last_kind,
            "player_last3": last3,
            # NOTE: no prev_round_kinds. See the module docstring.
        }
        if mv["date"] != q["round_date"]:
            entry["round_date_override"] = {
                "trace_date": mv["date"],
                "reason": q.get("round_date_note", "round_date fixed to the event date"),
            }
        built_ctx.append(entry)

    (RUN_DIR / "context-all-v5.json").write_text(
        json.dumps(built_ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote context-all-v5.json ({len(built_ctx)} questions, "
          f"{sum(1 for c in built_ctx if 'round_date_override' in c)} with round-date overrides)")

    # Group by round, in testset order.
    rounds = {}
    for q in questions:
        key = (q["season"], q["round_label"])
        rounds.setdefault(key, []).append(q)
    ordered_rounds = sorted(rounds, key=lambda k: (k[0], round_index_of[k]))
    ctx_by_qid = {c["q_id"]: c for c in built_ctx}

    rng = random.Random(SEED)
    for (season, label) in ordered_rounds:
        rows = rounds[(season, label)]
        rkey = f"S{season} {label}"
        trace_date = next(m["date"] for m in moves
                          if m["season"] == season and m["round_label"] == label)
        if len({r["player"] for r in rows}) != len(rows):
            fail(f"{rkey}: duplicate player in round")
        qs = []
        for q in rows:
            c = ctx_by_qid[q["q_id"]]
            if c["player"] != q["player"] or c["date"] != q["round_date"]:
                fail(f"{rkey}: context mismatch for {q['player']}")
            item = {
                "q_id": q["q_id"],
                "player": q["player"],
                "round_date": q["round_date"],
                "hp_start": c["hp_start"],
                "gold_start": c["gold_start"],
                "rules_version": c["rules_version"],
                "first_appearance": c["first_appearance"],
                "player_history_counts": c["player_history_counts"],
                "player_most_frequent": c["player_most_frequent"],
                "player_last_kind": c["player_last_kind"],
                "player_last3": c["player_last3"],
                # NOTE: no prev_round_kinds. See the module docstring.
            }
            if "round_date_override" in c:
                item["round_date_override"] = c["round_date_override"]
            qs.append(item)
        rng.shuffle(qs)
        out = {
            "round": rkey,
            "season": season,
            "round_label": label,
            "round_date": trace_date,
            "round_trace_date": trace_date,
            "vocabulary": vocab,
            "questions": qs,
        }
        text = json.dumps(out, ensure_ascii=False, indent=2)
        for banned in BANNED:
            if f'"{banned}"' in text:
                fail(f"{rkey}: banned field {banned} leaked into question file")
        (OUT_DIR / f"questions-S{season}-{label}.json").write_text(text, encoding="utf-8")
        print(f"{rkey}: {len(qs)} questions -> questions-S{season}-{label}.json")

    # Final sweep: the field must not appear anywhere in the built files.
    hits = []
    for p in [RUN_DIR / "context-all-v5.json"] + sorted(OUT_DIR.glob("*.json")):
        if "prev_round_kinds" in p.read_text(encoding="utf-8"):
            hits.append(str(p))
    if hits:
        fail(f"prev_round_kinds still present in: {hits}")
    print(f"verified: prev_round_kinds appears in 0 built question files "
          f"({len(ordered_rounds)} round files + context-all-v5.json)")
    print(f"rounds: {len(ordered_rounds)}, questions: {len(questions)}")


if __name__ == "__main__":
    main()
