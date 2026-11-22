#!/usr/bin/env python3
"""Audit the baseline predictions' facts_used.

Checks (automated):
  - Every facts_used entry has fact/date/source.
  - Every facts_used date is on or before the round date (date violation
    otherwise). Dates may be 'YYYY-MM-DD' or 'YYYYMMDD'.
  - Every prediction has predicted_kind/confidence/reasoning/facts_used.
  - Every predicted_kind is in the vocabulary.
Writes: audit88.json (summary), date-violations88.json (violations list).
The leakage check (a fact naming the player's own action this round) is
manual: the coordinator reads all predictions' facts_used.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs" / "baseline88-2026-11-22"
BATCHES = ["main", "control1", "control2", "control3"]


def norm_date(s):
    return str(s).replace("-", "")


def main():
    testset = json.loads((ROOT / "testset-v3.json").read_text(encoding="utf-8"))
    meta = {q["q_id"]: (f"S{q['season']} {q['round_label']}", q["player"], q["round_date"])
            for q in testset["questions"]}
    qfile = json.loads((RUNS / "questions-S4-1-1.json").read_text(encoding="utf-8"))
    vocab = set(qfile["vocabulary"])
    violations = []
    n_preds = 0
    n_facts = 0
    problems = []
    for b in BATCHES:
        for path in sorted(RUNS.glob(f"predictions-{b}-S*-*.json")):
            preds = json.loads(path.read_text(encoding="utf-8"))
            for p in preds:
                n_preds += 1
                idx = p["q_id"]
                if idx not in meta:
                    problems.append(f"{b}/{path.name}: unknown q_id {idx}")
                    continue
                rnd, player, rdate = meta[idx]
                if p.get("player") != player:
                    problems.append(f"{b} q_id {idx}: player {p.get('player')} != {player}")
                for f in ("predicted_kind", "confidence", "reasoning", "facts_used"):
                    if f not in p:
                        problems.append(f"{b} q_id {idx}: missing field {f}")
                if p.get("predicted_kind") not in vocab:
                    problems.append(f"{b} q_id {idx}: kind {p.get('predicted_kind')} not in vocabulary")
                for fu in p.get("facts_used", []):
                    n_facts += 1
                    for f in ("fact", "date", "source"):
                        if f not in fu:
                            problems.append(f"{b} q_id {idx}: facts_used entry missing {f}: {fu}")
                    if "date" in fu:
                        try:
                            d = norm_date(fu["date"])
                            if len(d) != 8 or not d.isdigit():
                                problems.append(f"{b} q_id {idx}: unparsable fact date {fu['date']}")
                            elif int(d) > int(rdate):
                                violations.append({
                                    "batch": b, "q_id": idx, "round": rnd,
                                    "player": player, "fact": fu.get("fact", ""),
                                    "date": fu["date"], "round_date": str(rdate),
                                })
                        except Exception as e:
                            problems.append(f"{b} q_id {idx}: bad fact date {fu['date']}: {e}")
    summary = {
        "predictions_checked": n_preds,
        "facts_checked": n_facts,
        "date_violations": len(violations),
        "problems": problems,
    }
    (RUNS / "audit88.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (RUNS / "date-violations88.json").write_text(
        json.dumps(violations, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"predictions={n_preds} facts={n_facts} date_violations={len(violations)} problems={len(problems)}")
    for v in violations:
        print(f"  VIOLATION {v['batch']} q_id={v['q_id']} {v['round']} {v['player']} fact_date={v['date']} round_date={v['round_date']}: {v['fact'][:80]}")
    for p in problems:
        print(f"  PROBLEM {p}")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
