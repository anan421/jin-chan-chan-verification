#!/usr/bin/env python3
"""Build diagnosis input for vision-1 round 5 (weakest-link diagnosis).

Reads:
  - testset-v3.json (88 questions)
  - /home/hatch/workspace/verification/traces/trace-latest.json (558 moves)
  - /home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22/context-all88.json
  - /home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22/predictions-{main,control1,control2,control3}-S*-*.json
  - /home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22/leaks88.json
Writes (runs/weakest-link-vision5-2026-11-22/, gitignored):
  - diagnosis-input.json: one record per weakest-kind question (21 distinct):
      {q_id, kind, season, round_label, round_date, event_real_date, event_name,
       player, action, source, origin, split,
       context: {player_history_counts, player_most_frequent, player_last_kind,
                 player_last3, prev_round_kinds},
       player_prior_actions: [{round, date, action, semantic_kind}],
       prior_round_actions: [{round, player, action, semantic_kind}],
       predictions: {batch: {predicted_kind, confidence, reasoning, facts_used}},
       leaked: {batch: bool}}

Weakest kinds (0 or near-0 in baseline main run, clean 0):
  capex(8), datacenter(2), energy(2), bis_rule(3), v3(2), megaspeed(1),
  sec_probe(1), blackwell(1), overseas_rental(1) = 21 distinct questions.

Prefix rule (strict walk-forward, same as build_prefixes.py):
  prefix = all trace moves with (season, round_index) strictly before the
  question's (season, round_index). Player's own prior actions = prefix
  moves by this player. Prior round = the round immediately before.
"""
import json
import glob
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "weakest-link-vision5-2026-11-22"
BASELINE_RUNS = Path("/home/hatch/workspace/verification-v1-baseline88/runs/baseline88-2026-11-22")
TRACE = Path("/home/hatch/workspace/verification/traces/trace-latest.json")

