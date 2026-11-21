"""Build per-round question files for round 5 (date fix) from test83.json +
trace-latest.json, adding per-question event_real_date and headline event.

Method (written before the run; do not tune on the test):
- event_real_date = the real-world date of the specific action described by
  (player, kind), evidenced by a dated public source. Verified by web search
  for the compressed rounds (S4 1-1, S5 1-1, S5 3-2, S4 4-1, S5 2-1 ANTH).
- If the action is a composite/state with no single dated event, keep the
  round date and flag it (basis NO-DATE / COMPOSITE / STATE).
- Fact cutoff per question = event_real_date (not the round nominal date).
- Headline event: same per-question given/not-given pattern as search-first
  (scored-full83.json event_given), EXCEPT S5 1-1 where the date fix newly
  makes a headline available (no headline could be given under the Jan 1
  cutoff; under the real-date cutoff the Nov 10 commitments headline is).
- Predictors must NOT use any fact stating this player's action in this
  round (that is the answer). The given headline event itself is input, not
  contamination. Audit checks facts_used afterwards.

Usage: python3 build_questions.py
Writes: runs/date-fix-round5-2026-11-22/event_dates.json
         runs/date-fix-round5-2026-11-22/questions-<round>.json (13 files)
"""
import json, os, glob
from collections import Counter

RUNDIR = "/home/hatch/workspace/verification-r5-date/runs/date-fix-round5-2026-11-22"
SRC = "/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22"

trace = json.load(open(os.path.join(RUNDIR, "trace-latest.json")))
moves = trace["moves"]
players = {p["id"]: p["key"] for p in trace["players"]}
test83 = json.load(open(os.path.join(RUNDIR, "test83.json")))

