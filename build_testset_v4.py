#!/usr/bin/env python3
"""Assemble testset-v4.json: testset-v3 (88) + 2 S5 patch questions (90).

Usage: python3 build_testset_v4.py
Reads:
  - testset-v3.json (88 questions, tracked)
  - traces/trace-2026-11-22-s5patch.json/trace-2026-11-22.json (new trace, 558 moves)
  - /home/hatch/workspace/verification-v1-testset/runs/testset-redesign-vision1-2026-11-22/facts-roundEvidence-fixed.json
    (fact base, fixed version -- same snapshot the other 88 questions used)
Writes (tracked):
  - testset-v4.json: v3's 88 + 2 new S5 questions, re-split A/B (same method
    as build_testset_v3.py: sort by (kind, season, round_index, player),
    assign A/B by alternating global index; fix one-sided rounds by swapping
    two same-kind questions).
Writes (runs/s5patch-2026-11-22/, gitignored review evidence):
  - prefixes-v4-new.json: walk-forward prefix + facts for the 2 new questions
    (same rules as build_prefixes.py: prefix = all trace moves strictly
    before the question's round; facts from rounds strictly before the
    question's round, fact_date <= event_real_date; own-round facts excluded;
    fact cannot describe this round's action itself -- checked by manual
    review of the audit flags).
  - prefix-audit-v4-new.json: validation results (3 checks + flags).

New questions (verified 2026-11-22, both in S5, both public actions):
  1. Baidu Q3 2026 capex (2026-11-16, RMB 7.35B, +116% YoY, FCF -4.57B),
     kind capex, player BIDU, round S5 1-1 (round_date 20260101).
     Source: Baidu Q3 2026 Form 6-K Ex 99.1 (2026-11-16); Zacks.
  2. NYT investigation (2026-11-18): Alibaba is Megaspeed's customer and
     financial backer; Megaspeed bought >$4B NVIDIA chips over several years,
     kind megaspeed, player ALI, round S5 5-1 (round_date 20261118).
     Source: NYT 2026-11-18 (via NeoTeo transcription).

Trace stays 558 moves (the two events are rewritten action texts on
existing moves, not new moves -- the converter requires exactly 18 moves
per round). Baseline 48/88 is not re-run; it is the 88-question reference.
"""
import json
import os
import re
from collections import Counter

TRACE = "traces/trace-2026-11-22-s5patch.json/trace-2026-11-22.json"
FACTS = ("/home/hatch/workspace/verification-v1-testset/runs/"
         "testset-redesign-vision1-2026-11-22/facts-roundEvidence-fixed.json")
RUN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "runs", "s5patch-2026-11-22")

DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
YM_RE = re.compile(r"20\d\d-\d\d")
Y_RE = re.compile(r"20\d\d")

