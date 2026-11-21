#!/usr/bin/env python3
"""data.json -> trace converter (page single source of truth -> schema v3 raw trace).

Reads the page's single source of truth (assets/data.json, machine-copied
into this directory as data.json) plus the pipeline rule table
(rules/rules.json) and emits a raw trace JSON (schema v3) that extract.py
can validate. The raw trace is NOT the canonical trace: run extract.py on
it, then ./run.sh.

Machine extraction path used: local file copy (cp) of the page's
assets/data.json from the artifact workspace
~/workspace/ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json
into ~/workspace/verification/data.json. No hand transcription of the 558
increments, no rank-back-computation, no fabricated data. The source file's
sha256 is recorded in the provenance output and in the raw trace header.

Design decisions (work decisions of the extraction coordinator, not
Gu-approved page changes):
- Dates: Chinese free text -> YYYYMMDD int, earliest day of the stated
  span, recorded throughout. Exact dates convert directly. "YYYY 年 M 月"
  -> YYYYMM01. Ranges take the start day. "年初" -> YYYY0101. "年底"/"年末"
  -> YYYY1201. "上半年" -> YYYY0101. "下半年" -> YYYY0701. "年中" -> YYYY0601.
  "M 月起" -> YYYYMM01. Consequence: S5:5-1 ("2026 年 11 月 18-19 日")
  -> 20261118, which resolves to RV-2026.1 while the page's roundRV records
  RV-2026.2 for that round. That is a real C5 round_rv discrepancy (the
  round straddles the rule-change day); it is reported, not papered over.
  S3:6-1 ("2024 年 12 月") -> 20241201, one day before RV-2024-12 takes
  effect (20241202), so it resolves to RV-2024.1 and matches roundRV. The
  page's month-granularity date cannot distinguish pre/post Dec 2.
- Rule table: rules.json is the base. Its ids are translated to the page's
  naming (RV-2022-10->RV-2022.2, RV-2023-10->RV-2023.2,
  RV-2025-01->RV-2025.1, RV-2026-11->RV-2026.2). Four page versions missing
  from rules.json are added: RV-2022.1 (pre-control, eff 20220101),
  RV-2024.1 (eff 20240404, page patch chapter: S3 2024-04-04 BIS revision),
  RV-2025.2 (eff 20250513, rules.json RV-2025-01 effective_to; page:
  diffusion rule rescinded 2025-05), RV-2026.1 (eff 20260724, INFERENCE:
  the DHS exclusion 2026-07-24 is the only rule event in that window; the
  page gives no separate version date). RV-2024-12 and RV-2026-07 keep
  their rules.json ids (no page name). Params are the baseline everywhere
  (hp 0-100, penalty floor(borrowed*0.5) on hp, no bans, no unavailable
  cards) except RV-2026.2, which bans overseas_rental (from rules.json).
  effective_to is exclusive (check.py resolve_rules: date >= effective_to
  means the rule no longer applies) and is set to the day before the next
  global rule takes effect. Moves' rules_version is taken verbatim from
  data.json roundRV.
- Moves: player id is the data.json players order mapped to int 0-17
  (verified identical to the fixture order). hp_start/gold_start are
  derived by the capped chain (hp capped [0,100] per round, gold uncapped),
  first round from openings, later rounds from the previous round's end.
  population = the season-end pop for that player (seasons[].meta; the
  page has no per-round population). win_streak = 0, roster_stars = 0
  (pipeline convention for unknown; formulaInputs.gaps keeps them
  un-verified). borrowed = 0, penalty = 0, liability = false on every move
  and season_state (no per-move/per-season borrowing is recorded in
  data.json; the leverage-penalty mechanism is therefore NOT independently
  verified by this run). action_kind = the round-type slug, except the
  four unambiguous event actions listed in EVENT_KINDS. semantic_kind =
  the substantive action thread (ordered text rules in
  classify_semantic; unclassifiable -> unknown, never force-fit).
  action_kind is unchanged by the semantic layer.
- season_state / rankings / hp_series are computed from openings +
  increments (never copied from a second source). Rankings sort by hp_end
  desc, ties by players-array order (page meta.derived).
- card_pool: the five tiers from data.json cardPool (cost->count); the
  special event card (cost null, "不进池") is excluded.
- holdings: playerCards joined to keyCards for cost. The three holdings
  of null-cost event cards are excluded (they are not pool cards).
  stars = 1 for every holding (data.json has no star data; null would
  crash the C6 synthesis computation in check.py).
- key_cards: the pool cards only (cost 1-5) with a parseable date.
  Excluded: the four null-cost event/policy cards (a null cost would emit
  the literal "None" into the Lean file and break the build) and the
  昇腾 card (when "持续出牌", no date; min_date/first_date are required).
  holders come from playerCards; shared = more than one holder.
  min_date = first_date = the parsed `when` date.
- facts: IPO / NVDA figures are the page's asserted numbers (see FACTS).
  The converter cross-checks every figure's decimal rendering against the
  page text (data.json + index.html) and fails loudly if any is absent.
  C7 only verifies the arithmetic, not the figures against the page; the
  cross-check is what ties them to the page. Combined/derived figures
  (base+private, greenshoe+private) are computed, not asserted.
- meta_players: the pipeline's nine-actor set (fixture shape). The page
  displays six seats (BIS·财政部·国安会 as one seat); DHS is a separate
  actor in the page's patch text. No rule_actions are copied from the
  fixture (its doc_numbers and trigger links are synthetic).
- rule_actions / political_record / trigger_links / lobby_actions /
  goal_checks: empty lists with provenance gaps. The page's rule chapter
  is prose; it has never been structurally extracted. The known real
  doc numbers (87 FR 62186, 2026-23529, 91 FR 66346) are NOT written here
  (there is no rule_action to attach them to); they are recorded in the
  provenance for the future rule-action extraction task.
- formulaInputs.gaps (5 items) stay un-verified: per-round population,
  win streaks, roster stars, borrowed principal, and key-card coverage of
  players without a card. They are listed in the provenance gaps.

Self-checks (fail loudly, exit non-zero, no silent pass):
- 558 moves / 31 rounds / 18 players per season.
- Every round has a roundRV entry and resolves to a base rule.
- Cross-season continuity: openings S2-S5 equal the computed prior
  season ends (breakpoint 0).
- Reconciliation: every one of the 137 entries matches the computed
  season end and new sum.
- FACTS figures all appear in the page text.
- Every playerCards card name exists in keyCards.
- Every keyCards `when` parses, or is the known dateless case.
Logged (not failed) data properties: gold going negative mid-chain,
roundRV-vs-resolved-rule mismatches, excluded cards/holdings, semantic
kind distribution (classified vs unknown). Hard-checked: the four
EVENT_KINDS moves classify to their event kind; every emitted semantic
kind is in SEMANTIC_VOCABULARY; the 15 legacy semantic-kind counts are
frozen (EXPECTED_LEGACY_COUNTS) so new rules can only classify from the
unknown pool.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------- constants

PLAYERS = ["NVDA", "OAI", "MSFT", "GOOG", "ANTH", "META", "AMZN", "MUSK",
           "AAPL", "ORCL", "BYTE", "ALI", "TCE", "BIDU", "HUAWEI", "DPSK",
           "TSMC", "SFTB"]
PID = {code: i for i, code in enumerate(PLAYERS)}

TYPE_SLUG = {"选秀": "draft", "野怪": "wild", "对战": "battle",
             "连胜轮": "streak", "经济轮": "economy", "内战": "civil_war",
             "决战": "final", "杠杆轮": "leverage", "事件": "event",
             "结算中": "settlement"}

# (season, round_code, player_code, action_kind, why this move is that action)
EVENT_KINDS = [
    ("S4", "1-1", "DPSK", "r1",
     "move text: R1 发布。AIME 79.8% 对 o1 的 79.2%"),
    ("S5", "4-1", "NVDA", "huang_resign",
     "move text: CEO 辞职。单轮重扣"),
    ("S5", "5-1", "ANTH", "anthropic_ipo",
     "move text: 分阶段募资到手。绿鞋后合计口径见本轮说明"),
    ("S5", "6-1", "NVDA", "sec_probe",
     "move text: SEC 调查报道。恐慌卖出"),
]

# ---------------------------------------------------------------- semantic kinds
# Semantic kind layer (added 2026-11-21, design/semantic-kinds.md).
#
# action_kind is the ROUND-TYPE slug (battle/economy/draft/...), which is
# what the trace has always carried. It cannot express WHAT a player did:
# the scenario bans in rules/scenarios.json (msft_invest, spacex_xai,
# stargate, colossus) use the fixture's SEMANTIC vocabulary, and the
# backtest's M1 (action-kind equality) on round-type slugs only measures
# round-type prediction, not action prediction. So every move now also
# carries semantic_kind: the substantive action thread it belongs to,
# classified from the move's own action text (player and round code only
# scope genuinely ambiguous keywords). action_kind is unchanged.
#
# Vocabulary: the fixture's 16 semantic kinds
# (fixtures/trace-fixture-ok.json) plus overseas_rental (banned by
# RV-2026.2; the fixture's broken variant carries it), plus 14 kinds
# added 2026-11-21 (second expansion, design/semantic-kinds.md §3):
# product threads tongyi/hunyuan/ascend/doubao/wenxin/pangu/llama/
# claude/gemini, event thread megaspeed, energy thread, and generic
# economic threads financing/capex/open_source. Two fixture kinds
# have no instance in the real trace and are never emitted: generic (the
# fixture's catch-all for ordinary moves; the real trace uses unknown for
# that) and openai_mar26 (the March 2026 OpenAI round is not in any move
# text: no 1220/8520/1.25万亿 hit). 29 kinds are emitted; the rest are
# unknown.
#
# Rules are ordered, first match wins. Each rule is a substring test on
# the move's action text, with the player/round scopes noted. The rules
# were written from a full keyword probe of the 558 move texts
# (2026-11-21, current data.json); the per-rule hit lists are in
# design/semantic-kinds.md. Deliberate exclusions (verified by the same
# probe): "100 亿美元" scoped to MSFT/OAI (ORCL S5 5-1 "债务包约 100 亿
# 美元未配售曝光" is Oracle debt, not the Microsoft investment);
# "上市" scoped to ANTH (SFTB S1 2-1 "ARM 上市筹备" is Arm's IPO);
# "IPO"/"上市" exclude "未上市" (MUSK's "未上市" moves are about not
# being listed); "承诺" only for ANTH S5 1-1 (other 承诺 moves are
# procurement or other players' receipts); "定价权" is NOT a price war;
# "扩散" in "项目融资模式扩散" is financing-model diffusion, not the AI
# diffusion rule; "不参与星门" (AAPL S4 1-2) still counts as stargate
# (a refusal stance on the thread).
# Second-expansion ordering constraints (each verified by probe; the
# new block runs after ALL 15 legacy rules so no legacy hit is stolen):
# tongyi after blackwell (S3 2-1 ALI "通义新版发布。阿里云打包 B200
# 替代方案" stays blackwell); ascend after r1 (S4 1-1 HUAWEI "昇腾成 R1
# 落地主平台" stays r1); doubao/wenxin after doubao_price_war (their
# price-war moves stay doubao_price_war); open_source after bis_rule
# (DPSK S5 5-1 "权重开源分发不受远程规则限" stays bis_rule) and after
# every product rule (product moves that mention 开源 stay with the
# product); doubao before llama (BYTE S2 3-2 "豆包拿 Llama 路线做内部版"
# is BYTE's own doubao action, Llama is the route); financing before
# capex (AAPL S3 1-1 "资本开支翻倍。借钱扩容" is a borrowing-funded
# capex move, counted as financing); open_source excludes "不开源"
# (GOOG S1 1-4 "Imagen 不开源" is about NOT open-sourcing).
SEMANTIC_VOCABULARY = [
    "chatgpt", "generic", "msft_invest", "doubao_price_war", "blackwell",
    "v3", "colossus", "r1", "stargate", "musk_table", "bis_rule",
    "openai_mar26", "anthropic_ipo", "spacex_xai", "huang_resign",
    "sec_probe", "overseas_rental",
    "tongyi", "hunyuan", "ascend", "doubao", "wenxin", "pangu",
    "llama", "claude", "gemini", "megaspeed", "energy", "financing",
    "capex", "open_source",
]
SEMANTIC_UNKNOWN = "unknown"

# Frozen counts of the 15 legacy kinds on the 2026-11-21 data.json
# (sha256 07995677...). Regression guard: the second-expansion rules
# may only classify from the unknown pool, never steal a legacy hit.
# If any count moves, a new rule (or a data change) stole a hit.
EXPECTED_LEGACY_COUNTS = {
    "stargate": 15, "anthropic_ipo": 8, "msft_invest": 7,
    "blackwell": 6, "r1": 6, "musk_table": 6, "colossus": 4,
    "spacex_xai": 4, "doubao_price_war": 4, "bis_rule": 4,
    "chatgpt": 3, "v3": 2, "overseas_rental": 2,
    "huang_resign": 1, "sec_probe": 1,
}


def classify_semantic(action, player, season, round_code):
    """Substantive action thread of one move. Ordered rules, first
    match wins; unclassifiable -> "unknown" (never force-fit)."""
    t = action
    if "SEC" in t:
        return "sec_probe"
    if "辞职" in t:
        return "huang_resign"
    if "星门" in t:
        return "stargate"
    if "Colossus" in t or (player == "MUSK" and "集群" in t):
        return "colossus"
    if "xAI" in t or "Grok" in t or "SpaceX" in t:
        return "spacex_xai"
    if "马斯克" in t or (player == "MUSK" and "推特" in t):
        return "musk_table"
    if "R1" in t or (season == "S4" and round_code == "1-1"
                     and "DeepSeek" in t):
        return "r1"
    if "V3" in t:
        return "v3"
    if ("B200" in t or "B300" in t or "Blackwell" in t
            or "GB200" in t):
        return "blackwell"
    if "价格战" in t or "降价" in t or "价格再降" in t:
        return "doubao_price_war"
    if "BIS" in t or "出口管制" in t or "远程规则" in t:
        return "bis_rule"
    if "IPO" in t and "未上市" not in t:
        return "anthropic_ipo"
    if player == "ANTH" and "上市" in t and "未上市" not in t:
        return "anthropic_ipo"
    if player == "ANTH" and "募资" in t:
        return "anthropic_ipo"
    if (player == "ANTH" and season == "S5" and round_code == "1-1"
            and "承诺" in t):
        return "anthropic_ipo"
    if ((player in ("MSFT", "OAI") and "100 亿美元" in t)
            or (player == "MSFT" and "追加投资" in t)
            or "循环图最大投资方" in t):
        return "msft_invest"
    if "ChatGPT" in t or "GPT-4" in t:
        return "chatgpt"
    if "海外算力" in t:
        return "overseas_rental"
    # --- second expansion (2026-11-21): rules 16-29, in this order ---
    # Product threads first (they own their moves even when the text
    # also mentions 开源/融资/资本开支), then the generic economic
    # threads, with open_source last. All run after the 15 legacy
    # rules above, so no legacy hit is stolen (guarded by
    # EXPECTED_LEGACY_COUNTS in the self-check).
    if "通义" in t:
        return "tongyi"
    if "混元" in t or (player == "TCE" and "微信" in t):
        return "hunyuan"
    if "昇腾" in t:
        return "ascend"
    if "豆包" in t:
        return "doubao"
    if "文心" in t:
        return "wenxin"
    if "盘古" in t:
        return "pangu"
    if "Llama" in t:
        return "llama"
    if "Claude" in t:
        return "claude"
    if "Gemini" in t or "Bard" in t:
        return "gemini"
    if "Megaspeed" in t:
        return "megaspeed"
    if ("核电" in t or "三哩岛" in t or "电力" in t or "绿电" in t
            or "燃气电厂" in t or "供电" in t):
        return "energy"
    if "融资" in t or "债务" in t or "借钱" in t:
        return "financing"
    if "资本开支" in t:
        return "capex"
    if "开源" in t and "不开源" not in t:
        return "open_source"
    return SEMANTIC_UNKNOWN

# Page-asserted figures. Cross-checked against page text at run time.
FACTS = {
    "ipo": {"base_usd_m": 81340, "greenshoe_total_usd_m": 93500,
            "private_usd_m": 26000, "base_plus_private_usd_m": 107340,
            "combined_usd_m": 119500, "net_usd_m": 117000},
    "nvda": {"close_high_cents": 23924, "close_drop_tenths_pct": 475,
             "intraday_high_cents": 24337, "intraday_drop_tenths_pct": 484,
             "low_cents": 12553},
    # Event min-dates (public record; each tagged move's date is >= its
    # min-date, verified by C5). r1 2025-01-20 and anthropic_ipo 2026-11-18
    # also appear in keyCards `when`. huang_resign: board accepted
    # 2026-11-11, announced 2026-11-12. sec_probe: first WSJ report
    # 2026-11-17 (Reuters accounting-probe report 2026-11-20).
    "dates": {"r1": 20250120, "huang_resign": 20261111,
              "anthropic_ipo": 20261118, "sec_probe": 20261117},
}
# Decimal renderings that must appear in the page text (data.json or
# index.html). If any is absent the FACTS table is stale: fail loudly.
FACT_STRINGS = {
    "813.4 亿美元": "ipo base 813.4亿美元",
    "935 亿美元": "ipo greenshoe total 935亿美元",
    "260 亿美元": "ipo private 260亿美元",
    "1195 亿美元": "ipo combined 1195亿美元",
    "1170 亿美元": "ipo net 1170亿美元",
    "1073.4": "ipo base+private 1073.4亿美元",
    "239.24": "nvda close high $239.24",
    "243.37": "nvda intraday high $243.37",
    "47.5": "nvda close drop 47.5%",
    "48.4": "nvda intraday drop 48.4%",
    "125.53": "nvda low $125.53",
}

# (rule_id, version, name, effective_from, effective_to, trigger,
#  trigger_type, applies_to_players, banned_action_kinds, note)
RULES_SPEC = [
    ("RV-2022.1", "2022-01", "管制前", 20220101, 20221007,
     "2022 年初：尚无针对先进 AI 芯片的出口管制", "none", None, [],
     "page patch chapter: S1 pre-2022-10-07; not in rules.json"),
    ("RV-2022.2", "2022-10", "BIS 2022-10 出口管制", 20221007, 20231017,
     "BIS 出口管制规则（2022-10-07）", "export_control", None, [],
     "rules.json RV-2022-10"),
    ("RV-2023.2", "2023-10", "BIS 2023-10 更新", 20231017, 20240404,
     "BIS 出口管制规则更新（2023-10-17）", "export_control", None, [],
     "rules.json RV-2023-10"),
    ("RV-2024.1", "2024-04", "BIS 2024-04 修订", 20240404, 20241202,
     "BIS 修订（2024-04-04）", "export_control", None, [],
     "page patch chapter: S3 2024-04-04 BIS revision; not in rules.json"),
    ("RV-2024-12", "2024-12", "BIS 2024-12 更新", 20241202, 20250113,
     "BIS 出口管制规则更新（2024-12-02）", "export_control", None, [],
     "rules.json RV-2024-12 (Dec 2024 update; no page version name). "
     "No round falls in its window [20241202, 20250113), so it never "
     "becomes the base rule for any move."),
    ("RV-2025.1", "2025-01", "AI 扩散规则", 20250113, 20250513,
     "AI 扩散规则发布（2025-01-13），2025-05-13 废止", "export_control",
     None, [], "rules.json RV-2025-01"),
    ("RV-2025.2", "2025-05", "扩散规则废止后", 20250513, 20260724,
     "扩散规则废止（2025-05-13）", "export_control", None, [],
     "rules.json RV-2025-01 effective_to; page patch chapter: diffusion "
     "rule rescinded 2025-05; not in rules.json as a separate rule"),
    ("RV-2026.1", "2026-07", "DHS 排除令时代", 20260724, 20261119,
     "DHS 排除令 #2026-01（2026-07-24 签署）", "procurement_exclusion",
     None, [], "INFERENCE: DHS exclusion 2026-07-24 is the only rule "
     "event in that window; the page gives no separate version date"),
    ("RV-2026.2", "2026-11", "BIS 远程接入规则 744.24", 20261119, None,
     "BIS 临时最终规则（2026-11-16 发布，11-19 生效，案卷 BIS-2026-0628）",
     "export_control", None, ["overseas_rental"],
     "rules.json RV-2026-11; page: remote-access rule effective 2026-11-19"),
]
# Overlay carried verbatim from rules.json (player-specific, not a base rule).
OVERLAY_SPEC = ("RV-2026-07", "2026-07", "DHS 排除令 #2026-01", 20260724,
                None,
                "DHS 排除令 #2026-01（2026-07-24 签署，联邦民事采购排除 DeepSeek）",
                "procurement_exclusion", [15], [],
                "rules.json RV-2026-07 (DHS overlay, applies to HUAWEI=15)")

# Pipeline actor vocabulary (fixture shape). The page displays six seats
# (BIS·财政部·国安会 as one seat); DHS is a separate actor in the page's
# patch text. No rule_actions are copied from the fixture.
META_PLAYERS = [
    {"id": "us_gov", "name": "美国政府", "kind": "government",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "congress", "name": "国会", "kind": "legislature",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "bis", "name": "BIS", "kind": "agency",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "treasury", "name": "财政部", "kind": "agency",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "nsc", "name": "国安会", "kind": "agency",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "dhs", "name": "DHS", "kind": "agency",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "california", "name": "加州", "kind": "state",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "china", "name": "中国", "kind": "government",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
    {"id": "eu", "name": "欧盟", "kind": "bloc",
     "layer1_role": "referee", "layer2_role": "rulemaker"},
]

GAPS = [
    "per-round population: data.json has only season-end pop "
    "(seasons[].meta); moves carry the season-end value",
    "win streaks (settlement income input): no source; moves carry 0",
    "roster stars (damage formula input): no source; moves carry 0",
    "borrowed principal (leverage penalty input): no source; "
    "season_state.borrowed = 0, penalty = 0, liability = false; the "
    "leverage-penalty mechanism is NOT independently verified by this run",
    "key-card coverage: 8 of 18 players have no card in playerCards; "
    "no source assigns them one",
    "event/policy cards (4, cost null) and the dateless 昇腾 card are not "
    "in trace key_cards (not pool cards / no date); they remain in the "
    "source data.json",
    "rule_actions / political_record / trigger_links / lobby_actions / "
    "goal_checks are empty: the page's rule chapter is prose, never "
    "structurally extracted; C10-C12 therefore check nothing (0 rows)",
    "known real doc numbers not yet attached to any rule_action: "
    "87 FR 62186, 2026-23529, 91 FR 66346 (for the future rule-action "
    "extraction task)",
    "page in-page fnv1a (8d90a977 per MEMORY, v13) could not be reproduced "
    "from the raw data.json bytes (raw c56c2078, compact-utf8 9d393414, "
    "compact-ascii 54d497f3, sorted-keys c23e110f); the page hashes some "
    "other serialization. sha256 is the provenance anchor here",
]


def fail(msg):
    print(f"convert: FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_cn_date(s):
    """Chinese free-text date -> YYYYMMDD int (earliest day), or None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return int(m.group(1) + m.group(2) + m.group(3))
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        return int(m.group(1) + m.group(2) + "01")
    m = re.match(r"^(\d{4}) 年 (\d{1,2}) 月 (\d{1,2})", s)
    if m:
        return int("%04d%02d%02d" % (int(m.group(1)), int(m.group(2)),
                                     int(m.group(3))))
    m = re.match(r"^(\d{4}) 年 (\d{1,2}) 月", s)
    if m:
        return int("%04d%02d01" % (int(m.group(1)), int(m.group(2))))
    m = re.match(r"^(\d{4}) 年", s)
    if m:
        y = int(m.group(1))
        if "年初" in s:
            return y * 10000 + 101
        if "年底" in s or "年末" in s:
            return y * 10000 + 1201
        if "上半年" in s:
            return y * 10000 + 101
        if "下半年" in s:
            return y * 10000 + 701
        if "年中" in s:
            return y * 10000 + 601
        return y * 10000 + 101
    return None


