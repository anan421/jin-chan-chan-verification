#!/usr/bin/env python3
"""Second independent scorer for the 88-question baseline (cross-check).

Written independently of score88.py: it reads testset-v3.json and the
prediction files directly, counts correct answers per batch with plain
loops, and asserts the totals match score-summary88.json. If the two
scripts disagree, stop and fix the scorer before reporting any score.
"""
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs" / "baseline88-2026-11-22"
BATCHES = ["main", "control1", "control2", "control3"]


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    testset = json.loads((ROOT / "testset-v3.json").read_text(encoding="utf-8"))
    answers = {}
    for q in testset["questions"]:
        answers[q["q_id"]] = q["kind"]
    totals = {}
    per_kind = {}
    per_round = {}
    for b in BATCHES:
        correct = 0
        seen = set()
        kc = Counter()
        kt = Counter()
        rc = Counter()
        rt = Counter()
        for path in sorted(RUNS.glob(f"predictions-{b}-S*-*.json")):
            for p in json.loads(path.read_text(encoding="utf-8")):
                qid = p["q_id"]
                if qid in seen:
                    fail(f"{b}: duplicate q_id {qid}")
                seen.add(qid)
                kind = answers[qid]
                kt[kind] += 1
                rnd = next(q for q in testset["questions"] if q["q_id"] == qid)
                rkey = f"S{rnd['season']} {rnd['round_label']}"
                rt[rkey] += 1
                if p["predicted_kind"] == kind:
                    correct += 1
                    kc[kind] += 1
                    rc[rkey] += 1
        if seen != set(range(88)):
            fail(f"{b}: covers {len(seen)} questions, want 88")
        totals[b] = correct
        per_kind[b] = {k: [kc[k], kt[k]] for k in sorted(kt)}
        per_round[b] = {k: [rc[k], rt[k]] for k in sorted(rt)}

    summary = json.loads((RUNS / "score-summary88.json").read_text(encoding="utf-8"))
    ok = True
    if summary["baseline_main"] != totals["main"]:
        print(f"MISMATCH main: score88 says {summary['baseline_main']}, verify says {totals['main']}")
        ok = False
    for b in ("control1", "control2", "control3"):
        if summary["control_scores"][b] != totals[b]:
            print(f"MISMATCH {b}: score88 says {summary['control_scores'][b]}, verify says {totals[b]}")
            ok = False
    for b in BATCHES:
        for k, (c, t) in per_kind[b].items():
            s = summary["by_kind"][k]
            if s[b] != c or s["n"] != t:
                print(f"MISMATCH {b} kind {k}: score88 {s}, verify {[c, t]}")
                ok = False
    if not ok:
        fail("score88.py and score88_verify.py disagree; fix the scorer")
    out = {"totals": totals, "per_kind": per_kind, "per_round": per_round,
           "cross_check": "PASS: matches score-summary88.json"}
    (RUNS / "verify88.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cross-check PASS: main={totals['main']} control1={totals['control1']} "
          f"control2={totals['control2']} control3={totals['control3']}")
    print("wrote verify88.json")


if __name__ == "__main__":
    main()
