#!/usr/bin/env python3
"""Generate fixture traces for pipeline testing (schema v4).

- trace-fixture-ok.json: full-scale, consistent by construction
  (18 players, 31 rounds, 558 moves, 5 seasons, pool, holdings, facts,
  6 versioned rules, meta-game layer, agent claims + daily events,
  knowledge + payoff feedback).
- trace-fixture-broken.json: same data with the known error pattern
  injected (S5 NVDA hp -7 / gold -32, S5 Anthropic hp -17, a player
  acting after death, a pool over-hold, a predated move, an
  overseas_rental move after RV-2026-11 took effect, a rule action
  whose doc number matches no political record, a trigger link with
  inverted dates, an unclassified event, a claim without evidence,
  a classification that disagrees with its signal, a payoff delta
  that pushes a meta-player out of range).
  The fast checker must PASS the ok fixture and FAIL the broken one
  with exact positions; the agent protocol checker must PASS the ok
  fixture and FAIL the broken one; Lean must prove the ok fixture
  (finite checks + inductive trajectory theorem + agent hypotheses)
  and refuse the broken one.

Player order, season round counts, pool totals, IPO/NVDA facts and
key dates come from the page inspection (2026-11-21). Deltas are
seeded-random and consistent by construction. Rules are loaded from
../rules/rules.json so the fixture and the rule table stay in sync.

Modelling notes (judgements, labelled as such):
- Early BIS rules list H100 as unavailable: the 2022-10 rule restricted
  advanced-computing chip exports; H100 first appeared 2022-03-22,
  before the rule, so no first-appearance violation. This is what makes
  the "restrictive" goal check true for those rules.
- The DHS exclusion lists R1 as unavailable for the same reason
  (R1 first appeared 2025-01-20, before the 2026-07-24 order).
- Doc numbers for the 2026-11 rule are real (FR doc 2026-23529,
  docket BIS-2026-0628); older doc numbers are FIXTURE- placeholders
  except 87 FR 62186 (2022-10, verified). The real trace must carry
  real numbers; the fixture only needs internal consistency.
- Payoff deltas are synthetic judgements (small integers); the
  invariant only bounds them to [-10, 10] and checks the feedback
  loop applies them.
"""
import copy
import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE
RULES_PATH = HERE.parent / "rules" / "rules.json"

PLAYERS = [
    (0, "英伟达", "NVDA"), (1, "OpenAI", "OAI"), (2, "微软", "MSFT"),
    (3, "谷歌", "GOOG"), (4, "Anthropic", "ANTH"), (5, "Meta", "META"),
    (6, "亚马逊", "AMZN"), (7, "马斯克·xAI", "MUSK"), (8, "苹果", "AAPL"),
    (9, "甲骨文", "ORCL"), (10, "字节跳动", "BYTE"),
    (11, "阿里·阿里云", "ALI"), (12, "腾讯·腾讯云", "TCE"),
    (13, "百度·百度智能云", "BIDU"), (14, "华为·昇腾", "HUAWEI"),
    (15, "DeepSeek", "DPSK"), (16, "台积电", "TSMC"), (17, "软银", "SFTB"),
]
ROUNDS_PER_SEASON = {1: 5, 2: 7, 3: 6, 4: 6, 5: 7}
SEASON_SPAN = {
    1: (date(2022, 11, 30), date(2022, 12, 31)),
    2: (date(2023, 1, 1), date(2023, 12, 31)),
    3: (date(2024, 1, 1), date(2024, 12, 31)),
    4: (date(2025, 1, 1), date(2025, 12, 31)),
    5: (date(2026, 1, 1), date(2026, 11, 21)),
}
# action kind -> earliest true date (YYYYMMDD)
KINDS = {
    "chatgpt": 20221130, "msft_invest": 20230101, "blackwell": 20240318,
    "doubao_price_war": 20240515, "v3": 20241226, "r1": 20250120,
    "stargate": 20250121, "musk_table": 20250121, "colossus": 20240901,
    "spacex_xai": 20260202, "openai_mar26": 20260331,
    "huang_resign": 20261111, "bis_rule": 20261116,
    "sec_probe": 20261117, "anthropic_ipo": 20261118,
    "generic": 20221130,
}
# key card: (card, cost, holder id, min_date, kind, season)
KEY_CARDS = [
    ("ChatGPT", 5, 1, 20221130, "chatgpt", 1),
    ("微软投资", 5, 2, 20230101, "msft_invest", 2),
    ("H100", 5, 0, 20220322, "generic", 2),
    ("Colossus", 5, 7, 20240901, "colossus", 3),
    ("R1", 5, 15, 20250120, "r1", 4),
    ("星门", 5, 1, 20250121, "stargate", 4),
    ("昇腾", 5, 14, 20190901, "generic", 2),
    ("OpenAI 3月轮", 5, 1, 20260331, "openai_mar26", 5),
    ("Anthropic上市", 5, 4, 20261118, "anthropic_ipo", 5),
    ("SpaceX收购xAI", 5, 7, 20260202, "spacex_xai", 5),
    ("豆包价格战", 2, 10, 20240515, "doubao_price_war", 3),
    ("马斯克掀桌", 3, 7, 20250121, "musk_table", 4),
    ("BIS规则", 3, 0, 20261116, "bis_rule", 5),
    ("黄仁勋辞职", 3, 0, 20261111, "huang_resign", 5),
    ("SEC调查", 3, 0, 20261117, "sec_probe", 5),
]
BORROWED = {(9, 3): 10, (17, 4): 10, (9, 5): 20}  # (player, season) -> borrowed

