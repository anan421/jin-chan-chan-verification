#!/usr/bin/env python3
"""Per-batch clean scores for baseline88.

A question counts as leaked for a batch only when THAT batch's predictor
used a fact describing the round's own action (same specific event/deal/
release). Leaks are per-batch: the same question may be clean in one batch
and leaked in another. This is different from score88.py --exclude, which
drops a question from ALL batches (global-clean, 65 questions).

Reads runs/baseline88-2026-11-22/scored-baseline88.json and
leaks88.json (same directory). Writes score-clean88-perbatch.json.
"""
import json
from pathlib import Path

RUN = Path("runs/baseline88-2026-11-22")
scored = json.loads((RUN / "scored-baseline88.json").read_text(encoding="utf-8"))
leaks = json.loads((RUN / "leaks88.json").read_text(encoding="utf-8"))
BATCHES = ["main", "control1", "control2", "control3"]

out = {"leaks_per_batch": {b: sorted(leaks[b]) for b in BATCHES}, "per_batch": {}}
# Extra exclusion (not a leak): control1 q86 has one fact dated "2025-01"
# (month precision, unparsable). The fact is a different January event, not
# the round action, but its date cannot be verified <= the round date, so
# q86 is dropped from control1's clean score as a conservative measure.
EXTRA_EXCLUDE = {"control1": [86]}
out["extra_excluded_not_leaks"] = EXTRA_EXCLUDE
for b in BATCHES:
    bad = set(leaks[b]) | set(EXTRA_EXCLUDE.get(b, []))
    kept = [r for r in scored if r["q_id"] not in bad]
    cor = sum(r[b + "_correct"] for r in kept)
    out["per_batch"][b] = {
        "clean_correct": cor,
        "clean_n": len(kept),
        "clean_pct": round(100 * cor / len(kept), 1),
        "excluded_q_ids": sorted(bad),
    }

# pooled clean rate across batches (each batch on its own clean set)
tot_c = sum(v["clean_correct"] for v in out["per_batch"].values())
tot_n = sum(v["clean_n"] for v in out["per_batch"].values())
out["pooled_clean"] = {
    "correct": tot_c, "n": tot_n, "pct": round(100 * tot_c / tot_n, 1)
}
(RUN / "score-clean88-perbatch.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(json.dumps(out, ensure_ascii=False, indent=1))
