#!/usr/bin/env python3
"""Fast deterministic checker (schema v3) for the Jin Chan Chan replay page.

Two layers:
- Layer 1 (market game): players, rounds, HP/gold, cards. Invariants
  C1-C9 as in v2, plus ROUND_RV: each move records the rule version in
  effect at its date; the recorded version must equal the resolved one,
  or be a base rule whose window overlaps the round span [date,
  spanEnd] from rules/round-spans.json (cross-span rule, 2026-11-21).
- Layer 2 (meta-game / rule table): rule-makers (US government,
  Congress, BIS/Treasury/NSC, California, China, EU) enact rule
  versions; companies lobby. Invariants:
  C10 rule actions match the political record (effective date, issuing
      body, doc number) and the rules[] mechanic table.
  C11 trigger links form the reflexive loop observe -> rule -> react
      -> observe again, with ordered dates and no dangling refs; every
      rule action is linked or carries its trigger.
  C12 dual roles (government is referee in layer 1, player in layer 2;
      companies are players in layer 1, lobbyists in layer 2) and
      stated-goal consistency (rule text vs publicly stated goal).

Whole trace, no sampling. Coverage is attested in the report.

Exit: 0 all pass; 1 any invariant fails; 2 trace missing / bad schema /
insufficient data to decide a check.

Usage:
    python3 check.py <trace.json> [--out report.json] [--summary summary.txt]
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

STATED_GOALS = {"national_security", "votes", "industrial_advantage",
                "public_safety", "other"}


class CheckResult:
    def __init__(self):
        self.failures = []
        self.gaps = []
        self.passed = []

    def fail(self, check, season, round_, player, field, expected, actual,
             note=""):
        self.failures.append({
            "check": check, "season": season, "round": round_,
            "player": player, "field": field,
            "expected": expected, "actual": actual, "note": note,
        })

    def gap(self, check, note):
        self.gaps.append({"check": check, "note": note})

    def ok(self, check, detail=""):
        self.passed.append({"check": check, "detail": detail})


def cap(v, lo, hi):
    return max(lo, min(hi, v))


def parse_penalty(formula):
    m = re.fullmatch(r"floor\(borrowed \* ([0-9.]+)\)", str(formula).strip())
    return float(m.group(1)) if m else None


def penalty_value(formula, borrowed):
    f = parse_penalty(formula)
    return None if f is None else math.floor(borrowed * f)


def resolve_rules(rules, date, player):
    """Return (base_rule, overlays) in effect on `date` for `player`."""
    base = None
    overlays = []
    for r in rules:
        if not (r["effective_from"] <= date):
            continue
        if r.get("effective_to") is not None and date >= r["effective_to"]:
            continue
        targets = r.get("applies_to_players")
        if targets is None:
            if base is None or (r["effective_from"], r["rule_id"]) > (
                    base["effective_from"], base["rule_id"]):
                base = r
        elif player in targets:
            overlays.append(r)
    return base, overlays


def load_round_spans():
    """Round date spans: {(season, round_label): span_end}.

    A round whose true date range crosses a rule-version change day is
    listed in rules/round-spans.json with its span end. Rounds without
    an entry have span_end == the move date (no span). A missing or
    unreadable file means no spans (the old strict behaviour).
    The file exists because no canonical-trace field expresses a round
    span: moves carry a single earliest-day date, seasons carry
    season-level start/end dates only.
    """
    try:
        data = json.loads(
            (Path(__file__).resolve().parent / "rules"
             / "round-spans.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    spans = {}
    for s in data.get("spans", []):
        try:
            spans[(s["season"], s["round_label"])] = s["end"]
        except Exception:
            continue
    return spans


ROUND_SPANS = load_round_spans()


def round_span_end(season, round_label, date):
    """End of the round span [date, span_end] for one move.

    The span end from round-spans.json only extends the window
    forward: an end earlier than the move date cannot shrink it.
    """
    end = ROUND_SPANS.get((season, round_label))
    if end is None:
        return date
    return max(date, end)


def rule_window_overlaps(rule, start, end):
    """True if the rule's window [effective_from, effective_to) overlaps
    the closed span [start, end]. effective_to None means open-ended."""
    if rule["effective_from"] > end:
        return False
    eff_to = rule.get("effective_to")
    if eff_to is not None and eff_to <= start:
        return False
    return True


def run(trace):
    r = CheckResult()
    players = trace.get("players", [])
    seasons = trace.get("seasons", [])
    moves = trace.get("moves", [])
    states = trace.get("season_state", [])
    rankings = trace.get("rankings", [])
    hp_series = trace.get("hp_series", [])
    pool = trace.get("card_pool", [])
    holdings = trace.get("holdings", [])
    key_cards = trace.get("key_cards", [])
    facts = trace.get("facts", {})
    rules = trace.get("rules", [])
    meta_players = trace.get("meta_players", [])
    rule_actions = trace.get("rule_actions", [])
    political_record = trace.get("political_record", [])
    trigger_links = trace.get("trigger_links", [])
    lobby_actions = trace.get("lobby_actions", [])
    goal_checks = trace.get("goal_checks", [])
    legacy_ids = trace.get("legacy_ids", [])

    pmap = {p["id"]: p for p in players}
    pname = {p["id"]: p.get("name", str(p["id"])) for p in players}
    smap = {s["season"]: s for s in seasons}
    active = {s["season"]: set(s["active_players"]) for s in seasons}
    meta_by_id = {m["id"]: m for m in meta_players}
    rule_by_id = {(x["rule_id"], x["version"]): x for x in rules}
    rule_action_by_id = {x["rule_id"]: x for x in rule_actions}

    # ---------- C1 counts ----------
    # Monthly structure (2026-11-24): a round holds a variable number of
    # moves (S0: 1-5, S1-S5: 1-117 per round); a player may act several
    # times in one round or not at all. The old "one move per player per
    # round" equalities (moves_total == sum(rounds * active), per
    # (season, player) == rounds) are false for this shape and are NOT
    # checked. What is checked: the move total and the per-season move
    # totals against the converter-recorded counts (seasons[].moves,
    # present in traces built from the 7-season data), the distinct
    # round indices per season, the ranking rows, and the hp series.
    # Traces without seasons[].moves (old fixtures) keep the old
    # equalities, which are correct for the old shape.
    new_shape = all("moves" in s for s in seasons)
    if new_shape:
        total_expected = sum(s["moves"] for s in seasons)
        if len(moves) != total_expected:
            r.fail("C1", None, None, None, "moves_total", total_expected,
                   len(moves))
        else:
            r.ok("C1", f"moves_total={total_expected}")
        for s in seasons:
            got = sum(1 for m in moves if m["season"] == s["season"])
            if got != s["moves"]:
                r.fail("C1", s["season"], None, None,
                       "moves_per_season", s["moves"], got)
    else:
        total_expected = sum(s["rounds"] * len(s["active_players"])
                             for s in seasons)
        if len(moves) != total_expected:
            r.fail("C1", None, None, None, "moves_total", total_expected,
                   len(moves))
        else:
            r.ok("C1", f"moves_total={total_expected}")
        per_ps = Counter((m["season"], m["player"]) for m in moves)
        for s in seasons:
            for pid in s["active_players"]:
                got = per_ps.get((s["season"], pid), 0)
                if got != s["rounds"]:
                    r.fail("C1", s["season"], None, pname[pid],
                           "moves_per_player_season", s["rounds"], got)
    per_season_rounds = defaultdict(set)
    for m in moves:
        per_season_rounds[m["season"]].add(m["round_index"])
    for s in seasons:
        got = len(per_season_rounds.get(s["season"], set()))
        if got != s["rounds"]:
            r.fail("C1", s["season"], None, None, "rounds_in_season",
                   s["rounds"], got)
    expect_rank = sum(len(s["active_players"]) for s in seasons)
    if len(rankings) != expect_rank:
        r.fail("C1", None, None, None, "ranking_rows", expect_rank,
               len(rankings))
    if len(hp_series) != len(players):
        r.fail("C1", None, None, None, "hp_series_lines", len(players),
               len(hp_series))
    for line in hp_series:
        pid = line.get("player")
        want = sum(1 for s in seasons if pid in s["active_players"])
        if len(line.get("points", [])) != want:
            r.fail("C1", None, None, pname.get(pid, pid),
                   "hp_series_points", want, len(line.get("points", [])))

    # ---------- C2/C3 ledger (rule version resolved per move date) ----------
    by_ps = defaultdict(list)
    for m in moves:
        by_ps[(m["season"], m["player"])].append(m)
    for k in by_ps:
        by_ps[k].sort(key=lambda m: m["round_index"])
    state = {(s["season"], s["player"]): s for s in states}
    rank = {(x["season"], x["player"]): x for x in rankings}

    for (s, pid), ms in sorted(by_ps.items()):
        st = state.get((s, pid))
        if st is None:
            r.fail("C2", s, None, pname[pid], "season_state", "present",
                   "missing")
            continue
        cur_hp, cur_gold = st["hp_start"], st["gold_start"]
        last_base = None
        for m in ms:
            base, overlays = resolve_rules(rules, m["date"], pid)
            if base is None:
                r.gap("C2/C3", f"S{s} {pname[pid]} round "
                      f"{m.get('round_label')}: no rule version applies to "
                      f"date {m['date']}")
                last_base = None
                continue
            params = base["params"]
            cap_hi, cap_lo = params["hp_cap"], params["hp_floor"]
            if m["hp_start"] != cur_hp:
                r.fail("C2", s, m.get("round_label"), pname[pid],
                       "hp_start_chain", cur_hp, m["hp_start"])
            if m["gold_start"] != cur_gold:
                r.fail("C3", s, m.get("round_label"), pname[pid],
                       "gold_start_chain", cur_gold, m["gold_start"])
            if not (cap_lo <= m["hp_start"] <= cap_hi):
                r.fail("C2", s, m.get("round_label"), pname[pid],
                       "hp_start_range", f"[{cap_lo},{cap_hi}]",
                       m["hp_start"])
            cur_hp = cap(cur_hp + m["hp_delta"], cap_lo, cap_hi)
            cur_gold = cur_gold + m["gold_delta"]
            if cur_gold < 0 and not m.get("liability", False):
                r.fail("C3", s, m.get("round_label"), pname[pid],
                       "gold_negative", ">=0", cur_gold)
            last_base = base
        if last_base is None:
            continue
        params = last_base["params"]
        pen = penalty_value(params["leverage_penalty"], st.get("borrowed", 0))
        if pen is None:
            r.gap("C3", f"S{s} {pname[pid]}: penalty formula "
                  f"'{params['leverage_penalty']}' not parseable")
            continue
        if st.get("penalty", 0) != pen:
            r.fail("C3", s, None, pname[pid], "leverage_penalty", pen,
                   st.get("penalty"),
                   f"borrowed={st.get('borrowed')} rule={last_base['rule_id']}")
        cap_hi, cap_lo = params["hp_cap"], params["hp_floor"]
        applies = params["penalty_applies_to"]
        hp_end = (cap(cur_hp - pen, cap_lo, cap_hi)
                  if applies == "hp" else cur_hp)
        gold_end = (cur_gold - pen
                    if applies == "gold" else cur_gold)
        if hp_end != st["hp_end"]:
            r.fail("C2", s, None, pname[pid], "hp_end", st["hp_end"], hp_end,
                   f"start={st['hp_start']} sum_delta="
                   f"{sum(m['hp_delta'] for m in ms)} penalty={pen} "
                   f"rule={last_base['rule_id']}")
        if gold_end != st["gold_end"]:
            r.fail("C3", s, None, pname[pid], "gold_end", st["gold_end"],
                   gold_end,
                   f"start={st['gold_start']} sum_delta="
                   f"{sum(m['gold_delta'] for m in ms)} penalty={pen} "
                   f"rule={last_base['rule_id']}")
        rk = rank.get((s, pid))
        if rk is None:
            r.fail("C9", s, None, pname[pid], "ranking_row", "present",
                   "missing")
        else:
            if rk["hp_end"] != st["hp_end"]:
                r.fail("C9", s, None, pname[pid], "ranking_hp_end",
                       st["hp_end"], rk["hp_end"])
            if rk["gold_end"] != st["gold_end"]:
                r.fail("C9", s, None, pname[pid], "ranking_gold_end",
                       st["gold_end"], rk["gold_end"])
    # Empty groups (monthly structure, 2026-11-24): an active player
    # with no moves in a season (most S6 players; MANUS/ZHIPU/MINIMAX
    # in S5) must end the season where they started, with no penalty,
    # and the ranking must match. The old structure had no empty
    # group, so the loop above never saw one.
    for s in seasons:
        for pid in s["active_players"]:
            if (s["season"], pid) in by_ps:
                continue
            st = state.get((s["season"], pid))
            if st is None:
                r.fail("C2", s["season"], None, pname[pid],
                       "season_state", "present", "missing")
                continue
            if st["hp_end"] != st["hp_start"]:
                r.fail("C2", s["season"], None, pname[pid], "hp_end",
                       st["hp_start"], st["hp_end"], "no moves in season")
            if st["gold_end"] != st["gold_start"]:
                r.fail("C3", s["season"], None, pname[pid], "gold_end",
                       st["gold_start"], st["gold_end"],
                       "no moves in season")
            if st.get("penalty", 0) != 0:
                r.fail("C3", s["season"], None, pname[pid],
                       "leverage_penalty", 0, st.get("penalty"),
                       "no moves in season")
            rk = rank.get((s["season"], pid))
            if rk is None:
                r.fail("C9", s["season"], None, pname[pid],
                       "ranking_row", "present", "missing")
            else:
                if rk["hp_end"] != st["hp_end"]:
                    r.fail("C9", s["season"], None, pname[pid],
                           "ranking_hp_end", st["hp_end"], rk["hp_end"])
                if rk["gold_end"] != st["gold_end"]:
                    r.fail("C9", s["season"], None, pname[pid],
                           "ranking_gold_end", st["gold_end"],
                           rk["gold_end"])
    if not r.failures and not r.gaps:
        r.ok("C2", "hp chain + season ends reconcile")
        r.ok("C3", "gold chain + season ends reconcile")

    # ---------- C4 elimination ----------
    for pid in pmap:
        for s in smap:
            rk = rank.get((s, pid))
            if rk and rk["hp_end"] == 0:
                later = [m for (ss, pp), ms in by_ps.items()
                         for m in ms if ss > s and pp == pid]
                if later:
                    r.fail("C4", s, None, pname[pid], "moves_after_death",
                           0, len(later),
                           f"hp=0 at end of S{s}, still acts in later seasons")

    # ---------- C5 time + legality + ROUND_RV ----------
    dates = facts.get("dates", {})
    for m in moves:
        kind = m.get("action_kind", "")
        min_date = dates.get(kind)
        if min_date and m["date"] < min_date:
            r.fail("C5", m["season"], m.get("round_label"), pname[m["player"]],
                   "date_before_true", f">={min_date}", m["date"],
                   f"action_kind={kind}")
        base, overlays = resolve_rules(rules, m["date"], m["player"])
        banned = set()
        rule_ids = []
        if base is not None:
            banned |= set(base["params"].get("banned_action_kinds", []))
            rule_ids.append(base["rule_id"])
        for ov in overlays:
            banned |= set(ov["params"].get("banned_action_kinds", []))
            rule_ids.append(ov["rule_id"])
        if kind in banned:
            r.fail("C5", m["season"], m.get("round_label"), pname[m["player"]],
                   "action_banned_by_rule_in_effect", "legal", kind,
                   f"rules in effect: {rule_ids} on {m['date']}")
        recorded = m.get("rules_version")
        if recorded is None:
            r.gap("C5", f"S{m['season']} {pname[m['player']]} "
                  f"{m.get('round_label')}: rules_version (ROUND_RV) "
                  f"not recorded")
        elif base is not None and recorded != base["rule_id"]:
            # Cross-span rule (decision 2026-11-21, Gu approved): a
            # recorded base rule is also accepted when its effective
            # window overlaps the round span [D, spanEnd], where D is
            # the move date and spanEnd comes from
            # rules/round-spans.json (no entry -> spanEnd = D, no
            # span). The date check and the banned-kind check above
            # still use D only; this changes ROUND_RV acceptance only.
            # Overlays (player-specific rules) never qualify: the
            # recorded version must be a base (global) rule.
            span_end = round_span_end(m["season"], m.get("round_label"),
                                      m["date"])
            accepted = any(
                r_["rule_id"] == recorded
                and rule_window_overlaps(r_, m["date"], span_end)
                for r_ in rules
                if r_.get("applies_to_players") is None)
            if not accepted:
                r.fail("C5", m["season"], m.get("round_label"),
                       pname[m["player"]],
                       "round_rv", base["rule_id"], recorded,
                       f"rule in effect on {m['date']}; "
                       f"round span [{m['date']},{span_end}]")
    for kc in key_cards:
        first = kc.get("first_date")
        if first is None:
            r.gap("C5", f"key card {kc['card']}: first_date missing")
        elif first < kc["min_date"]:
            r.fail("C5", None, None, None,
                   f"card_date:{kc['card']}", f">={kc['min_date']}", first)
        if first is not None:
            for r_ in rules:
                if kc["card"] in r_["params"].get("unavailable_cards", []):
                    if r_["effective_from"] <= first and (
                            r_.get("effective_to") is None
                            or first < r_["effective_to"]):
                        r.fail("C5", None, None, None,
                               f"card_unavailable:{kc['card']}",
                               f"not under {r_['rule_id']}", first)

    # ---------- C6 card pool ----------
    # Distinct-card counting (decision 2026-11-21, Gu approved): a
    # shared card (key_cards entry with shared=true) counts once per
    # (cost, card), however many players hold it; a non-shared card
    # counts once per holding row, as before. The weighted synthesis
    # check below is unchanged: it does not fail on the real trace,
    # and changing it is out of scope.
    pool_total = {c["cost"]: c["total"] for c in pool}
    shared_keys = {(kc["cost"], kc["card"]) for kc in key_cards
                   if kc.get("shared", False)}
    held_by_cost = Counter()
    seen_shared = set()
    for h in holdings:
        key = (h["cost"], h["card"])
        if key in shared_keys:
            if key in seen_shared:
                continue
            seen_shared.add(key)
        held_by_cost[h["cost"]] += 1
    for cost, total in pool_total.items():
        if held_by_cost.get(cost, 0) > total:
            r.fail("C6", None, None, None, f"pool_cost_{cost}_overheld",
                   f"<= {total}", held_by_cost.get(cost, 0))
    for kc in key_cards:
        holders = kc.get("holders", [])
        if len(holders) > 1 and not kc.get("shared", False):
            r.fail("C6", None, None, None,
                   f"key_card_shared:{kc['card']}", "1 holder",
                   len(holders))
    fam = defaultdict(lambda: defaultdict(int))
    for h in holdings:
        fam[h["card"]][h["stars"]] += 1
    for card, stars in fam.items():
        weighted = sum((3 ** (s - 1)) * n for s, n in stars.items())
        kc = next((k for k in key_cards if k["card"] == card), None)
        if kc and weighted > pool_total.get(kc["cost"], 10 ** 9):
            r.fail("C6", None, None, None, f"synthesis_overpool:{card}",
                   f"<= {pool_total.get(kc['cost'])}", weighted)

    # ---------- C7 facts ----------
    ipo = facts.get("ipo", {})
    if ipo:
        b, g, p = (ipo.get("base_usd_m"), ipo.get("greenshoe_total_usd_m"),
                   ipo.get("private_usd_m"))
        if None not in (b, p) and ipo.get("base_plus_private_usd_m") != b + p:
            r.fail("C7", None, None, None, "ipo_base_plus_private",
                   b + p, ipo.get("base_plus_private_usd_m"))
        if None not in (g, p) and ipo.get("combined_usd_m") != g + p:
            r.fail("C7", None, None, None, "ipo_combined",
                   g + p, ipo.get("combined_usd_m"))
    nv = facts.get("nvda", {})
    if nv:
        ch, cd = nv.get("close_high_cents"), nv.get("close_drop_tenths_pct")
        ih, idd = (nv.get("intraday_high_cents"),
                   nv.get("intraday_drop_tenths_pct"))
        low = nv.get("low_cents")
        if None not in (ch, cd, low):
            got = (ch - low) * 1000 // ch
            if got != cd:
                r.fail("C7", None, None, None, "nvda_close_drop",
                       cd, got, f"high={ch} low={low}")
        if None not in (ih, idd, low):
            got = (ih - low) * 1000 // ih
            if got != idd:
                r.fail("C7", None, None, None, "nvda_intraday_drop",
                       idd, got, f"high={ih} low={low}")

    # ---------- C8 roster (per-season active players) ----------
    for m in moves:
        if m["season"] not in smap:
            r.fail("C8", m["season"], m.get("round_label"), None,
                   "unknown_season", "one of seasons", m["season"])
        elif m["player"] not in active[m["season"]]:
            r.fail("C8", m["season"], m.get("round_label"), None,
                   "player_not_active", "active in season", m["player"])
    for s in seasons:
        round_players = defaultdict(set)
        for m in moves:
            if m["season"] == s["season"]:
                round_players[m["round_index"]].add(m["player"])
        for idx, ps in round_players.items():
            # Monthly structure (2026-11-24): a round holds a subset of
            # the season's active players (a player may act several
            # times in one round or not at all). The old equality
            # (every round holds exactly the active set) is false for
            # this shape; what is checked is that no round holds a
            # player outside the active set.
            extra = ps - set(s["active_players"])
            if extra:
                r.fail("C8", s["season"], idx, None, "players_per_round",
                       f"subset of {sorted(s['active_players'])}",
                       sorted(ps), f"not active: {sorted(extra)}")
    probe = {k: v for k, v in trace.items() if k != "legacy_ids"}
    blob = json.dumps(probe, ensure_ascii=False)
    for legacy in legacy_ids:
        if legacy in blob:
            r.fail("C8", None, None, None, "legacy_id_present",
                   "absent", legacy)

    # ---------- C9 chart lines vs rankings ----------
    series = {h["player"]: h.get("points", []) for h in hp_series}
    for s in seasons:
        for pid in s["active_players"]:
            rk = rank.get((s["season"], pid))
            pts = series.get(pid, [])
            active_seasons = [x["season"] for x in seasons
                              if pid in x["active_players"]]
            pos = active_seasons.index(s["season"])
            if rk and len(pts) > pos and pts[pos] != rk["hp_end"]:
                r.fail("C9", s["season"], None, pname[pid],
                       "hp_series_point", rk["hp_end"], pts[pos])

    # ---------- C10 meta: rule actions match the political record ----------
    rec_by_doc = {}
    for rec in political_record:
        rec_by_doc.setdefault(rec["doc_number"], []).append(rec)
    for ra in rule_actions:
        if not ra.get("issued_by") or not ra.get("doc_number") \
                or not ra.get("stated_goal"):
            r.fail("C10", None, None, None,
                   f"rule_action_incomplete:{ra['rule_id']}",
                   "issued_by + doc_number + stated_goal present",
                   "missing field")
        if ra.get("stated_goal") not in STATED_GOALS:
            r.fail("C10", None, None, None,
                   f"rule_action_goal:{ra['rule_id']}",
                   f"one of {sorted(STATED_GOALS)}",
                   ra.get("stated_goal"))
        recs = rec_by_doc.get(ra.get("doc_number"), [])
        match = [x for x in recs
                 if x["issuing_body"] == ra.get("issued_by")
                 and x["effective_date"] == ra.get("effective_from")]
        if not recs:
            r.fail("C10", None, None, None,
                   f"no_political_record:{ra['rule_id']}",
                   "a record with this doc_number", "none")
        elif not match:
            r.fail("C10", None, None, None,
                   f"record_mismatch:{ra['rule_id']}",
                   f"issuing_body={ra.get('issued_by')} "
                   f"effective_date={ra.get('effective_from')}",
                   [(x["issuing_body"], x["effective_date"])
                    for x in recs])
        key = (ra["rule_id"], ra["version"])
        if key not in rule_by_id:
            r.fail("C10", None, None, None,
                   f"no_matching_rule:{ra['rule_id']}",
                   "a rules[] entry with same id+version", "none")
        else:
            rr = rule_by_id[key]
            if rr["effective_from"] != ra["effective_from"] or \
                    rr.get("effective_to") != ra.get("effective_to"):
                r.fail("C10", None, None, None,
                       f"rule_dates_mismatch:{ra['rule_id']}",
                       (rr["effective_from"], rr.get("effective_to")),
                       (ra["effective_from"], ra.get("effective_to")))

    # ---------- C11 trigger links: the reflexive loop ----------
    move_index = {(m["season"], m["player"], m["round_index"]): m
                  for m in moves}

    def ref_date(ref):
        if ref is None:
            return None
        if ref.get("type") == "move":
            m = move_index.get((ref["season"], ref["player"],
                                ref["round_index"]))
            return None if m is None else m["date"]
        return ref.get("date")

    def ref_exists(ref):
        if ref is None:
            return True
        if ref.get("type") == "move":
            return (ref["season"], ref["player"],
                    ref["round_index"]) in move_index
        return ref.get("event_id") is not None

    for lk in trigger_links:
        ra = rule_action_by_id.get(lk["rule_action"])
        if ra is None:
            r.fail("C11", None, None, None,
                   f"link_unknown_rule:{lk['id']}",
                   "a rule_action with this rule_id", lk["rule_action"])
            continue
        for part in ("observe", "react", "observe_again"):
            ref = lk.get(part)
            if ref is not None and not ref_exists(ref):
                r.fail("C11", None, None, None,
                       f"link_dangling_ref:{lk['id']}:{part}",
                       "an existing move/event", ref)
        d_obs = ref_date(lk.get("observe"))
        d_react = ref_date(lk.get("react"))
        d_again = ref_date(lk.get("observe_again"))
        eff = ra["effective_from"]
        if d_obs is not None and not (d_obs < eff):
            r.fail("C11", None, None, None,
                   f"link_order:{lk['id']}:observe_before_rule",
                   f"observe < {eff}", d_obs)
        if d_react is not None and not (eff <= d_react):
            r.fail("C11", None, None, None,
                   f"link_order:{lk['id']}:rule_before_react",
                   f"{eff} <= react", d_react)
        if d_again is not None and d_react is not None \
                and not (d_react < d_again):
            r.fail("C11", None, None, None,
                   f"link_order:{lk['id']}:react_before_observe_again",
                   f"react < {d_again}", d_react)
        obs = lk.get("observe") or {}
        trig = ra.get("trigger_event") or ""
        if obs.get("type") == "event" and trig.startswith("evt-") \
                and trig != obs.get("event_id"):
            r.fail("C11", None, None, None,
                   f"link_trigger_mismatch:{lk['id']}",
                   obs.get("event_id"), trig)
    linked = {lk["rule_action"] for lk in trigger_links}
    for ra in rule_actions:
        if ra["rule_id"] not in linked and not ra.get("trigger_event"):
            r.fail("C11", None, None, None,
                   f"unlinked_rule_action:{ra['rule_id']}",
                   "a trigger link or a trigger_event", "neither")

    # ---------- C12 dual roles + stated-goal consistency ----------
    for ra in rule_actions:
        mp = meta_by_id.get(ra["actor"])
        if mp is None:
            r.fail("C12", None, None, None,
                   f"rule_actor_unknown:{ra['rule_id']}",
                   "a meta_player", ra["actor"])
        elif mp["layer2_role"] != "rulemaker":
            r.fail("C12", None, None, None,
                   f"rule_actor_not_rulemaker:{ra['rule_id']}",
                   "rulemaker", mp["layer2_role"])
    for mp in meta_players:
        if mp["kind"] in ("government", "agency", "state") \
                and mp["layer1_role"] != "referee":
            r.fail("C12", None, None, None,
                   f"government_not_referee:{mp['name']}",
                   "referee", mp["layer1_role"])
    for lb in lobby_actions:
        if lb["actor"] not in pmap:
            r.fail("C12", None, None, None,
                   f"lobby_actor_not_company:{lb['id']}",
                   "a layer-1 company player", lb["actor"])
        if lb["target_rule"] not in rule_action_by_id:
            r.fail("C12", None, None, None,
                   f"lobby_target_unknown:{lb['id']}",
                   "a rule_action", lb["target_rule"])
        if lb["position"] not in ("support", "oppose", "draft"):
            r.fail("C12", None, None, None,
                   f"lobby_position:{lb['id']}",
                   "support/oppose/draft", lb["position"])
    global_rules = sorted(
        [x for x in rules if x.get("applies_to_players") is None],
        key=lambda x: x["effective_from"])
    for ra in rule_actions:
        rr = rule_by_id.get((ra["rule_id"], ra["version"]))
        if rr is None:
            continue
        for gc in goal_checks:
            if gc["goal"] != ra["stated_goal"]:
                continue
            req = gc["requirement"]
            if req == "restrictive":
                banned = rr["params"].get("banned_action_kinds", [])
                unav = rr["params"].get("unavailable_cards", [])
                if not banned and not unav:
                    r.fail("C12", None, None, None,
                           f"goal_restrictive:{ra['rule_id']}",
                           "a ban or an unavailable card",
                           "neither", f"goal={ra['stated_goal']}")
            elif req == "public":
                if not ra.get("doc_number"):
                    r.fail("C12", None, None, None,
                           f"goal_public:{ra['rule_id']}",
                           "a public doc_number", "none")
            elif req == "param_change":
                prev = [x for x in global_rules
                        if x["effective_from"] < rr["effective_from"]]
                if prev and prev[-1]["params"] == rr["params"]:
                    r.fail("C12", None, None, None,
                           f"goal_param_change:{ra['rule_id']}",
                           "at least one param changed vs previous version",
                           "identical params")

    # ---------- coverage attestation: whole trace, no sampling ----------
    coverage = {
        "moves_checked": len(moves),
        "players_checked": len(players),
        "seasons_checked": len(seasons),
        "rankings_checked": len(rankings),
        "rule_actions_checked": len(rule_actions),
        "trigger_links_checked": len(trigger_links),
        "invariants": 12,
        "sampled": False,
        "complete": True,
    }
    return r, coverage


def main():
    ap = argparse.ArgumentParser(description="Fast deterministic trace checker (schema v3).")
    ap.add_argument("trace")
    ap.add_argument("--out", default=None)
    ap.add_argument("--summary", default=None)
    args = ap.parse_args()

    path = Path(args.trace)
    if not path.exists():
        print(f"check: trace not found: {path}", file=sys.stderr)
        return 2
    try:
        trace = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"check: cannot parse trace: {e}", file=sys.stderr)
        return 2
    if trace.get("schema_version") not in (3, 4):
        print("check: trace must be schema v3 or v4 (meta-game layer); "
              "re-extract", file=sys.stderr)
        return 2
    for k in ("players", "seasons", "moves", "season_state", "rankings",
              "hp_series", "card_pool", "holdings", "key_cards", "facts",
              "formulas", "rules", "meta_players", "rule_actions",
              "political_record", "trigger_links", "lobby_actions",
              "goal_checks"):
        if k not in trace:
            print(f"check: trace missing top-level field '{k}'",
                  file=sys.stderr)
            return 2

    r, coverage = run(trace)
    report = {
        "trace": str(path),
        "trace_sha256": trace.get("meta", {}).get("trace_sha256"),
        "page_version": trace.get("meta", {}).get("page_version"),
        "schema_version": 3,
        "coverage": coverage,
        "passed": r.passed,
        "failures": r.failures,
        "gaps": r.gaps,
        "verdict": ("pass" if not r.failures and not r.gaps
                    else "insufficient_data" if r.gaps and not r.failures
                    else "fail"),
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                             indent=2), encoding="utf-8")
    lines = [f"check: verdict={report['verdict']} "
             f"passed={len(r.passed)} failures={len(r.failures)} "
             f"gaps={len(r.gaps)}",
             f"check: coverage moves={coverage['moves_checked']} "
             f"players={coverage['players_checked']} "
             f"seasons={coverage['seasons_checked']} "
             f"rankings={coverage['rankings_checked']} "
             f"rule_actions={coverage['rule_actions_checked']} "
             f"links={coverage['trigger_links_checked']} "
             f"invariants={coverage['invariants']} sampled=False"]
    for f in r.failures:
        lines.append(
            f"  FAIL {f['check']} S{f['season']} round={f['round']} "
            f"player={f['player']} field={f['field']} "
            f"expected={f['expected']} actual={f['actual']} {f['note']}")
    for g in r.gaps:
        lines.append(f"  GAP {g['check']}: {g['note']}")
    summary = "\n".join(lines)
    print(summary)
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    return 0 if report["verdict"] == "pass" else 1 if r.failures else 2


if __name__ == "__main__":
    sys.exit(main())
