#!/usr/bin/env python3
"""Round-6 S5 patch: rewrite 9 existing S5 actions with the 9 missed events.

Reads data.json (in sync with the page assets/data.json, sha 7eda7ce4...).
Writes data.json (patched) + a JSON summary for the report.

The 9 rewrites (one per event; action count stays 558, 18 per round):
  S5 4-1 OAI  GPT-6.2 Astra/Sol (2026-11-17)   chatgpt
  S5 5-1 GOOG Gemini 4 Neon (2026-11-18)       gemini
  S5 5-1 NVDA FT Aivres-Megaspeed (2026-11-20) megaspeed
  S5 4-1 ALI  Zhenwu Guangzhou cluster (2026-11-16) datacenter
  S5 6-1 TSMC halt <=16nm orders (2026-11-20)  bis_rule
  S5 6-1 ORCL financing secured (2026-11-20)   financing
  S5 2-1 AMZN Q3 capex $75.9B (2026-10-29)     capex
  S5 1-1 SFTB $11.87B term loan (2026-09-14)   financing
  S5 5-1 MUSK Grok 4.8 soft rollout (2026-11-18) spacex_xai

Placement rule: the round whose [date, next round date) range contains
the event date. ONE exception: FT Aivres-Megaspeed (11-20) belongs to
6-1 by date, but NVDA 6-1 holds the SEC-probe question (v4 q64); rewriting
it would destroy that question. It goes to NVDA 5-1 (round 11-18, event
2 days later, still a valid prediction point).

hp/gold are set from each event (this round differs from the first S5
patch, which kept them unchanged). See design/s5patch-round6-2026-11-22.md
for the reasoning per event. The script recomputes the S5 chains and
updates the 18 affected reconciliation entries (seasonEnd/newSum; SFTB
1-1 moveTo/breakpoint, since its 1-1 delta itself changes) and asserts
the recomputed ends match.

Also adds 9 roundEvidence items + move pointers (page display only).
Round statuses are NOT changed.
"""
import json
import sys
from collections import Counter

DATA = "data.json"

# (season, round, player, new_action, new_hp, new_gold)
REWRITES = [
    ("S5", "4-1", "OAI",
     "GPT-6.2 Astra 与 Sol 发布。ChatGPT Work 与 Codex 同日上线", 4, 1),
    ("S5", "5-1", "GOOG",
     "Google 发布 Gemini 4 Neon。中端编码与分析模型", 3, 1),
    ("S5", "5-1", "NVDA",
     "FT 调查：Aivres–Megaspeed 芯片通道。Speedmatrix 申报自 Aivres 进口约 46 亿美元", -10, -3),
    ("S5", "4-1", "ALI",
     "广州首个真武国产万卡智算集群投产运营。计划扩至 10 万卡", 3, -1),
    ("S5", "6-1", "TSMC",
     "台积电执行 BIS 规则：叫停 16nm 及以下中国客户订单。无许可证改用 28nm/40nm", -4, -2),
    ("S5", "6-1", "ORCL",
     "甲骨文宣布 OpenAI 基建合同融资全部落实。约 3000 亿美元、4.5GW", 3, 2),
    ("S5", "2-1", "AMZN",
     "亚马逊 Q3 现金资本开支 759 亿美元。全年指引约 2200 亿美元", 3, -6),
    ("S5", "1-1", "SFTB",
     "软银落实 118.7 亿美元两年期定期贷款。为 OpenAI 投资融资", 2, -2),
    ("S5", "5-1", "MUSK",
     "xAI Grok 4.8 开始向部分 Bot 用户软发布", 2, -1),
]