# (round_label, player) -> (event_real_date int YYYYMMDD, event_name, basis, flag)
# flag: "" = dated event; "judgment" = best dated anchor for a composite
# action; "no-date" = no single dated event, round date kept.
DATES = {
    # S4 1-1, round date 20250120
    (4, "1-1", "MSFT"):   (20250121, "Stargate announced at White House; Microsoft exclusivity loosened",
                        "roundEvidence S4:1-2 (Stargate Jan 21) + predictor fact", ""),
    (4, "1-1", "META"):   (20250120, "R1 release vindicates open-source route",
                        "R1 released Jan 20 (roundEvidence S4:1-1)", ""),
    (4, "1-1", "AMZN"):   (20250130, "R1 on Amazon Bedrock Marketplace and SageMaker JumpStart",
                        "AWS blogs Jan 30 (predictor fact)", ""),
    (4, "1-1", "MUSK"):   (20250120, "R1 triggers open-source reasoning follow-on",
                        "R1 released Jan 20", ""),
    (4, "1-1", "ORCL"):   (20250127, "Enterprise orders hold through DeepSeek shock (market crash day)",
                        "JUDGMENT: NVDA -17% Jan 27; crash day is when demand-holding became observable", "judgment"),
    (4, "1-1", "BYTE"):   (20250122, "Doubao-1.5-Pro released",
                        "predictor fact (Jan 22)", ""),
    (4, "1-1", "ALI"):    (20250120, "Qwen downloads top global charts after R1",
                        "R1 release trigger", ""),
    (4, "1-1", "TCE"):    (20250202, "Tencent Cloud deploys R1 on HAI (one-click)",
                        "Pandaily Feb 2, 2025", ""),
    (4, "1-1", "BIDU"):   (20250213, "Baidu announces Ernie Bot free from Apr 1",
                        "Reuters/Nikkei Feb 13, 2025", ""),
    (4, "1-1", "HUAWEI"): (20250201, "Huawei Cloud + SiliconFlow launch R1/V3 on Ascend Cloud",
                        "predictor fact + Manila Times (Sat Feb 1)", ""),
    (4, "1-1", "DPSK"):   (20250120, "R1 released", "roundEvidence S4:1-1", ""),
    (4, "1-1", "TSMC"):   (20250120, "R1 proves old nodes can compete", "R1 release trigger", ""),
    # S4 1-2, round date 20250121: Stargate announced Jan 21 (all same)
    # S4 1-3, round date 20250127: crash day (all same)
    # S4 3-2, round date 20250601: energy theme, composite (all same)
    # S4 4-1, round date 20250801: per-model release dates
    (4, "4-1", "GOOG"):   (20250617, "Gemini 2.5 Pro/Flash GA",
                        "9to5Google Jun 17, 2025", ""),
    (4, "4-1", "ANTH"):   (20250522, "Claude Opus 4 / Sonnet 4 released",
                        "predictor fact (May 22)", ""),
    (4, "4-1", "MUSK"):   (20250709, "Grok 4 released",
                        "predictor fact (Jul 9)", ""),
    (4, "4-1", "ORCL"):   (20250722, "OpenAI confirms $30B/yr Oracle deal (4.5 GW Stargate)",
                        "predictor fact (Jul 22)", ""),
    (4, "4-1", "BYTE"):   (20250611, "Doubao-Seed-1.6 announced",
                        "predictor fact (Jun 11)", ""),
    (4, "4-1", "ALI"):    (20250429, "Qwen3 released",
                        "predictor fact (Apr 29)", ""),
    (4, "4-1", "TCE"):    (20250627, "Hunyuan-A13B released",
                        "predictor fact (Jun 27)", ""),
    (4, "4-1", "BIDU"):   (20250630, "Ernie 4.5 open-sourced",
                        "predictor fact (Jun 30)", ""),
    (4, "4-1", "HUAWEI"): (20250620, "Pangu 5.5 released at HDC",
                        "Huawei Cloud Jun 20, 2025", ""),
    (4, "4-1", "SFTB"):   (20250722, "OpenAI confirms $30B/yr Oracle deal (4.5 GW Stargate)",
                        "predictor fact (Jul 22)", ""),
    # S4 5-1, round date 20251201: year-end states (all same)
    # S5 1-1, round date 20260101
    (5, "1-1", "ANTH"):   (20261110, "S-1/A No.2: ~$900.9B compute commitments",
                        "EDGAR 0001628280-26-072484 (Nov 10, 2026)", ""),
    (5, "1-1", "MUSK"):   (20260106, "xAI $20B Series E closes",
                        "NYT Jan 6, 2026", ""),
    (5, "1-1", "BYTE"):   (20260527, "Bloomberg: ByteDance weighing up to $70B 2026 capex",
                        "Bloomberg May 27, 2026", ""),
    (5, "1-1", "ALI"):    (20261119, "Alibaba Q2 FY2027 earnings: capex +60% to RMB 50.48B",
                        "Nikkei/Fool Nov 19, 2026", ""),
    (5, "1-1", "TCE"):    (20261118, "Tencent Q3 2026 earnings: capex +527%",
                        "Tencent Q3 (Nov 18, 2026)", ""),
    (5, "1-1", "HUAWEI"): (20260917, "Xu Zhijun: Ascend shipments in China have surpassed Nvidia",
                        "JUDGMENT: best dated anchor for composite Ascend-orders judgment (Sept 17, 2026 statement)", "judgment"),
    (5, "1-1", "SFTB"):   (20260101, "No single dated event found for Stargate funding questioning; round date kept",
                        "NO-DATE: round date kept", "no-date"),
    # S5 2-1, round date 20261006
    (5, "2-1", "ANTH"):   (20261026, "Anthropic files public S-1",
                        "TechCrunch Oct 26, 2026", ""),
    # S5 3-2, round date 20261105
    (5, "3-2", "BYTE"):   (20261117, "Bloomberg: banks pause $480M Aolani loan for ByteDance GPUs",
                        "Bloomberg Nov 17, 2026", ""),
    (5, "3-2", "ALI"):    (20261116, "BIS remote-access rule published",
                        "BIS IFR Nov 16, 2026", ""),
    (5, "3-2", "HUAWEI"): (20261109, "NYT Alice Huang / MSS investigation published",
                        "NYT Nov 8-9, 2026", ""),
    (5, "3-2", "DPSK"):   (20261105, "Nov 5 war-room meeting (Bessent presses Lutnick on Megaspeed)",
                        "round headline = round date", ""),
    (5, "3-2", "TSMC"):   (20261116, "BIS remote-access rule published",
                        "BIS IFR Nov 16, 2026", ""),
    # S5 5-1, round date 20261118
    (5, "5-1", "BYTE"):   (20261116, "BIS remote-access rule published",
                        "BIS IFR Nov 16, 2026", ""),
    (5, "5-1", "DPSK"):   (20261116, "BIS remote-access rule published",
                        "BIS IFR Nov 16, 2026", ""),
}

