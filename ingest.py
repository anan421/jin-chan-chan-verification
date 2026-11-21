#!/usr/bin/env python3
"""Daily ingest: monitor events -> proposed rounds appended to the trace.

Pipeline for a daily run:
    daily monitor output -> proposed moves -> append to trace
    -> recompute derived values -> re-verify whole trace
    -> only then update the page.

The mapping from a real-world event to a game move is a judgement call
and stays explicit, sourced and auditable: `daily/event-map.json`
maps each event type to {player, action_kind, hp_delta, gold_delta}.
The pipeline never invents deltas; it only applies the map and then
machine-checks the arithmetic. A proposed move that breaks any
invariant fails the whole run and the page is NOT updated.

A daily batch must form complete rounds: every event in one season
must cover all of that season's active players, each exactly once.
A partial batch is not a failure, it is "not yet a round": ingest
exits 3, writes nothing, and the daily run waits for the remaining
players' events. (The checker requires every round to contain all
active players and every player to have one move per round, so a
partial round can never verify.)

Chain state: the next move's hp_start/gold_start is the PRE-penalty
chain end folded from that season's moves, not the post-penalty
season_state hp_end. The leverage penalty applies only at season end
(check.py C2/C3); using hp_end as the next start would understate the
chain by the penalty for every leveraged player and fail C2.

Each new move records its rules_version (ROUND_RV), resolved from the
trace's rules[] by the move's date (same resolution as check.py). A
move with no applicable rule version is an input error (exit 2).

Schema: accepts trace schema 2, 3 or 4. For schema v4 the ingested
events are also appended to trace["events"] (v4 event shape:
event_id, date, summary, source; signal/classification carried
through only when the events file supplies them).

Event file schema (daily/events-<date>.json):
    {"date": 20261122, "events": [
       {"event_id": "evt-001", "event_type": "bis_rule",
        "player": 0, "action": "...", "source": "https://...",
        "hp_delta": -6, "gold_delta": -10, "season": 5, "round_label": "5-8"}]}
`event_type` must exist in the map; `hp_delta`/`gold_delta` in the file
override the map defaults (the override must be justified in `source`).

Usage:
    python3 ingest.py <trace.json> <events.json> --map daily/event-map.json
                    [--out traces/trace-<date>.json]
Exit: 0 proposed; 2 input error; 3 incomplete round (wait, not a failure).
"""
import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from check import cap, resolve_rules  # noqa: E402


def chain_end(trace, season, pid):
    """Pre-penalty chain end for (season, player), folded from moves."""
    states = {(s["season"], s["player"]): s
              for s in trace.get("season_state", [])}
    st = states.get((season, pid), {})
    hp, gold = st.get("hp_start", 100), st.get("gold_start", 50)
    moves = sorted(
        (m for m in trace["moves"]
         if m["season"] == season and m["player"] == pid),
        key=lambda m: m["round_index"])
    for m in moves:
        base, _ = resolve_rules(trace["rules"], m["date"], pid)
        if base is None:
            return None, None, (f"no rule version applies to existing "
                                f"move date {m['date']}")
        params = base["params"]
        hp = cap(hp + m["hp_delta"], params["hp_floor"], params["hp_cap"])
        gold = gold + m["gold_delta"]
    return hp, gold, ""