# (round_key, player_pid, player_code, ref_url, label)
EVIDENCE = [
    ("S5:4-1", 1, "OAI",
     "https://openai.com/index/introducing-gpt-6-2-astra-sol/",
     "OpenAI 发布 GPT-6.2 Astra 与 Sol（2026-11-17）：旗舰模型更新，ChatGPT Work 与 Codex 同日上线；Astra API 价降 20%。"),
    ("S5:5-1", 3, "GOOG",
     "https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/",
     "Google 发布 Gemini 4 Neon（2026-11-18）：Gemini 4 家族中端模型，介于 Carbon 与 Hydrogen 之间；1M 上下文，$3/$15。"),
    ("S5:5-1", 0, "NVDA",
     "https://fourweekmba.com/ai-ft-maps-4-6b-chip-route-nvidia-says-it-blocked-megaspeed/",
     "FT 调查（2026-11-20）：浪潮未列清单的美国子公司 Aivres 持续与英伟达交易；Megaspeed 马来西亚子公司 Speedmatrix 申报自 Aivres 进口约 46 亿美元货物；英伟达称 2025 年已将 Megaspeed 列入内部禁售名单。（FT 原文付费墙，本条为转述）"),
    ("S5:4-1", 11, "ALI",
     "https://news.dayoo.com/finance/202611/16/171077_55024197.htm",
     "广州首个真武国产万卡智算集群投产运营（2026-11-16）：中国电信广东公司联合阿里云智能集团主办，黄埔区上线发布；计划扩至 10 万卡，TokenHub 平台同步发布。"),
    ("S5:6-1", 16, "TSMC",
     "https://www.taiwannews.com.tw/news/6478978",
     "台积电叫停 16nm 及以下中国客户订单（2026-11-20，路透引述知情人士）：无许可证暂停，改用 28nm/40nm、无 HBM 或先进封装；BIS 远程规则 11-19 生效后执行收紧。（Nikkei Asia 同日跟进）"),
    ("S5:6-1", 9, "ORCL",
     "https://www.oracle.com/news/announcement/oracle-statement-2026-11-20/",
     "甲骨文官方声明（2026-11-20）：OpenAI 基建合同融资已全部落实；五年约 3000 亿美元、4.5GW；最后一次融资约 100 亿美元股票 + 100 亿美元债务。"),
    ("S5:2-1", 6, "AMZN",
     "https://gloom.sh/stocks/amzn/transcripts/q3-2026",
     "亚马逊 Q3 财报电话会（2026-10-29）：Q3 现金资本开支 759 亿美元，全年指引约 2200 亿美元，多数投向 AWS；2027 年将显著增加。"),
    ("S5:1-1", 17, "SFTB",
     "https://www.japantimes.co.jp/business/2026/09/14/companies/softbank-loan-openai/",
     "软银落实 118.7 亿美元两年期定期贷款（2026-09-14，彭博）：约 20 家银行承诺，原目标 100 亿美元，超额认购；以 OpenAI 持股作抵押，用于 OpenAI 投资。"),
    ("S5:5-1", 7, "MUSK",
     "https://explainx.ai/blog/grok-4-8-soft-rollout-rl-cpp-stack-november-2026",
     "xAI Grok 4.8 软发布（2026-11-18，马斯克 X 帖文）：已向部分 Grok Bot 用户软发布，全面发布还需一到两周打磨；无 xAI 官方新闻稿、无 API 发布、无基准成绩。（本条为马斯克帖文转述）"),
]

# Expected semantic-kind distribution deltas vs the pre-patch data.json.
# Old kinds of the 9 rewritten moves: unknown x6 (OAI, GOOG, NVDA, ALI,
# TSMC, AMZN), financing x1 (ORCL), stargate x1 (SFTB), anthropic_ipo x1
# (MUSK). New kinds: chatgpt, gemini, megaspeed, unknown (ALI), bis_rule,
# financing, capex, financing, spacex_xai. Net: unknown 344->339,
# chatgpt 3->4, gemini 4->5, megaspeed 2->3, bis_rule 4->5, financing
# 19->20, capex 16->17, stargate 15->14, anthropic_ipo 8->7,
# spacex_xai 4->5. The five guarded legacy kinds that move need the
# EXPECTED_LEGACY_COUNTS update in convert_data_json.py (same commit).
EXPECTED_NEW_DIST = {
    "chatgpt": 4, "bis_rule": 5, "spacex_xai": 5, "stargate": 14,
    "anthropic_ipo": 7, "gemini": 5, "megaspeed": 3, "financing": 20,
    "capex": 17, "unknown": 339,
}


