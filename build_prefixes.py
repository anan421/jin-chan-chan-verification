#!/usr/bin/env python3
"""Build walk-forward prefixes for S1-S3 questions.

Usage: python3 build_prefixes.py
Reads:
  - /home/hatch/workspace/verification/traces/trace-latest.json (trace, single source)
  - runs/walkforward-vision1-2026-11-22/s1-review.json, s2-review.json, s3-review.json
    (kept questions only; verdict == 'keep')
  - /home/hatch/workspace/verification-v1-testset/runs/testset-redesign-vision1-2026-11-22/facts-roundEvidence-fixed.json
    (fact base, fixed version)
Writes (runs/walkforward-vision1-2026-11-22/, gitignored review evidence):
  - prefixes.json: one record per kept question:
      {q_id, trace_idx, season, round, round_index, player, kind, event_real_date,
       event_name, source, prefix: [...], prefix_n, facts: [...], facts_n}
  - prefix-audit.json: validation results (3 checks + flags for manual review)

Prefix rule (strict walk-forward): prefix = all trace moves with
(season, round_index) strictly before the question's (season, round_index),
in trace order. S1 round 1 questions get an empty prefix (only the opening).
Fact rule: facts from rounds strictly before the question's round
(by season/round_index order), with fact_date <= event_real_date.
Own-round facts are excluded outright (they are mostly the round headline,
which is exactly what the 'no describing the action' rule guards against).
Fact date: first YYYY-MM-DD in the label (exact); else first YYYY-MM
(mid-month, approx); else first YYYY (Dec 31, approx); else the round date
(approx). date_confidence records exact/approx.
"""
import json
import os
import re

TRACE = "/home/hatch/workspace/verification/traces/trace-latest.json"
FACTS = ("/home/hatch/workspace/verification-v1-testset/runs/"
         "testset-redesign-vision1-2026-11-22/facts-roundEvidence-fixed.json")
RUN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "runs", "walkforward-vision1-2026-11-22")
REVIEW_FILES = ["s1-review.json", "s2-review.json", "s3-review.json"]
# Same-event duplicates: drop these trace_idx (keep the primary actor).
# Must match build_testset_v3.py DEDUP.
DEDUP_DROP = {91, 146, 166}

DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
YM_RE = re.compile(r"20\d\d-\d\d")
Y_RE = re.compile(r"20\d\d")


def fact_date(label, round_date):
    """Return (date_int YYYYMMDD, confidence 'exact'/'approx')."""
    m = DATE_RE.search(label)
    if m:
        return int(m.group(0).replace("-", "")), "exact"
    m = YM_RE.search(label)
    if m:
        y, mo = m.group(0).split("-")
        return int(y + mo + "15"), "approx"
    m = Y_RE.search(label)
    if m:
        return int(m.group(0) + "1231"), "approx"
    return int(round_date), "approx"


