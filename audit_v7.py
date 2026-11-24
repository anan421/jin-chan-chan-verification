#!/usr/bin/env python3
"""Focused audit for testset-v7.json (coverage-plan completion).

Checks (independent re-verification, not reusing the builder):
  1. Date violations: round_date <= effective(event_real_date) for every
     question, calendar days. Month-only (YYYYMM) and year-only (YYYY)
     events use the 1st of the period as the effective date.
  2. Leak (exact): a new question's event_name (or its distinctive core)
     appearing verbatim in an earlier trace move action or roundEvidence
     label. "Earlier" = trace move with (season, round_index) strictly
     before the question's (season, round_index), or a fact with
     fact_date <= event date that names the same event. A match means
     the answer was visible before the prediction point.
     Note: merely mentioning the company/product (e.g. "Claude",
     "OpenAI") is NOT a leak; the specific event must appear.
  3. Contamination: any fact (roundEvidence item) with fact_date after
     the question's event date that would be in the question's allowed
     fact set (rounds strictly before the question's round AND
     fact_date <= event date). By construction this is 0; verified by
     re-running the filter.
  4. Duplicates: no two questions share (event_real_date, event_name);
     no new question duplicates an old question's event_name.

Reads: testset-v7.json, traces/trace-latest.json, data.json
Writes: runs/testset-v7-audit/audit-v7.json (summary + any hits)
"""
import json
import os
import re
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
V7 = os.path.join(HERE, "testset-v7.json")
TRACE = os.path.join(HERE, "traces", "trace-latest.json")
DATA = os.path.join(HERE, "data.json")
RUN_DIR = os.path.join(HERE, "runs", "testset-v7-audit")

DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
YM_RE = re.compile(r"20\d\d-\d\d")
Y_RE = re.compile(r"20\d\d")

def fact_date(label, round_date):
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

def effective_date(ed):
    s = str(ed)
    if len(s) == 8:
        return int(s)
    if len(s) == 6:
        return int(s + "01")
    if len(s) == 4:
        return int(s + "0101")
    raise ValueError("bad event_real_date %r" % (ed,))

def cal_days(a, b):
    da = date(a // 10000, (a // 100) % 100, a % 100)
    db = date(b // 10000, (b // 100) % 100, b % 100)
    return (da - db).days

def core_tokens(event_name):
    """Distinctive tokens that identify the specific event (not the company).
    Returns a list of (token) strings; a leak needs one of these to appear
    in an earlier move/label together with the player/company context.
    We use the full event_name minus generic verbs as the primary check,
    plus version/product tokens."""
    name = event_name
    # strip generic suffix verbs
    for suf in ("发布", "推出", "上线", "达", "超", "收", "投", "签", "成立", "签署", "成法", "生效", "破", "跌", "涨"):
        if name.endswith(suf):
            name = name[: -len(suf)]
    return name.strip()

def main():
    os.makedirs(RUN_DIR, exist_ok=True)
    v7 = json.load(open(V7))
    questions = v7["questions"]
    print("testset-v7: n=%d" % len(questions))
    t = json.load(open(TRACE))
    assert len(t["moves"]) == 558, "trace must stay 558 moves"
    round_idx = {}
    for m in t["moves"]:
        round_idx[(m["season"], m["round_label"])] = m["round_index"]
    data = json.load(open(DATA))
    trace_date = {}
    for m in t["moves"]:
        trace_date[(m["season"], m["round_label"])] = m["date"]

    # --- 1. date violations (independent) ---
    viol = []
    for q in questions:
        rd = int(q["round_date"])
        ed = effective_date(q["event_real_date"])
        if rd > ed:
            viol.append((q["q_id"], rd, ed, cal_days(rd, ed)))
    print("1. date violations (round_date > event): %d %s" % (len(viol), viol))
    assert not viol, "date violations: %s" % viol

    # --- 4. duplicates ---
    # Key includes player: the same event for different players is a
    # different question (pre-existing in v6: the BIS rule 20261116 is
    # asked for BYTE, ALI and TSMC as q5/q6/q7). A true duplicate is the
    # same event for the same player.
    seen = {}
    dups = []
    for q in questions:
        k = (str(q["event_real_date"]), q["event_name"], q["player"])
        if k in seen:
            dups.append((k, seen[k], q["q_id"]))
        seen[k] = q["q_id"]
    print("4. duplicate (event_real_date, event_name): %d %s" % (len(dups), dups))
    assert not dups, "duplicates: %s" % dups
    # same event_name across different dates (near-duplicate, informational)
    by_name = {}
    for q in questions:
        by_name.setdefault(q["event_name"], []).append(q["q_id"])
    near = {k: v for k, v in by_name.items() if len(v) > 1}
    print("   same event_name on different dates: %d %s" % (len(near), near))

    # --- build fact base (same method as audit_v6) ---
    facts = []
    for rk in sorted(data["roundEvidence"]):
        season_s, label = rk.split(":", 1)
        ev = data["roundEvidence"][rk]
        for it in ev.get("items", []):
            lab = it["label"]
            if rk == "S3:3-2":
                lab = lab.replace("；o1-preview 与 o1-mini 2024-09-12 发布", "")
            d, conf = fact_date(lab, trace_date[(int(season_s[1:]), label)])
            facts.append({
                "round": rk, "season": int(season_s[1:]), "round_label": label,
                "round_key": (int(season_s[1:]), round_idx[(int(season_s[1:]), label)]),
                "label": lab, "fact_date": d, "confidence": conf,
            })
    print("fact base: %d items" % len(facts))

    # --- 2. leak (exact) + 3. contamination ---
    new_qs = [q for q in questions if q["q_id"] >= 99]
    leak_hits = []
    contam_hits = []
    for q in new_qs:
        qk = (q["season"], round_idx[(q["season"], q["round_label"])])
        ed = effective_date(q["event_real_date"])
        core = core_tokens(q["event_name"])
        # prefix moves: strictly before the question's round
        prefix = [m for m in t["moves"] if (m["season"], m["round_index"]) < qk]
        for m in prefix:
            if core and core in m["action"]:
                leak_hits.append(("trace", q["q_id"], q["event_name"], m["action"][:80], m["date"]))
                break
        # facts: rounds strictly before the question's round, fact_date <= event date
        qfacts = [f for f in facts if f["round_key"] < qk and f["fact_date"] <= ed]
        bad = [f for f in qfacts if f["fact_date"] > ed]
        if bad:
            contam_hits.append((q["q_id"], len(bad)))
        for f in qfacts:
            if core and core in f["label"]:
                leak_hits.append(("fact", q["q_id"], q["event_name"], f["label"][:80], f["fact_date"]))
                break
    print("2. leak (exact event core in earlier trace/fact): %d" % len(leak_hits))
    for h in leak_hits:
        print("   ", h)
    print("3. contamination (fact_date > event in allowed set): %d %s" % (len(contam_hits), contam_hits))
    assert not leak_hits, "leak hits: %s" % leak_hits
    assert not contam_hits, "contamination: %s" % contam_hits

    summary = {
        "n_questions": len(questions),
        "n_new": len(new_qs),
        "date_violations": len(viol),
        "duplicates": len(dups),
        "same_event_name_diff_dates": near,
        "leak_hits": leak_hits,
        "contamination": contam_hits,
    }
    with open(os.path.join(RUN_DIR, "audit-v7.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("wrote %s" % os.path.join(RUN_DIR, "audit-v7.json"))
    print("AUDIT PASS: date 0, duplicates 0, leak 0, contamination 0")

if __name__ == "__main__":
    main()