# Meta-game parties (layer 2). kind/layer1_role/layer2_role per schema v3.
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
# rule_id -> (actor, issued_by, doc_number, stated_goal, trigger_event id)
RULE_ACTION_META = {
    "RV-2022-10": ("bis", "BIS", "87 FR 62186", "national_security",
                   "evt-bis-2022-10-obs"),
    "RV-2023-10": ("bis", "BIS", "FIXTURE-BIS-2023-10", "national_security",
                   "evt-bis-2023-10-obs"),
    "RV-2024-12": ("bis", "BIS", "FIXTURE-BIS-2024-12", "national_security",
                   "evt-bis-2024-12-obs"),
    "RV-2025-01": ("bis", "BIS", "FIXTURE-BIS-2025-01", "national_security",
                   "evt-bis-2025-01-obs"),
    "RV-2026-07": ("dhs", "DHS", "FIXTURE-DHS-2026-07",
                   "industrial_advantage", "evt-dhs-2026-07-obs"),
    "RV-2026-11": ("bis", "BIS", "2026-23529", "national_security",
                   "evt-bis-2026-11-obs"),
}
# rule_id -> payoff delta over META_PLAYERS order (synthetic judgements)
PAYOFFS = {
    "RV-2022-10": [1, 0, 1, 0, 0, 0, 0, 0, 0],
    "RV-2023-10": [0, 0, 1, 0, 0, 0, 0, 0, 0],
    "RV-2024-12": [1, 0, 1, 0, 0, 0, 0, 0, 0],
    "RV-2025-01": [0, 0, 1, 0, 0, 0, 0, -1, 0],
    "RV-2026-07": [1, 0, 0, 0, 0, 1, 0, 0, 0],
    "RV-2026-11": [0, 0, 2, 0, 0, 0, 0, -1, 0],
}
# (season, player, round_index, date, kind) anchor moves for trigger links
ANCHORS = {
    "RV-2022-10": (1, 0, 1, None, None),
    "RV-2023-10": (2, 0, 7, 20231101, None),
    "RV-2024-12": (3, 0, 6, 20241215, None),
    "RV-2025-01": (4, 0, 6, 20250201, None),
    "RV-2026-07": (5, 15, 7, 20260801, None),
    "RV-2026-11": (5, 0, 7, 20261120, "bis_rule"),
}
# rule_id -> (observe event date, observe-again event date)
LINK_DATES = {
    "RV-2022-10": (20221001, 20230115),
    "RV-2023-10": (20231010, 20231201),
    "RV-2024-12": (20241125, 20250115),
    "RV-2025-01": (20250105, 20250301),
    "RV-2026-07": (20260715, 20260901),
    "RV-2026-11": (20261116, 20261215),
}


def cap(v):
    return max(0, min(100, v))


def ymd(d):
    return d.year * 10000 + d.month * 100 + d.day


def rand_date(rng, start, end):
    span = (end - start).days
    d = start + timedelta(days=rng.randint(0, max(span, 0)))
    return ymd(d)


