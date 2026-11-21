#!/usr/bin/env python3
"""Score search-first on the enlarged 105-question set (round 5).

Inputs (runs/sample-expansion-round5-2026-11-22/):
  test105.json                 105 questions (with answers)
  predictions-S4-1-2.json      new predictions, 10 questions
  predictions-S4-3-2.json      new predictions, 7 questions
  predictions-S5-3-2.json      new predictions, 5 questions
  (old 83 predictions come from the round-2 search-first run)
Outputs: scored-sample-expansion.json + a printed summary.
Baselines (computed exactly on the 105, same walk-forward prefix):
  - global frequency: most frequent kind in the whole prefix
  - per-player history: the player's most frequent kind in the prefix
    (ties: most recent occurrence, then alphabetical)
  - transition model and formula: see the report (run separately)
Agent baselines (plain Agent 30/83, optimized Agent 46/83) are NOT
re-run; they are bounded by assuming they get all 22 new questions
right (see the report for the bounding argument).
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "sample-expansion-round5-2026-11-22"
R2 = Path("/home/hatch/workspace/verification-r2-search/runs/"
          "search-first-full83-2026-11-22")

PLAYERS = ["NVDA", "OAI", "MSFT", "GOOG", "ANTH", "META", "AMZN", "MUSK",
           "AAPL", "ORCL", "BYTE", "ALI", "TCE", "BIDU", "HUAWEI", "DPSK",
           "TSMC", "SFTB"]


def main():
    test105 = json.loads((RUNS / "test105.json").read_text())
    old_preds = json.loads((R2 / "predictions-full83.json").read_text())
    new_preds = []
    for f in ("predictions-S4-1-2.json", "predictions-S4-3-2.json",
              "predictions-S5-3-2.json"):
        new_preds += json.loads((RUNS / f).read_text())
    assert len(new_preds) == 22, f"expected 22 new predictions, got {len(new_preds)}"

    by_key = {}
    for p in old_preds:
        by_key[(p["season"], p["round_label"], p["player"])] = p["predicted_kind"]
    for p in new_preds:
        k = (p["season"], p["round_label"], p["player"])
        assert k not in by_key, f"duplicate prediction for {k}"
        by_key[k] = p["predicted_kind"]
    assert len(by_key) == 105, f"expected 105 merged predictions, got {len(by_key)}"

    # --- search-first score on the 105 ----------------------------------
    rows = []
    for q in test105:
        pred = by_key[(q["season"], q["round_label"], q["player"])]
        rows.append({**q, "predicted_kind": pred,
                     "correct": pred == q["kind"]})
    sf = sum(1 for r in rows if r["correct"])
    # old 83 = the questions in test83 (join by season/round/player)
    old83 = json.loads((R2 / "test83.json").read_text())
    old_keys = {(q["season"], q["round_label"], q["player"]) for q in old83}
    old_rows = [r for r in rows
                if (r["season"], r["round_label"], r["player"]) in old_keys]
    new_rows = [r for r in rows
                if (r["season"], r["round_label"], r["player"]) not in old_keys]
    assert len(old_rows) == 83 and len(new_rows) == 22
    sf_old = sum(1 for r in old_rows if r["correct"])
    sf_new = sum(1 for r in new_rows if r["correct"])
    assert sf_old == 60, f"old-83 search-first must reproduce 60, got {sf_old}"

    # --- script baselines on the 105 (walk-forward prefix) --------------
    trace = json.loads((HERE / "traces" / "trace-latest.json").read_text())
    moves = trace["moves"]
    base_rows = []
    for q in test105:
        i = q["idx"]
        prefix = [m for m in moves[:i] if m["semantic_kind"] != "unknown"]
        # global frequency
        gcounts = Counter(m["semantic_kind"] for m in prefix)
        gpred = gcounts.most_common(1)[0][0] if gcounts else None
        # per-player history (ties: most recent, then alphabetical)
        phist = [m for m in prefix if m["player"] == q["player_idx"]]
        pcounts = Counter(m["semantic_kind"] for m in phist)
        ppred = None
        if pcounts:
            top = max(pcounts.values())
            cands = [k for k, v in pcounts.items() if v == top]
            if len(cands) == 1:
                ppred = cands[0]
            else:
                last_seen = {}
                for m in phist:
                    if m["semantic_kind"] in cands:
                        last_seen[m["semantic_kind"]] = m["date"]
                ppred = sorted(cands,
                               key=lambda k: (-last_seen.get(k, 0), k))[0]
        base_rows.append({
            "season": q["season"], "round_label": q["round_label"],
            "player": q["player"], "kind": q["kind"],
            "global_pred": gpred, "global_correct": gpred == q["kind"],
            "perplayer_pred": ppred,
            "perplayer_correct": ppred == q["kind"],
        })
    gscore = sum(1 for r in base_rows if r["global_correct"])
    pscore = sum(1 for r in base_rows if r["perplayer_correct"])

    out = {
        "n": 105,
        "search_first": sf,
        "search_first_old83": sf_old,
        "search_first_new22": sf_new,
        "global_frequency": gscore,
        "per_player_history": pscore,
        "by_kind_new": {k: [sum(1 for r in new_rows
                                if r["kind"] == k and r["correct"]),
                            sum(1 for r in new_rows if r["kind"] == k)]
                        for k in sorted({r["kind"] for r in new_rows})},
        "by_round_new": {(r["season"], r["round_label"]): None
                         for r in new_rows},
        "rows": [{k: r[k] for k in
                  ("season", "round_label", "player", "kind",
                   "predicted_kind", "correct", "first_appearance")}
                 for r in rows],
        "baseline_rows": base_rows,
    }
    # by-round breakdown for the new questions
    by_round = {}
    for r in new_rows:
        key = f"S{r['season']} {r['round_label']}"
        a, b = by_round.get(key, (0, 0))
        by_round[key] = (a + (1 if r["correct"] else 0), b + 1)
    out["by_round_new"] = {k: f"{a}/{b}" for k, (a, b) in by_round.items()}
    (RUNS / "scored-sample-expansion.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"search-first on 105: {sf}/105 ({sf / 105:.1%})")
    print(f"  old 83: {sf_old}/83 ({sf_old / 83:.1%})")
    print(f"  new 22: {sf_new}/22 ({sf_new / 22:.1%})")
    print(f"  new by kind: {out['by_kind_new']}")
    print(f"  new by round: {out['by_round_new']}")
    print(f"global frequency on 105: {gscore}/105 ({gscore / 105:.1%})")
    print(f"per-player history on 105: {pscore}/105 ({pscore / 105:.1%})")
    # sanity: the same baselines on the old 83 (expect ~6 and ~22-23)
    old_base = [r for r in base_rows
                if (r["season"], r["round_label"], r["player"]) in old_keys]
    print(f"  (old 83 check: global "
          f"{sum(1 for r in old_base if r['global_correct'])}/83, "
          f"per-player "
          f"{sum(1 for r in old_base if r['perplayer_correct'])}/83)")
    # first-appearance split on the 105
    fa = [r for r in rows if r["first_appearance"]]
    rep = [r for r in rows if not r["first_appearance"]]
    print(f"first-appearance on 105: "
          f"{sum(1 for r in fa if r['correct'])}/{len(fa)}; "
          f"repeat: {sum(1 for r in rep if r['correct'])}/{len(rep)}")


if __name__ == "__main__":
    main()