# Rounds whose questions are NOT in DATES keep the round date.
ROUND_NO_DATE_NOTE = {
    ("1-2",): "Stargate announced Jan 21 = round date",
    ("1-3",): "DeepSeek crash day Jan 27 = round date",
    ("3-2",): "COMPOSITE energy theme, no single dated event",
    ("5-1",): "Year-end financing states, no single dated event",
    ("2-1",): "Oct 2026 states except ANTH S-1 (Oct 26)",
    ("4-1",): "Huang resignation announced Nov 12 = round date",
    ("6-1",): "SEC probe Nov 20 = round date",
    ("6-2",): "Post-crash settlement Nov 21 = round date",
}

# Headline event per round: (text, date int, given_to set of players or "all").
# Given/not-given replicates search-first (scored-full83.json event_given),
# except S5 1-1 (date-fix change: headline newly available).
HEADLINES = {
    "S4 1-1": ("DeepSeek R1 released Jan 20, 2025 (open weights, AIME 79.8% vs o1 79.2%)",
               20250120, "all-except-DPSK"),
    "S4 1-2": ("Stargate announced Jan 21, 2025: $500B over 4 years (OpenAI, SoftBank, Oracle, MGX)",
               20250121, "all"),
    "S4 1-3": ("Nvidia crashes ~17% Jan 27, 2025 on DeepSeek shock; AI capex questioned",
               20250127, "all"),
    "S4 3-2": ("Data-center power is the binding constraint (energy theme)",
               20250601, "all"),
    "S4 4-1": ("Flagship model race: Claude 4 (May), Grok 4 (Jul 9), GPT-5 season",
               20250801, "all"),
    "S4 5-1": ("Circular financing under scrutiny (OpenAI / Microsoft / Oracle)",
               20251201, {"MUSK", "ORCL"}),
    "S5 1-1": ("Anthropic's ~$900.9B compute commitments disclosed (S-1/A No.2, Nov 10, 2026)",
               20261110, "all-except-ANTH"),
    "S5 2-1": ("Anthropic files public S-1 Oct 26, 2026 (ticker ANT)",
               20261026, {"MUSK", "ORCL"}),
    "S5 3-2": ("Nov 5 war-room meeting: Bessent presses Lutnick on Megaspeed enforcement",
               20261105, {"DPSK", "HUAWEI", "TSMC"}),
    "S5 4-1": ("Huang resigns: board accepted Nov 11, announced Nov 12, 2026",
               20261112, {"ANTH", "BYTE"}),
    "S5 5-1": ("Anthropic IPO priced $83 Nov 18, 2026",
               20261118, "all-except-ANTH"),
    "S5 6-1": ("Reuters: SEC probing Nvidia accounting, Nov 20, 2026; NVDA -14%",
               20261120, "all-except-NVDA"),
    "S5 6-2": ("Anthropic IPO proceeds landed; market settles after Nov 20 crash",
               20261121, {"ANTH"}),
}

VOCAB = sorted(set(
    m["semantic_kind"] for m in moves if m.get("semantic_kind") not in (None, "unknown")
))
assert len(VOCAB) == 29, len(VOCAB)

move_pos = {}
for i, m in enumerate(moves):
    move_pos[(m["season"], m["round_label"], players[m["player"]])] = i

round_order = []
for m in moves:
    k = (m["season"], m["round_label"])
    if k not in round_order:
        round_order.append(k)

def prev_round_key(season, label):
    i = round_order.index((season, label))
    return round_order[i - 1] if i > 0 else None

def headline_given(round_key, player):
    text, date, who = HEADLINES[round_key]
    if who == "all":
        return True
    if who == "all-except-DPSK":
        return player != "DPSK"
    if who == "all-except-ANTH":
        return player != "ANTH"
    if who == "all-except-NVDA":
        return player != "NVDA"
    return player in who

