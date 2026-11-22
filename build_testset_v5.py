#!/usr/bin/env python3
"""Assemble testset-v5.json: testset-v4 (90) + 9 round-6 S5 patch questions (99).

Usage: python3 build_testset_v5.py
Reads:
  - testset-v4.json (90 questions, tracked)
  - traces/trace-latest.json (new trace, 558 moves, post-patch)
  - /home/hatch/workspace/verification-v1-testset/runs/testset-redesign-vision1-2026-11-22/facts-roundEvidence-fixed.json
    (old fact base; the v5 fact base is regenerated from the current
    data.json roundEvidence in runs/s5patch-round6-2026-11-22/ and diffed
    against this file -- the only allowed differences are additions)
Writes (tracked):
  - testset-v5.json: v4's 90 (with date fixes) + 9 new S5 questions,
    re-split A/B (same method as build_testset_v4.py: sort by (kind,
    season, round_index, player), assign A/B by alternating global index;
    fix one-sided rounds by swapping, with the cross-kind swap guards).
Writes (runs/s5patch-round6-2026-11-22/, gitignored review evidence):
  - facts-roundEvidence-v5.json: regenerated fact base.
  - prefixes-v5-new.json: walk-forward prefix + facts for the 9 new
    questions (same rules as build_prefixes.py / build_testset_v4.py).
  - prefix-audit-v5-new.json: validation results (3 checks + flags).

Date fixes (round-5 report item 5; see design/s5patch-round6-2026-11-22.md):
  - v4 q13 (MSFT capex, S3 6-1): round_date 20241201 -> 20241030
    (round date was 32 days AFTER the event; prediction point must be
    on/before the event date).
  - S5 1-1 (6 questions, v4 q_ids 0, 14, 15, 16, 17, 38): round_date
    20260101 -> each question's event_real_date. S5 1-1 has no single
    true date: its events span 2026-01-06 to 2026-11-19, and the page's
    "2026 年上半年" label does not describe its content. A single date
    cannot work (2026-10-26, the S-1 filing, would sit after the Jan/May
    events). Each question's prediction point is its own event date.
  - v4 q32 (v3 q31; MSFT energy, S4 3-2): round_date 20250601 -> 20240920
    (event 8 months BEFORE the round).
  - The new SFTB 1-1 question gets the same S5 1-1 treatment:
    round_date = event date 20260914, not the trace date 20260101.
  Each fixed question carries a round_date_note recording the fix.

q57 de-dup (round-5 report item 6): NO question is removed. The duplicate
was old83 q58 (S5 3-2 BYTE overseas_rental, same Bloomberg 11-17 Aolani
event as old83 q65). The v3 redesign already dropped q58 and kept q65
(see design/testset-redesign-vision1.md lines 36-38). testset-v4 holds
exactly one overseas_rental question (v4 q59 = v3 q57 = old83 q65).
Removing it would leave the kind with zero questions. So v5 = 90 + 9 = 99,
not 98. See the patch report for the full verification.

Kind-field fix (round-5 report item 7): the prev_round_kinds field is
removed from the predictor-facing question files by build_questions_v5.py
in this worktree (it drops the field at the context builder, not just at
the emitter). This script only assembles the test set; the question files
are built separately.
"""
import json
import os
import re
from collections import Counter

TRACE = "traces/trace-latest.json"
OLD_FACTS = ("/home/hatch/workspace/verification-v1-testset/runs/"
             "testset-redesign-vision1-2026-11-22/facts-roundEvidence-fixed.json")
RUN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "runs", "s5patch-round6-2026-11-22")

DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
YM_RE = re.compile(r"20\d\d-\d\d")
Y_RE = re.compile(r"20\d\d")

