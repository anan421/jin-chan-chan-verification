#!/usr/bin/env python3
"""Build trial question files for vision-1 round 5 (weakest-link trial).

Reads:
  - /home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22/context-all88.json
  - /home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22/questions-S3-1-1.json (vocabulary)
  - runs/weakest-link-vision5-2026-11-22/diagnosis-input.json (weakest q_ids)
Writes (runs/weakest-link-vision5-2026-11-22/trial/, gitignored):
  - questions-trial-S{season}-{round}.json, one per round (11 rounds, 21 questions),
    in the same format as the baseline question files (round, season, round_label,
    round_date, vocabulary, questions[]). Questions carry NO kind, event_name,
    action, or source -- the predictor must infer the kind.

Rounds (weakest questions only):
  S3 1-1: q9,10,11,12 | S3 2-1: q8 | S3 6-1: q13,q81
  S4 1-2: q26,27 | S4 3-2: q31,32 | S4 4-1: q82
  S5 1-1: q14,15,16 | S5 3-2: q5,6,53 | S5 4-1: q57 | S5 5-1: q7 | S5 6-1: q64
"""
import json
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "weakest-link-vision5-2026-11-22"
BASELINE_RUNS = Path("/home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22")
TRIAL = RUNS / "trial"


def main():
    TRIAL.mkdir(parents=True, exist_ok=True)
    diag = json.loads((RUNS / "diagnosis-input.json").read_text(encoding="utf-8"))
    weak_ids = {e["q_id"] for e in diag}
    ctx = {c["q_id"]: c for c in json.loads((BASELINE_RUNS / "context-all88.json").read_text(encoding="utf-8"))}
    vocab = json.loads((BASELINE_RUNS / "questions-S3-1-1.json").read_text(encoding="utf-8"))["vocabulary"]
    by_round = defaultdict(list)
    for qid in sorted(weak_ids):
        c = ctx[qid]
        by_round[(c["season"], c["round_label"])].append(c)
    for (season, rlabel), cs in sorted(by_round.items()):
        cs.sort(key=lambda c: c["q_id"])
        first = cs[0]
        out = {
            "round": first["round"],
            "season": season,
            "round_label": rlabel,
            "round_date": first["date"],
            "vocabulary": vocab,
            "questions": [
                {
                    "q_id": c["q_id"],
                    "player": c["player"],
                    "hp_start": c["hp_start"],
                    "gold_start": c["gold_start"],
                    "rules_version": c["rules_version"],
                    "first_appearance": c["first_appearance"],
                    "player_history_counts": c["player_history_counts"],
                    "player_most_frequent": c["player_most_frequent"],
                    "player_last_kind": c["player_last_kind"],
                    "player_last3": c["player_last3"],
                    "prev_round_kinds": c["prev_round_kinds"],
                }
                for c in cs
            ],
        }
        name = f"questions-trial-S{season}-{rlabel}.json"
        (TRIAL / name).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: {len(cs)} questions (q_ids {[c['q_id'] for c in cs]})")
    print("rounds:", len(by_round), "questions:", len(weak_ids))


if __name__ == "__main__":
    main()