WEAKEST = ["capex", "datacenter", "energy", "bis_rule", "v3", "megaspeed",
           "sec_probe", "blackwell", "overseas_rental"]


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    testset = json.loads((HERE / "testset-v3.json").read_text(encoding="utf-8"))
    trace = json.loads(TRACE.read_text(encoding="utf-8"))
    moves = trace["moves"]
    players = trace["players"]
    # player code -> index. players is a list; find the code field.
    code_to_idx = {}
    for i, p in enumerate(players):
        if isinstance(p, dict):
            code = p.get("key") or p.get("code") or p.get("player")
            idx = p.get("id")
            if code:
                code_to_idx[str(code)] = int(idx) if idx is not None else i
        elif isinstance(p, str):
            code_to_idx[p] = i
    # Fallback: meta_players
    if not code_to_idx and "meta_players" in trace:
        mp = trace["meta_players"]
        if isinstance(mp, dict):
            for code, idx in mp.items():
                code_to_idx[str(code)] = int(idx)
        elif isinstance(mp, list):
            for i, code in enumerate(mp):
                code_to_idx[str(code)] = i
    context = {c["q_id"]: c for c in json.loads((BASELINE_RUNS / "context-all88.json").read_text(encoding="utf-8"))}
    leaks = json.loads((BASELINE_RUNS / "leaks88.json").read_text(encoding="utf-8"))
    # Aggregate predictions by q_id and batch.
    preds = {}
    for b in ["main", "control1", "control2", "control3"]:
        for path in sorted(BASELINE_RUNS.glob(f"predictions-{b}-S*-*.json")):
            for p in json.loads(path.read_text(encoding="utf-8")):
                preds.setdefault(p["q_id"], {})[b] = p
    # Round order: list of (season, round_index, round_label) in trace order.
    round_order = []
    seen = set()
    # (season, round_label) -> round_index (questions carry season+round_label,
    # only walkforward ones carry trace_idx).
    label_to_index = {}
    for m in moves:
        key = (m["season"], m["round_index"])
        if key not in seen:
            seen.add(key)
            round_order.append((m["season"], m["round_index"], m["round_label"]))
        label_to_index[(m["season"], m["round_label"])] = m["round_index"]
    round_pos = {k[:2]: i for i, k in enumerate(round_order)}
    # First move index of each round.
    round_start = {}
    for i, m in enumerate(moves):
        key = (m["season"], m["round_index"])
        if key not in round_start:
            round_start[key] = i
    # Player code for each move index: moves store player as index already.
    # Build a code->name map for display: use players list.
    def player_code(idx):
        p = players[idx] if 0 <= idx < len(players) else idx
        if isinstance(p, dict):
            return p.get("key") or p.get("code") or p.get("player") or p.get("name") or str(idx)
        return str(p)

    out = []
    for q in testset["questions"]:
        if q.get("kind") not in WEAKEST:
            continue
        qid = q["q_id"]
        # Find the question's round via (season, round_label).
        ridx = label_to_index.get((q["season"], q["round_label"]))
        if ridx is None:
            print(f"  WARNING q{qid}: round not found in trace, skipping")
            continue
        rkey = (q["season"], ridx)
        start = round_start[rkey]
        prefix = moves[:start]
        # Player's own prior actions.
        pidx = code_to_idx.get(str(q["player"]))
        own_prior = []
        for m in prefix:
            if pidx is not None and m.get("player") == pidx:
                own_prior.append({
                    "round": f"S{m['season']} {m['round_label']}",
                    "date": m["date"],
                    "action": m["action"],
                    "semantic_kind": m.get("semantic_kind"),
                })
        # Prior round's actions (all players).
        pos = round_pos[rkey]
        prior_actions = []
        if pos > 0:
            prev_key = round_order[pos - 1][:2]
            for m in moves:
                if (m["season"], m["round_index"]) == prev_key:
                    prior_actions.append({
                        "round": f"S{m['season']} {m['round_label']}",
                        "player": player_code(m["player"]),
                        "action": m["action"],
                        "semantic_kind": m.get("semantic_kind"),
                    })
        ctx = context.get(qid, {})
        entry = {
            "q_id": qid,
            "kind": q["kind"],
            "season": q["season"],
            "round_label": q["round_label"],
            "round_date": q["round_date"],
            "event_real_date": q["event_real_date"],
            "event_name": q["event_name"],
            "player": q["player"],
            "action": q.get("action"),
            "source": q.get("source"),
            "origin": q.get("origin"),
            "split": q.get("split"),
            "context": {
                "player_history_counts": ctx.get("player_history_counts"),
                "player_most_frequent": ctx.get("player_most_frequent"),
                "player_last_kind": ctx.get("player_last_kind"),
                "player_last3": ctx.get("player_last3"),
                "prev_round_kinds": ctx.get("prev_round_kinds"),
            },
            "player_prior_actions": own_prior,
            "player_prior_n": len(own_prior),
            "prior_round_actions": prior_actions,
            "predictions": {},
            "leaked": {},
        }
        for b in ["main", "control1", "control2", "control3"]:
            p = preds.get(qid, {}).get(b)
            if p:
                entry["predictions"][b] = {
                    "predicted_kind": p.get("predicted_kind"),
                    "confidence": p.get("confidence"),
                    "reasoning": p.get("reasoning"),
                    "facts_used": p.get("facts_used", []),
                }
            entry["leaked"][b] = qid in leaks.get(b, [])
        out.append(entry)
    out.sort(key=lambda e: (e["kind"], e["q_id"]))
    (RUNS / "diagnosis-input.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    print("questions:", len(out))
    print("by kind:", Counter(e["kind"] for e in out))
    for e in out:
        print(f"  q{e['q_id']:>2} {e['kind']:<10} S{e['season']} {e['round_label']:<4} {e['player']:<5} prior={e['player_prior_n']:>2} preds={len(e['predictions'])} leaked={sum(e['leaked'].values())}/4")


if __name__ == "__main__":
    main()