# (v4 q_id, player, kind, old round_date, new round_date, note)
DATE_FIXES = [
    (13, "MSFT", "capex", 20241201, 20241030,
     "round date was 32 days AFTER the event (2024-10-30); prediction point "
     "must be on/before the event date, so round_date = event date."),
    (0, "ANTH", "anthropic_ipo", 20260101, 20261110,
     "S5 1-1 has no single true date (events 2026-01-06 to 2026-11-19); "
     "round_date = this question's event date."),
    (14, "ALI", "capex", 20260101, 20261119,
     "S5 1-1 has no single true date; round_date = this question's event date."),
    (15, "BIDU", "capex", 20260101, 20261116,
     "S5 1-1 has no single true date; round_date = this question's event date."),
    (16, "BYTE", "capex", 20260101, 20260527,
     "S5 1-1 has no single true date; round_date = this question's event date."),
    (17, "TCE", "capex", 20260101, 20261118,
     "S5 1-1 has no single true date; round_date = this question's event date."),
    (38, "MUSK", "financing", 20260101, 20260106,
     "S5 1-1 has no single true date; round_date = this question's event date."),
    (32, "MSFT", "energy", 20250601, 20240920,
     "event (2024-09-20) is 8 months BEFORE the round (2025-06-01); "
     "round_date = event date."),
]

