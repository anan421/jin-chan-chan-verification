#!/usr/bin/env python3
"""Score the forward-guidance experiment (with parallel control group).

1. Reproduce old search-first 60/83 from predictions-full83.json (assert).
   This only validates the script; it is NOT the comparison.
2. Score the control group (fresh 13 predictors, no guidance) from
   predictions-control-S<season>-<label>.json (13 files).
3. Score the experiment group (13 predictors, with guidance) from
   predictions-S<season>-<label>.json (13 files).
4. Paired comparison control vs experiment (same question): both right /
   only experiment right / only control right / both wrong, plus McNemar
   chi2 (continuity-corrected) as an informational number. By round, by
   actual kind, by player, for both groups.
5. Optional --exclude <file>: JSON list of q_idx to drop (contaminated
   questions found by the audit); recomputes a clean score.

Outputs: scored-forward-guidance.json, score-summary.json
(clean variants get a -clean suffix when --exclude is used).
"""
import argparse
import json
import math
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


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def load_predictions(pattern, label):
    preds = {}
    for path in sorted(RUNS.glob(pattern)):
        if "full83" in path.name:
            continue
        for p in json.loads(path.read_text(encoding="utf-8")):
            idx = p["q_idx"]
            if idx in preds:
                fail(f"duplicate {label} prediction q_idx {idx} in {path.name}")
            if p["predicted_kind"] not in VOCABULARY:
                fail(f"{label} q_idx {idx}: kind {p['predicted_kind']} not in vocabulary")
            for f in ("predicted_kind", "confidence", "reasoning", "facts_used"):
                if f not in p:
                    fail(f"{label} q_idx {idx}: missing field {f} in {path.name}")
            preds[idx] = p
    if set(preds) != set(range(83)):
        missing = sorted(set(range(83)) - set(preds))
        fail(f"{label} predictions cover {len(preds)} questions, want 83; missing {missing}")
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude", default=None,
                    help="JSON list of q_idx to drop (audit findings)")
    args = ap.parse_args()
    exclude = set()
    if args.exclude:
        exclude = set(json.loads(Path(args.exclude).read_text(encoding="utf-8")))

    test83 = json.loads((RUNS / "test83.json").read_text(encoding="utf-8"))
    actual = {pos: row["kind"] for pos, row in enumerate(test83)}
    meta = {pos: (f"S{row['season']} {row['round_label']}", row["player"], row["date"])
            for pos, row in enumerate(test83)}

    # 1. Script validation only: reproduce old search-first 60/83.
    sf = json.loads((RUNS / "predictions-full83.json").read_text(encoding="utf-8"))
    # Old file mixes two schemas: 24 rows carry "idx", 59 carry "q_idx".
    # Both are test83 positions 0..82 (verified: union is exactly 0..82,
    # actual_kind matches test83 at every position, "correct" sums to 60).
    sf_pred = {p.get("idx", p.get("q_idx")): p["predicted_kind"] for p in sf}
    if set(sf_pred) != set(range(83)):
        fail(f"old search-first predictions cover {len(sf_pred)} questions, want 83")
    sf_correct = sum(1 for i in range(83) if sf_pred[i] == actual[i])
    print(f"script validation: old search-first reproduced {sf_correct}/83")
    if sf_correct != 60:
        fail(f"old search-first reproduction is {sf_correct}/83, want 60/83")

    # 2-3. Load control + experiment predictions.
    ctrl = load_predictions("predictions-control-S*-*.json", "control")
    exp = load_predictions("predictions-S*-*.json", "experiment")

    # 4. Score (with optional exclusion) + paired comparison.
    kept = [i for i in range(83) if i not in exclude]
    rows = []
    for i in kept:
        rows.append({
            "q_idx": i,
            "round": meta[i][0],
            "player": meta[i][1],
            "date": meta[i][2],
            "actual_kind": actual[i],
            "old_search_first_kind": sf_pred[i],
            "old_search_first_correct": sf_pred[i] == actual[i],
            "control_kind": ctrl[i]["predicted_kind"],
            "control_correct": ctrl[i]["predicted_kind"] == actual[i],
            "control_confidence": ctrl[i]["confidence"],
            "experiment_kind": exp[i]["predicted_kind"],
            "experiment_correct": exp[i]["predicted_kind"] == actual[i],
            "experiment_confidence": exp[i]["confidence"],
        })
    n = len(rows)
    ctrl_c = sum(1 for r in rows if r["control_correct"])
    exp_c = sum(1 for r in rows if r["experiment_correct"])
    both = sum(1 for r in rows if r["experiment_correct"] and r["control_correct"])
    only_exp = sum(1 for r in rows if r["experiment_correct"] and not r["control_correct"])
    only_ctrl = sum(1 for r in rows if not r["experiment_correct"] and r["control_correct"])
    neither = sum(1 for r in rows if not r["experiment_correct"] and not r["control_correct"])
    # McNemar chi2 (continuity-corrected) on the discordant pairs.
    b, c = only_exp, only_ctrl
    mcnemar = ((abs(b - c) - 1) ** 2 / (b + c)) if (b + c) > 0 else 0.0

    def breakdown(key):
        out = {}
        for r in rows:
            d = out.setdefault(r[key], {"n": 0, "control": 0, "experiment": 0})
            d["n"] += 1
            d["control"] += r["control_correct"]
            d["experiment"] += r["experiment_correct"]
        return out

    summary = {
        "n": n,
        "excluded": sorted(exclude),
        "script_validation_old_search_first": sf_correct,
        "control": ctrl_c,
        "experiment": exp_c,
        "delta_experiment_minus_control": exp_c - ctrl_c,
        "paired_both_correct": both,
        "paired_only_experiment": only_exp,
        "paired_only_control": only_ctrl,
        "paired_both_wrong": neither,
        "mcnemar_chi2_continuity_corrected": round(mcnemar, 2),
        "by_round": breakdown("round"),
        "by_kind": breakdown("actual_kind"),
        "by_player": breakdown("player"),
    }
    suffix = "-clean" if exclude else ""
    (RUNS / f"scored-forward-guidance{suffix}.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNS / f"score-summary{suffix}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"n={n} control={ctrl_c} experiment={exp_c} delta={exp_c - ctrl_c:+d}")
    print(f"paired both={both} only_exp={only_exp} only_ctrl={only_ctrl} neither={neither} mcnemar_chi2={mcnemar:.2f}")
    print(f"wrote scored-forward-guidance{suffix}.json + score-summary{suffix}.json")


if __name__ == "__main__":
    main()