def main():
    ap = argparse.ArgumentParser(description="Append daily monitor events to a trace.")
    ap.add_argument("trace")
    ap.add_argument("events")
    ap.add_argument("--map", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    events = json.loads(Path(args.events).read_text(encoding="utf-8"))
    event_map = {}
    if args.map and Path(args.map).exists():
        raw_map = json.loads(Path(args.map).read_text(encoding="utf-8"))
        # Accept both {"map": {...}} and a flat {event_type: {...}} file.
        event_map = raw_map.get("map", raw_map) if isinstance(raw_map, dict) \
            else {}

    if trace.get("schema_version") not in (2, 3, 4):
        print("ingest: trace must be schema v2, v3 or v4", file=sys.stderr)
        return 2
    schema_v4 = trace.get("schema_version") == 4
    seasons = {s["season"]: s for s in trace["seasons"]}

    # --- build proposed moves, grouped by season ----------------------
    by_season = defaultdict(list)
    for ev in events.get("events", []):
        etype = ev["event_type"]
        mapped = event_map.get(etype, {})
        season = ev["season"]
        pid = ev.get("player", mapped.get("player"))
        if season not in seasons:
            print(f"ingest: unknown season {season} in {ev['event_id']}",
                  file=sys.stderr)
            return 2
        if pid not in seasons[season]["active_players"]:
            print(f"ingest: player {pid} not active in season {season}",
                  file=sys.stderr)
            return 2
        if "action_kind" not in ev and "action_kind" not in mapped:
            print(f"ingest: {ev['event_id']}: no action_kind and no map "
                  f"entry for {etype}", file=sys.stderr)
            return 2
        by_season[season].append((ev, mapped, pid))

    # --- complete-round rule: each season's batch must cover all -----
    # --- active players exactly once. Partial = exit 3 (wait). --------
    for season, batch in sorted(by_season.items()):
        active = set(seasons[season]["active_players"])
        got = [pid for _, _, pid in batch]
        if len(got) != len(set(got)):
            dup = sorted({p for p in got if got.count(p) > 1})
            print(f"ingest: season {season}: duplicate player(s) in one "
                  f"batch: {dup}", file=sys.stderr)
            return 2
        if set(got) != active:
            missing = sorted(active - set(got))
            print(f"ingest: season {season}: incomplete round, missing "
                  f"players {missing} (have {len(got)}/{len(active)}); "
                  f"waiting for the remaining events, nothing written",
                  file=sys.stderr)
            return 3

    new_moves = []
    new_events = []
    for season, batch in sorted(by_season.items()):
        existing = [m for m in trace["moves"] if m["season"] == season]
        ridx = max([m["round_index"] for m in existing], default=0) + 1
        for ev, mapped, pid in batch:
            hp_start, gold_start, err = chain_end(trace, season, pid)
            if err:
                print(f"ingest: {ev['event_id']}: {err}", file=sys.stderr)
                return 2
            date = ev.get("date", events.get("date"))
            base, _ = resolve_rules(trace["rules"], date, pid)
            if base is None:
                print(f"ingest: {ev['event_id']}: no rule version applies "
                      f"to date {date}", file=sys.stderr)
                return 2
            new_moves.append({
                "season": season, "round_index": ridx,
                "round_label": ev.get("round_label", f"{season}-{ridx}"),
                "player": pid,
                "hp_delta": ev.get("hp_delta", mapped.get("hp_delta", 0)),
                "gold_delta": ev.get("gold_delta",
                                     mapped.get("gold_delta", 0)),
                "action_kind": ev.get("action_kind",
                                      mapped.get("action_kind")),
                "action": ev.get("action", mapped.get("action", ev["event_type"])),
                "date": date,
                "hp_start": hp_start, "gold_start": gold_start,
                "population": ev.get("population", 8),
                "win_streak": ev.get("win_streak", 0),
                "roster_stars": ev.get("roster_stars", 2),
                "borrowed": ev.get("borrowed", 0),
                "rules_version": base["rule_id"],
                "source": ev.get("source", ""),
                "event_id": ev["event_id"],
            })
            if schema_v4:
                rec = {"event_id": ev["event_id"], "date": date,
                       "summary": new_moves[-1]["action"],
                       "source": ev.get("source", ""),
                       "claim_ids": ev.get("claim_ids", [])}
                for opt in ("signal", "classification"):
                    if opt in ev:
                        rec[opt] = ev[opt]
                new_events.append(rec)

    # The ingest only proposes moves. Season state / rankings / chart are
    # recomputed by recompute.py from the moves (and re-verified by the
    # checker); the ingest does NOT hand-write them.
    trace = copy.deepcopy(trace)
    trace["moves"].extend(new_moves)
    if schema_v4:
        trace.setdefault("events", []).extend(new_events)
    trace["meta"]["last_ingest"] = events.get("date")
    trace["meta"]["pending_moves"] = len(new_moves)
    Path(args.out).write_text(json.dumps(trace, ensure_ascii=False, indent=2,
                                         sort_keys=True), encoding="utf-8")
    print(f"ingest: proposed {len(new_moves)} moves -> {args.out}")
    print("ingest: page must NOT update until the pipeline passes; "
          "season_state/rankings/chart are recomputed, not hand-written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
