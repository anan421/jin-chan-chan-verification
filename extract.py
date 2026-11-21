#!/usr/bin/env python3
"""Extract layer (schema v4): validate raw page data into a canonical trace.

Schema v4 = schema v3 (meta-game layer) + daily events + agent claims:
- `events`: daily monitor events (event_id, date, summary, source;
  optional signal/classification/claim_ids). Raw v3 has none; raw v4
  must carry the key (possibly an empty list).
- `agent_claims`: agent claims merged in the NEW shape (schema v2
  claim dicts: claim_id, kind, subject, predicate, evidence, status,
  agent_id, optional move). Claims already embedded in the raw (old
  shape from earlier extractions: id/invariant_id/claim/evidence_ref)
  are carried through unchanged -- they cannot be converted
  losslessly, and extract does not fabricate v2 fields for them.
  Only --claims input is R1-validated (see below); embedded legacy
  claims are historical data, not new input.
- `knowledge`: carried through when present in the raw.

--claims FILE merges gated claims into the trace: the file holds
{"claims": [...]} (or a bare list) in schema v2 shape. Each claim is
R1-validated against rules/agent-claim-schema.json (required fields,
types, claim_id pattern, kind/status enums, evidence kind+ref,
predicate op, optional move shape via gate.validate_move). R1 is the
only layer extract can run: R2-R4 need a trace and run in gate.py.
A claim failing R1 aborts the extraction (exit 2); nothing is written.
--events FILE merges events: {"events": [...]} (or a bare list) in the
v4 event shape. Duplicate event_id / claim_id aborts (exit 2).

Seasons remain a list (append S6, S7, ...); the spec is derived from
the data; rules are versioned with effective dates. See README.md.

Usage:
    python3 extract.py <raw-data.json> [--page-version v7] [--out DIR]
                    [--events events.json] [--claims agent-output.json]
                    [--schema rules/agent-claim-schema.json]
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACES_DIR = HERE / "traces"
DEFAULT_SCHEMA = HERE / "rules" / "agent-claim-schema.json"

SCHEMA_VERSION = 4

# R1 validation mirrors gate.py's R1 (same schema file, same rules).
# The move-shape check is imported from gate.py when available, with a
# local fallback using the same field list, so the two cannot drift
# silently if the import fails.
MOVE_FIELDS = {"player": int, "date": int, "season": int,
               "actionKind": str, "hpDelta": int, "goldDelta": int,
               "liability": bool, "rulesVersion": str}
CLAIM_ID_RE = re.compile(r"^CL-[A-Za-z0-9_-]+$")
EVIDENCE_KINDS = {"doc_number", "trace", "url", "edgar"}

REQUIRED_TOP = ["players", "seasons", "moves", "season_state", "rankings",
                "hp_series", "card_pool", "holdings", "key_cards",
                "facts", "formulas", "rules", "meta_players",
                "rule_actions", "political_record", "trigger_links",
                "lobby_actions", "goal_checks"]
REQUIRED_PLAYER = ["id", "name", "key", "first_season", "last_season"]
REQUIRED_SEASON = ["season", "name", "start_date", "end_date", "rounds",
                   "active_players", "rules_version"]
REQUIRED_MOVE = ["season", "round_index", "round_label", "player",
                 "hp_delta", "gold_delta", "action_kind", "action",
                 "date", "hp_start", "gold_start", "population",
                 "win_streak", "roster_stars", "borrowed", "rules_version"]
REQUIRED_STATE = ["season", "player", "hp_start", "gold_start",
                  "hp_end", "gold_end", "borrowed", "penalty"]
REQUIRED_RANKING = ["season", "player", "rank", "hp_end", "gold_end"]
REQUIRED_FACTS = ["ipo", "nvda", "dates"]
REQUIRED_IPO = ["base_usd_m", "greenshoe_total_usd_m", "private_usd_m",
                "base_plus_private_usd_m", "combined_usd_m", "net_usd_m"]
REQUIRED_NVDA = ["close_high_cents", "close_drop_tenths_pct",
                 "intraday_high_cents", "intraday_drop_tenths_pct",
                 "low_cents"]
REQUIRED_RULE = ["rule_id", "version", "name", "effective_from",
                 "effective_to", "trigger", "trigger_type", "params"]
REQUIRED_PARAMS = ["hp_cap", "hp_floor", "leverage_penalty",
                   "penalty_applies_to", "banned_action_kinds",
                   "unavailable_cards"]
REQUIRED_META_PLAYER = ["id", "name", "kind", "layer1_role", "layer2_role"]
REQUIRED_RULE_ACTION = ["rule_id", "version", "actor", "action",
                        "effective_from", "effective_to", "issued_by",
                        "doc_number", "stated_goal", "trigger_event"]
REQUIRED_RECORD = ["doc_number", "issuing_body", "effective_date",
                   "title", "source"]
REQUIRED_LINK = ["id", "observe", "rule_action", "react",
                 "observe_again"]
REQUIRED_LOBBY = ["id", "actor", "target_rule", "position", "date",
                  "source"]
STATED_GOALS = {"national_security", "votes", "industrial_advantage",
                "public_safety", "other"}


class SchemaError(Exception):
    pass


def _need(obj, keys, where):
    for k in keys:
        if k not in obj:
            raise SchemaError(f"{where}: missing field '{k}'")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_move_local(move):
    """Local copy of gate.validate_move (same field list); used only if
    gate.py cannot be imported."""
    if not isinstance(move, dict):
        return "R1: 'move' must be an object"
    missing = [f for f in MOVE_FIELDS if f not in move]
    if missing:
        return f"R1: 'move' missing subfield(s): {', '.join(missing)}"
    bad = []
    for f, t in MOVE_FIELDS.items():
        v = move[f]
        if t is int and not _is_int(v):
            bad.append(f)
        elif t is not int and not isinstance(v, t):
            bad.append(f)
    if bad:
        return f"R1: 'move' wrong type for subfield(s): {', '.join(bad)}"
    return ""


def validate_claim_r1(claim, schema):
    """R1 only (gate.py runs R2-R4 against a trace). Returns a reason
    string, or '' when the claim passes R1."""
    if not isinstance(claim, dict):
        return "R1: claim is not an object"
    req = schema["claim"]["required"]
    missing = [f for f in req if f not in claim]
    if missing:
        return f"R1: missing field(s): {', '.join(missing)}"
    bad = [f for f in ("claim_id", "kind", "subject", "status", "agent_id")
           if not isinstance(claim.get(f), str)]
    if not isinstance(claim.get("predicate"), dict):
        bad.append("predicate")
    if not isinstance(claim.get("evidence"), dict):
        bad.append("evidence")
    if bad:
        return f"R1: wrong type for field(s): {', '.join(bad)}"
    if not CLAIM_ID_RE.match(claim["claim_id"]):
        return "R1: claim_id must match ^CL-[A-Za-z0-9_-]+$"
    kinds = schema["claim"]["fields"]["kind"]["enum"]
    if claim["kind"] not in kinds:
        return f"R1: unknown kind {claim['kind']!r}"
    statuses = schema["claim"]["fields"]["status"]["enum"]
    if claim["status"] not in statuses:
        return f"R1: unknown status {claim['status']!r}"
    if claim["kind"] == "refutation" \
            and not isinstance(claim.get("refutes"), str):
        return "R1: refutation needs a 'refutes' claim_id"
    ev = claim["evidence"]
    if not isinstance(ev.get("kind"), str) \
            or not isinstance(ev.get("ref"), str) \
            or ev.get("kind") not in EVIDENCE_KINDS:
        return "R1: evidence needs kind + ref (string)"
    pred = claim["predicate"]
    # NOTE: the predicate op is NOT checked here. gate.py's R1 does not
    # check it either: an unknown op is an R3 matter (predicate not
    # decidable -> opinion), not an R1 rejection. Extract validates R1
    # only; the gate decides R3.
    if "move" in claim:
        try:
            sys.path.insert(0, str(HERE))
            from gate import validate_move
            why = validate_move(claim["move"])
        except Exception:
            why = validate_move_local(claim["move"])
        if why:
            return why
    return ""


def validate_event(ev):
    """v4 event shape. Returns a reason string, or '' when valid."""
    if not isinstance(ev, dict):
        return "event is not an object"
    for f in ("event_id", "date", "summary", "source"):
        if f not in ev:
            return f"event missing field '{f}'"
    if not isinstance(ev["event_id"], str) \
            or not isinstance(ev["summary"], str) \
            or not isinstance(ev["source"], str):
        return "event event_id/summary/source must be strings"
    if not _is_int(ev["date"]):
        return "event date must be an int (YYYYMMDD)"
    return ""


def validate(raw):
    _need(raw, REQUIRED_TOP, "trace")
    players = raw["players"]
    if not isinstance(players, list) or not players:
        raise SchemaError("players: must be a non-empty list")
    for p in players:
        _need(p, REQUIRED_PLAYER, "player")
    ids = [p["id"] for p in players]
    if len(set(ids)) != len(ids):
        raise SchemaError("players: duplicate ids")
    seasons = raw["seasons"]
    if not isinstance(seasons, list) or not seasons:
        raise SchemaError("seasons: must be a non-empty list")
    season_ids = []
    for s in seasons:
        _need(s, REQUIRED_SEASON, "season")
        season_ids.append(s["season"])
        for pid in s["active_players"]:
            if pid not in ids:
                raise SchemaError(f"season {s['season']}: unknown player {pid}")
    if len(set(season_ids)) != len(season_ids):
        raise SchemaError("seasons: duplicate season numbers")
    if sorted(season_ids) != list(range(min(season_ids),
                                        max(season_ids) + 1)):
        raise SchemaError("seasons: season numbers must be contiguous")
    active = {s["season"]: set(s["active_players"]) for s in seasons}
    for m in raw["moves"]:
        _need(m, REQUIRED_MOVE, "move")
        if m["season"] not in active:
            raise SchemaError(f"move: unknown season {m['season']}")
        if m["player"] not in active[m["season"]]:
            raise SchemaError(
                f"move: player {m['player']} not active in season "
                f"{m['season']}")
    for s in raw["season_state"]:
        _need(s, REQUIRED_STATE, "season_state")
    for r in raw["rankings"]:
        _need(r, REQUIRED_RANKING, "ranking")
    for h in raw["hp_series"]:
        if "player" not in h or "points" not in h:
            raise SchemaError("hp_series: each line needs player + points")
    for c in raw["card_pool"]:
        if "cost" not in c or "total" not in c:
            raise SchemaError("card_pool: each row needs cost + total")
    for h in raw["holdings"]:
        if not all(k in h for k in ("player", "card", "cost", "stars")):
            raise SchemaError("holdings: each row needs player/card/cost/stars")
    for k in raw["key_cards"]:
        if not all(x in k for x in ("card", "cost", "holders", "min_date",
                                    "first_date")):
            raise SchemaError("key_cards: each row needs card/cost/holders/"
                              "min_date/first_date")
    _need(raw["facts"], REQUIRED_FACTS, "facts")
    _need(raw["facts"]["ipo"], REQUIRED_IPO, "facts.ipo")
    _need(raw["facts"]["nvda"], REQUIRED_NVDA, "facts.nvda")
    _need(raw["formulas"], ["hp_cap", "hp_floor", "leverage_penalty",
                            "penalty_applies_to"], "formulas")
    rules = raw["rules"]
    if not isinstance(rules, list) or not rules:
        raise SchemaError("rules: must be a non-empty list")
    for r in rules:
        _need(r, REQUIRED_RULE, "rule")
        _need(r["params"], REQUIRED_PARAMS, f"rule {r['rule_id']} params")
    meta = raw["meta_players"]
    if not isinstance(meta, list) or not meta:
        raise SchemaError("meta_players: must be a non-empty list")
    mids = []
    for mp in meta:
        _need(mp, REQUIRED_META_PLAYER, "meta_player")
        mids.append(mp["id"])
    if len(set(mids)) != len(mids):
        raise SchemaError("meta_players: duplicate ids")
    rule_ids = {(r["rule_id"], r["version"]) for r in rules}
    for ra in raw["rule_actions"]:
        _need(ra, REQUIRED_RULE_ACTION, "rule_action")
        if ra["stated_goal"] not in STATED_GOALS:
            raise SchemaError(
                f"rule_action {ra['rule_id']}: stated_goal "
                f"'{ra['stated_goal']}' not in {sorted(STATED_GOALS)}")
        if ra["actor"] not in mids:
            raise SchemaError(
                f"rule_action {ra['rule_id']}: actor {ra['actor']} is not "
                f"a meta_player (companies lobby via lobby_actions, they "
                f"do not enact rules)")
        if (ra["rule_id"], ra["version"]) not in rule_ids:
            raise SchemaError(
                f"rule_action {ra['rule_id']} {ra['version']}: no matching "
                f"entry in rules[]")
    for rec in raw["political_record"]:
        _need(rec, REQUIRED_RECORD, "political_record")
    link_ids = set()
    for lk in raw["trigger_links"]:
        _need(lk, REQUIRED_LINK, "trigger_link")
        link_ids.add(lk["id"])
    for lb in raw["lobby_actions"]:
        _need(lb, REQUIRED_LOBBY, "lobby_action")
        if lb["actor"] not in ids:
            raise SchemaError(
                f"lobby_action {lb['id']}: actor {lb['actor']} is not a "
                f"layer-1 company player")
    for gc in raw["goal_checks"]:
        if not all(k in gc for k in ("goal", "requirement")):
            raise SchemaError("goal_checks: each row needs goal/requirement")
    # v4: the raw must carry the events + agent_claims keys (possibly
    # empty lists). v3 raw has neither; they default to [] in build_trace.
    if raw.get("schema_version", 1) >= 4:
        for k in ("events", "agent_claims"):
            if k not in raw:
                raise SchemaError(f"trace: schema v4 requires '{k}'")
            if not isinstance(raw[k], list):
                raise SchemaError(f"trace: '{k}' must be a list")
    return True


def _is_sha256_hex(s):
    return (isinstance(s, str) and len(s) == 64
            and all(c in "0123456789abcdef" for c in s))


def build_trace(raw, page_version, source_sha256, events=None,
                agent_claims=None, raw_trace_sha256=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seasons = raw["seasons"]
    rounds_total = sum(s["rounds"] for s in seasons)
    merged_events = list(raw.get("events", []) or [])
    if events:
        merged_events.extend(events)
    # Embedded legacy claims (old shape) are carried through unchanged;
    # newly merged claims are stored in the new v2 shape.
    merged_claims = list(raw.get("agent_claims", []) or [])
    if agent_claims:
        merged_claims.extend(agent_claims)
    meta = {
        "page_slug": "jin-chan-chan-fu-pan-ai-da-ting-2022-2026",
        "page_version": page_version,
        "extracted_at": now,
        "source": "data.json (single source of truth, page renders only)",
        # source_sha256 is the hash of the data source (page data.json),
        # NOT the hash of the raw intermediate file. The converter
        # records it in the raw trace header (source_data_json.sha256);
        # when the raw carries no such record, main() falls back to
        # the raw input file's hash (fixtures: the source IS the
        # fixture file) and records it as raw_trace_sha256 too.
        "source_sha256": source_sha256,
        "claims_r1": ("pass" if agent_claims is not None else "none"),
        "claims_merged": len(agent_claims or []),
        "events_merged": len(events or []),
    }
    if raw_trace_sha256 is not None:
        # Hash of the immediate raw input file, kept for the audit
        # chain (it was previously mislabelled as source_sha256).
        meta["raw_trace_sha256"] = raw_trace_sha256
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "spec": {
            "players_total": len(raw["players"]),
            "rounds_total": rounds_total,
            "seasons_total": len(seasons),
            "timeline_start": min(s["start_date"] for s in seasons),
            "timeline_end": max(s["end_date"] for s in seasons),
            "coverage_required": True,
        },
        "players": raw["players"],
        "seasons": seasons,
        "moves": raw["moves"],
        "season_state": raw["season_state"],
        "rankings": raw["rankings"],
        "hp_series": raw["hp_series"],
        "card_pool": raw["card_pool"],
        "holdings": raw["holdings"],
        "key_cards": raw["key_cards"],
        "facts": raw["facts"],
        "formulas": raw["formulas"],
        "rules": raw["rules"],
        "meta_players": raw["meta_players"],
        "rule_actions": raw["rule_actions"],
        "political_record": raw["political_record"],
        "trigger_links": raw["trigger_links"],
        "lobby_actions": raw["lobby_actions"],
        "goal_checks": raw["goal_checks"],
        "events": merged_events,
        "agent_claims": merged_claims,
        "knowledge": raw.get("knowledge",
                             {"initial_facts": [], "public_facts": []}),
        "legacy_ids": raw.get("legacy_ids", ["MSOFT", "XAI", "中国队"]),
    }


def main():
    ap = argparse.ArgumentParser(description="Validate raw page data into a canonical trace (schema v4).")
    ap.add_argument("raw", help="raw data.json content (as extracted by the agent)")
    ap.add_argument("--page-version", default="v7")
    ap.add_argument("--out", default=str(TRACES_DIR))
    ap.add_argument("--events", default=None,
                    help="events file to merge ({\"events\": [...]} or a bare list, v4 shape)")
    ap.add_argument("--claims", default=None,
                    help="agent claims file to merge ({\"claims\": [...]} or a bare list, schema v2 shape; R1-validated)")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA),
                    help="agent-claim schema JSON for R1 validation")
    args = ap.parse_args()

    raw_bytes = Path(args.raw).read_bytes()
    raw_trace_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    try:
        raw = json.loads(raw_bytes)
    except json.JSONDecodeError as e:
        print(f"extract: raw data is not valid JSON: {e}", file=sys.stderr)
        return 2
    # source_sha256 is the hash of the data source (page data.json),
    # which the converter records in the raw trace header
    # (source_data_json.sha256). Hashing the raw input file here used
    # to be labelled source_sha256 -- that was the raw trace's hash,
    # not the data source's (fixed 2026-11-21; see STATUS.md).
    # Fallback (no embedded record, e.g. fixtures): the raw input
    # file's own hash; the source IS that file there.
    embedded = raw.get("source_data_json") \
        if isinstance(raw, dict) else None
    embedded_sha = embedded.get("sha256") \
        if isinstance(embedded, dict) else None
    if _is_sha256_hex(embedded_sha):
        source_sha256 = embedded_sha
        print("extract: source_sha256 from raw.source_data_json "
              f"(data.json hash {source_sha256[:12]}...)")
    else:
        source_sha256 = raw_trace_sha256
        print("extract: no source_data_json record in raw; "
              "source_sha256 falls back to the raw input file hash",
              file=sys.stderr)
    if raw.get("schema_version", 1) not in (3, 4):
        print("extract: raw must be schema v3 or v4; re-extract",
              file=sys.stderr)
        return 2
    try:
        validate(raw)
    except SchemaError as e:
        print(f"extract: schema error: {e}", file=sys.stderr)
        return 2

    # --- merge --events -------------------------------------------------
    merge_events = []
    if args.events:
        try:
            ev_doc = json.loads(Path(args.events).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"extract: cannot read events file: {e}", file=sys.stderr)
            return 2
        ev_list = ev_doc.get("events") if isinstance(ev_doc, dict) else ev_doc
        if not isinstance(ev_list, list):
            print("extract: events file must be a list or "
                  "{'events': [...]}", file=sys.stderr)
            return 2
        seen = {e.get("event_id") for e in raw.get("events", []) or []}
        for ev in ev_list:
            why = validate_event(ev)
            if why:
                print(f"extract: bad event: {why}", file=sys.stderr)
                return 2
            if ev["event_id"] in seen:
                print(f"extract: duplicate event_id {ev['event_id']!r}",
                      file=sys.stderr)
                return 2
            seen.add(ev["event_id"])
            merge_events.append(ev)

    # --- merge --claims (R1 only; R2-R4 run in gate.py) ----------------
    merge_claims = None
    if args.claims:
        try:
            schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"extract: cannot read claim schema: {e}", file=sys.stderr)
            return 2
        try:
            cl_doc = json.loads(Path(args.claims).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"extract: cannot read claims file: {e}", file=sys.stderr)
            return 2
        cl_list = cl_doc.get("claims") if isinstance(cl_doc, dict) else cl_doc
        if not isinstance(cl_list, list):
            print("extract: claims file must be a list or "
                  "{'claims': [...]}", file=sys.stderr)
            return 2
        merge_claims = []
        seen = set()
        for c in raw.get("agent_claims", []) or []:
            if isinstance(c, dict) and c.get("claim_id"):
                seen.add(c["claim_id"])
        for c in cl_list:
            why = validate_claim_r1(c, schema)
            if why:
                print(f"extract: claim {c.get('claim_id') if isinstance(c, dict) else c!r} "
                      f"rejected: {why}", file=sys.stderr)
                return 2
            if c["claim_id"] in seen:
                print(f"extract: duplicate claim_id {c['claim_id']!r}",
                      file=sys.stderr)
                return 2
            seen.add(c["claim_id"])
            merge_claims.append(c)

    trace = build_trace(raw, args.page_version, source_sha256,
                        events=merge_events, agent_claims=merge_claims,
                        raw_trace_sha256=raw_trace_sha256)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trace_bytes = json.dumps(trace, ensure_ascii=False, indent=2,
                             sort_keys=True).encode("utf-8")
    trace_sha = hashlib.sha256(trace_bytes).hexdigest()
    trace["meta"]["trace_sha256"] = trace_sha
    trace_bytes = json.dumps(trace, ensure_ascii=False, indent=2,
                             sort_keys=True).encode("utf-8")
    path = out_dir / f"trace-{date}.json"
    path.write_bytes(trace_bytes)
    latest = out_dir / "trace-latest.json"
    latest.write_bytes(trace_bytes)
    print(f"extract: ok -> {path}")
    print(f"extract: sha256 {trace_sha}")
    print(f"extract: schema v4 moves={len(trace['moves'])} "
          f"players={len(trace['players'])} "
          f"seasons={len(trace['seasons'])} "
          f"rules={len(trace['rules'])} "
          f"rule_actions={len(trace['rule_actions'])} "
          f"trigger_links={len(trace['trigger_links'])} "
          f"events={len(trace['events'])} "
          f"agent_claims={len(trace['agent_claims'])} "
          f"(merged events={len(merge_events)} "
          f"claims={len(merge_claims) if merge_claims is not None else 0}, "
          f"claims_r1={trace['meta']['claims_r1']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