def cap(v, lo, hi):
    return max(lo, min(hi, v))


def resolve_base(rules, date):
    """Same logic as check.py resolve_rules (global rules only)."""
    base = None
    for r in rules:
        if r.get("applies_to_players") is not None:
            continue
        if not (r["effective_from"] <= date):
            continue
        if r.get("effective_to") is not None and date >= r["effective_to"]:
            continue
        if base is None or (r["effective_from"], r["rule_id"]) > (
                base["effective_from"], base["rule_id"]):
            base = r
    return base


def main():
    ap = argparse.ArgumentParser(
        description="Convert page data.json to a schema v3 raw trace.")
    ap.add_argument("data", help="data.json (machine copy of page assets)")
    ap.add_argument("--rules", default="rules/rules.json",
                    help="pipeline rule table")
    ap.add_argument("--page", default=None,
                    help="page index.html (for the FACTS cross-check)")
    ap.add_argument("--out", default="raw-trace-real.json",
                    help="raw trace output")
    ap.add_argument("--provenance", default="raw-trace-real.provenance.json",
                    help="provenance output")
    args = ap.parse_args()

    data_path = Path(args.data)
    raw_bytes = data_path.read_bytes()
    data = json.loads(raw_bytes)
    src_sha = hashlib.sha256(raw_bytes).hexdigest()

    # --- anchor the rule translation to rules.json ---------------------
    rules_json = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    by_id = {r["rule_id"]: r for r in rules_json.get("rules", [])}
    expected = {"RV-2022-10": 20221007, "RV-2023-10": 20231017,
                "RV-2024-12": 20241202, "RV-2025-01": 20250113,
                "RV-2026-07": 20260724, "RV-2026-11": 20261119}
    for rid, eff in expected.items():
        if rid not in by_id:
            fail(f"rules.json: missing expected rule {rid} (table changed?)")
        if by_id[rid]["effective_from"] != eff:
            fail(f"rules.json: {rid} effective_from "
                 f"{by_id[rid]['effective_from']} != {eff}")
        p = by_id[rid]["params"]
        if (p.get("hp_cap") != 100 or p.get("hp_floor") != 0
                or p.get("leverage_penalty") != "floor(borrowed * 0.5)"
                or p.get("penalty_applies_to") != "hp"):
            fail(f"rules.json: {rid} params no longer the baseline")

    # --- FACTS cross-check against page text ---------------------------
    page_text = raw_bytes.decode("utf-8")
    if args.page:
        page_text += "\n" + Path(args.page).read_text(encoding="utf-8")
    fact_checks = {}
    for needle, what in FACT_STRINGS.items():
        found = needle in page_text
        fact_checks[what] = {"needle": needle, "found_in_page_text": found}
        if not found:
            fail(f"FACTS cross-check: '{needle}' ({what}) not found in "
                 f"page text; FACTS table is stale")
    # arithmetic the converter itself computes (C7 re-verifies):
    ipo = FACTS["ipo"]
    assert ipo["base_usd_m"] + ipo["private_usd_m"] == ipo["base_plus_private_usd_m"]
    assert ipo["greenshoe_total_usd_m"] + ipo["private_usd_m"] == ipo["combined_usd_m"]

    # --- players --------------------------------------------------------
    if [p["id"] for p in data["players"]] != PLAYERS:
        fail("data.json players order changed; int-id mapping needs review")
    players = [{"id": PID[p["id"]], "name": p["name"], "key": p["id"],
                "first_season": 1, "last_season": 5}
               for p in data["players"]]
    pname = {PID[p["id"]]: p["name"] for p in data["players"]}

    # --- seasons, rounds, moves, chains ---------------------------------
    seasons = data["seasons"]
    round_rv = data.get("roundRV", {})
    if len(round_rv) != 31:
        fail(f"roundRV has {len(round_rv)} entries, expected 31")
    openings = data["openings"]
    event_map = {(s, c, p): k for (s, c, p, k, _why) in EVENT_KINDS}

    # rules for the trace
    formulas = data["formulas"]
    hp_cap = formulas["accounting"]["hpRange"]["max"]
    hp_floor = formulas["accounting"]["hpRange"]["min"]
    lev_mult = formulas["settlement"]["leverage"]["multiplier"]
    lev_formula = "floor(borrowed * %s)" % (str(lev_mult).rstrip("0").rstrip(".")
                                            if "." in str(lev_mult)
                                            else str(lev_mult))
    income = formulas["settlement"]["income"]

    def base_params(banned):
        return {"hp_cap": hp_cap, "hp_floor": hp_floor,
                "leverage_penalty": lev_formula,
                "penalty_applies_to": "hp",
                "banned_action_kinds": list(banned),
                "unavailable_cards": [],
                "income_base": income["base"],
                "income_interest_cap": income["interestCap"],
                "win_streak_bonus_max": income["streakBonusMax"]}

    rules = []
    for (rid, ver, name, eff, eff_to, trig, ttype, applies, banned,
         note) in RULES_SPEC:
        rules.append({"rule_id": rid, "version": ver, "name": name,
                      "effective_from": eff, "effective_to": eff_to,
                      "trigger": trig, "trigger_type": ttype,
                      "applies_to_players": applies,
                      "params": base_params(banned), "note": note})
    (orid, over, oname, oeff, oeff_to, otrig, ottype, oapplies, obanned,
     onote) = OVERLAY_SPEC
    rules.append({"rule_id": orid, "version": over, "name": oname,
                  "effective_from": oeff, "effective_to": oeff_to,
                  "trigger": otrig, "trigger_type": ottype,
                  "applies_to_players": oapplies,
                  "params": base_params(obanned), "note": onote})

    out_seasons, moves = [], []
    season_state, rankings, hp_series = [], [], []
    season_ends = {}          # (season_no, pid) -> (hp_end, gold_end)
    season_open = {}          # (season_no, pid) -> (hp_start, gold_start)
    gold_negative_log = []
    rv_mismatch_log = []
    for si, s in enumerate(seasons, start=1):
        sid = s["id"]
        if sid != "S%d" % si:
            fail(f"seasons out of order: {sid} at position {si}")
        pop = {e["id"]: e["pop"] for e in s["meta"]}
        sdate = parse_cn_date(s.get("start"))
        edate = parse_cn_date(s.get("end"))
        if sdate is None or edate is None:
            fail(f"{sid}: start/end date unparseable: "
                 f"{s.get('start')!r} / {s.get('end')!r}")
        rounds = s["rounds"]
        last_rv = None
        for ri, r in enumerate(rounds, start=1):
            key = "%s:%s" % (sid, r["code"])
            if key not in round_rv:
                fail(f"roundRV missing {key}")
            last_rv = round_rv[key]
            rdate = parse_cn_date(r["date"])
            if rdate is None:
                fail(f"{key}: round date unparseable: {r['date']!r}")
            base = resolve_base(rules, rdate)
            if base is None:
                fail(f"{key}: no rule version applies to date {rdate}")
            if base["rule_id"] != round_rv[key]:
                rv_mismatch_log.append(
                    {"round": key, "date": rdate,
                     "recorded_roundRV": round_rv[key],
                     "resolved_base": base["rule_id"],
                     "note": "round straddles a rule-change day; page "
                             "records the later version"})
            if r["type"] not in TYPE_SLUG:
                fail(f"{key}: unknown round type {r['type']!r}")
            kind = TYPE_SLUG[r["type"]]
            if len(r["moves"]) != 18:
                fail(f"{key}: {len(r['moves'])} moves, expected 18")
            for (pcode, action, hpd, gd) in r["moves"]:
                pid = PID[pcode]
                moves.append({"season": si, "round_index": ri,
                              "round_label": r["code"], "player": pid,
                              "hp_delta": hpd, "gold_delta": gd,
                              "action_kind": event_map.get(
                                  (sid, r["code"], pcode), kind),
                              "semantic_kind": classify_semantic(
                                  action, pcode, sid, r["code"]),
                              "action": action, "date": rdate,
                              "hp_start": None, "gold_start": None,
                              "population": pop[pcode], "win_streak": 0,
                              "roster_stars": 0, "borrowed": 0,
                              "liability": False,
                              "rules_version": round_rv[key]})
        # chain per player (openings -> capped hp, uncapped gold)
        for pid in range(18):
            pcode = PLAYERS[pid]
            cur_hp = openings[sid]["hp"][pcode]
            cur_gold = openings[sid]["gold"][pcode]
            season_open[(si, pid)] = (cur_hp, cur_gold)
            for m in [x for x in moves
                      if x["season"] == si and x["player"] == pid]:
                m["hp_start"] = cur_hp
                m["gold_start"] = cur_gold
                cur_hp = cap(cur_hp + m["hp_delta"], hp_floor, hp_cap)
                cur_gold = cur_gold + m["gold_delta"]
                if cur_gold < 0 and not m.get("liability", False):
                    gold_negative_log.append(
                        {"season": si, "round_label": m["round_label"],
                         "player": pname[pid], "gold_after": cur_gold})
            season_ends[(si, pid)] = (cur_hp, cur_gold)
            season_state.append({"season": si, "player": pid,
                                 "hp_start": season_open[(si, pid)][0],
                                 "gold_start": season_open[(si, pid)][1],
                                 "hp_end": cur_hp, "gold_end": cur_gold,
                                 "borrowed": 0, "penalty": 0})
        out_seasons.append({"season": si, "name": sid,
                            "start_date": sdate, "end_date": edate,
                            "rounds": len(rounds),
                            "active_players": list(range(18)),
                            "rules_version": last_rv})
        # rankings: hp_end desc, ties by players-array order
        order = sorted(range(18),
                       key=lambda pid: (-season_ends[(si, pid)][0], pid))
        for rank, pid in enumerate(order, start=1):
            rankings.append({"season": si, "player": pid, "rank": rank,
                             "hp_end": season_ends[(si, pid)][0],
                             "gold_end": season_ends[(si, pid)][1]})
    for pid in range(18):
        hp_series.append({"player": pid,
                          "points": [season_ends[(si, pid)][0]
                                     for si in range(1, 6)]})

    # --- semantic-kind consistency --------------------------------------
    # The four EVENT_KINDS moves must classify to their event kind (the
    # semantic rules reproduce them); every emitted kind must be in the
    # vocabulary. Distribution is logged, not failed (unknown is a
    # legitimate outcome: unclassifiable moves are not force-fit).
    sem_dist = Counter(m["semantic_kind"] for m in moves)
    for (s, c, p, k, _why) in EVENT_KINDS:
        got = next((m["semantic_kind"] for m in moves
                    if m["season"] == int(s[1:])
                    and m["round_label"] == c
                    and PLAYERS[m["player"]] == p), None)
        if got != k:
            fail(f"semantic kind mismatch: {s} {c} {p} classified "
                 f"{got!r}, expected event kind {k!r}")
    for k in sem_dist:
        if k != SEMANTIC_UNKNOWN and k not in SEMANTIC_VOCABULARY:
            fail(f"semantic kind {k!r} not in the vocabulary")
    for k, want in EXPECTED_LEGACY_COUNTS.items():
        got = sem_dist.get(k, 0)
        if got != want:
            fail(f"semantic kind regression: legacy kind {k!r} count "
                 f"{got}, expected {want} (a new rule stole a legacy hit "
                 f"or the source data changed)")

    if len(moves) != 558:
        fail(f"moves total {len(moves)}, expected 558")

    # --- cross-season continuity (openings S2-S5 == prior season ends) --
    for si in range(2, 6):
        sid = "S%d" % si
        for pid in range(18):
            pcode = PLAYERS[pid]
            if openings[sid]["hp"][pcode] != season_ends[(si - 1, pid)][0]:
                fail(f"cross-season break: {sid} {pcode} hp opening "
                     f"{openings[sid]['hp'][pcode]} != "
                     f"S{si-1} end {season_ends[(si-1, pid)][0]}")
            if openings[sid]["gold"][pcode] != season_ends[(si - 1, pid)][1]:
                fail(f"cross-season break: {sid} {pcode} gold opening "
                     f"{openings[sid]['gold'][pcode]} != "
                     f"S{si-1} end {season_ends[(si-1, pid)][1]}")

    # --- reconciliation cross-check (137 fixed items) --------------------
    rec_checked = 0
    for e in data.get("reconciliation", []):
        si = int(e["season"][1:])
        pid = PID[e["player"]]
        field = e["field"]
        if field not in ("hp", "gold"):
            fail(f"reconciliation: unknown field {field!r}")
        idx = 0 if field == "hp" else 1
        computed = season_ends[(si, pid)][idx]
        opening = season_open[(si, pid)][idx]
        if computed != e["seasonEnd"]:
            fail(f"reconciliation mismatch: {e['season']} {e['player']} "
                 f"{field}: computed season end {computed} != "
                 f"seasonEnd {e['seasonEnd']} (round {e['round']})")
        if computed - opening != e["newSum"]:
            fail(f"reconciliation mismatch: {e['season']} {e['player']} "
                 f"{field}: computed new sum {computed - opening} != "
                 f"newSum {e['newSum']}")
        if opening != e["prevEnd"]:
            fail(f"reconciliation mismatch: {e['season']} {e['player']} "
                 f"{field}: opening {opening} != prevEnd {e['prevEnd']}")
        rec_checked += 1

    # --- card pool / holdings / key cards --------------------------------
    pool = []
    for row in data["cardPool"]:
        if row.get("cost") is None:
            continue  # special event card: 不进池
        pool.append({"cost": row["cost"], "total": row["count"]})
    if sorted((c["cost"], c["total"]) for c in pool) != \
            [(1, 29), (2, 22), (3, 18), (4, 12), (5, 10)]:
        fail(f"card pool changed: {pool}")

    key_by_name = {k["name"]: k for k in data["keyCards"]}
    holders_by_card = {}
    for pcode, cards in data["playerCards"].items():
        for card in cards:
            if card not in key_by_name:
                fail(f"playerCards: {pcode} holds {card!r}, "
                     f"not in keyCards")
            holders_by_card.setdefault(card, []).append(PID[pcode])

    holdings, excluded_holdings = [], []
    for pcode, cards in data["playerCards"].items():
        for card in cards:
            cost = key_by_name[card].get("cost")
            if cost is None:
                excluded_holdings.append(
                    {"player": pcode, "card": card,
                     "reason": "null cost: event/policy card, not a pool "
                               "card; excluded from holdings"})
                continue
            holdings.append({"player": PID[pcode], "card": card,
                             "cost": cost, "stars": 1})

    key_cards, excluded_cards = [], []
    for kc in data["keyCards"]:
        name = kc["name"]
        if kc.get("cost") is None:
            excluded_cards.append(
                {"card": name, "reason": "null cost: event/policy card, "
                 "not a pool card; a null cost would emit 'None' into the "
                 "Lean file and break the build"})
            continue
        d = parse_cn_date(kc.get("when"))
        if d is None:
            excluded_cards.append(
                {"card": name, "when": kc.get("when"),
                 "reason": "no parseable date; min_date/first_date are "
                           "required and must not be invented"})
            continue
        holders = holders_by_card.get(name, [])
        key_cards.append({"card": name, "cost": kc["cost"],
                          "holders": holders,
                          "shared": len(holders) > 1,
                          "min_date": d, "first_date": d})

    trace = {
        "schema_version": 3,
        "source_data_json": {"path": str(data_path), "sha256": src_sha,
                             "bytes": len(raw_bytes)},
        "players": players,
        "seasons": out_seasons,
        "moves": moves,
        "season_state": season_state,
        "rankings": rankings,
        "hp_series": hp_series,
        "card_pool": pool,
        "holdings": holdings,
        "key_cards": key_cards,
        "facts": FACTS,
        "formulas": {"hp_cap": hp_cap, "hp_floor": hp_floor,
                     "leverage_penalty": lev_formula,
                     "penalty_applies_to": "hp"},
        "rules": rules,
        "meta_players": META_PLAYERS,
        "rule_actions": [],
        "political_record": [],
        "trigger_links": [],
        "lobby_actions": [],
        "goal_checks": [],
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(trace, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    provenance = {
        "converter": "convert_data_json.py (data.json -> schema v3 raw trace)",
        "source": {"file": str(data_path), "sha256": src_sha,
                   "bytes": len(raw_bytes),
                   "note": "machine copy (cp) of page assets/data.json; "
                           "no hand transcription, no rank back-computation"},
        "page_version": "v13 (per parent handoff 2026-11-21 19:48 CST)",
        "counts": {"moves": len(moves), "rounds": 31, "players": 18,
                   "seasons": 5, "holdings": len(holdings),
                   "key_cards": len(key_cards),
                   "key_cards_in_source": len(data["keyCards"]),
                   "reconciliation_checked": rec_checked},
        "facts_cross_check": fact_checks,
        "roundRV_vs_resolved_rule_mismatches": rv_mismatch_log,
        "gold_negative_mid_chain": gold_negative_log,
        "excluded_holdings": excluded_holdings,
        "excluded_key_cards": excluded_cards,
        "event_kinds": [{"season": s, "round": c, "player": p, "kind": k,
                         "why": w} for (s, c, p, k, w) in EVENT_KINDS],
        "semantic_kinds": {
            "vocabulary": SEMANTIC_VOCABULARY,
            "unknown_marker": SEMANTIC_UNKNOWN,
            "distribution": dict(sorted(sem_dist.items())),
            "classified": sum(v for k, v in sem_dist.items()
                              if k != SEMANTIC_UNKNOWN),
            "unknown": sem_dist.get(SEMANTIC_UNKNOWN, 0),
            "note": ("Per-move substantive action thread, classified "
                     "from the move's own action text (see "
                     "design/semantic-kinds.md). action_kind (round-type "
                     "slug) is unchanged. generic and openai_mar26 have "
                     "no instance in the real trace."),
        },
        "rules": [{"rule_id": r["rule_id"], "version": r["version"],
                   "effective_from": r["effective_from"],
                   "effective_to": r["effective_to"],
                   "applies_to_players": r["applies_to_players"],
                   "note": r["note"]} for r in rules],
        "defaults_and_gaps": GAPS,
        "season_rules_version": {s["name"]: s["rules_version"]
                                 for s in out_seasons},
        "season_dates": {s["name"]: [s["start_date"], s["end_date"]]
                         for s in out_seasons},
    }
    Path(args.provenance).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(f"convert: ok -> {out_path} ({len(moves)} moves, "
          f"{len(holdings)} holdings, {len(key_cards)} key cards, "
          f"{rec_checked} reconciliation items checked)")
    print(f"convert: semantic kinds: "
          f"{sum(v for k, v in sem_dist.items() if k != SEMANTIC_UNKNOWN)}"
          f" classified / {sem_dist.get(SEMANTIC_UNKNOWN, 0)} unknown; "
          + ", ".join(f"{k}={v}" for k, v in sorted(sem_dist.items())
                      if k != SEMANTIC_UNKNOWN))
    print(f"convert: provenance -> {args.provenance}")
    print(f"convert: source data.json sha256 {src_sha}")
    if rv_mismatch_log:
        print(f"convert: NOTE {len(rv_mismatch_log)} round(s) where "
              f"roundRV != resolved base rule: "
              + ", ".join(f"{m['round']} recorded {m['recorded_roundRV']} "
                          f"vs resolved {m['resolved_base']}"
                          for m in rv_mismatch_log))
    if gold_negative_log:
        print(f"convert: NOTE gold goes negative mid-chain in "
              f"{len(gold_negative_log)} move(s)")
    if excluded_cards or excluded_holdings:
        print(f"convert: NOTE excluded {len(excluded_cards)} key card(s), "
              f"{len(excluded_holdings)} holding(s) (see provenance)")


if __name__ == "__main__":
    main()