NEW_QUESTIONS = [
    {
        "season": 5, "round_label": "4-1", "event_real_date": 20261117,
        "event_name": "OpenAI 发布 GPT-6.2 Astra 与 Sol",
        "player": "OAI", "kind": "chatgpt",
        "action": "GPT-6.2 Astra 与 Sol 发布。ChatGPT Work 与 Codex 同日上线",
        "source": ("OpenAI 官方博客（11-17）：GPT-6.2 Astra 与 Sol 发布，"
                   "ChatGPT Work 与 Codex 同日上线；Astra API 价降 20%"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "5-1", "event_real_date": 20261118,
        "event_name": "Google 发布 Gemini 4 Neon",
        "player": "GOOG", "kind": "gemini",
        "action": "Google 发布 Gemini 4 Neon。中端编码与分析模型",
        "source": ("Google 官方博客（11-18）：Gemini 4 Neon 发布，Gemini 4 家族"
                   "中端模型，介于 Carbon 与 Hydrogen 之间"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "5-1", "event_real_date": 20261120,
        "event_name": "FT 调查：Aivres–Megaspeed 46 亿美元芯片通道",
        "player": "NVDA", "kind": "megaspeed",
        "action": "FT 调查：Aivres–Megaspeed 芯片通道。Speedmatrix 申报自 Aivres 进口约 46 亿美元",
        "source": ("FT 调查（11-20）：Aivres–Megaspeed 芯片通道，Speedmatrix "
                   "申报自 Aivres 进口约 46 亿美元"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "4-1", "event_real_date": 20261116,
        "event_name": "广州首个真武国产万卡智算集群投产运营",
        "player": "ALI", "kind": "datacenter",
        "action": "广州首个真武国产万卡智算集群投产运营。计划扩至 10 万卡",
        "source": ("中国电信广东公司与阿里云智能联合主办（11-16）：广州首个"
                   "真武国产万卡智算集群投产运营；广州日报、21财经"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "6-1", "event_real_date": 20261120,
        "event_name": "台积电叫停 16nm 及以下中国客户订单",
        "player": "TSMC", "kind": "bis_rule",
        "action": "台积电执行 BIS 规则：叫停 16nm 及以下中国客户订单。无许可证改用 28nm/40nm",
        "source": ("路透/Nikkei Asia（11-20）：台积电叫停 16nm 及以下中国客户"
                   "订单，无许可证改用 28nm/40nm"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "6-1", "event_real_date": 20261120,
        "event_name": "甲骨文宣布 OpenAI 基建合同融资已全部落实",
        "player": "ORCL", "kind": "financing",
        "action": "甲骨文宣布 OpenAI 基建合同融资全部落实。约 3000 亿美元、4.5GW",
        "source": ("甲骨文官方声明（11-20）：OpenAI 基建合同融资已全部落实，"
                   "约 3000 亿美元、4.5GW"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "2-1", "event_real_date": 20261029,
        "event_name": "亚马逊 Q3 财报：Q3 现金资本开支 759 亿美元，全年指引约 2200 亿美元",
        "player": "AMZN", "kind": "capex",
        "action": "亚马逊 Q3 现金资本开支 759 亿美元。全年指引约 2200 亿美元",
        "source": ("亚马逊 Q3 2026 财报电话会（10-29）：Q3 现金资本开支 759 亿"
                   "美元，全年指引约 2200 亿美元"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "1-1", "event_real_date": 20260914,
        "event_name": "软银 118.7 亿美元定期贷款（为 OpenAI 投资融资）",
        "player": "SFTB", "kind": "financing",
        "action": "软银落实 118.7 亿美元两年期定期贷款。为 OpenAI 投资融资",
        "source": ("彭博（9-14）：软银落实 118.7 亿美元两年期定期贷款，"
                   "约 20 家银行承诺，用于 OpenAI 投资"),
        "origin": "s5patch-round6",
    },
    {
        "season": 5, "round_label": "5-1", "event_real_date": 20261118,
        "event_name": "xAI Grok 4.8 软发布",
        "player": "MUSK", "kind": "spacex_xai",
        "action": "xAI Grok 4.8 开始向部分 Bot 用户软发布",
        "source": ("马斯克 X 帖文（11-18）：Grok 4.8 已向部分 Bot 用户软发布；"
                   "无 xAI 官方新闻稿"),
        "origin": "s5patch-round6",
    },
]

# Kinds with no classify_semantic rule: the question kind comes from the
# 35-kind boundary rules, the trace move stays "unknown". Precedent: the
# v3 datacenter questions (S4 1-2 BYTE/META) have trace kind unknown.
NO_RULE_KINDS = {"datacenter"}


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

    # --- regenerate the fact base from the current data.json roundEvidence,
    # and diff it against the old fixed file: only additions allowed. ---
    data = json.load(open("data.json"))
    trace_date = {}
    for m in t["moves"]:
        trace_date[(m["season"], m["round_label"])] = m["date"]
    new_facts = []
    for rk in sorted(data["roundEvidence"]):
        season_s, label = rk.split(":", 1)
        ev = data["roundEvidence"][rk]
        items = []
        for it in ev.get("items", []):
            lab = it["label"]
            # Known fix from the redesign (facts-roundEvidence-fixed.json):
            # S3:3-2's o1-preview half-sentence is an S3 5-1 event, not
            # this round's. The fixed file removed it; keep it removed.
            if rk == "S3:3-2":
                lab = lab.replace("；o1-preview 与 o1-mini 2024-09-12 发布", "")
            items.append({"kind": it["kind"], "ref": it["ref"], "label": lab})
        new_facts.append({
            "round": rk, "season": int(season_s[1:]), "round_label": label,
            "date": trace_date[(int(season_s[1:]), label)],
            "status": ev["status"], "note": ev.get("note", ""),
            "items": items,
            "per_move_keys": sorted(ev.get("moves", {}).keys()),
        })
    old_facts = json.load(open(OLD_FACTS))
    old_by_round = {e["round"]: e for e in old_facts}
    new_by_round = {e["round"]: e for e in new_facts}
    assert set(old_by_round) == set(new_by_round), "round set changed in fact base"
    diffs = []
    for rk in sorted(old_by_round):
        o, n = old_by_round[rk], new_by_round[rk]
        if o["items"] != n["items"]:
            o_labels = [i["label"] for i in o["items"]]
            n_labels = [i["label"] for i in n["items"]]
            removed = [l for l in o_labels if l not in n_labels]
            added = [l for l in n_labels if l not in o_labels]
            if removed:
                diffs.append((rk, "REMOVED", removed))
            if added:
                diffs.append((rk, "ADDED", [a[:80] for a in added]))
        if o["status"] != n["status"]:
            diffs.append((rk, "STATUS", (o["status"], n["status"])))
    print("fact-base diff vs old fixed file (only additions allowed):")
    for d in diffs:
        print("  ", d[0], d[1], d[2] if d[1] != "ADDED" else "%d added" % len(d[2]))
    assert all(d[1] in ("ADDED",) for d in diffs), "unexpected fact-base change: %s" % diffs
    with open(os.path.join(RUN_DIR, "facts-roundEvidence-v5.json"), "w", encoding="utf-8") as f:
        json.dump(new_facts, f, ensure_ascii=False, indent=1)
    print("wrote facts-roundEvidence-v5.json (%d rounds)" % len(new_facts))

    # --- trace_idx + round_date for the 9 new questions ---
    for q in NEW_QUESTIONS:
        rd = next(m["date"] for m in t["moves"]
                  if m["season"] == q["season"] and m["round_label"] == q["round_label"])
        if (q["season"], q["round_label"]) == (5, "1-1"):
            # S5 1-1 round date is the 20260101 fiction; prediction point
            # is the event date (same rule as the other S5 1-1 questions).
            q["round_date"] = int(q["event_real_date"])
            q["round_date_note"] = ("S5 1-1 has no single true date; "
                                    "round_date = this question's event date.")
        else:
            q["round_date"] = rd
        idx = [i for i, m in enumerate(t["moves"])
               if m["season"] == q["season"] and m["round_label"] == q["round_label"]
               and pmap[m["player"]] == q["player"]]
        assert len(idx) == 1, "trace move not unique: %s %s %s" % (
            q["season"], q["round_label"], q["player"])
        q["trace_idx"] = idx[0]
        mv = t["moves"][idx[0]]
        assert mv["action"] == q["action"], "action text mismatch for %s %s %s: trace %r vs question %r" % (
            q["season"], q["round_label"], q["player"], mv["action"], q["action"])
        if q["kind"] in NO_RULE_KINDS:
            assert mv["semantic_kind"] == "unknown", \
                "datacenter question must have trace kind unknown, got %s" % mv["semantic_kind"]
        else:
            assert mv["semantic_kind"] == q["kind"], \
                "semantic kind mismatch for %s: trace %s vs question %s" % (
                    q["action"], mv["semantic_kind"], q["kind"])
        assert q["round_date"] <= int(q["event_real_date"]), \
            "round date after event date for %s" % q["event_name"]
        print("new question: %s %s %s (trace_idx %d, round_date %s)" % (
            q["player"], q["kind"], q["event_real_date"], q["trace_idx"], q["round_date"]))

    # --- assemble test set: v4 (with date fixes) + 9 new ---
    v4 = json.load(open("testset-v4.json"))
    questions = []
    by_old_id = {}
    for q in v4["questions"]:
        q = dict(q)
        by_old_id[q["q_id"]] = q
        q.pop("split", None)
        q.pop("q_id", None)
        questions.append(q)
    n_v4 = len(questions)
    assert n_v4 == 90, "v4 must have 90 questions, got %d" % n_v4
    for (qid, player, kind, old_rd, new_rd, note) in DATE_FIXES:
        q = by_old_id[qid]
        assert q["player"] == player and q["kind"] == kind, \
            "date-fix target mismatch at v4 q_id %d" % qid
        assert q["round_date"] == old_rd, \
            "v4 q_id %d round_date %s != expected %s" % (qid, q["round_date"], old_rd)
        q["round_date"] = new_rd
        q["round_date_note"] = note
        print("date fix: v4 q%d %s %s round_date %s -> %s" % (
            qid, player, kind, old_rd, new_rd))
    # q57 de-dup: verify the duplicate is already gone (old83 q58 dropped
    # in the v3 redesign); exactly one overseas_rental question must remain.
    overseas = [q for q in questions if q["kind"] == "overseas_rental"]
    assert len(overseas) == 1, "expected exactly 1 overseas_rental question, got %d" % len(overseas)
    print("q57 de-dup check: 1 overseas_rental question remains (%s %s, old83 q65); "
          "the duplicate (old83 q58) was already dropped in the v3 redesign." % (
              overseas[0]["season"], overseas[0]["round_label"]))
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
    # fix one-sided rounds (same method + guards as build_testset_v4.py)
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
                                continue
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
    new_qs = [q for q in questions if q.get("origin") == "s5patch-round6"]
    assert len(new_qs) == 9, "expected 9 new questions, got %d" % len(new_qs)
    ev_new = Counter((q["event_real_date"], q["event_name"]) for q in new_qs)
    dup_new = [k for k, n in ev_new.items() if n > 1]
    assert not dup_new, "same-event duplicates among new questions: %s" % dup_new
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
        "name": "testset-v5 (testset-v4 + 9 round-6 S5 patch questions)",
        "n": len(questions),
        "split": {"A": split["A"], "B": split["B"]},
        "split_method": ("stratified: sorted by (kind, season, round_index, player), "
                         "assigned A/B by alternating global index; one-sided rounds "
                         "fixed by swapping two same-kind questions, or (for a singleton "
                         "kind with no same-kind partner) by swapping with a question of "
                         "another kind while keeping every kind with 2+ questions on both "
                         "sides; each kind with 2+ questions and each round with 2+ "
                         "questions appears in both sets"),
        "v4_kept": n_v4,
        "new_from_s5patch_round6": 9,
        "new_S5": 9,
        "gap_to_140": 140 - len(questions),
        "date_fixes": ("v4 q13 round_date 20241201->20241030; S5 1-1 six questions "
                       "round_date 20260101->event date each; v4 q32 (v3 q31) round_date "
                       "20250601->20240920; new SFTB 1-1 question round_date = event "
                       "date 20260914 (see round_date_note on each fixed question)."),
        "q57_dedup": ("no question removed: the duplicate (old83 q58, same Bloomberg "
                      "11-17 Aolani event as old83 q65) was already dropped in the v3 "
                      "redesign; v5 keeps the single overseas_rental question."),
        "note": ("trace stays 558 moves: the nine S5 events are rewritten action texts "
                 "on existing moves (with hp/gold set from the events), not new moves -- "
                 "the converter requires exactly 18 moves per round. Baseline 48/88 is "
                 "the 88-question reference, not re-run. A/B splits are re-derived, so "
                 "v5 splits differ from v4 splits; compare scores on the full set."),
    }
    with open("testset-v5.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "questions": questions}, f, ensure_ascii=False, indent=1)
    print("wrote testset-v5.json: n=%d, A %d, B %d, gap to 140: %d" % (
        len(questions), split["A"], split["B"], meta["gap_to_140"]))

    # --- walk-forward prefixes + facts for the 9 new questions ---
    facts = []
    for e in new_facts:
        rk = (e["season"], round_idx[(e["season"], e["round_label"])])
        for it in e.get("items", []):
            d, conf = fact_date(it.get("label", ""), e["date"])
            facts.append({
                "round": e["round"], "season": e["season"],
                "round_label": e["round_label"], "round_key": list(rk),
                "ref": it.get("ref", ""), "label": it.get("label", ""),
                "fact_date": d, "date_confidence": conf,
            })

    testset_qid = {}
    for q in questions:
        if q.get("origin") == "s5patch-round6":
            testset_qid[(q["season"], q["round_label"], q["player"])] = q["q_id"]
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
            "q_id": qi,
            "testset_q_id": testset_qid[(q["season"], q["round_label"], q["player"])],
            "trace_idx": q["trace_idx"], "season": q["season"],
            "round": "S%d %s" % (q["season"], q["round_label"]),
            "round_index": qk[1], "player": q["player"], "kind": q["kind"],
            "event_real_date": q["event_real_date"],
            "event_name": q["event_name"], "source": q["source"],
            "round_date": q["round_date"],
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

    with open(os.path.join(RUN_DIR, "prefixes-v5-new.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(RUN_DIR, "prefix-audit-v5-new.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print("wrote prefixes-v5-new.json (%d questions)" % len(out))
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
