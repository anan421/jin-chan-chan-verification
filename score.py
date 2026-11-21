#!/usr/bin/env python3
"""Score round 4 exception-override predictions against the 83 answers.

Joins by (round, player). Baseline = search-first prediction (60/83).
Reports: total score, paired comparison vs baseline, override ledger
(fixed / broke / no change), per-round breakdown.
"""
import json
import glob
import os
from collections import Counter

RUNDIR = "/home/hatch/workspace/verification-r4-exception/runs/exception-override-round4-2026-11-22"
ANSWERS = "/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22/scored-full83.json"

def main():
    scored = json.load(open(ANSWERS))
    ans = {(r["round"], r["player"]): r for r in scored}
    assert len(ans) == 83, len(ans)
    baseline_correct = sum(1 for r in scored if r["correct"])
    print("baseline (search-first) correct:", baseline_correct, "/ 83")

    preds = []
    for fn in sorted(glob.glob(os.path.join(RUNDIR, "predictions-*.json"))):
        preds.extend(json.load(open(fn)))
    print("override predictions collected:", len(preds))
    assert len(preds) == 83, len(preds)

    rows = []
    for p in preds:
        key = (p["round"], p["player"])
        assert key in ans, key
        a = ans[key]
        assert p["baseline_kind"] == a["predicted_kind"], (key, p["baseline_kind"], a["predicted_kind"])
        final_ok = p["final_kind"] == a["actual_kind"]
        base_ok = a["correct"]
        rows.append({
            "round": p["round"], "player": p["player"],
            "baseline_kind": p["baseline_kind"], "final_kind": p["final_kind"],
            "actual_kind": a["actual_kind"],
            "decision": p["decision"], "criterion": p.get("criterion"),
            "evidence": p.get("evidence"), "reasoning": p.get("reasoning"),
            "baseline_correct": base_ok, "final_correct": final_ok,
        })

    total = sum(1 for r in rows if r["final_correct"])
    both = sum(1 for r in rows if r["final_correct"] and r["baseline_correct"])
    only_final = sum(1 for r in rows if r["final_correct"] and not r["baseline_correct"])
    only_base = sum(1 for r in rows if not r["final_correct"] and r["baseline_correct"])
    neither = sum(1 for r in rows if not r["final_correct"] and not r["baseline_correct"])
    overrides = [r for r in rows if r["decision"] == "override"]
    fixed = [r for r in overrides if r["final_correct"] and not r["baseline_correct"]]
    broke = [r for r in overrides if not r["final_correct"] and r["baseline_correct"]]
    neutral = [r for r in overrides if r["final_correct"] == r["baseline_correct"]]

    print("final score:", total, "/ 83")
    print(f"paired: both {both}, only-override {only_final}, only-baseline {only_base}, neither {neither} (net {only_final - only_base:+d})")
    print(f"overrides: {len(overrides)} total, fixed {len(fixed)}, broke {len(broke)}, neutral {len(neutral)}")
    print("overrides by criterion:", dict(Counter(r["criterion"] for r in overrides)))
    print("per-round:")
    for rnd in sorted({r["round"] for r in rows}):
        sub = [r for r in rows if r["round"] == rnd]
        b = sum(1 for r in sub if r["baseline_correct"])
        f = sum(1 for r in sub if r["final_correct"])
        print(f"  {rnd}: {f}/{len(sub)} (baseline {b}/{len(sub)}, {f-b:+d})")

    out = {
        "baseline_score": baseline_correct,
        "final_score": total,
        "paired": {"both": both, "only_override": only_final, "only_baseline": only_base, "neither": neither},
        "overrides": {"total": len(overrides), "fixed": len(fixed), "broke": len(broke), "neutral": len(neutral)},
        "rows": rows,
    }
    with open(os.path.join(RUNDIR, "scored-exception-override.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote scored-exception-override.json")

if __name__ == "__main__":
    main()
