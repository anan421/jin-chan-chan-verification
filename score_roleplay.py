#!/usr/bin/env python3
"""Score the role-play pilot.

Reads:
  - testset-v5.json in this worktree (truth: q_id -> kind)
  - runs/roleplay-pilot-2026-11-22/predictions/predictions-{batch}-{round}.json
    (each a list of {q_id, player, predicted_kind, confidence, reasoning,
    facts_used, [roleplay_text, forecast_prop, forecast_prob]})
Writes (stdout + runs/roleplay-pilot-2026-11-22/predictions/score-roleplay.json):
  - per-batch totals, per prototype forecast class, per player,
    q5 separately, confidence calibration.
Prototype forecast class mapping (see design/roleplay-pilot-design.md):
  policy_regulatory: bis_rule
  infra_capex:       capex, datacenter
  model_release:     chatgpt, gemini, v3
  chip_supply:       blackwell, megaspeed
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRED = HERE / "runs" / "roleplay-pilot-2026-11-22" / "predictions"

CLS = {
    "bis_rule": "policy_regulatory",
    "capex": "infra_capex",
    "datacenter": "infra_capex",
    "chatgpt": "model_release",
    "gemini": "model_release",
    "v3": "model_release",
    "blackwell": "chip_supply",
    "megaspeed": "chip_supply",
}


def main():
    ts = json.loads((HERE / "testset-v5.json").read_text(encoding="utf-8"))
    truth = {q["q_id"]: q for q in ts["questions"]}
    focus = {5, 8, 9, 10, 15, 24, 32, 49, 63, 92}

    batches = {}
    for f in sorted(PRED.glob("predictions-*.json")):
        # predictions-C1-S3-1-1.json -> batch C1
        batch = f.stem.split("-")[1]
        preds = json.loads(f.read_text(encoding="utf-8"))
        for p in preds:
            qid = p["q_id"]
            assert qid in focus, f"{f.name}: unexpected q_id {qid}"
            assert p["player"] == truth[qid]["player"], (
                f"{f.name} q{qid}: player mismatch")
            batches.setdefault(batch, {})[qid] = p

    for batch, ps in sorted(batches.items()):
        assert set(ps) == focus, (
            f"batch {batch}: has {sorted(ps)}, want {sorted(focus)}")

    out = {"batches": {}, "classes": {}, "players": {}, "q5": {}}
    for batch, ps in sorted(batches.items()):
        correct = [qid for qid, p in ps.items()
                   if p["predicted_kind"] == truth[qid]["kind"]]
        out["batches"][batch] = {
            "total": len(correct),
            "n": len(ps),
            "correct_qids": sorted(correct),
            "without_q5": len([q for q in correct if q != 5]),
        }
        # confidence calibration
        for conf in ("high", "medium", "low"):
            sub = [qid for qid, p in ps.items()
                   if p.get("confidence") == conf]
            if sub:
                hit = sum(1 for q in sub
                          if ps[q]["predicted_kind"] == truth[q]["kind"])
                out["batches"][batch].setdefault("confidence", {})[conf] = (
                    f"{hit}/{len(sub)}")

    for cls in ("policy_regulatory", "infra_capex", "model_release",
                "chip_supply"):
        qids = [qid for qid in sorted(focus)
                if CLS[truth[qid]["kind"]] == cls]
        out["classes"][cls] = {
            "q_ids": qids,
            **{b: sum(1 for q in qids
                      if ps[q]["predicted_kind"] == truth[q]["kind"])
               for b, ps in sorted(batches.items())},
        }
    for player in sorted({truth[q]["player"] for q in focus}):
        qids = [qid for qid in sorted(focus)
                if truth[qid]["player"] == player]
        out["players"][player] = {
            "q_ids": qids,
            **{b: sum(1 for q in qids
                      if ps[q]["predicted_kind"] == truth[q]["kind"])
               for b, ps in sorted(batches.items())},
        }
    for batch, ps in sorted(batches.items()):
        out["q5"][batch] = (
            ps[5]["predicted_kind"] == truth[5]["kind"])

    (PRED / "score-roleplay.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