def build_item(qi, q):
    p = move_pos[(q["season"], q["round_label"], q["player"])]
    m = moves[p]
    pid = m["player"]
    pkey = players[pid]
    hist = [mm for mm in moves[:p] if mm["player"] == pid and mm.get("semantic_kind") not in (None, "unknown")]
    counts = Counter(mm["semantic_kind"] for mm in hist)
    most = counts.most_common(1)[0][0] if counts else None
    last_kind = hist[-1]["semantic_kind"] if hist else None
    cur = round_order.index((q["season"], q["round_label"]))
    last3 = []
    for rk in round_order[max(0, cur - 3):cur]:
        for mm in moves:
            if (mm["season"], mm["round_label"]) == rk and mm["player"] == pid:
                if mm.get("semantic_kind") not in (None, "unknown"):
                    last3.append([mm["semantic_kind"], mm["date"]])
                break
    pk = prev_round_key(q["season"], q["round_label"])
    prev = {}
    if pk:
        for mm in moves:
            if (mm["season"], mm["round_label"]) == pk and mm.get("semantic_kind") not in (None, "unknown"):
                prev[players[mm["player"]]] = mm["semantic_kind"]
    round_key = "S%d %s" % (q["season"], q["round_label"])
    # event real date: per-question override, else round date
    key = (q["season"], q["round_label"], q["player"])
    if key in DATES:
        erd, ename, basis, flag = DATES[key]
    else:
        erd, ename, basis, flag = q["date"], "", "round date kept", "no-date"
    htext, hdate, _ = HEADLINES[round_key]
    return {
        "q_idx": qi,
        "trace_idx": p,
        "season": q["season"],
        "round_label": q["round_label"],
        "round": round_key,
        "date": q["date"],
        "round_date": q["date"],
        "event_real_date": erd,
        "event_name": ename,
        "event_basis": basis,
        "event_flag": flag,
        "headline_event": htext,
        "headline_date": hdate,
        "headline_given": headline_given(round_key, pkey),
        "player": pkey,
        "hp_start": q["hp_start"],
        "gold_start": q["gold_start"],
        "rules_version": q["rules_version"],
        "first_appearance": q["first_appearance"],
        "player_history_counts": dict(counts),
        "player_most_frequent": most,
        "player_last_kind": last_kind,
        "player_last3": last3,
        "prev_round_kinds": prev,
        "vocabulary": VOCAB,
    }

FIELDS = ["player_history_counts", "player_most_frequent", "player_last_kind",
          "player_last3", "prev_round_kinds", "hp_start", "gold_start",
          "rules_version", "first_appearance", "date", "player"]

def validate():
    """Reproduce the existing search-first context files (0 mismatches expected)."""
    existing = {}
    for f in glob.glob(os.path.join(SRC, "round-*-context.json")):
        for it in json.load(open(f)):
            existing[it["q_idx"]] = it
    b = json.load(open(os.path.join(SRC, "batchD_S5_late-context.json")))
    for it in b:
        existing.setdefault(it["q_idx"], it)
    mismatch = Counter()
    bad_items = 0
    for qi, q in enumerate(test83):
        if qi not in existing:
            continue
        got = build_item(qi, q)
        exp = existing[qi]
        item_bad = False
        for field in FIELDS:
            if got[field] != exp[field]:
                mismatch[field] += 1
                item_bad = True
        bad_items += item_bad
    print("existing context items:", len(existing))
    print("mismatches by field:", dict(mismatch))
    print("mismatched items:", bad_items, "/", len(existing))
    return bad_items

if __name__ == "__main__":
    bad = validate()
    # event_dates.json (no answers: kind/action excluded)
    table = []
    changed = 0
    for qi, q in enumerate(test83):
        it = build_item(qi, q)
        table.append({
            "q_idx": qi,
            "round": it["round"],
            "player": it["player"],
            "round_date": it["round_date"],
            "event_real_date": it["event_real_date"],
            "event_name": it["event_name"],
            "event_basis": it["event_basis"],
            "event_flag": it["event_flag"],
            "changed": it["event_real_date"] != it["round_date"],
        })
        changed += it["event_real_date"] != it["round_date"]
    json.dump(table, open(os.path.join(RUNDIR, "event_dates.json"), "w"),
              ensure_ascii=False, indent=1)
    print("event_dates.json:", len(table), "rows,", changed, "changed cutoffs")
    by_round = {}
    for qi, q in enumerate(test83):
        by_round.setdefault((q["season"], q["round_label"]), []).append(build_item(qi, q))
    for (s, lab), items in sorted(by_round.items()):
        fn = os.path.join(RUNDIR, "questions-S%d-%s.json" % (s, lab))
        json.dump(items, open(fn, "w"), ensure_ascii=False, indent=1)
        print("wrote", fn, len(items), "items")
    # safety: question files must not contain answers
    for fn in glob.glob(os.path.join(RUNDIR, "questions-*.json")):
        txt = open(fn).read()
        for bad_word in ('"actual_kind"', '"correct"', '"kind": "'):
            assert bad_word not in txt, (fn, bad_word)
    print("leak check on question files: OK (no actual_kind/correct/kind fields)")
    print("validation mismatched items:", bad)
