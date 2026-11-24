#!/usr/bin/env python3
"""Generate lean/Verification/Trace.lean from a trace.json (schema v3/v4).

Machine-generated, never hand-written. Maps string ids to Nat codes
(first-seen order, or a fixed code table for enums), parses the
leverage-penalty fraction from the declared formula, and emits the
trace data as Lean definitions. Fails loudly when a rule is
undeclared or a reference does not resolve: a proof must not guess
the settlement rule or invent an id mapping.

Usage:
    python3 gen_trace_lean.py <trace.json> --out lean/Verification/Trace.lean [--modular]

--modular also writes lean/Verification/ProofsByPlayer.lean and
lean/Verification/ProofsBySeason.lean: per-player and per-season
native_decide theorems that partition the full ledger/counts checks
(every player and every season is covered, nothing is dropped).
"""
import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

META_KIND = {"government": 0, "agency": 1, "legislature": 2, "state": 3,
             "bloc": 4, "company": 5}
ROLE1 = {"referee": 0, "player": 1}
ROLE2 = {"rulemaker": 0, "lobbyist": 1, "observer": 2}
ACTION = {"enact": 0, "amend": 1, "rescind": 2}
GOAL = {"national_security": 0, "votes": 1, "industrial_advantage": 2,
        "public_safety": 3, "other": 4}
POSITION = {"support": 0, "oppose": 1, "draft": 2}
REQUIREMENT = {"restrictive": 0, "public": 1, "param_change": 2}
PENALTY_RE = re.compile(r"^floor\(borrowed \* ([0-9]+(?:\.[0-9]+)?)\)$")
VERSION_RE = re.compile(r"^(\d{4})-(\d{2})$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def lean_str(s):
    out = []
    for ch in str(s):
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def to_date(v):
    if isinstance(v, int):
        return v
    m = DATE_RE.match(str(v))
    if not m:
        raise ValueError(f"bad date {v!r}")
    return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))


def parse_penalty(formula):
    m = PENALTY_RE.match(str(formula))
    if not m:
        raise ValueError(f"unparseable leverage penalty {formula!r}")
    return Fraction(m.group(1))


def version_nat(v, seen):
    m = VERSION_RE.match(str(v))
    if m:
        return int(m.group(1)) * 100 + int(m.group(2))
    if v not in seen:
        seen.append(v)
    return seen.index(v) + 1


def code(table, key):
    if key not in table:
        table[key] = len(table) + 1
    return table[key]


