#!/usr/bin/env python3
"""Score the 88-question baseline experiment (4 batches, same method).

1. Reproduce old search-first 60/83 from predictions-full83.json (assert).
   This only validates the script; it is NOT the comparison.
2. Score the main batch (13 fresh predictors) from
   predictions-main-S<season>-<label>.json (28 files).
3. Score the 3 control batches (13 fresh predictors each) from
   predictions-control<N>-S<season>-<label>.json (28 files each).
4. Paired comparison between batches (same question): both right /
   only A right / only B right / both wrong, plus McNemar chi2
   (continuity-corrected) as an informational number. By round, by
   actual kind, by player, per batch. Confidence calibration per batch.
5. Optional --exclude <file>: JSON list of q_id to drop (contaminated
   questions found by the audit); recomputes a clean score.

The baseline score is the main batch's score. The noise band is the
spread (min-max) of the 3 control batches. The 4-batch mean and range
are also reported.

Outputs: scored-baseline88.json, score-summary88.json
(clean variants get a -clean suffix when --exclude is used).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs" / "baseline88-2026-11-22"
GUIDANCE_RUNS = Path("/home/hatch/workspace/verification-v1-guidance/runs/forward-guidance-vision1-2026-11-22")
BATCHES = ["main", "control1", "control2", "control3"]


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_predictions(pattern, label):
    preds = {}
    for path in sorted(RUNS.glob(pattern)):
        if "full83" in path.name:
            continue
        for p in json.loads(path.read_text(encoding="utf-8")):
            idx = p["q_id"]
            if idx in preds:
                fail(f"duplicate {label} prediction q_id {idx} in {path.name}")
            if p["predicted_kind"] not in VOCAB:
                fail(f"{label} q_id {idx}: kind {p['predicted_kind']} not in vocabulary")
            for f in ("predicted_kind", "confidence", "reasoning", "facts_used"):
                if f not in p:
                    fail(f"{label} q_id {idx}: missing field {f} in {path.name}")
            preds[idx] = p
    if set(preds) != set(range(88)):
        missing = sorted(set(range(88)) - set(preds))
        fail(f"{label} predictions cover {len(preds)} questions, want 88; missing {missing}")
    return preds


def main():
    global VOCAB
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude", default=None,
                    help="JSON list of q_id to drop (audit findings)")
    args = ap.parse_args()
    exclude = set()
    if args.exclude:
        exclude = set(json.loads(Path(args.exclude).read_text(encoding="utf-8")))

    testset = json.loads((ROOT / "testset-v3.json").read_text(encoding="utf-8"))
    questions = testset["questions"]
    actual = {q["q_id"]: q["kind"] for q in questions}
    meta = {q["q_id"]: (f"S{q['season']} {q['round_label']}", q["player"], q["round_date"])
            for q in questions}
    qfile = json.loads((RUNS / "questions-S4-1-1.json").read_text(encoding="utf-8"))
    VOCAB = qfile["vocabulary"]

    # 1. Script validation only: reproduce old search-first 60/83.
    sf = json.loads((RUNS / "predictions-full83.json").read_text(encoding="utf-8"))
    test83 = json.loads((GUIDANCE_RUNS / "test83.json").read_text(encoding="utf-8"))
    actual83 = {pos: row["kind"] for pos, row in enumerate(test83)}
    sf_pred = {p.get("idx", p.get("q_idx")): p["predicted_kind"] for p in sf}
    if set(sf_pred) != set(range(83)):
        fail(f"old search-first predictions cover {len(sf_pred)} questions, want 83")
    sf_correct = sum(1 for i in range(83) if sf_pred[i] == actual83[i])
    print(f"script validation: old search-first reproduced {sf_correct}/83")
    if sf_correct != 60:
        fail(f"old search-first reproduction is {sf_correct}/83, want 60/83")

    # 2-3. Load the 4 batches.
    batches = {}
    for b in BATCHES:
        batches[b] = load_predictions(f"predictions-{b}-S*-*.json", b)

    # 4. Score (with optional exclusion) + paired comparisons.
    kept = [i for i in range(88) if i not in exclude]
    rows = []
    for i in kept:
        row = {
            "q_id": i,
            "round": meta[i][0],
            "player": meta[i][1],
            "date": meta[i][2],
            "actual_kind": actual[i],
        }
        for b in BATCHES:
            row[f"{b}_kind"] = batches[b][i]["predicted_kind"]
            row[f"{b}_correct"] = batches[b][i]["predicted_kind"] == actual[i]
            row[f"{b}_confidence"] = batches[b][i]["confidence"]
        rows.append(row)
    n = len(rows)
    scores = {b: sum(1 for r in rows if r[f"{b}_correct"]) for b in BATCHES}
    ctrl_scores = [scores[b] for b in ("control1", "control2", "control3")]
    noise_band = [min(ctrl_scores), max(ctrl_scores)]
    mean4 = sum(scores.values()) / 4.0

    def paired(a, b):
        both = sum(1 for r in rows if r[f"{a}_correct"] and r[f"{b}_correct"])
        only_a = sum(1 for r in rows if r[f"{a}_correct"] and not r[f"{b}_correct"])
        only_b = sum(1 for r in rows if not r[f"{a}_correct"] and r[f"{b}_correct"])
        neither = sum(1 for r in rows if not r[f"{a}_correct"] and not r[f"{b}_correct"])
        d = only_a + only_b
        mcnemar = ((abs(only_a - only_b) - 1) ** 2 / d) if d > 0 else 0.0
        return {"both_correct": both, "only_a": only_a, "only_b": only_b,
                "both_wrong": neither, "mcnemar_chi2": round(mcnemar, 2)}

    def breakdown(key):
        out = {}
        for r in rows:
            d = out.setdefault(r[key], {"n": 0})
            d["n"] += 1
            for b in BATCHES:
                d[b] = d.get(b, 0) + (1 if r[f"{b}_correct"] else 0)
        return out

    def calibration(batch):
        out = {}
        for r in rows:
            c = r[f"{batch}_confidence"]
            d = out.setdefault(c, {"n": 0, "correct": 0})
            d["n"] += 1
            d["correct"] += 1 if r[f"{batch}_correct"] else 0
        return out

    summary = {
        "n": n,
        "excluded": sorted(exclude),
        "script_validation_old_search_first": sf_correct,
        "baseline_main": scores["main"],
        "control_scores": {b: scores[b] for b in ("control1", "control2", "control3")},
        "noise_band_control_min_max": noise_band,
        "noise_band_width": noise_band[1] - noise_band[0],
        "mean_of_4_batches": round(mean4, 2),
        "range_of_4_batches": [min(scores.values()), max(scores.values())],
        "paired_main_vs_control1": paired("main", "control1"),
        "paired_main_vs_control2": paired("main", "control2"),
        "paired_main_vs_control3": paired("main", "control3"),
        "paired_control1_vs_control2": paired("control1", "control2"),
        "paired_control1_vs_control3": paired("control1", "control3"),
        "paired_control2_vs_control3": paired("control2", "control3"),
        "by_round": breakdown("round"),
        "by_kind": breakdown("actual_kind"),
        "by_player": breakdown("player"),
        "calibration": {b: calibration(b) for b in BATCHES},
    }
    suffix = "-clean" if exclude else ""
    (RUNS / f"scored-baseline88{suffix}.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNS / f"score-summary88{suffix}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"n={n} main={scores['main']} control1={scores['control1']} "
          f"control2={scores['control2']} control3={scores['control3']}")
    print(f"noise band (controls): {noise_band[0]}-{noise_band[1]} "
          f"(width {noise_band[1] - noise_band[0]}); mean of 4: {mean4:.2f}")
    print(f"wrote scored-baseline88{suffix}.json + score-summary88{suffix}.json")


if __name__ == "__main__":
    main()
