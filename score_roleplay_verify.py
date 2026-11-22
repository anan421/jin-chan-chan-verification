#!/usr/bin/env python3
"""Independent verification of the role-play pilot score.

Recomputes per-batch totals straight from the prediction files and
testset-v5.json (a different code path from score_roleplay.py) and
compares against runs/roleplay-pilot-2026-11-22/predictions/score-roleplay.json.
Exits non-zero on any mismatch (so a tampered score file is caught).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRED = HERE / "runs" / "roleplay-pilot-2026-11-22" / "predictions"


def main():
    ts = json.loads((HERE / "testset-v5.json").read_text(encoding="utf-8"))
    truth = {q["q_id"]: q["kind"] for q in ts["questions"]}
    scored = json.loads((PRED / "score-roleplay.json").read_text(encoding="utf-8"))

    seen = {}
    for f in sorted(PRED.glob("predictions-*.json")):
        batch = f.stem.split("-")[1]
        for p in json.loads(f.read_text(encoding="utf-8")):
            seen.setdefault(batch, []).append(p)

    ok = True
    for batch, ps in sorted(seen.items()):
        total = sum(1 for p in ps if p["predicted_kind"] == truth[p["q_id"]])
        want = scored["batches"][batch]["total"]
        if total != want:
            print(f"MISMATCH {batch}: recomputed {total} != scored {want}")
            ok = False
        else:
            print(f"OK {batch}: {total}/{len(ps)}")
        # q5 check
        q5 = [p for p in ps if p["q_id"] == 5][0]
        want5 = scored["q5"][batch]
        got5 = q5["predicted_kind"] == truth[5]
        if got5 != want5:
            print(f"MISMATCH {batch} q5: recomputed {got5} != scored {want5}")
            ok = False
    # role-play batches must carry roleplay_text + forecast fields
    for batch, ps in sorted(seen.items()):
        if batch.startswith("R"):
            for p in ps:
                if not p.get("roleplay_text") or not p.get("forecast_prop") \
                        or p.get("forecast_prob") is None:
                    print(f"MISSING role-play fields in {batch} q{p['q_id']}")
                    ok = False
    print("VERIFY " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