def main():
    ap = argparse.ArgumentParser(
        description="Generate Trace.lean from trace.json.")
    ap.add_argument("trace")
    ap.add_argument("--out", required=True)
    ap.add_argument("--modular", action="store_true",
                    help="also write ProofsByPlayer/ProofsBySeason.lean")
    args = ap.parse_args()

    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    if trace.get("schema_version") not in (3, 4):
        print("gen_trace_lean: trace must be schema v3 or v4",
              file=sys.stderr)
        return 2
    for k in ("players", "seasons", "moves", "season_state", "rankings",
              "hp_series", "card_pool", "holdings", "key_cards", "facts",
              "formulas", "rules", "meta_players", "rule_actions",
              "political_record", "trigger_links", "lobby_actions",
              "goal_checks"):
        if k not in trace:
            print(f"gen_trace_lean: trace missing field '{k}'",
                  file=sys.stderr)
            return 2
    formulas = trace["formulas"]
    if formulas.get("penalty_applies_to") not in ("hp", "gold", "none"):
        print("gen_trace_lean: formulas undeclared; refusing to generate "
              "a proof from guessed rules", file=sys.stderr)
        return 2

    # --- id maps ------------------------------------------------------
    # rule id string -> Nat (rules list order, 1-based)
    rule_id = {r["rule_id"]: i + 1 for i, r in enumerate(trace["rules"])}
    # action_kind string -> Nat code, first-seen over moves, then
    # extended with kinds that only appear in bans / min-dates.
    kind_code = {}
    for m in trace["moves"]:
        code(kind_code, m["action_kind"])
    for r in trace["rules"]:
        for k in r.get("params", {}).get("banned_action_kinds", []):
            code(kind_code, k)
    for k in trace.get("facts", {}).get("dates", {}):
        code(kind_code, k)
    # meta player id string -> Nat (list order)
    meta_id = {p["id"]: i for i, p in enumerate(trace["meta_players"])}
    # trigger link id string -> Nat (list order, 1-based)
    link_id = {lk["id"]: i + 1 for i, lk in enumerate(trace["trigger_links"])}
    # lobby action id string -> Nat (list order, 1-based)
    lobby_id = {lb["id"]: i + 1 for i, lb in enumerate(trace["lobby_actions"])}

    def rule_nat(rid):
        if rid not in rule_id:
            print(f"gen_trace_lean: unknown rule id {rid!r}",
                  file=sys.stderr)
            sys.exit(2)
        return rule_id[rid]

    def meta_nat(mid):
        if mid not in meta_id:
            print(f"gen_trace_lean: unknown meta player {mid!r}",
                  file=sys.stderr)
            sys.exit(2)
        return meta_id[mid]

    def enum(table, value, what):
        if value not in table:
            print(f"gen_trace_lean: unknown {what} {value!r}",
                  file=sys.stderr)
            sys.exit(2)
        return table[value]

    version_seen = []

    # --- round spans --------------------------------------------------
    # rules/round-spans.json lists rounds whose true date range crosses
    # a rule-version change day, keyed by (season, round_label). The
    # trace carries round_label per move, so resolve each entry to the
    # trace's round_index for that (season, round_label) and emit
    # (season, round_index, span_end). Rounds without an entry have
    # spanEnd == the move date (no span); the Lean side defaults to
    # that. Entries with no matching move in this trace are skipped
    # with a warning (a trace need not contain every listed round).
    # A missing or unreadable file means no spans (the old strict
    # behaviour), mirroring check.py.
    spans_path = (Path(__file__).resolve().parent / "rules"
                  / "round-spans.json")
    trace_spans = {}
    try:
        spans_data = json.loads(spans_path.read_text(encoding="utf-8"))
    except Exception:
        spans_data = {"spans": []}
    label_to_idx = {}
    for m in trace["moves"]:
        lab = m.get("round_label")
        if lab is None:
            continue
        key = (m["season"], lab)
        if key in label_to_idx and label_to_idx[key] != m["round_index"]:
            print(f"gen_trace_lean: round label {key} maps to two "
                  f"round_index values", file=sys.stderr)
            return 2
        label_to_idx[key] = m["round_index"]
    for sp in spans_data.get("spans", []):
        key = (sp["season"], sp["round_label"])
        if key not in label_to_idx:
            print(f"gen_trace_lean: warning: span {key} has no move "
                  f"in this trace, skipped", file=sys.stderr)
            continue
        trace_spans[(sp["season"], label_to_idx[key])] = sp["end"]

    lines = []
    a = lines.append
    a("-- MACHINE GENERATED from trace.json. Do not edit by hand.")
    a("-- Regenerate with: python3 gen_trace_lean.py <trace.json> "
      "--out lean/Verification/Trace.lean")
    a("import Verification.Model")
    a("import Verification.Dynamics")
    a("")
    a("namespace Jjc")
    a("")
    players = trace["players"]
    a(f"def traceNPlayers : Nat := {len(players)}")
    a(f"def tracePlayers : List String := "
      f"[{', '.join(lean_str(p['name']) for p in players)}]")
    a(f"def traceLegacyIds : List String := "
      f"[{', '.join(lean_str(x) for x in trace.get('legacy_ids', []))}]")
    a("")
    a("-- action_kind codes (first-seen order): " +
      ", ".join(f"{kind_code[k]}={k}" for k in kind_code))
    a(f"-- rule ids: " +
      ", ".join(f"{rule_id[r['rule_id']]}={r['rule_id']}"
                for r in trace["rules"]))
    moves = []
    for m in trace["moves"]:
        moves.append(
            f"⟨{m['season']}, {m['round_index']}, {m['player']}, "
            f"{m['hp_delta']}, {m['gold_delta']}, "
            f"{kind_code[m['action_kind']]}, {to_date(m['date'])}, "
            f"{m['hp_start']}, {m['gold_start']}, "
            f"{rule_nat(m['rules_version'])}, "
            f"{'true' if m.get('liability') else 'false'}⟩")
    a(f"def traceMoves : List Move := [{', '.join(moves)}]")
    a("")
    states = []
    for s in trace["season_state"]:
        states.append(
            f"⟨{s['season']}, {s['player']}, {s['hp_start']}, "
            f"{s['gold_start']}, {s['hp_end']}, {s['gold_end']}, "
            f"{s['borrowed']}, {s['penalty']}⟩")
    a(f"def traceStates : List SeasonState := [{', '.join(states)}]")
    a("")
    ranks = []
    for r in trace["rankings"]:
        ranks.append(
            f"⟨{r['season']}, {r['player']}, {r['rank']}, "
            f"{r['hp_end']}, {r['gold_end']}⟩")
    a(f"def traceRankings : List Ranking := [{', '.join(ranks)}]")
    a("")
    seasons = []
    for s in trace["seasons"]:
        # SeasonInfo is (season, rounds, moves, activePlayers); moves
        # is the converter-recorded season move total. Old traces
        # without it fall back to rounds * players (the old shape).
        moves_n = s.get("moves", s["rounds"] * len(s["active_players"]))
        seasons.append(
            f"⟨{s['season']}, {s['rounds']}, {moves_n}, "
            f"{s['active_players']}⟩")
    a(f"def traceSeasons : List SeasonInfo := [{', '.join(seasons)}]")
    a("")
    rules = []
    for r in trace["rules"]:
        p = r.get("params", {})
        try:
            pen = parse_penalty(p.get("leverage_penalty", ""))
        except ValueError as e:
            print(f"gen_trace_lean: rule {r['rule_id']}: {e}",
                  file=sys.stderr)
            return 2
        banned = [kind_code[k] for k in p.get("banned_action_kinds", [])]
        unavail = [lean_str(c) for c in p.get("unavailable_cards", [])]
        targets = r.get("applies_to_players") or []
        rules.append(
            f"⟨{rule_id[r['rule_id']]}, "
            f"{version_nat(r.get('version'), version_seen)}, "
            f"{to_date(r['effective_from'])}, "
            f"{to_date(r['effective_to']) if r.get('effective_to') else 0}, "
            f"{p.get('hp_cap', 100)}, {p.get('hp_floor', 0)}, "
            f"{pen.numerator}, {pen.denominator}, "
            f"{'true' if p.get('penalty_applies_to') == 'hp' else 'false'}, "
            f"[{', '.join(str(b) for b in banned)}], "
            f"[{', '.join(unavail)}], "
            f"[{', '.join(str(t) for t in targets)}]⟩")
    a(f"def traceRules : List RuleVersion := [{', '.join(rules)}]")
    a("")
    a("-- round spans (season, roundIdx, spanEnd) from "
      "rules/round-spans.json; rounds without an entry have spanEnd "
      "== the move date (no span).")
    span_items = sorted(trace_spans.items())
    a(f"def traceRoundSpans : List (Nat × Nat × Nat) := "
      f"[{', '.join(f'({s}, {r}, {e})' for (s, r), e in span_items)}]")
    a("")
    mps = []
    for mp in trace["meta_players"]:
        mps.append(
            f"⟨{meta_id[mp['id']]}, {enum(META_KIND, mp['kind'], 'meta kind')}, "
            f"{enum(ROLE1, mp['layer1_role'], 'layer1 role')}, "
            f"{enum(ROLE2, mp['layer2_role'], 'layer2 role')}⟩")
    a(f"def traceMetaPlayers : List MetaPlayer := [{', '.join(mps)}]")
    a("")
    ras = []
    for ra in trace["rule_actions"]:
        ras.append(
            f"⟨{rule_nat(ra['rule_id'])}, "
            f"{version_nat(ra.get('version'), version_seen)}, "
            f"{meta_nat(ra['actor'])}, "
            f"{enum(ACTION, ra['action'], 'rule action')}, "
            f"{to_date(ra['effective_from'])}, "
            f"{to_date(ra['effective_to']) if ra.get('effective_to') else 0}, "
            f"{lean_str(ra.get('issued_by', ''))}, "
            f"{lean_str(ra.get('doc_number', ''))}, "
            f"{enum(GOAL, ra.get('stated_goal', 'other'), 'stated goal')}, "
            f"{lean_str(ra.get('trigger_event', ''))}⟩")
    a(f"def traceRuleActions : List RuleAction := [{', '.join(ras)}]")
    a("")
    recs = []
    for rec in trace["political_record"]:
        recs.append(
            f"⟨{lean_str(rec['doc_number'])}, "
            f"{lean_str(rec['issuing_body'])}, "
            f"{to_date(rec['effective_date'])}, "
            f"{lean_str(rec.get('title', ''))}⟩")
    a(f"def tracePoliticalRecords : List PoliticalRecord := "
      f"[{', '.join(recs)}]")
    a("")

    def trigger_ref(ref):
        if ref.get("type") == "move":
            return (f"⟨true, {ref['season']}, {ref['player']}, "
                    f"{ref['round_index']}, {lean_str('')}, 0⟩")
        return (f"⟨false, 0, 0, 0, {lean_str(ref.get('event_id', ''))}, "
                f"{to_date(ref['date'])}⟩")

    links = []
    for lk in trace["trigger_links"]:
        again = lk.get("observe_again")
        links.append(
            f"⟨{link_id[lk['id']]}, {trigger_ref(lk['observe'])}, "
            f"{rule_nat(lk['rule_action'])}, {trigger_ref(lk['react'])}, "
            f"{'true' if again else 'false'}, "
            f"{trigger_ref(again) if again else '⟨false, 0, 0, 0, \"\", 0⟩'}⟩")
    a(f"def traceTriggerLinks : List TriggerLink := [{', '.join(links)}]")
    a("")
    lbs = []
    for lb in trace["lobby_actions"]:
        lbs.append(
            f"⟨{lobby_id[lb['id']]}, {lb['actor']}, "
            f"{rule_nat(lb['target_rule'])}, "
            f"{enum(POSITION, lb['position'], 'lobby position')}⟩")
    a(f"def traceLobbyActions : List LobbyAction := [{', '.join(lbs)}]")
    a("")
    gcs = [(enum(GOAL, g["goal"], "goal check"),
            enum(REQUIREMENT, g["requirement"], "requirement"))
           for g in trace["goal_checks"]]
    a(f"def traceGoalChecks : List (Nat × Nat) := "
      f"[{', '.join(f'({g}, {r})' for g, r in gcs)}]")
    a("")
    series = []
    for h in trace["hp_series"]:
        series.append(f"[{', '.join(str(x) for x in h['points'])}]")
    a(f"def traceHpSeries : List (List Int) := [{', '.join(series)}]")
    a("")
    pool = sorted((c["cost"], c["total"]) for c in trace["card_pool"])
    a(f"def tracePool : List (Nat × Nat) := "
      f"[{', '.join(f'({c}, {t})' for c, t in pool)}]")
    holds = []
    for h in trace["holdings"]:
        holds.append(
            f"⟨{h['player']}, {lean_str(h['card'])}, {h['cost']}, "
            f"{h['stars']}⟩")
    a(f"def traceHoldings : List Holding := [{', '.join(holds)}]")
    kcs = []
    for kc in trace["key_cards"]:
        kcs.append(
            f"⟨{lean_str(kc['card'])}, {kc['cost']}, "
            f"{kc.get('holders', [])}, "
            f"{'true' if kc.get('shared', False) else 'false'}, "
            f"{kc['min_date']}⟩")
    a(f"def traceKeyCards : List KeyCard := [{', '.join(kcs)}]")
    a("")
    ipo = trace["facts"]["ipo"]
    a(f"def traceIpo : IpoFacts := ⟨{ipo['base_usd_m']}, "
      f"{ipo['greenshoe_total_usd_m']}, {ipo['private_usd_m']}, "
      f"{ipo['base_plus_private_usd_m']}, {ipo['combined_usd_m']}, "
      f"{ipo['net_usd_m']}⟩")
    nv = trace["facts"]["nvda"]
    a(f"def traceNvda : NvdaFacts := ⟨{nv['close_high_cents']}, "
      f"{nv['close_drop_tenths_pct']}, {nv['intraday_high_cents']}, "
      f"{nv['intraday_drop_tenths_pct']}, {nv['low_cents']}⟩")
    a("")
    dates = trace.get("facts", {}).get("dates", {})
    min_dates = sorted(
        {(kind_code[k], to_date(v)) for k, v in dates.items()
         if k in kind_code})
    a(f"def traceMinDates : List (Nat × Nat) := "
      f"[{', '.join(f'({c}, {d})' for c, d in min_dates)}]")
    card_first = sorted({(kc["card"], to_date(kc["first_date"]))
                         for kc in trace["key_cards"]
                         if kc.get("first_date") is not None})
    a(f"def traceCardFirstDates : List (String × Nat) := "
      f"[{', '.join(f'({lean_str(c)}, {d})' for c, d in card_first)}]")
    card_min = sorted({(kc["card"], to_date(kc["min_date"]))
                       for kc in trace["key_cards"]})
    a(f"def traceCardMinDates : List (String × Nat) := "
      f"[{', '.join(f'({lean_str(c)}, {d})' for c, d in card_min)}]")
    a("")
    # --- dynamics initial states --------------------------------------
    # One initial state per (player, season) segment (one per
    # season_state row): the season opening, the base rule in effect
    # at the season's start date, and the season start as the date
    # (so rule.effectiveFrom <= date holds for dynInvariant).
    # Segments, not whole player trajectories: the S0->S1 breakpoint
    # is intentional (S1 openings are frozen starts, not the S0
    # ends), so a single continuous trajectory per player does not
    # exist. checkDynamics runs each segment from its own opening.
    global_rules = [r for r in trace["rules"]
                    if not r.get("applies_to_players")]
    season_start = {s["season"]: s["start_date"]
                    for s in trace["seasons"]}

    def base_rule_at(date):
        cands = [r for r in global_rules
                 if to_date(r["effective_from"]) <= date
                 and (not r.get("effective_to")
                      or date < to_date(r["effective_to"]))]
        if not cands:
            raise ValueError(f"no base rule in effect at {date}")
        return max(cands, key=lambda r: to_date(r["effective_from"]))

    inits = []
    for st in trace["season_state"]:
        start_date = season_start[st["season"]]
        start_rule = base_rule_at(start_date)
        inits.append(
            f"⟨{st['player']}, {st['hp_start']}, {st['gold_start']}, "
            f"false, false, {rule_id[start_rule['rule_id']]}, "
            f"{start_date}, {st['season']}⟩")
    a("-- dynamics: one initial state per (player, season) segment "
      "(the season opening, base rule in effect at the season start).")
    a(f"def traceDynInit : List DState := [{', '.join(inits)}]")
    a("")
    a("end Jjc")
    a("")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"gen_trace_lean: ok -> {args.out} "
          f"({len(moves)} moves, {len(states)} states, "
          f"{len(ranks)} rankings, {len(rules)} rules, "
          f"{len(trace_spans)} round spans)")

    if args.modular:
        out_dir = Path(args.out).parent
        # per-player actual move counts (monthly structure: a player
        # may act several times in one round or not at all, so the
        # old rounds-in-active-seasons count is not the move count).
        per_player = {}
        for p in players:
            per_player[p["id"]] = sum(
                1 for m in trace["moves"] if m["player"] == p["id"])
        pl = ["-- MACHINE GENERATED from trace.json. Do not edit by hand.",
              "import Verification.Model",
              "import Verification.Trace", "",
              "namespace Jjc", ""]
        for p in players:
            pid = p["id"]
            pl.append(
                f"-- player {pid} ({p['name']}): ledger on this player's "
                f"slice only.")
            pl.append(
                f"theorem ledger_player_{pid} : checkLedger traceRules "
                f"traceRoundSpans "
                f"(traceMoves.filter fun m => m.player == {pid}) "
                f"(traceStates.filter fun st => st.player == {pid}) "
                f"(traceRankings.filter fun r => r.player == {pid}) "
                f"= true := by native_decide")
            pl.append(
                f"theorem moves_player_{pid} : "
                f"(traceMoves.filter fun m => m.player == {pid}).length "
                f"= {per_player[pid]} := by native_decide")
            pl.append("")
        pl.append("end Jjc")
        pl.append("")
        (out_dir / "ProofsByPlayer.lean").write_text("\n".join(pl),
                                                     encoding="utf-8")
        sl = ["-- MACHINE GENERATED from trace.json. Do not edit by hand.",
              "import Verification.Model",
              "import Verification.Trace", "",
              "namespace Jjc", ""]
        for s in trace["seasons"]:
            sid = s["season"]
            moves_n = s.get("moves", s["rounds"]
                            * len(s["active_players"]))
            sl.append(f"-- season {sid}: counts + ledger on this season only.")
            sl.append(
                f"theorem counts_season_{sid} : checkCounts "
                f"(traceMoves.filter fun m => m.season == {sid}) "
                f"[⟨{sid}, {s['rounds']}, {moves_n}, "
                f"{s['active_players']}⟩] "
                f"= true := by native_decide")
            sl.append(
                f"theorem ledger_season_{sid} : checkLedger traceRules "
                f"traceRoundSpans "
                f"(traceMoves.filter fun m => m.season == {sid}) "
                f"(traceStates.filter fun st => st.season == {sid}) "
                f"(traceRankings.filter fun r => r.season == {sid}) "
                f"= true := by native_decide")
            sl.append("")
        sl.append("end Jjc")
        sl.append("")
        (out_dir / "ProofsBySeason.lean").write_text("\n".join(sl),
                                                     encoding="utf-8")
        print(f"gen_trace_lean: modular -> ProofsByPlayer.lean "
              f"({len(players)} players), ProofsBySeason.lean "
              f"({len(trace['seasons'])} seasons)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
