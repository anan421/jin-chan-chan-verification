#!/usr/bin/env python3
"""Build per-round question files for the forward-guidance experiment.

Two versions per round (the only difference is the guidance input):
  questions-S<season>-<label>.json          (experiment: with guidance)
  questions-control-S<season>-<label>.json  (control:    no guidance)

Inputs (all in runs/forward-guidance-vision1-2026-11-22/):
  test83.json, round-S*-context.json (13), headline-events.json,
  guidance-S4.json, guidance-S5-early.json, guidance-S5-late.json.
Question order inside a round is shuffled with a fixed seed (20261122);
both versions of a round share the same shuffled order.

Rules enforced (fail loudly):
  - No answer fields anywhere (no kind/action/hp_delta/gold_delta).
  - Every guidance entry attached has date <= round date.
  - Question count per round matches test83; every player appears once.
  - Control and experiment files contain the same questions in the same
    order; only the guidance field differs.
"""
import json
import random
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs" / "forward-guidance-vision1-2026-11-22"
VOCABULARY = [
    "chatgpt", "generic", "msft_invest", "doubao_price_war", "blackwell",
    "v3", "colossus", "r1", "stargate", "musk_table", "bis_rule",
    "openai_mar26", "anthropic_ipo", "spacex_xai", "huang_resign",
    "sec_probe", "overseas_rental", "tongyi", "hunyuan", "ascend",
    "doubao", "wenxin", "pangu", "llama", "claude", "gemini",
    "megaspeed", "energy", "financing", "capex", "open_source",
]
BANNED = {"kind", "action", "action_kind", "hp_delta", "gold_delta"}


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    test83 = json.loads((RUNS / "test83.json").read_text(encoding="utf-8"))
    headlines = json.loads((RUNS / "headline-events.json").read_text(encoding="utf-8"))["rounds"]
    guidance = []
    for name in ("guidance-S4.json", "guidance-S5-early.json", "guidance-S5-late.json"):
        p = RUNS / name
        if not p.exists():
            fail(f"missing guidance file {name}")
        entries = json.loads(p.read_text(encoding="utf-8"))["entries"]
        for e in entries:
            for f in ("player", "date", "statement", "source", "type"):
                if f not in e:
                    fail(f"{name}: entry missing field {f}: {e}")
            if e["type"] not in ("earnings_guidance", "ceo_statement", "filing", "announced_plan"):
                fail(f"{name}: bad type {e['type']}: {e}")
            if len(e["date"]) != 10 or e["date"][4] != "-":
                fail(f"{name}: bad date {e['date']}: {e}")
        guidance.extend(entries)
    print(f"guidance entries total: {len(guidance)}")

    # Group test83 rows by round, in file order (q_idx = position 0..82).
    rounds = {}
    for pos, row in enumerate(test83):
        key = (row["season"], row["round_label"])
        rounds.setdefault(key, []).append((pos, row))

    # Context rebuilt for all 83 from the trace (rebuild_context.py,
    # verified to reproduce the 54 known round-2 rows exactly). The
    # round-*-context.json files only cover 54 questions.
    ctx_all = json.loads((RUNS / "context-all83.json").read_text(encoding="utf-8"))
    ctx_by_round = {}
    for c in ctx_all:
        ctx_by_round.setdefault((c["season"], c["round_label"]), []).append(c)

    rng = random.Random(20261122)
    for (season, label), rows in sorted(rounds.items()):
        rkey = f"S{season} {label}"
        ctx = ctx_by_round.get((season, label))
        if ctx is None:
            fail(f"missing rebuilt context for {rkey}")
        ctx_by_player = {c["player"]: c for c in ctx}
        if rkey not in headlines:
            fail(f"missing headline for {rkey}")
        head = headlines[rkey]
        round_date = rows[0][1]["date"]
        if any(r["date"] != round_date for _, r in rows):
            fail(f"{rkey}: mixed round dates")
        if len(ctx) != len(rows):
            fail(f"{rkey}: context has {len(ctx)} rows, test83 has {len(rows)}")
        rdate_str = f"{str(round_date)[:4]}-{str(round_date)[4:6]}-{str(round_date)[6:]}"

        questions = []
        for pos, row in rows:
            player = row["player"]
            if player not in ctx_by_player:
                fail(f"{rkey}: player {player} missing from context")
            c = ctx_by_player[player]
            if c["player"] != player or c["date"] != round_date:
                fail(f"{rkey}: context mismatch for {player}")
            g = [e for e in guidance
                 if e["player"] == player and e["date"] <= rdate_str]
            questions.append({
                "q_idx": pos,
                "player": player,
                "hp_start": c["hp_start"],
                "gold_start": c["gold_start"],
                "rules_version": c["rules_version"],
                "first_appearance": c["first_appearance"],
                "player_history_counts": c["player_history_counts"],
                "player_most_frequent": c["player_most_frequent"],
                "player_last_kind": c["player_last_kind"],
                "player_last3": c["player_last3"],
                "prev_round_kinds": c["prev_round_kinds"],
                "guidance": g,
            })
        # Same shuffled order for both versions of this round.
        rng.shuffle(questions)
        order = [q["q_idx"] for q in questions]

        base = {
            "round": rkey,
            "season": season,
            "round_label": label,
            "round_date": round_date,
            "headline": head["headline"],
            "headline_given_to": head["given_to"],
            "headline_not_given_to": head.get("not_given_to", []),
            "vocabulary": VOCABULARY,
        }
        exp_out = dict(base, questions=questions)
        ctrl_questions = [dict(q, guidance=[]) for q in questions]
        ctrl_out = dict(base, questions=ctrl_questions)
        for name, out in ((f"questions-S{season}-{label}.json", exp_out),
                          (f"questions-control-S{season}-{label}.json", ctrl_out)):
            text = json.dumps(out, ensure_ascii=False, indent=2)
            for banned in BANNED:
                if f'"{banned}"' in text:
                    fail(f"{rkey} {name}: banned field {banned} leaked into question file")
            (RUNS / name).write_text(text, encoding="utf-8")
        # Control/experiment must be identical except guidance.
        assert [q["q_idx"] for q in ctrl_questions] == order
        assert all(q["guidance"] == [] for q in ctrl_questions)
        n_guide = sum(len(q["guidance"]) for q in questions)
        print(f"{rkey}: {len(questions)} questions, {n_guide} guidance entries, "
              f"order {order} -> questions-S{season}-{label}.json + control version")

    total_q = sum(len(v) for v in rounds.values())
    print(f"done: {len(rounds)} rounds, {total_q} questions, 26 files (13 experiment + 13 control)")


if __name__ == "__main__":
    main()