NEW_QUESTIONS = [
    {
        "season": 5,
        "round_label": "1-1",
        "event_real_date": 20261116,
        "event_name": "Baidu Q3 2026 earnings: capex RMB 7.35B (+116% YoY)",
        "player": "BIDU",
        "kind": "capex",
        "action": "百度 Q3 资本开支 73.5 亿元。自由现金流转负",
        "source": ("百度 2026 年 Q3 财报（11-16，Form 6-K Ex 99.1）："
                   "资本开支 73.5 亿元，同比增 116%，自由现金流 -45.7 亿元"),
        "origin": "s5patch",
    },
    {
        "season": 5,
        "round_label": "5-1",
        "event_real_date": 20261118,
        "event_name": ("NYT investigation: Alibaba is Megaspeed's customer "
                       "and financial backer"),
        "player": "ALI",
        "kind": "megaspeed",
        "action": "纽约时报调查：阿里是 Megaspeed 客户与资金支持方",
        "source": ("纽约时报调查（11-18）：阿里是 Megaspeed 的客户与资金支持方；"
                   "Megaspeed 几年间购买逾 40 亿美元英伟达芯片"),
        "origin": "s5patch",
    },
]


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
    os.makedirs(RUN_DIR, exist_ok=True)
    t = json.load(open(TRACE))
    pmap = {p["id"]: p["key"] for p in t["players"]}
    pname = {p["key"]: p["name"] for p in t["players"]}
    round_idx = {}
    for m in t["moves"]:
        round_idx[(m["season"], m["round_label"])] = m["round_index"]
    assert len(t["moves"]) == 558, "trace must stay 558 moves"

    # --- trace_idx + round_date for the 2 new questions (from the new trace) ---
    for q in NEW_QUESTIONS:
        rd = next(m["date"] for m in t["moves"]
                  if m["season"] == q["season"] and m["round_label"] == q["round_label"])
        q["round_date"] = rd
        idx = [i for i, m in enumerate(t["moves"])
               if m["season"] == q["season"] and m["round_label"] == q["round_label"]
               and pmap[m["player"]] == q["player"]
               and m["action"] == q["action"]]
        assert len(idx) == 1, "new action must appear exactly once in trace: %s" % q["action"]
        q["trace_idx"] = idx[0]
        # sanity: the move's semantic kind must match the question kind
        assert t["moves"][idx[0]]["semantic_kind"] == q["kind"], \
            "semantic kind mismatch for %s" % q["action"]
        print("new question: %s %s %s (trace_idx %d, round_date %s)" % (
            q["player"], q["kind"], q["event_real_date"], q["trace_idx"], q["round_date"]))

    # --- assemble test set ---
    v3 = json.load(open("testset-v3.json"))
    questions = []
    for q in v3["questions"]:
        q = dict(q)
        q.pop("split", None)
        q.pop("q_id", None)
        questions.append(q)
    n_v3 = len(questions)
    questions.extend(dict(q) for q in NEW_QUESTIONS)

    def skey(q):
        return (q["kind"], q["season"],
                round_idx[(q["season"], q["round_label"])], q["player"])
    questions.sort(key=skey)
    for i, q in enumerate(questions):
        q["q_id"] = i
    for i, q in enumerate(questions):
        q["split"] = "A" if i % 2 == 0 else "B"

    def round_key(q):
        return (q["season"], q["round_label"])
    # fix one-sided rounds (2+ questions all on one side) by swapping.
    # Same-kind swap first (kind counts per side unchanged). If a question's
    # kind is a singleton (only 1 question in the whole set, e.g. S5 4-1's
    # huang_resign and overseas_rental), no same-kind partner exists, so
    # allow a cross-kind swap: the singleton kind just moves, and the
    # partner's kind must keep a question on its side (unless it is also
    # a singleton). The partner's round must not become one-sided.
    for _ in range(100):
        by_round = {}
        for q in questions:
            by_round.setdefault(round_key(q), []).append(q)
        one_sided = [rk for rk, qs in by_round.items()
                     if len(qs) >= 2 and len({q["split"] for q in qs}) == 1]
        if not one_sided:
            break
        fixed = False
        for rk in one_sided:
            qs = by_round[rk]
            side = qs[0]["split"]
            other = "B" if side == "A" else "A"
            for q1 in qs:
                kind_n = sum(1 for q in questions if q["kind"] == q1["kind"])
                partners = [q for q in questions
                            if q["kind"] == q1["kind"] and q["split"] == other
                            and round_key(q) != rk]
                if kind_n == 1:
                    partners += [q for q in questions
                                 if q["kind"] != q1["kind"] and q["split"] == other
                                 and round_key(q) != rk]
                for q2 in partners:
                    if q2["kind"] != q1["kind"]:
                        k2_total = sum(1 for q in questions if q["kind"] == q2["kind"])
                        if k2_total >= 2:
                            k2_n_other = sum(1 for q in questions
                                             if q["kind"] == q2["kind"] and q["split"] == other)
                            if k2_n_other < 2:
                                continue  # would empty q2's kind from `other`
                    r2 = by_round[round_key(q2)]
                    if len(r2) >= 2 and len({q["split"] for q in r2 if q is not q2} | {side}) == 1:
                        continue
                    q1["split"], q2["split"] = q2["split"], q1["split"]
                    fixed = True
                    break
                if fixed:
                    break
            if fixed:
                break
        if not fixed:
            print("could not fix one-sided rounds:", one_sided)
            break

    split = Counter(q["split"] for q in questions)
    new_qs = [q for q in questions if q.get("origin") == "s5patch"]
    ev_new = Counter((q["event_real_date"], q["event_name"]) for q in new_qs)
    dup_new = [k for k, n in ev_new.items() if n > 1]
    print("same-event duplicates among new questions:", dup_new)
    assert not dup_new, "unresolved same-event duplicates: %s" % dup_new
    by_kind = {}
    by_round = {}
    for q in questions:
        by_kind.setdefault(q["kind"], set()).add(q["split"])
        by_round.setdefault(round_key(q), set()).add(q["split"])
    kinds_one_sided = [k for k, s in by_kind.items()
                       if sum(1 for q in questions if q["kind"] == k) >= 2 and len(s) == 1]
    rounds_one_sided = [rk for rk, s in by_round.items()
                        if sum(1 for q in questions if round_key(q) == rk) >= 2 and len(s) == 1]
    print("split: A %d, B %d" % (split["A"], split["B"]))
    print("kinds with 2+ one-sided:", kinds_one_sided)
    print("rounds with 2+ one-sided:", rounds_one_sided)
    assert not kinds_one_sided and not rounds_one_sided, "split is one-sided somewhere"

    meta = {
        "name": "testset-v4 (testset-v3 + 2 S5 patch questions)",
        "n": len(questions),
        "split": {"A": split["A"], "B": split["B"]},
        "split_method": ("stratified: sorted by (kind, season, round_index, player), "
                         "assigned A/B by alternating global index; one-sided rounds "
                         "fixed by swapping two same-kind questions, or (for a singleton "
                         "kind with no same-kind partner, e.g. S5 4-1's huang_resign and "
                         "overseas_rental) by swapping with a question of another kind "
                         "while keeping every kind with 2+ questions on both sides; "
                         "each kind with 2+ questions and each round with 2+ questions "
                         "appears in both sets"),
        "v3_kept": n_v3,
        "new_from_s5patch": 2,
        "new_S5": 2,
        "gap_to_140": 140 - len(questions),
        "note": ("trace stays 558 moves: the two S5 events are rewritten action texts "
                 "on existing moves (S5 1-1 BIDU capex, S5 5-1 ALI megaspeed), not new "
                 "moves -- the converter requires exactly 18 moves per round. "
                 "Baseline 48/88 is the 88-question reference, not re-run."),
    }
    with open("testset-v4.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "questions": questions}, f, ensure_ascii=False, indent=1)
    print("wrote testset-v4.json: n=%d, A %d, B %d, gap to 140: %d" % (
        len(questions), split["A"], split["B"], meta["gap_to_140"]))

    # --- walk-forward prefixes + facts for the 2 new questions ---
    facts_raw = json.load(open(FACTS))
    facts = []
    for e in facts_raw:
        rk = (e["season"], round_idx[(e["season"], e["round_label"])])
        for it in e.get("items", []):
            d, conf = fact_date(it.get("label", ""), e["date"])
            facts.append({
                "round": e["round"], "season": e["season"],
                "round_label": e["round_label"], "round_key": list(rk),
                "ref": it.get("ref", ""), "label": it.get("label", ""),
                "fact_date": d, "date_confidence": conf,
            })

    out = []
    audit = {"n_questions": len(NEW_QUESTIONS), "checks": [], "flags": []}
    for qi, q in enumerate(NEW_QUESTIONS):
        qk = (q["season"], round_idx[(q["season"], q["round_label"])])
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
        ev_date = int(q["event_real_date"])
        qfacts = [f for f in facts
                  if tuple(f["round_key"]) < qk and f["fact_date"] <= ev_date]
        out.append({
            "q_id": qi, "trace_idx": q["trace_idx"], "season": q["season"],
            "round": "S%d %s" % (q["season"], q["round_label"]),
            "round_index": qk[1], "player": q["player"], "kind": q["kind"],
            "event_real_date": q["event_real_date"],
            "event_name": q["event_name"], "source": q["source"],
            "prefix": prefix, "prefix_n": len(prefix),
            "facts": qfacts, "facts_n": len(qfacts),
        })
        bad_prefix = [p for p in prefix
                      if (p["season"], round_idx[(p["season"], p["round"].split(" ", 1)[1])]) >= qk]
        bad_facts = [f for f in qfacts if f["fact_date"] > ev_date]
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
                    "q_id": qi, "round": "S%d %s" % (q["season"], q["round_label"]),
                    "player": q["player"], "kind": q["kind"],
                    "event_name": q["event_name"], "fact_round": f["round"],
                    "fact_date": f["fact_date"], "fact_label": f["label"][:160],
                    "why_flagged": why,
                })
        audit["checks"].append({
            "q_id": qi, "round": "S%d %s" % (q["season"], q["round_label"]),
            "player": q["player"], "kind": q["kind"],
            "prefix_n": len(prefix), "prefix_violations": len(bad_prefix),
            "facts_n": len(qfacts), "fact_date_violations": len(bad_facts),
            "check3_flags": len(flags),
        })
        audit["flags"].extend(flags)

    with open(os.path.join(RUN_DIR, "prefixes-v4-new.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(RUN_DIR, "prefix-audit-v4-new.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print("wrote prefixes-v4-new.json (%d questions)" % len(out))
    print("prefix violations: %d, fact date violations: %d, check3 flags: %d" % (
        sum(c["prefix_violations"] for c in audit["checks"]),
        sum(c["fact_date_violations"] for c in audit["checks"]),
        len(audit["flags"])))
    for c in audit["checks"]:
        print("  q%d %s %s: prefix %d moves, facts %d" % (
            c["q_id"], c["player"], c["kind"], c["prefix_n"], c["facts_n"]))
    for fl in audit["flags"]:
        print("  FLAG q%d %s (%s): %s | %s" % (
            fl["q_id"], fl["player"], fl["why_flagged"], fl["fact_round"], fl["fact_label"]))


if __name__ == "__main__":
    main()
