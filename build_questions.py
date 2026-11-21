#!/usr/bin/env python3
"""Build the enlarged question set (test105) and per-round question files
for the 22 new questions (round 5 sample expansion).

Inputs: the NEW canonical trace (traces/trace-latest.json in this worktree,
built by the third-expansion converter) and the OLD test83 for regression.
Outputs (runs/sample-expansion-round5-2026-11-22/):
  test105.json            all S4-S5 classified moves (105), test83 format
  questions-S4-1-2.json   the 10 new questions in S4 1-2 (no answers)
  questions-S4-3-2.json   the 7 new questions in S4 3-2 (no answers)
  questions-S5-3-2.json   the 5 new questions in S5 3-2 (no answers)
  headline-events.json    headline event per affected round (from the
                          round-4 project-means reconstruction, same
                          convention as search-first)
Vocabulary for predictors: the 32 kinds that appear in the new trace
(generic and openai_mar26 never appear in the real trace).
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "sample-expansion-round5-2026-11-22"
RUNS.mkdir(parents=True, exist_ok=True)

PLAYERS = ["NVDA", "OAI", "MSFT", "GOOG", "ANTH", "META", "AMZN", "MUSK",
           "AAPL", "ORCL", "BYTE", "ALI", "TCE", "BIDU", "HUAWEI", "DPSK",
           "TSMC", "SFTB"]

VOCABULARY = ["anthropic_ipo", "ascend", "bis_rule", "blackwell", "capex",
              "chatgpt", "claude", "colossus", "compliance", "datacenter",
              "doubao", "doubao_price_war", "energy", "financing", "gemini",
              "huang_resign", "hunyuan", "invest_plan", "llama", "megaspeed",
              "msft_invest", "musk_table", "open_source", "overseas_rental",
              "pangu", "r1", "sec_probe", "spacex_xai", "stargate",
              "tongyi", "v3", "wenxin"]

# Headline event per affected round. Same convention as search-first:
# the round's headline is given as known input, except when the player
# IS the event's protagonist (not the case for any of the 22 new
# questions). Text taken from the round-4 project-means reconstruction
# (headline-events.json), which reproduced the search-first convention.
HEADLINES = {
    "S4 1-2": {
        "headline": "星门计划在白宫宣布（2025-01-21）：四年 5000 亿美元，首批 1000 亿美元；OpenAI、软银、甲骨文、MGX 组队；马斯克当天在 X 称“他们根本没有这笔钱”。",
        "event_given": True,
    },
    "S4 3-2": {
        "headline": "美国数据中心并网排队激增、“电不够了”（2025-06 前后）：ERCOT 大负荷排队从 2024 年底约 63 GW 升至约 226 GW；新电源从申请到投运的中位时间约 5 年。",
        "event_given": True,
    },
    "S5 3-2": {
        "headline": "Axios 报道：2026-11-05 白宫战情室会议上，财长贝森特当面质问商务部长 Lutnick 为何未将 Megaspeed 列入实体清单；商务部发言人否认有过该对话。",
        "event_given": True,
    },
}


def main():
    trace = json.loads((HERE / "traces" / "trace-latest.json").read_text())
    moves = trace["moves"]
    # --- first appearance: kind never seen in any EARLIER ROUND -------
    # (rounds are the unit: moves within the same round do not count
    # against each other. Verified against test83: 0/83 mismatches.
    # Per-move or per-player definitions mismatch 15 and 12.)
    seen_rounds = set()
    first_app = {}
    cur = None
    buf = set()
    for i, m in enumerate(moves):
        rk = (m["season"], m["round_index"])
        if rk != cur:
            seen_rounds |= buf
            buf = set()
            cur = rk
        k = m["semantic_kind"]
        first_app[i] = (k != "unknown" and k not in seen_rounds)
        if k != "unknown":
            buf.add(k)
    # --- test105: all S4-S5 classified moves, test83 format -------------
    test105 = []
    for i, m in enumerate(moves):
        if m["season"] not in (4, 5) or m["semantic_kind"] == "unknown":
            continue
        test105.append({
            "idx": i,
            "season": m["season"],
            "round_index": m["round_index"],
            "round_label": m["round_label"],
            "date": m["date"],
            "player_idx": m["player"],
            "player": PLAYERS[m["player"]],
            "kind": m["semantic_kind"],
            "action": m["action"],
            "action_kind": m["action_kind"],
            "hp_start": m["hp_start"],
            "hp_delta": m["hp_delta"],
            "gold_start": m["gold_start"],
            "gold_delta": m["gold_delta"],
            "rules_version": m["rules_version"],
            "first_appearance": first_app[i],
        })
    (RUNS / "test105.json").write_text(
        json.dumps(test105, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- regression: the old 83 must reproduce exactly ------------------
    old83 = json.loads(Path(
        "/home/hatch/workspace/verification-r2-search/runs/"
        "search-first-full83-2026-11-22/test83.json").read_text())
    by_key = {(q["season"], q["round_label"], q["player"]): q
              for q in test105}
    bad = []
    for q in old83:
        nq = by_key.get((q["season"], q["round_label"], q["player"]))
        if nq is None:
            bad.append((q, "missing from test105"))
            continue
        for f in ("kind", "action", "date", "first_appearance",
                  "action_kind", "hp_start", "hp_delta",
                  "gold_start", "gold_delta", "rules_version"):
            if nq[f] != q[f]:
                bad.append((q["season"], q["round_label"], q["player"],
                            f, q[f], nq[f]))
    assert not bad, f"old-83 regression failed: {bad[:5]}"
    print(f"regression: old 83 reproduce exactly (kind/action/date/"
          f"first_appearance all match)")

    # --- per-round question files: NEW questions only, no answers ------
    old_keys = {(q["season"], q["round_label"], q["player"])
                for q in old83}
    new_qs = [q for q in test105
              if (q["season"], q["round_label"], q["player"]) not in old_keys]
    print(f"new questions: {len(new_qs)} "
          f"(S4: {sum(1 for q in new_qs if q['season'] == 4)}, "
          f"S5: {sum(1 for q in new_qs if q['season'] == 5)})")
    print("new kinds:", Counter(q["kind"] for q in new_qs))

    # context per question, same fields as the round-*-context.json files
    def context_for(q):
        i = q["idx"]
        prefix = moves[:i]
        phist = [m for m in prefix if m["player"] == q["player_idx"]]
        counts = Counter(m["semantic_kind"] for m in phist
                         if m["semantic_kind"] != "unknown")
        last = [m for m in phist if m["semantic_kind"] != "unknown"]
        # Global round order (across seasons). Both prev_round_kinds and
        # player_last3 use it: S4 1-1's previous round is S3 6-1.
        # Verified against the original round-*-context.json files.
        round_order = []
        for m in moves:
            rk = (m["season"], m["round_index"])
            if rk not in round_order:
                round_order.append(rk)
        my_rk = (q["season"], q["round_index"])
        my_pos = round_order.index(my_rk)
        # prev round: all moves of the previous round in global order.
        prev_rk = round_order[my_pos - 1] if my_pos > 0 else None
        prev = [m for m in prefix
                if prev_rk is not None
                and (m["season"], m["round_index"]) == prev_rk]
        prev_kinds = {PLAYERS[m["player"]]: m["semantic_kind"]
                      for m in prev if m["semantic_kind"] != "unknown"}
        # player_last3: the player's classified kinds in the previous 3
        # ROUNDS (global round order -- e.g. S3 6-1 counts for an
        # S4 1-2 question).
        prev3 = round_order[max(0, my_pos - 3):my_pos]
        last3 = []
        for rk in prev3:
            for m in moves:
                if ((m["season"], m["round_index"]) == rk
                        and m["player"] == q["player_idx"]
                        and m["semantic_kind"] != "unknown"):
                    last3.append([m["semantic_kind"], m["date"]])
        return {
            "season": q["season"],
            "round_label": q["round_label"],
            "round": f"S{q['season']} {q['round_label']}",
            "date": q["date"],
            "player": q["player"],
            "hp_start": q["hp_start"],
            "gold_start": q["gold_start"],
            "rules_version": q["rules_version"],
            "first_appearance": q["first_appearance"],
            "player_history_counts": dict(counts),
            "player_most_frequent": counts.most_common(1)[0][0]
            if counts else None,
            "player_last_kind": last[-1]["semantic_kind"] if last else None,
            "player_last3": last3,
            "prev_round_kinds": prev_kinds,
        }

    rounds = {}
    for q in new_qs:
        rounds.setdefault(f"S{q['season']} {q['round_label']}", []).append(q)
    for rkey, qs in sorted(rounds.items()):
        payload = {
            "round": rkey,
            "date": qs[0]["date"],
            "headline": HEADLINES[rkey]["headline"],
            "event_given": HEADLINES[rkey]["event_given"],
            "vocabulary": VOCABULARY,
            "questions": [context_for(q) for q in qs],
        }
        fname = f"questions-{rkey.replace(' ', '-')}.json"
        (RUNS / fname).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"{fname}: {len(qs)} questions, "
              f"kinds {[q['kind'] for q in qs]}")
    # headline events file (record, for the report)
    (RUNS / "headline-events.json").write_text(
        json.dumps({"rounds": {k: {"headline": v["headline"],
                                   "event_given": v["event_given"]}
                             for k, v in HEADLINES.items()}},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"test105: {len(test105)} questions "
          f"(S4: {sum(1 for q in test105 if q['season'] == 4)}, "
          f"S5: {sum(1 for q in test105 if q['season'] == 5)})")
    print(f"first-appearance in test105: "
          f"{sum(1 for q in test105 if q['first_appearance'])}")


if __name__ == "__main__":
    main()