def main():
    t = json.load(open(TRACE))
    pmap = {p["id"]: p["key"] for p in t["players"]}
    pname = {p["key"]: p["name"] for p in t["players"]}
    # (season, round_label) -> round_index
    round_idx = {}
    for m in t["moves"]:
        round_idx[(m["season"], m["round_label"])] = m["round_index"]
    # order key for rounds
    def rkey(season, label):
        return (season, round_idx[(season, label)])

    # kept questions
    kept = []
    for fn in REVIEW_FILES:
        p = os.path.join(RUN_DIR, fn)
        if not os.path.exists(p):
            print("missing %s (reviewer not done yet), skipping" % fn)
            continue
        for r in json.load(open(p)):
            if r.get("verdict") == "keep" and r["trace_idx"] not in DEDUP_DROP:
                kept.append(r)
    print("kept questions: %d" % len(kept))

    # facts: (season, round_label, date, ref, label)
    facts_raw = json.load(open(FACTS))
    facts = []
    for e in facts_raw:
        rk = rkey(e["season"], e["round_label"])
        for it in e.get("items", []):
            d, conf = fact_date(it.get("label", ""), e["date"])
            facts.append({
                "round": e["round"],
                "season": e["season"],
                "round_label": e["round_label"],
                "round_key": list(rk),
                "ref": it.get("ref", ""),
                "label": it.get("label", ""),
                "fact_date": d,
                "date_confidence": conf,
            })

    out = []
    audit = {"n_questions": len(kept), "checks": [], "flags": []}
    for qi, q in enumerate(kept):
        qk = rkey(q["season"], q["round"].split(" ", 1)[1])
        # prefix: moves strictly before the question's round
        prefix = []
        for i, m in enumerate(t["moves"]):
            mk = (m["season"], m["round_index"])
            if mk < qk:
                prefix.append({
                    "trace_idx": i,
                    "season": m["season"],
                    "round": "S%d %s" % (m["season"], m["round_label"]),
                    "player": pmap[m["player"]],
                    "action": m["action"],
                    "semantic_kind": m["semantic_kind"],
                    "date": m["date"],
                })
        # facts: rounds strictly before the question's round, date <= event date
        ev_date = int(q["event_real_date"])
        qfacts = [f for f in facts
                  if tuple(f["round_key"]) < qk and f["fact_date"] <= ev_date]
        rec = {
            "q_id": qi,
            "trace_idx": q["trace_idx"],
            "season": q["season"],
            "round": q["round"],
            "round_index": qk[1],
            "player": q["player"],
            "kind": q["kind"],
            "event_real_date": q["event_real_date"],
            "event_name": q.get("event_name", ""),
            "source": q.get("source", ""),
            "prefix": prefix,
            "prefix_n": len(prefix),
            "facts": qfacts,
            "facts_n": len(qfacts),
        }
        out.append(rec)
        # check 1: prefix moves all strictly before the question's round
        bad_prefix = [p for p in prefix
                      if (p["season"], round_idx[(p["season"], p["round"].split(" ", 1)[1])]) >= qk]
        # check 2: facts all <= event date (filter guarantees it; verify)
        bad_facts = [f for f in qfacts if f["fact_date"] > ev_date]
        # check 3 (flag for manual review): fact label mentions the question's player
        # (by key or Chinese name) or the fact date equals the event date
        flags = []
        cname = pname.get(q["player"], "")
        for f in qfacts:
            why = None
            if q["player"] in f["label"] or (cname and cname in f["label"]):
                why = "mentions player"
            elif f["fact_date"] == ev_date:
                why = "date == event date"
            if why:
                flags.append({
                    "q_id": qi, "round": q["round"], "player": q["player"],
                    "kind": q["kind"], "event_name": q.get("event_name", ""),
                    "fact_round": f["round"], "fact_date": f["fact_date"],
                    "fact_label": f["label"][:120],
                    "why_flagged": why,
                })
        audit["checks"].append({
            "q_id": qi, "round": q["round"], "player": q["player"],
            "kind": q["kind"], "prefix_n": len(prefix),
            "prefix_violations": len(bad_prefix),
            "facts_n": len(qfacts), "fact_date_violations": len(bad_facts),
            "check3_flags": len(flags),
        })
        audit["flags"].extend(flags)

    with open(os.path.join(RUN_DIR, "prefixes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(RUN_DIR, "prefix-audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print("wrote prefixes.json (%d questions)" % len(out))
    print("wrote prefix-audit.json")
    print("total prefix moves: %d, total facts: %d, check3 flags: %d" % (
        sum(r["prefix_n"] for r in out), sum(r["facts_n"] for r in out),
        len(audit["flags"])))
    print("prefix violations: %d, fact date violations: %d" % (
        sum(c["prefix_violations"] for c in audit["checks"]),
        sum(c["fact_date_violations"] for c in audit["checks"])))


if __name__ == "__main__":
    main()
