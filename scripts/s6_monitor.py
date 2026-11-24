#!/usr/bin/env python3
"""S6 daily monitor helper: pool I/O, dedup, watermark.

Pool file: s6-pending-pool.json (next to the repository root)
Schema:
  meta: {s6_start_date, last_run_date, testset_n, gap_to_140,
         gap_to_140_status, created, updated}
  candidates: verified S6 candidates (event_real_date >= S6_START_DATE,
    i.e. real date later than 2026-11-21; S6 starts 2026-11-22)
  missed_s5: S5-era events (< S6_START_DATE) not in trace/testset
  kind_gap: real public events with no matching kind among the KINDS
    read from testset-v7
  rejected: examined but rejected, with reason

Unified vocabulary sources (read, never hard-coded):
  - players: data.json "players" (32 historical players)
  - kinds: testset-v7 questions' "kind" field (43 kinds)
  - trace: traces/trace-latest.json (751 moves)

Dedup sources (read-only):
  - trace: traces/trace-latest.json
  - testset: ../verification-v1-testset-complete/testset-v7.json (215)

Usage:
  python3 scripts/s6_monitor.py trial   # run the trial classification, write pool
  python3 scripts/s6_monitor.py check   # validate pool file (schema + dedup)
  python3 scripts/s6_monitor.py status  # print pool counts
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POOL_PATH = os.path.join(ROOT, "s6-pending-pool.json")
DATA_PATH = os.path.join(ROOT, "data.json")
TRACE_PATH = os.path.join(ROOT, "traces", "trace-latest.json")
TESTSET_PATH = os.path.normpath(
    os.path.join(ROOT, "..", "verification-v1-testset-complete",
                 "testset-v7.json"))

# Single S6 boundary constant. S6 starts 2026-11-22. A candidate must
# have a real date later than 2026-11-21, i.e. event_real_date >=
# S6_START_DATE. Pool meta s6_start_date uses this same constant.
S6_START_DATE = 20261122

# Legacy 140-question target. The target expired: testset-v7 already
# holds 215 questions. Do not set a new target here. gap_to_140 is
# computed honestly as LEGACY_TARGET_140 - testset_n and marked
# legacy_target_pending_rescope until Gu re-scopes it.
LEGACY_TARGET_140 = 140
GAP_TO_140_STATUS = "legacy_target_pending_rescope"


def _load_players():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [p["id"] for p in data["players"]]


def _load_testset_questions():
    with open(TESTSET_PATH, encoding="utf-8") as f:
        return json.load(f)["questions"]


# Unified vocabulary, read from the sources above at import time.
PLAYERS = _load_players()
_TESTSET_QUESTIONS = _load_testset_questions()
KINDS = {q["kind"] for q in _TESTSET_QUESTIONS}
TESTSET_N = len(_TESTSET_QUESTIONS)


def new_pool():
    return {
        "meta": {
            "s6_start_date": S6_START_DATE,
            "last_run_date": None,
            "testset_n": TESTSET_N,
            "gap_to_140": LEGACY_TARGET_140 - TESTSET_N,
            "gap_to_140_status": GAP_TO_140_STATUS,
            "note": ("2026-11-24: gap_to_140 为旧目标口径（140 道），待 Gu 重定"
                     "新目标；数值按 140 - testset_n 如实计算。"),
            "created": "2026-11-22",
            "updated": "2026-11-22",
        },
        "candidates": [],
        "missed_s5": [],
        "kind_gap": [],
        "new_player": [],
        "rejected": [],
    }


def load_pool(path=POOL_PATH):
    if not os.path.exists(path):
        return new_pool()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_pool(pool, path=POOL_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=1)
        f.write("\n")


def load_trace():
    with open(TRACE_PATH, encoding="utf-8") as f:
        t = json.load(f)
    return t.get("moves", t.get("trace", []))


def load_testset():
    return _TESTSET_QUESTIONS


def player_of_trace_move(m):
    p = m.get("player")
    if isinstance(p, int):
        if p < 0 or p >= len(PLAYERS):
            raise ValueError(
                "trace player index %d out of range for %d players "
                "from data.json" % (p, len(PLAYERS)))
        return PLAYERS[p]
    return p


def active_players(trace_moves):
    """Players with at least one move in the latest season in the trace.

    Computed from the trace, never hard-coded. Returns (season, players)
    with players in roster order. Historical players are PLAYERS;
    active players are this subset for the current season.
    """
    seasons = [m.get("season") for m in trace_moves
               if isinstance(m.get("season"), int)]
    if not seasons:
        return (None, [])
    latest = max(seasons)
    active_idx = {m["player"] for m in trace_moves
                  if m.get("season") == latest
                  and isinstance(m.get("player"), int)}
    return (latest, [PLAYERS[i] for i in sorted(active_idx)
                     if 0 <= i < len(PLAYERS)])


def is_duplicate(candidate, trace_moves, questions, pool):
    """True if the candidate is already a trace move, a testset question,
    or a pool entry. Match on (player, kind, event_real_date) and on
    event_name containment."""
    pl, kind, d = (candidate.get("player"), candidate.get("kind"),
                   candidate.get("event_real_date"))
    name = (candidate.get("event_name") or "").lower()
    for q in questions:
        if q.get("player") == pl and q.get("kind") == kind and \
                q.get("event_real_date") == d:
            return ("testset", q.get("q_id"))
        if name and name in (q.get("event_name") or "").lower():
            return ("testset-name", q.get("q_id"))
    for m in trace_moves:
        if player_of_trace_move(m) == pl and \
                (m.get("semantic_kind") == kind or
                 m.get("action_kind") == kind) and \
                d is not None and m.get("date") == d:
            # same player + same kind + same date in the trace: check the
            # action text. Require at least two distinct name words in the
            # action text, counting overlapping words once ("chat" inside
            # "chatgpt" is one hit, not two). One generic word alone is not
            # a duplicate: on 2026-11-24 the old any-word rule flagged
            # Claude Ship on the single word "Claude" matching the old S1
            # action "Claude 1 低调发布"; manual review confirmed it is
            # not one. The date must also match: GPT-6.2 Sol Chat tab
            # (20261123) is a different rollout from the S5 trace move
            # "GPT-6.2 Astra 与 Sol 发布" (20261101), manually verified
            # distinct. Near-duplicates stay a manual-review call.
            act = (m.get("action") or "").lower()
            words = [w for w in name.split() if len(w) > 3]
            hits = [w for w in words if w in act]
            hits = [w for w in hits
                    if not any(w != u and w in u for u in hits)]
            if name and len(hits) >= 2:
                return ("trace", (m.get("season"), m.get("round_label")))
    for e in pool.get("candidates", []) + pool.get("missed_s5", []):
        if e.get("player") == pl and e.get("kind") == kind and \
                e.get("event_real_date") == d:
            return ("pool", e.get("event_name"))
    return None


def classify(event, trace_moves, questions, pool):
    """Mechanical pre-check. Returns (bucket, reason).
    The agent still judges public-action / kind-fit; this only enforces
    the hard rules: date boundary, player roster, kind list, dedup.
    The agent only feeds real public events to classify(); non-events
    (policy statements, future events, claims) are rejected by the agent."""
    d = event.get("event_real_date")
    pl = event.get("player")
    kind = event.get("kind")
    if d is None:
        return ("rejected", "日期不清")
    dup = is_duplicate(event, trace_moves, questions, pool)
    if dup:
        return ("rejected", "已在%s里，不重复收" % dup[0])
    if kind is None or kind not in KINDS:
        return ("kind_gap", "%d 个种类里无对应种类" % len(KINDS))
    if pl is None:
        return ("rejected", "归属不清，无玩家")
    if pl not in PLAYERS:
        return ("new_player",
                "玩家不在 %d 人名单里，需 Gu 定是否加进大厅" % len(PLAYERS))
    if d < S6_START_DATE:
        return ("missed_s5", "真实日期在 S5 时期内（<2026-11-22），不在 trace 里")
    return ("candidates", "已核验：公开动作、种类能定、真实日期晚于 2026-11-21、来源齐全")


# Trial window: 2026-11-16 to 2026-11-22 (recent events from the daily logs).
TRIAL_EVENTS = [
    {"event_name": "百度 Q3 财报：资本开支 73.5 亿元", "player": "BIDU",
     "kind": "capex", "event_real_date": 20261116,
     "source": "百度 Q3 财报（Capital Times、Motley Fool 实录）",
     "action": "百度 Q3 资本开支 73.5 亿元，同比翻倍以上",
     "found_date": "2026-11-22"},
    {"event_name": "纽约时报调查：阿里是 Megaspeed 的客户与资金支持方",
     "player": "ALI", "kind": "megaspeed", "event_real_date": 20261118,
     "source": "纽约时报 11-18/19 调查（NeoTeo、explainx 转述）",
     "action": "纽约时报调查披露阿里是 Megaspeed 的客户与资金支持方",
     "found_date": "2026-11-22"},
    {"event_name": "腾讯 Q3 财报：资本开支 814.33 亿元（+527%）",
     "player": "TCE", "kind": "capex", "event_real_date": 20261118,
     "source": "腾讯官方财报",
     "action": "腾讯 Q3 资本开支 814.33 亿元，增 527%",
     "found_date": "2026-11-22"},
    {"event_name": "Anthropic IPO 交割：超额配售权全额行使，募资约 935 亿美元",
     "player": "ANTH", "kind": "anthropic_ipo", "event_real_date": 20261120,
     "source": "Anthropic 官方公告 11-20",
     "action": "IPO 交割，承销商全额行使超额配售权，合计发行 11.27 亿股",
     "found_date": "2026-11-22"},
    {"event_name": "Ricketts 参议员提出《MEGA 法案》", "player": None,
     "kind": None, "event_real_date": 20261117,
     "source": "参议员办公室新闻稿 11-17",
     "action": "《MEGA 法案》提出，要求商务部 30 天内决定是否将 Megaspeed 列入实体清单",
     "found_date": "2026-11-22"},
    {"event_name": "加州总检察长 Bonta 向英伟达发出调查传票",
     "player": "NVDA", "kind": None, "event_real_date": 20261119,
     "source": "加州司法部官网新闻稿 11-19",
     "action": "Bonta 向英伟达发调查传票，查芯片或机密是否流向中国",
     "found_date": "2026-11-22"},
    {"event_name": "加州候任州长 Becerra 支持对失控智能体刑事指控",
     "player": None, "kind": None, "event_real_date": 20261119,
     "source": "POLITICO 首报 11-19",
     "action": "Becerra 表态：智能体发起网络攻击时刑事指控应成为选项",
     "found_date": "2026-11-22"},
    {"event_name": "黄仁勋同意在参议院银行委员会公开作证", "player": "NVDA",
     "kind": None, "event_real_date": 20261119,
     "source": "参议院银行委员会主席 Scott 11-19 确认",
     "action": "黄仁勋同意圣诞节前公开作证，日期未定",
     "found_date": "2026-11-22"},
    {"event_name": "众议院三委员会 12-01 闭门访谈黄仁勋", "player": "NVDA",
     "kind": None, "event_real_date": 20261201,
     "source": "众议院 11-18 确认",
     "action": "众议院 12-01 闭门访谈黄仁勋（未来事件）",
     "found_date": "2026-11-22"},
    {"event_name": "马斯克 TomorrowX：SpaceX 每月带上线约 0.5GW AI 算力",
     "player": "MUSK", "kind": "datacenter", "event_real_date": 20261118,
     "source": "TomorrowX 11-18（马斯克本人表述，未独立核验）",
     "action": "马斯克称 SpaceX 每月带上线约 0.5GW AI 算力",
     "found_date": "2026-11-22"},
]


def run_trial():
    pool = load_pool()
    trace_moves = load_trace()
    questions = load_testset()
    results = []
    for ev in TRIAL_EVENTS:
        # Manual judgment (agent-side) for the two judgment calls:
        # - TomorrowX is a claim/target, not a completed public action.
        # - Huang testimony / House interview are future events, not happened.
        if "TomorrowX" in ev["event_name"]:
            bucket, reason = ("rejected", "只是主张/目标，不是已发生的公开动作；且日期在 S5 时期内")
        elif ev["event_name"] in ("黄仁勋同意在参议院银行委员会公开作证",
                                 "众议院三委员会 12-01 闭门访谈黄仁勋"):
            bucket, reason = ("rejected", "未来事件，还没发生")
        elif ev["event_name"].startswith("加州候任州长"):
            bucket, reason = ("rejected", "政策表态，未点名公司，无玩家动作")
        else:
            bucket, reason = classify(ev, trace_moves, questions, pool)
        entry = dict(ev)
        entry["status"] = "verified" if bucket == "candidates" else None
        entry["reason"] = reason
        pool[bucket].append(entry)
        results.append((ev["event_name"][:30], bucket, reason))
    pool["meta"]["last_run_date"] = "2026-11-22"
    pool["meta"]["updated"] = "2026-11-22"
    save_pool(pool)
    for name, bucket, reason in results:
        print(f"{bucket:12s} {name} | {reason}")
    print("counts:", {k: len(pool[k]) for k in
                      ("candidates", "missed_s5", "kind_gap", "new_player",
                       "rejected")})
    return pool


def check():
    pool = load_pool()
    trace_moves = load_trace()
    questions = load_testset()
    assert set(pool) >= {"meta", "candidates", "missed_s5", "kind_gap",
                         "new_player", "rejected"}, "pool schema incomplete"
    # no candidate may have a date before S6 starts or duplicate the testset
    for e in pool["candidates"]:
        assert e["event_real_date"] >= S6_START_DATE, e
        assert not is_duplicate(e, trace_moves, questions,
                                {"candidates": [], "missed_s5": []}), e
    # no candidate may duplicate another pool entry
    seen = set()
    for e in pool["candidates"] + pool["missed_s5"]:
        key = (e.get("player"), e.get("kind"), e.get("event_real_date"))
        assert key not in seen, key
        seen.add(key)
    season, active = active_players(trace_moves)
    print("check ok:", {k: len(pool[k]) for k in
                        ("candidates", "missed_s5", "kind_gap", "new_player",
                         "rejected")})
    print("players: historical=%d active(S%d)=%s"
          % (len(PLAYERS), season, active))


def status():
    pool = load_pool()
    trace_moves = load_trace()
    season, active = active_players(trace_moves)
    print(json.dumps(pool["meta"], ensure_ascii=False))
    print({k: len(pool[k]) for k in
           ("candidates", "missed_s5", "kind_gap", "new_player", "rejected")})
    print("players: historical=%d active(S%d)=%s"
          % (len(PLAYERS), season, active))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"trial": run_trial, "check": check, "status": status}[cmd]()