def cap(v):
    return max(0, min(100, v))


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    seasons = {s["id"]: s for s in d["seasons"]}
    s5 = seasons["S5"]
    old = {}
    for (sid, code, pc, action, hp, gold) in REWRITES:
        r = next(r for r in s5["rounds"] if r["code"] == code)
        m = next(m for m in r["moves"] if m[0] == pc)
        old[(code, pc)] = (m[1], m[2], m[3])
        m[1], m[2], m[3] = action, hp, gold
        print("rewrite S5 %s %s: %r (hp %s gold %s) -> %r (hp %s gold %s)" % (
            code, pc, old[(code, pc)][0], old[(code, pc)][1], old[(code, pc)][2],
            action, hp, gold))

    # --- recompute S5 chains (capped hp, uncapped gold) ---
    openings = d["openings"]["S5"]
    ends = {}
    for pc in openings["hp"]:
        hp, gold = openings["hp"][pc], openings["gold"][pc]
        for r in s5["rounds"]:
            for (p2, _a, h, g) in r["moves"]:
                if p2 == pc:
                    hp, gold = cap(hp + h), gold + g
        ends[pc] = (hp, gold)
    affected = {pc for (_s, _c, pc, _a, _h, _g) in REWRITES}
    print("\nnew S5 ends (affected players):")
    for pc in sorted(affected):
        print("  %s hp %d gold %d" % (pc, ends[pc][0], ends[pc][1]))

    # --- update reconciliation (S5 entries only; converter checks
    # seasonEnd/newSum/prevEnd) ---
    n_upd = 0
    for e in d["reconciliation"]:
        if e["season"] != "S5" or e["player"] not in affected:
            continue
        idx = 0 if e["field"] == "hp" else 1
        e["seasonEnd"] = ends[e["player"]][idx]
        e["newSum"] = ends[e["player"]][idx] - e["prevEnd"]
        n_upd += 1
        # SFTB 1-1 delta itself changed: keep the audit trail honest.
        if e["player"] == "SFTB":
            new_delta = 2 if e["field"] == "hp" else -2
            e["moveTo"] = new_delta
            e["breakpoint"] = new_delta - e["moveFrom"]
    print("reconciliation entries updated: %d" % n_upd)
    assert n_upd == 18, "expected 18 S5 reconciliation entries (9 players x hp/gold)"

    # --- roundEvidence: add items + move pointers, statuses unchanged ---
    statuses_before = {k: v["status"] for k, v in d["roundEvidence"].items()}
    for (rk, pid, pc, ref, label) in EVIDENCE:
        ev = d["roundEvidence"][rk]
        ev["items"].append({"kind": "url", "ref": ref, "label": label})
        key = "%d:%s" % (pid, pc)
        assert key not in ev["moves"], "evidence pointer already exists: %s %s" % (rk, key)
        ev["moves"][key] = [{"kind": "url", "ref": ref, "label": label}]
    statuses_after = {k: v["status"] for k, v in d["roundEvidence"].items()}
    assert statuses_before == statuses_after, "round statuses must not change"
    print("roundEvidence items added: 9 (statuses unchanged)")

    json.dump(d, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # --- verify: semantic distribution matches the expected deltas ---
    import importlib.util
    spec = importlib.util.spec_from_file_location("conv", "convert_data_json.py")
    conv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conv)
    dist = Counter()
    for s in d["seasons"]:
        for r in s["rounds"]:
            for (pc, action, _h, _g) in r["moves"]:
                dist[conv.classify_semantic(action, pc, s["id"], r["code"])] += 1
    for k, want in EXPECTED_NEW_DIST.items():
        got = dist.get(k, 0)
        assert got == want, "semantic kind %s: got %d, expected %d" % (k, got, want)
    total_moves = sum(1 for s in d["seasons"] for r in s["rounds"] for _ in r["moves"])
    assert total_moves == 558, "moves total %d, expected 558" % total_moves
    assert all(len(r["moves"]) == 18 for s in d["seasons"] for r in s["rounds"])
    print("semantic distribution verified: %s" % {k: dist[k] for k in sorted(EXPECTED_NEW_DIST)})
    print("moves total 558, 18 per round: ok")
    json.dump({"rewrites": [
        {"round": c, "player": p, "old_action": old[(c, p)][0],
         "old_hp": old[(c, p)][1], "old_gold": old[(c, p)][2],
         "new_action": a, "new_hp": h, "new_gold": g}
        for (_s, c, p, a, h, g) in REWRITES],
        "new_s5_ends": {pc: {"hp": ends[pc][0], "gold": ends[pc][1]}
                        for pc in sorted(affected)}},
        open("runs/s5patch-round6-2026-11-22/patch-summary.json", "w", encoding="utf-8"),
        ensure_ascii=False, indent=1)
    print("wrote patched data.json + runs/s5patch-round6-2026-11-22/patch-summary.json")


if __name__ == "__main__":
    main()
