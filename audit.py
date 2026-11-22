#!/usr/bin/env python3
"""Audit the new predictions' facts_used.

Checks (automated):
  - Every facts_used entry has fact/date/source.
  - Every facts_used date is on or before the round date (date violation
    otherwise). Dates may be 'YYYY-MM-DD' or 'YYYYMMDD'.
  - Every prediction has predicted_kind/confidence/reasoning/facts_used.
Writes: audit.json (summary), date-violations.json (violations list).
The leakage check (a fact naming the player's own action this round) is
manual: the coordinator reads all 83 predictions' facts_used.
"""
import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs" / "forward-guidance-vision1-2026-11-22"


def norm_date(s):
    return str(s).replace("-", "")


def main():
    test83 = json.loads((RUNS / "test83.json").read_text(encoding="utf-8"))
    meta = {pos: (f"S{row['season']} {row['round_label']}", row["player"], row["date"])
            for pos, row in enumerate(test83)}
    violations = []
    n_preds = 0
    n_facts = 0
    problems = []
    for path in sorted(list(RUNS.glob("predictions-S*-*.json"))
                       + list(RUNS.glob("predictions-control-S*-*.json"))):
        if "full83" in path.name:
            continue
        preds = json.loads(path.read_text(encoding="utf-8"))
        for p in preds:
            n_preds += 1
            idx = p["q_idx"]
            if idx not in meta:
                problems.append(f"{path.name}: unknown q_idx {idx}")
                continue
            rnd, player, rdate = meta[idx]
            if p.get("player") != player:
                problems.append(f"q_idx {idx}: player {p.get('player')} != {player}")
            for f in ("predicted_kind", "confidence", "reasoning", "facts_used"):
                if f not in p:
                    problems.append(f"q_idx {idx}: missing field {f}")
            for fu in p.get("facts_used", []):
                n_facts += 1
                for f in ("fact", "date", "source"):
                    if f not in fu:
                        problems.append(f"q_idx {idx}: facts_used entry missing {f}: {fu}")
                if "date" in fu:
                    try:
                        d = norm_date(fu["date"])
                        if len(d) != 8 or not d.isdigit():
                            problems.append(f"q_idx {idx}: unparsable fact date {fu['date']}")
                        elif int(d) > int(rdate):
                            violations.append({
                                "q_idx": idx, "round": rnd, "player": player,
                                "fact": fu.get("fact", ""), "date": fu["date"],
                                "round_date": str(rdate),
                            })
                    except Exception as e:
                        problems.append(f"q_idx {idx}: bad fact date {fu['date']}: {e}")
    summary = {
        "predictions_checked": n_preds,
        "facts_checked": n_facts,
        "date_violations": len(violations),
        "problems": problems,
    }
    (RUNS / "audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNS / "date-violations.json").write_text(
        json.dumps(violations, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"predictions={n_preds} facts={n_facts} date_violations={len(violations)} problems={len(problems)}")
    for v in violations:
        print(f"  VIOLATION q_idx={v['q_idx']} {v['round']} {v['player']} fact_date={v['date']} round_date={v['round_date']}: {v['fact'][:80]}")
    for p in problems:
        print(f"  PROBLEM {p}")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