def load_rules():
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rules = data["rules"]
    # Modelling: early BIS rules restricted advanced-chip exports (H100
    # unavailable from the rule onward); the DHS order excluded DeepSeek
    # (R1 unavailable from the order onward). First appearances predate
    # the rules, so C5 stays green; the "restrictive" goal check holds.
    for r in rules:
        if r["rule_id"] in ("RV-2022-10", "RV-2023-10", "RV-2024-12",
                            "RV-2025-01"):
            r["params"]["unavailable_cards"] = ["H100"]
        if r["rule_id"] == "RV-2026-07":
            r["params"]["unavailable_cards"] = ["R1"]
    return rules


def resolve_rule(rules, d):
    """Rule id in effect on date d (global rules only; latest wins)."""
    base = None
    for r in rules:
        if r.get("applies_to_players") is not None:
            continue
        if r["effective_from"] > d:
            continue
        if r.get("effective_to") is not None and d >= r["effective_to"]:
            continue
        if base is None or r["effective_from"] > base["effective_from"]:
            base = r
    return base["rule_id"] if base else None


def build(seed=42):
    rng = random.Random(seed)
    rules = load_rules()
    moves, states, rankings = [], [], []
    hp = {pid: 100 for pid, _, _ in PLAYERS}
    gold = {pid: 50 for pid, _, _ in PLAYERS}
    series = {pid: [] for pid, _, _ in PLAYERS}

    for s in range(1, 6):
        s_start, s_end = SEASON_SPAN[s]
        for ridx in range(1, ROUNDS_PER_SEASON[s] + 1):
            for pid, _, _ in PLAYERS:
                kinds_ok = [k for k, d in KINDS.items()
                            if d <= int(s_end.strftime("%Y%m%d"))]
                kind = rng.choice(kinds_ok)
                lo = max(s_start, date(KINDS[kind] // 10000,
                                       (KINDS[kind] // 100) % 100,
                                       KINDS[kind] % 100))
                d = rand_date(rng, lo, s_end)
                hp_delta = rng.randint(-12, 6)
                if hp[pid] < 35:
                    # keep everyone alive: the real page has no elimination
                    hp_delta = rng.randint(0, 8)
                gold_delta = rng.randint(-25, 30)
                if gold[pid] + gold_delta < 0:
                    gold_delta = -gold[pid]
                moves.append({
                    "season": s, "round_index": ridx,
                    "round_label": f"{s}-{ridx}", "player": pid,
                    "hp_delta": hp_delta, "gold_delta": gold_delta,
                    "action_kind": kind,
                    "action": f"{kind} 动作",
                    "date": d, "hp_start": hp[pid], "gold_start": gold[pid],
                    "population": rng.randint(3, 9),
                    "win_streak": rng.randint(0, 5),
                    "roster_stars": rng.randint(1, 3),
                    "borrowed": BORROWED.get((pid, s), 0),
                    "liability": False,
                })
                hp[pid] = cap(hp[pid] + hp_delta)
                gold[pid] = gold[pid] + gold_delta
        # season end: leverage penalty on HP
        for pid, _, _ in PLAYERS:
            borrowed = BORROWED.get((pid, s), 0)
            penalty = borrowed // 2
            hp_end = cap(hp[pid] - penalty)
            gold_end = gold[pid]
            states.append({
                "season": s, "player": pid,
                "hp_start": None, "gold_start": None,
                "hp_end": hp_end, "gold_end": gold_end,
                "borrowed": borrowed, "penalty": penalty,
            })
            series[pid].append(hp_end)
            hp[pid], gold[pid] = hp_end, gold_end
    # fix season starts (S1: 100/50, later: previous season end)
    prev = {}
    for st in states:
        pid = st["player"]
        if st["season"] == 1:
            st["hp_start"], st["gold_start"] = 100, 50
        else:
            st["hp_start"] = prev[pid]["hp_end"]
            st["gold_start"] = prev[pid]["gold_end"]
        prev[pid] = st
    # rankings: rank by hp_end desc, then gold_end desc
    for s in range(1, 6):
        rows = [st for st in states if st["season"] == s]
        rows.sort(key=lambda x: (-x["hp_end"], -x["gold_end"], x["player"]))
        for i, st in enumerate(rows, 1):
            rankings.append({"season": s, "player": st["player"], "rank": i,
                             "hp_end": st["hp_end"],
                             "gold_end": st["gold_end"]})
    # overlay key cards onto distinct moves (one card per move)
    used = {}
    for card, cost, holder, min_date, kind, season in KEY_CARDS:
        cand = [m for m in moves if m["season"] == season
                and m["player"] == holder]
        key = (season, holder)
        m = cand[used.get(key, 0) % len(cand)]
        used[key] = used.get(key, 0) + 1
        m["action_kind"] = kind
        m["action"] = f"{card}（关键牌）"
        if m["date"] < min_date:
            m["date"] = min_date
    # anchor moves for trigger links (fixed dates after each rule's
    # effective date; the RV-2026-11 anchor is a bis_rule move).
    # The anchor's kind is forced to a kind whose true earliest date
    # precedes the anchor date, so C5 stays green; a key-card marker
    # in the action text is preserved (the card gain is detected
    # from the marker, not from the kind).
    for rule_id, (s, pid, ridx, d, kind) in ANCHORS.items():
        if d is None:
            continue
        m = next(x for x in moves if x["season"] == s
                 and x["player"] == pid and x["round_index"] == ridx)
        m["date"] = d
        m["action_kind"] = kind if kind else "generic"
        if "（关键牌）" not in m["action"]:
            m["action"] = f"{m['action_kind']} 动作"
    # recorded rule version per move (ROUND_RV), resolved by final date
    for m in moves:
        m["rules_version"] = resolve_rule(rules, m["date"])

    seasons = []
    for s in range(1, 6):
        s_start, s_end = SEASON_SPAN[s]
        seasons.append({
            "season": s, "name": f"S{s}",
            "start_date": ymd(s_start), "end_date": ymd(s_end),
            "rounds": ROUNDS_PER_SEASON[s],
            "active_players": [pid for pid, _, _ in PLAYERS],
            "rules_version": resolve_rule(rules, ymd(s_start)),
        })

    rule_actions = []
    political_record = []
    trigger_links = []
    for r in rules:
        rid = r["rule_id"]
        actor, issued_by, doc, goal, trig = RULE_ACTION_META[rid]
        rule_actions.append({
            "rule_id": rid, "version": r["version"], "actor": actor,
            "action": "enact",
            "effective_from": r["effective_from"],
            "effective_to": r["effective_to"],
            "issued_by": issued_by, "doc_number": doc,
            "stated_goal": goal, "trigger_event": trig,
            "public": True, "payoff_delta": PAYOFFS[rid],
        })
        political_record.append({
            "doc_number": doc, "issuing_body": issued_by,
            "effective_date": r["effective_from"],
            "title": r["name"],
            "source": ("fixture-synthetic" if doc.startswith("FIXTURE")
                       else "Federal Register"),
        })
        obs_date, again_date = LINK_DATES[rid]
        s, pid, ridx, _, _ = ANCHORS[rid]
        trigger_links.append({
            "id": f"LK-{rid}",
            "observe": {"type": "event", "event_id": trig,
                        "date": obs_date},
            "rule_action": rid,
            "react": {"type": "move", "season": s, "player": pid,
                      "round_index": ridx},
            "observe_again": {"type": "event",
                              "event_id": f"evt-{rid.lower()}-again",
                              "date": again_date},
        })

    lobby_actions = [
        {"id": "LB-1", "actor": 0, "target_rule": "RV-2026-11",
         "position": "oppose", "date": 20261110,
         "source": "fixture-synthetic",
         "payoff_delta": [0, 0, -1, 0, 0, 0, 0, 0, 0]},
        {"id": "LB-2", "actor": 4, "target_rule": "RV-2026-11",
         "position": "support", "date": 20261112,
         "source": "fixture-synthetic",
         "payoff_delta": [0, 0, 1, 0, 0, 0, 0, 0, 0]},
    ]

    agent_claims = [
        {"id": "CL-1", "invariant_id": 10, "kind": "checkable",
         "claim": "BIS 远程接入规则 744.24 于 2026-11-19 生效，文号 2026-23529",
         "evidence_ref": "2026-23529", "confidence": 95,
         "checkable_by": "lean", "agent": "monitor",
         "date": 20261119, "subject": "2026-23529", "check_nat": 20261119},
        {"id": "CL-2", "invariant_id": 5, "kind": "checkable",
         "claim": "R1 首次出现于 2025-01-20",
         "evidence_ref": "https://github.com/deepseek-ai/DeepSeek-R1",
         "confidence": 95, "checkable_by": "lean", "agent": "monitor",
         "date": 20250120, "subject": "R1", "check_nat": 20250120},
        {"id": "CL-3", "invariant_id": 2, "kind": "checkable",
         "claim": "S5 英伟达血量账对得上（季初 + 全季增减 - 杠杆惩罚 = 季末）",
         "evidence_ref": "trace:check-report", "confidence": 90,
         "checkable_by": "fast-checker", "agent": "monitor",
         "date": 20261121, "subject": "S5 NVDA ledger", "check_nat": 0},
        {"id": "CL-4", "invariant_id": 12, "kind": "judgment",
         "claim": "远程接入规则文本与宣称目标一致：禁令直接服务国家安全",
         "evidence_ref": "https://www.federalregister.gov/documents/"
                         "2026/11/19/2026-23529",
         "confidence": 80, "checkable_by": "agent", "agent": "monitor",
         "date": 20261120, "subject": "RV-2026-11", "check_nat": 0},
    ]
    events = [
        {"event_id": "evt-bis-2026-11-obs", "date": 20261116,
         "summary": "BIS 发布远程接入规则 744.24，11-19 生效",
         "signal": 1, "classification": 1, "claim_ids": ["CL-1"],
         "source": "https://www.federalregister.gov/documents/"
                   "2026/11/19/2026-23529"},
        {"event_id": "evt-r1-release", "date": 20250120,
         "summary": "DeepSeek 发布 R1 模型",
         "signal": 2, "classification": 2, "claim_ids": ["CL-2"],
         "source": "https://github.com/deepseek-ai/DeepSeek-R1"},
        {"event_id": "evt-nvda-earnings", "date": 20261117,
         "summary": "英伟达发布 Q3 财报",
         "signal": 2, "classification": 2, "claim_ids": ["CL-3"],
         "source": "fixture-synthetic"},
        {"event_id": "evt-goal-review", "date": 20261120,
         "summary": "规则文本与宣称目标一致性复核",
         "signal": 3, "classification": 3, "claim_ids": ["CL-4"],
         "source": "https://www.federalregister.gov/documents/"
                   "2026/11/19/2026-23529"},
    ]

    trace = {
        "schema_version": 4,
        "meta": {
            "page_slug": "jin-chan-chan-fu-pan-ai-da-ting-2022-2026",
            "page_version": "fixture",
            "extracted_at": "2026-11-21T00:00:00Z",
            "source": "fixture (synthetic, consistent by construction)",
            "source_sha256": "fixture",
            "trace_sha256": "fixture",
        },
        "spec": {"players_total": 18, "rounds_total": 31,
                 "seasons_total": 5,
                 "timeline_start": 20221130, "timeline_end": 20261121,
                 "coverage_required": True},
        "players": [{"id": pid, "name": name, "key": key,
                     "first_season": 1, "last_season": 5}
                    for pid, name, key in PLAYERS],
        "seasons": seasons,
        "moves": moves,
        "season_state": states,
        "rankings": rankings,
        "hp_series": [{"player": pid, "points": series[pid]}
                      for pid, _, _ in PLAYERS],
        "card_pool": [{"cost": c, "total": t} for c, t in
                      [(1, 29), (2, 22), (3, 18), (4, 12), (5, 10)]],
        "holdings": [{"player": h, "card": c, "cost": co, "stars": 1}
                     for c, co, h, _, _, _ in KEY_CARDS],
        "key_cards": [{"card": c, "cost": co, "holders": [h],
                       "shared": False, "min_date": md, "first_date": md}
                      for c, co, h, md, _, _ in KEY_CARDS],
        "facts": {
            "ipo": {"base_usd_m": 81340, "greenshoe_total_usd_m": 93500,
                    "private_usd_m": 26000, "base_plus_private_usd_m": 107340,
                    "combined_usd_m": 119500, "net_usd_m": 117000},
            "nvda": {"close_high_cents": 23924, "close_drop_tenths_pct": 475,
                     "intraday_high_cents": 24337,
                     "intraday_drop_tenths_pct": 484, "low_cents": 12553},
            "dates": KINDS,
        },
        "formulas": {"hp_cap": 100, "hp_floor": 0,
                     "leverage_penalty": "floor(borrowed * 0.5)",
                     "penalty_applies_to": "hp"},
        "rules": rules,
        "meta_players": META_PLAYERS,
        "rule_actions": rule_actions,
        "political_record": political_record,
        "trigger_links": trigger_links,
        "lobby_actions": lobby_actions,
        "goal_checks": [
            {"goal": "national_security", "requirement": "restrictive"},
            {"goal": "industrial_advantage", "requirement": "restrictive"},
        ],
        "agent_claims": agent_claims,
        "events": events,
        "knowledge": {"initial_facts": [1],
                      "public_facts": [1, 2, 3, 4, 5, 6]},
        "legacy_ids": ["MSOFT", "XAI", "中国队"],
    }
    return trace


def inject_broken(trace):
    t = copy.deepcopy(trace)
    t["meta"]["source"] = "fixture (broken variant)"
    # S5 NVDA (player 0): hp -7, gold -32 vs the chain
    for st in t["season_state"]:
        if st["season"] == 5 and st["player"] == 0:
            st["hp_end"] -= 7
            st["gold_end"] -= 32
        if st["season"] == 5 and st["player"] == 4:
            st["hp_end"] -= 17
    for rk in t["rankings"]:
        if rk["season"] == 5 and rk["player"] == 0:
            rk["hp_end"] -= 7
            rk["gold_end"] -= 32
        if rk["season"] == 5 and rk["player"] == 4:
            rk["hp_end"] -= 17
    for h in t["hp_series"]:
        if h["player"] == 0:
            h["points"][4] -= 7
        if h["player"] == 4:
            h["points"][4] -= 17
    # elimination violation: SoftBank (17) at 0 HP end of S4, still acts in S5
    for st in t["season_state"]:
        if st["season"] == 4 and st["player"] == 17:
            st["hp_end"] = 0
    for rk in t["rankings"]:
        if rk["season"] == 4 and rk["player"] == 17:
            rk["hp_end"] = 0
    for h in t["hp_series"]:
        if h["player"] == 17:
            h["points"][3] = 0
    # pool over-hold: two extra 5-cost holdings (pool total is 10, held 12)
    t["holdings"].append({"player": 3, "card": "H100", "cost": 5,
                          "stars": 1})
    t["holdings"].append({"player": 5, "card": "R1", "cost": 5, "stars": 1})
    # predated move: an R1 move dated before 2025-01-20
    for m in t["moves"]:
        if m["action_kind"] == "r1":
            m["date"] = 20250101
            m["rules_version"] = resolve_rule(t["rules"], 20250101)
            break
    # overseas_rental after RV-2026-11 took effect (banned kind, C5)
    for m in t["moves"]:
        if m["season"] == 5 and m["player"] == 1:
            m["action_kind"] = "overseas_rental"
            m["action"] = "overseas_rental 动作"
            m["date"] = 20261120
            m["rules_version"] = "RV-2026-11"
            break
    # C10: rule action doc number matches no political record
    for ra in t["rule_actions"]:
        if ra["rule_id"] == "RV-2026-11":
            ra["doc_number"] = "2026-99999"
    # C11: trigger link observe-again dated before the react move
    for lk in t["trigger_links"]:
        if lk["rule_action"] == "RV-2023-10":
            lk["observe_again"]["date"] = 20231001
    # agent protocol: unclassified event + claim without evidence +
    # classification disagreeing with its signal
    for ev in t["events"]:
        if ev["event_id"] == "evt-r1-release":
            ev["classification"] = 5
    for cl in t["agent_claims"]:
        if cl["id"] == "CL-4":
            cl["evidence_ref"] = ""
    for ev in t["events"]:
        if ev["event_id"] == "evt-nvda-earnings":
            ev["classification"] = 1
    # trajectory: payoff delta pushes BIS out of [-10, 10]
    for ra in t["rule_actions"]:
        if ra["rule_id"] == "RV-2026-11":
            ra["payoff_delta"] = [0, 0, 100, 0, 0, 0, 0, 0, 0]
    return t


def main():
    # retry seeds until the ok fixture has no elimination (real page: none)
    seed = 42
    while True:
        ok = build(seed)
        if all(st["hp_end"] != 0 for st in ok["season_state"]):
            break
        seed += 1
    broken = inject_broken(ok)
    (OUT / "trace-fixture-ok.json").write_text(
        json.dumps(ok, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "trace-fixture-broken.json").write_text(
        json.dumps(broken, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"fixture ok: moves={len(ok['moves'])} "
          f"states={len(ok['season_state'])} rankings={len(ok['rankings'])} "
          f"rules={len(ok['rules'])} rule_actions={len(ok['rule_actions'])} "
          f"claims={len(ok['agent_claims'])} events={len(ok['events'])}")
    print("fixture broken: injected S5 NVDA hp-7/gold-32, S5 ANTH hp-17, "
          "S4 SoftBank death + S5 moves, pool over-hold, predated R1 move, "
          "overseas_rental after 2026-11-19, C10 doc mismatch, C11 inverted "
          "dates, unclassified event, claim without evidence, "
          "classification/signal mismatch, payoff out of range")


if __name__ == "__main__":
    main()
