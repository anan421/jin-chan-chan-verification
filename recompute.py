#!/usr/bin/env python3
"""Recompute derived trace values from moves (schema v3/v4).

Derived values (never hand-written, always recomputed from moves):
- seasons[].rounds: distinct round_index count per season.
- spec.rounds_total, spec.timeline_start/end.
- season_state hp_end/gold_end/penalty per (season, player), and
  hp_start/gold_start for S>1 (previous season's recomputed end).
- rankings: rank by hp_end desc, gold_end desc, player asc.
- hp_series: per player, season-end hp in season order.
- meta.trace_sha256: recomputed over the canonical trace bytes.
- meta.recomputed_at: timestamp.

The ledger math mirrors check.py exactly (same resolve_rules,
penalty_value, cap). Moves are inputs: if a move's hp_start does not
match the chain, recompute does NOT rewrite it; it records a warning
and the checker will fail C2 (a data error, not a recompute error).
If a move has no applicable rule version, or the penalty formula is
unparseable, recompute fails (exit 2): it cannot derive the end state.
A season_state borrowed of null is treated as 0, with a warning that
the leverage penalty was not independently verified.

Usage:
    python3 recompute.py <trace.json> --out <trace.json>
"""
import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from check import cap, penalty_value, resolve_rules  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Recompute derived trace values.")
    ap.add_argument("trace")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    if trace.get("schema_version") not in (3, 4):
        print("recompute: trace must be schema v3 or v4", file=sys.stderr)
        return 2

    players = trace["players"]
    seasons = sorted(trace["seasons"], key=lambda s: s["season"])
    moves = trace["moves"]
    rules = trace["rules"]
    warnings = []
    errors = []
    changed = []

    by_ps = defaultdict(list)
    for m in moves:
        by_ps[(m["season"], m["player"])].append(m)
    for k in by_ps:
        by_ps[k].sort(key=lambda m: m["round_index"])

    old_state = {(s["season"], s["player"]): s
                 for s in trace.get("season_state", [])}

    # Chain state across seasons: S1 starts at the recorded start
    # (100/50 when absent); S>1 starts at the previous season's
    # recomputed end.
    new_state = {}
    prev_end = {}
    for s in seasons:
        sn = s["season"]
        for pid in s["active_players"]:
            st = old_state.get((sn, pid), {})
            if sn == min(x["season"] for x in seasons):
                hp_start = st.get("hp_start", 100)
                gold_start = st.get("gold_start", 50)
                if "hp_start" not in st:
                    warnings.append(
                        f"S{sn} P{pid}: no recorded season start, "
                        f"default 100/50")
            else:
                if (pid in prev_end) and prev_end[pid] is not None:
                    hp_start, gold_start = prev_end[pid]
                else:
                    hp_start = st.get("hp_start", 100)
                    gold_start = st.get("gold_start", 50)
                    warnings.append(
                        f"S{sn} P{pid}: no previous season end, using "
                        f"recorded start {hp_start}/{gold_start}")
            borrowed = st.get("borrowed", 0)
            if borrowed is None:
                borrowed = 0
                warnings.append(
                    f"S{sn} P{pid}: borrowed is null, treated as 0; "
                    f"leverage penalty not independently verified")
            cur_hp, cur_gold = hp_start, gold_start
            last_base = None
            for m in by_ps.get((sn, pid), []):
                base, _ = resolve_rules(rules, m["date"], pid)
                if base is None:
                    errors.append(
                        f"S{sn} P{pid} round {m.get('round_label')}: no "
                        f"rule version applies to date {m['date']}")
                    last_base = None
                    continue
                params = base["params"]
                cur_hp = cap(cur_hp + m["hp_delta"],
                             params["hp_floor"], params["hp_cap"])
                cur_gold = cur_gold + m["gold_delta"]
                last_base = base
            if last_base is None:
                errors.append(
                    f"S{sn} P{pid}: no applicable rule version for the "
                    f"last move; cannot derive season end")
                prev_end[pid] = None
                continue
            params = last_base["params"]
            pen = penalty_value(params["leverage_penalty"], borrowed)
            if pen is None:
                errors.append(
                    f"S{sn} P{pid}: penalty formula "
                    f"'{params['leverage_penalty']}' not parseable")
                prev_end[pid] = None
                continue
            applies = params["penalty_applies_to"]
            hp_end = (cap(cur_hp - pen, params["hp_floor"],
                          params["hp_cap"]) if applies == "hp" else cur_hp)
            gold_end = (cur_gold - pen if applies == "gold" else cur_gold)
            row = {"season": sn, "player": pid,
                   "hp_start": hp_start, "gold_start": gold_start,
                   "hp_end": hp_end, "gold_end": gold_end,
                   "borrowed": borrowed, "penalty": pen}
            old_row = old_state.get((sn, pid))
            if old_row is None:
                warnings.append(f"S{sn} P{pid}: season_state row created")
            elif (old_row.get("hp_end"), old_row.get("gold_end"),
                  old_row.get("penalty")) != (hp_end, gold_end, pen):
                changed.append({"season": sn, "player": pid,
                                "hp_end_old": old_row.get("hp_end"),
                                "hp_end_new": hp_end,
                                "gold_end_old": old_row.get("gold_end"),
                                "gold_end_new": gold_end})
            new_state[(sn, pid)] = row
            prev_end[pid] = (hp_end, gold_end)

    # Warn (do not rewrite) when a later season's first move start does
    # not match the recomputed previous end: the checker will fail C2.
    for (sn, pid), ms in sorted(by_ps.items()):
        if not ms:
            continue
        first = ms[0]
        st = new_state.get((sn, pid))
        if st is None:
            continue
        if first.get("hp_start") != st["hp_start"]:
            warnings.append(
                f"S{sn} P{pid} round {first.get('round_label')}: move "
                f"hp_start {first.get('hp_start')} != recomputed season "
                f"start {st['hp_start']} (checker will fail C2; "
                f"moves are inputs, recompute does not rewrite them)")
        if first.get("gold_start") != st["gold_start"]:
            warnings.append(
                f"S{sn} P{pid} round {first.get('round_label')}: move "
                f"gold_start {first.get('gold_start')} != recomputed "
                f"season start {st['gold_start']}")

    if errors:
        for e in errors:
            print(f"recompute: error: {e}", file=sys.stderr)
        return 2

    trace = copy.deepcopy(trace)
    trace["season_state"] = [new_state[k] for k in sorted(new_state)]

    # rankings: rank by hp_end desc, gold_end desc, player asc
    rankings = []
    for s in seasons:
        rows = [new_state[(s["season"], pid)]
                for pid in s["active_players"]
                if (s["season"], pid) in new_state]
        rows.sort(key=lambda x: (-x["hp_end"], -x["gold_end"], x["player"]))
        for i, row in enumerate(rows, 1):
            rankings.append({"season": s["season"], "player": row["player"],
                             "rank": i, "hp_end": row["hp_end"],
                             "gold_end": row["gold_end"]})
    trace["rankings"] = rankings

    # hp_series: per player, season-end hp in season order
    series = {p["id"]: [] for p in players}
    for s in seasons:
        for pid in s["active_players"]:
            if (s["season"], pid) in new_state:
                series[pid].append(new_state[(s["season"], pid)]["hp_end"])
    trace["hp_series"] = [{"player": pid, "points": series[pid]}
                          for pid in [p["id"] for p in players]]

    # seasons[].rounds + spec, derived from moves
    for s in trace["seasons"]:
        distinct = {m["round_index"] for m in moves
                    if m["season"] == s["season"]}
        s["rounds"] = len(distinct)
    spec = trace.get("spec", {})
    spec["rounds_total"] = sum(s["rounds"] for s in trace["seasons"])
    spec["timeline_start"] = min(s["start_date"] for s in trace["seasons"])
    spec["timeline_end"] = max(s["end_date"] for s in trace["seasons"])
    trace["spec"] = spec

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    trace.setdefault("meta", {})["recomputed_at"] = now
    trace_bytes = json.dumps(trace, ensure_ascii=False, indent=2,
                             sort_keys=True).encode("utf-8")
    trace["meta"]["trace_sha256"] = hashlib.sha256(trace_bytes).hexdigest()
    trace_bytes = json.dumps(trace, ensure_ascii=False, indent=2,
                             sort_keys=True).encode("utf-8")
    Path(args.out).write_text(trace_bytes.decode("utf-8"), encoding="utf-8")

    print(f"recompute: ok -> {args.out}")
    print(f"recompute: seasons={len(seasons)} "
          f"states={len(new_state)} rankings={len(rankings)} "
          f"changed_ends={len(changed)} warnings={len(warnings)}")
    for w in warnings:
        print(f"  warn: {w}")
    for c in changed:
        print(f"  changed: S{c['season']} P{c['player']} hp_end "
              f"{c['hp_end_old']}->{c['hp_end_new']} gold_end "
              f"{c['gold_end_old']}->{c['gold_end_new']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
