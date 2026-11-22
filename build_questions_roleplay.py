#!/usr/bin/env python3
"""Build pilot question files for the role-play pilot (paper SSR adaptation).

Reads:
  - /home/hatch/workspace/verification-v1-round6/runs/s5patch-round6-2026-11-22/context-all-v5.json
    (per-question context: hp/gold start, player history)
  - testset-v5.json in this worktree (truth; only to check round_date)
  - vocabulary from the round-6 question file (34 kinds)
Writes (runs/roleplay-pilot-2026-11-22/questions/, gitignored):
  - questions-roleplay-S{season}-{round}.json, one per round (8 rounds,
    10 pilot questions), same format as the v5/v6 question files.
    Questions carry NO answer field: no kind, no event_name, no action,
    no source, and NO prev_round_kinds.

Pilot focus set (10 questions, by prototype forecast class):
  policy_regulatory: q5 (ALI bis_rule), q8 (TSMC bis_rule)
  infra_capex:       q10 (AMZN capex), q15 (ALI capex), q32 (ALI datacenter)
  model_release:     q24 (OAI chatgpt), q49 (GOOG gemini), q92 (DPSK v3)
  chip_supply:       q9 (NVDA blackwell), q63 (NVDA megaspeed)

Pre-issue checks (any failure exits non-zero):
  1. The 8 files contain exactly the 10-ID focus set, no more, no fewer.
  2. Zero occurrences of banned field names (exact JSON key):
     prev_round_kinds, kind, action, action_kind, hp_delta, gold_delta,
     event_name, event_real_date, source. (Kind NAMES as values in
     player_history_counts / player_last_kind / player_most_frequent are
     allowed; the check is on the exact field name "kind".)
     A separate substring check asserts "prev_round" appears nowhere.
  3. Every question's round_date matches testset-v5.json exactly.
  4. Every file header round_date equals the trace round date.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R6 = Path("/home/hatch/workspace/verification-v1-round6")
V5CTX = R6 / "runs" / "s5patch-round6-2026-11-22" / "context-all-v5.json"
OUT = HERE / "runs" / "roleplay-pilot-2026-11-22" / "questions"

FOCUS = {5, 8, 9, 10, 15, 24, 32, 49, 63, 92}
BANNED_FIELDS = {"prev_round_kinds", "kind", "action", "action_kind",
                 "hp_delta", "gold_delta", "event_name", "event_real_date",
                 "source"}


def count_banned(obj, counts):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BANNED_FIELDS:
                counts[k] += 1
            count_banned(v, counts)
    elif isinstance(obj, list):
        for v in obj:
            count_banned(v, counts)


def main():
    ctx = {c["q_id"]: c
           for c in json.loads(V5CTX.read_text(encoding="utf-8"))}
    ts = json.loads((HERE / "testset-v5.json").read_text(encoding="utf-8"))
    truth = {q["q_id"]: q for q in ts["questions"]}
    vocab = json.loads(
        (R6 / "runs" / "round6-vision6-2026-11-22" / "questions" /
         "questions-round6-S5-1-1.json").read_text(encoding="utf-8")
    )["vocabulary"]
    assert len(vocab) == 34, f"vocabulary should be 34 kinds, got {len(vocab)}"

    missing = FOCUS - set(ctx)
    assert not missing, f"focus q_ids missing from v5 context: {sorted(missing)}"

    # Group focus questions by round (season, round_label).
    by_round = defaultdict(list)
    for qid in sorted(FOCUS):
        c = ctx[qid]
        by_round[(c["season"], c["round_label"])].append(c)

    OUT.mkdir(parents=True, exist_ok=True)
    written_ids = set()
    for (season, round_label), cs in sorted(by_round.items()):
        # Header round_date = trace round date (the trace_date of the round).
        # S5 1-1 has no single trace date; use the trace_date of its questions.
        trace_dates = sorted({c["trace_date"] for c in cs})
        header_date = trace_dates[0]
        questions = []
        for c in sorted(cs, key=lambda x: x["q_id"]):
            t = truth[c["q_id"]]
            # Each question's own round_date = prediction point from testset-v5.
            assert c["date"] == t["round_date"], (
                f"q{c['q_id']}: context date {c['date']} != "
                f"testset round_date {t['round_date']}")
            q = {
                "q_id": c["q_id"],
                "player": c["player"],
                "round_date": c["date"],
                "hp_start": c["hp_start"],
                "gold_start": c["gold_start"],
                "rules_version": c["rules_version"],
                "first_appearance": c["first_appearance"],
                "player_history_counts": c["player_history_counts"],
                "player_most_frequent": c["player_most_frequent"],
                "player_last_kind": c["player_last_kind"],
                "player_last3": c["player_last3"],
            }
            # S5 1-1 carries a round_date_override (trace date + reason).
            if c["round_label"] == "1-1" and c["season"] == 5:
                q["round_date_override"] = {
                    "trace_date": c["trace_date"],
                    "reason": "S5 1-1 has no single true date; "
                              "round_date = this question's event date.",
                }
            questions.append(q)
            written_ids.add(c["q_id"])
        fname = f"questions-roleplay-S{season}-{round_label}.json"
        doc = {
            "round": f"S{season} {round_label}",
            "season": season,
            "round_label": round_label,
            "round_date": header_date,
            "round_trace_date": header_date,
            "vocabulary": vocab,
            "questions": questions,
        }
        (OUT / fname).write_text(
            json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        print(f"wrote {fname}: {[q['q_id'] for q in questions]}")

    # Pre-issue check 1: exactly the focus set.
    assert written_ids == FOCUS, (
        f"written {sorted(written_ids)} != focus {sorted(FOCUS)}")
    # Pre-issue check 2: zero banned fields.
    counts = defaultdict(int)
    for f in OUT.glob("*.json"):
        count_banned(json.loads(f.read_text(encoding="utf-8")), counts)
    bad = {k: v for k, v in counts.items() if v}
    assert not bad, f"banned fields present: {bad}"
    raw = "".join(f.read_text(encoding="utf-8") for f in OUT.glob("*.json"))
    assert "prev_round" not in raw, "substring prev_round found"
    print("pre-issue checks passed: 10 questions, 0 banned fields, "
          "round_dates match testset-v5")


if __name__ == "__main__":
    sys.exit(main())
