#!/usr/bin/env python3
"""Conformance gate for Agent outputs (agent-claim-schema.json R1-R4).

An Agent output is a JSON file: {"claims": [...]} or a bare list.
Each claim must be an AgentClaim (claim_id, kind, subject, predicate,
evidence, status, agent_id). The gate enforces the four rules:

  R1 schema        missing field / wrong type / unknown kind or
                   status / bad claim_id  -> REJECT (recorded).
  R2 evidence      the evidence pointer must resolve (doc_number in
                   the trace's political_record or rule_actions;
                   trace subject resolves in the trace; url is a
                   well-formed https URL; edgar matches the accession
                   pattern). The claim's own subject must also
                   resolve. Unresolvable -> REJECT.
  R3 predicate     the predicate must be a known op with well-typed
                   args. Undecidable -> recorded as OPINION only,
                   never as verified.
  R4 conflict      two claims on the same subject with the same op
                   and mutually exclusive expectations -> both
                   CONTESTED, the run fails until one is refuted or
                   corrected. A refutation that passes R1-R3 marks
                   its target REFUTED.

Predicate truth is evaluated against the trace only for
fact_correction and refutation claims (they speak about the current
trace). propose_action and evidence_downgrade claims speak about a
future state or about evidence quality: the gate checks decidability
and evidence only; the pipeline re-verifies after applying them.

Schema v2: a claim may carry an optional `move` object (a proposed
Move: player, date, season, actionKind, hpDelta, goldDelta,
liability, rulesVersion). When present, all 8 subfields are required
and type-checked (R1). A subject in season max_season + 1 whose
player exists resolves as a future location (found=True, value=None,
result marked future=True), not a rejection; its evidence must still
resolve (R2). A fact_correction whose subject is future is rejected:
the future cannot be corrected as fact. R4 groups by subject string,
so future subjects take part in conflicts like any other.

Exit codes: 0 = no rejects and no contested claims (opinion claims
allowed through, listed); 1 = at least one reject or contested;
2 = bad input (unreadable file, invalid JSON, missing trace or
schema). A refuted claim is a resolved conflict and does not by
itself fail the run; it is flagged in the report.

NOTE: the gate reads standalone Agent output files in the new
schema. The trace's embedded `agent_claims` field (old shape from
the pre-design-doc fixture generator) is NOT a gate input.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SCHEMA = HERE / "rules" / "agent-claim-schema.json"

CLAIM_ID_RE = re.compile(r"^CL-[A-Za-z0-9_-]+$")
EDGAR_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
URL_RE = re.compile(r"^https://[^\s/$.?#].[^\s]*$")
NUM = (int, float)
# A JSON bool is an int subclass; keep it out of numeric comparisons.
SCALAR = (int, float, str, bool)

OPS = {"eq", "ne", "lt", "lte", "gt", "gte", "in_range", "exists",
       "contains"}
# Schema v2: fields of an optional `move` object, with their types.
# bool is an int subclass in Python, so int fields must exclude bool.
MOVE_FIELDS = {"player": int, "date": int, "season": int,
               "actionKind": str, "hpDelta": int, "goldDelta": int,
               "liability": bool, "rulesVersion": str}
FUTURE_FIELDS = {"hp_start", "gold_start", "hp_end", "gold_end",
                 "borrowed", "penalty", "rank", "hp_series"}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_move(move):
    """Schema v2 R1: return a reason string, or '' when the move is OK."""
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


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Gate:
    def __init__(self, trace, schema):
        self.trace = trace
        self.schema = schema
        self.players_by_id = {p["id"]: p for p in trace.get("players", [])}
        self.players_by_key = {p["key"]: p for p in trace.get("players", [])}
        self.states = {(s["season"], s["player"]): s
                       for s in trace.get("season_state", [])}
        self.ranks = {(r["season"], r["player"]): r
                      for r in trace.get("rankings", [])}
        self.series = {h["player"]: h["points"]
                       for h in trace.get("hp_series", [])}
        self.rules = {r["rule_id"]: r for r in trace.get("rules", [])}
        self.rule_actions = {a["rule_id"]: a
                             for a in trace.get("rule_actions", [])}
        self.doc_numbers = {r["doc_number"]
                            for r in trace.get("political_record", [])}
        self.doc_numbers |= {a["doc_number"]
                             for a in trace.get("rule_actions", [])}
        seasons = trace.get("seasons", [])
        season_nums = [s["season"] for s in seasons
                       if isinstance(s, dict) and isinstance(
                           s.get("season"), int)]
        if not season_nums:
            season_nums = [s["season"] for s in trace.get("season_state", [])
                           if isinstance(s.get("season"), int)]
        self.max_season = max(season_nums) if season_nums else 0

    # --- subject resolution (R2) -------------------------------------
    def player_id(self, token):
        if token.isdigit():
            pid = int(token)
            return pid if pid in self.players_by_id else None
        p = self.players_by_key.get(token)
        return p["id"] if p else None

    def is_future_subject(self, subject):
        """Schema v2 R2: S<max+1>/P<existing player>/<known field>."""
        parts = subject.split("/")
        if len(parts) != 3 or not parts[0].startswith("S") \
                or not parts[0][1:].isdigit() or not parts[1].startswith("P"):
            return False
        if int(parts[0][1:]) != self.max_season + 1:
            return False
        if self.player_id(parts[1][1:]) is None:
            return False
        return parts[2] in FUTURE_FIELDS

    def resolve(self, subject):
        """Return (found, value). Grammar is the schema's `subject`.

        A future subject resolves as (True, None): the location
        exists as a future position, but it has no current value.
        """
        if self.is_future_subject(subject):
            return True, None
        parts = subject.split("/")
        if len(parts) >= 2 and parts[0].startswith("S") \
                and parts[0][1:].isdigit() and parts[1].startswith("P"):
            season = int(parts[0][1:])
            pid = self.player_id(parts[1][1:])
            if pid is None:
                return False, None
            if len(parts) == 3:
                field = parts[2]
                if field == "rank":
                    row = self.ranks.get((season, pid))
                    return (True, row["rank"]) if row else (False, None)
                if field == "hp_series":
                    pts = self.series.get(pid)
                    if pts is None or not (1 <= season <= len(pts)):
                        return False, None
                    return True, pts[season - 1]
                row = self.states.get((season, pid))
                if row is None or field not in row:
                    return False, None
                return True, row[field]
            return False, None
        if len(parts) == 3 and parts[0] == "facts":
            section = self.trace.get("facts", {}).get(parts[1])
            if not isinstance(section, dict) or parts[2] not in section:
                return False, None
            return True, section[parts[2]]
        if len(parts) == 3 and parts[0] == "rules":
            rule = self.rules.get(parts[1])
            if rule is None:
                return False, None
            if parts[2] in rule:
                return True, rule[parts[2]]
            if parts[2] in rule.get("params", {}):
                return True, rule["params"][parts[2]]
            return False, None
        if len(parts) == 3 and parts[0] == "meta":
            action = self.rule_actions.get(parts[1])
            if action is None or parts[2] not in action:
                return False, None
            return True, action[parts[2]]
        return False, None

    # --- evidence resolution (R2) ------------------------------------
    def evidence_resolves(self, ev):
        kind, ref = ev.get("kind"), ev.get("ref")
        if kind == "doc_number":
            return ref in self.doc_numbers
        if kind == "trace":
            return self.resolve(ref)[0]
        if kind == "url":
            return isinstance(ref, str) and bool(URL_RE.match(ref))
        if kind == "edgar":
            return isinstance(ref, str) and bool(EDGAR_RE.match(ref))
        return False

    # --- predicate decidability (R3) ---------------------------------
    def predicate_decidable(self, pred):
        """Return (decidable, reason)."""
        op = pred.get("op")
        if op not in OPS:
            return False, f"unknown predicate op {op!r}"
        if op == "exists":
            return True, ""
        if op == "in_range":
            args = pred.get("args")
            if not (isinstance(args, list) and len(args) == 2
                    and all(isinstance(a, NUM) and not isinstance(a, bool)
                            for a in args)):
                return False, "in_range needs args [lo, hi] of numbers"
            return True, ""
        if "value" not in pred or not isinstance(pred["value"], SCALAR):
            return False, f"{op} needs a scalar 'value'"
        return True, ""

    # --- predicate evaluation ----------------------------------------
    def evaluate(self, pred, value):
        """Return (applicable, result)."""
        op = pred["op"]
        if op == "exists":
            return True, True
        if op == "eq":
            return True, value == pred["value"]
        if op == "ne":
            return True, value != pred["value"]
        if op == "contains":
            if not isinstance(value, list):
                return False, None
            return True, pred["value"] in value
        if op == "in_range":
            if not (isinstance(value, NUM) and not isinstance(value, bool)):
                return False, None
            lo, hi = pred["args"]
            return True, lo <= value <= hi
        # lt / lte / gt / gte
        if not (isinstance(value, NUM) and not isinstance(value, bool)
                and isinstance(pred["value"], NUM)
                and not isinstance(pred["value"], bool)):
            return False, None
        if op == "lt":
            return True, value < pred["value"]
        if op == "lte":
            return True, value <= pred["value"]
        if op == "gt":
            return True, value > pred["value"]
        return True, value >= pred["value"]


def check_claims(gate, claims):
    """Return per-claim results (dicts)."""
    results = []
    by_id = {}
    for claim in claims:
        r = {"claim_id": claim.get("claim_id") if isinstance(claim, dict)
             else None, "kind": claim.get("kind") if isinstance(claim, dict)
             else None, "verdict": "reject", "status": None, "reason": "",
             "future": False}
        if not isinstance(claim, dict):
            r["reason"] = "R1: claim is not an object"
            results.append(r)
            continue
        # --- R1: schema ---------------------------------------------
        req = gate.schema["claim"]["required"]
        missing = [f for f in req if f not in claim]
        if missing:
            r["reason"] = f"R1: missing field(s): {', '.join(missing)}"
            results.append(r)
            continue
        bad = []
        for f in ("claim_id", "kind", "subject", "status", "agent_id"):
            if not isinstance(claim.get(f), str):
                bad.append(f)
        if not isinstance(claim.get("predicate"), dict):
            bad.append("predicate")
        if not isinstance(claim.get("evidence"), dict):
            bad.append("evidence")
        if bad:
            r["reason"] = f"R1: wrong type for field(s): {', '.join(bad)}"
            results.append(r)
            continue
        if not CLAIM_ID_RE.match(claim["claim_id"]):
            r["reason"] = "R1: claim_id must match ^CL-[A-Za-z0-9_-]+$"
            results.append(r)
            continue
        kinds = gate.schema["claim"]["fields"]["kind"]["enum"]
        if claim["kind"] not in kinds:
            r["reason"] = f"R1: unknown kind {claim['kind']!r}"
            results.append(r)
            continue
        statuses = gate.schema["claim"]["fields"]["status"]["enum"]
        if claim["status"] not in statuses:
            r["reason"] = f"R1: unknown status {claim['status']!r}"
            results.append(r)
            continue
        if claim["kind"] == "refutation":
            if not isinstance(claim.get("refutes"), str):
                r["reason"] = "R1: refutation needs a 'refutes' claim_id"
                results.append(r)
                continue
        ev = claim["evidence"]
        if not isinstance(ev.get("kind"), str) \
                or not isinstance(ev.get("ref"), str) \
                or ev.get("kind") not in ("doc_number", "trace", "url",
                                           "edgar"):
            r["reason"] = "R1: evidence needs kind + ref (string)"
            results.append(r)
            continue
        # --- R1 (schema v2): optional `move` shape -------------------
        if "move" in claim:
            why = validate_move(claim["move"])
            if why:
                r["reason"] = why
                results.append(r)
                continue
        # --- R2: evidence + subject resolve --------------------------
        if not gate.evidence_resolves(ev):
            r["reason"] = (f"R2: evidence pointer does not resolve: "
                           f"{ev['kind']} {ev['ref']!r}")
            results.append(r)
            continue
        found, value = gate.resolve(claim["subject"])
        if not found:
            r["reason"] = (f"R2: subject does not resolve in trace: "
                           f"{claim['subject']!r}")
            results.append(r)
            continue
        r["future"] = gate.is_future_subject(claim["subject"])
        if r["future"] and claim["kind"] == "fact_correction":
            r["reason"] = ("R2: fact_correction cannot target a future "
                           "subject; the future is not a fact to correct")
            results.append(r)
            continue
        if r["future"] and claim["kind"] == "refutation":
            # No current value exists to evaluate against; the
            # predicate is not applicable to a future location.
            r["verdict"] = "opinion"
            r["status"] = "opinion"
            r["reason"] = ("R3: predicate not applicable to a future "
                           "subject; recorded as opinion only")
            results.append(r)
            by_id[claim["claim_id"]] = r
            continue
        # --- R3: predicate decidable ---------------------------------
        decidable, why = gate.predicate_decidable(claim["predicate"])
        if not decidable:
            r["verdict"] = "opinion"
            r["status"] = "opinion"
            r["reason"] = f"R3: {why}; recorded as opinion only"
            results.append(r)
            by_id[claim["claim_id"]] = r
            continue
        # --- predicate truth (fact_correction / refutation only) -----
        if claim["kind"] in ("fact_correction", "refutation"):
            applicable, outcome = gate.evaluate(claim["predicate"], value)
            if not applicable:
                r["verdict"] = "opinion"
                r["status"] = "opinion"
                r["reason"] = ("R3: predicate not applicable to this "
                               "subject's type; recorded as opinion only")
                results.append(r)
                by_id[claim["claim_id"]] = r
                continue
            if not outcome:
                r["reason"] = ("predicate evaluates to false against the "
                               "trace; refuted by the trace")
                r["status"] = "refuted"
                results.append(r)
                continue
        r["verdict"] = "pass"
        r["status"] = "verified"
        r["reason"] = "passed R1-R3"
        results.append(r)
        by_id[claim["claim_id"]] = r
    # --- R4: refutations ----------------------------------------------
    for claim, r in zip(claims, results):
        if not isinstance(claim, dict) or r["verdict"] != "pass":
            continue
        if claim["kind"] != "refutation":
            continue
        target = by_id.get(claim.get("refutes"))
        if target is None:
            r["verdict"] = "reject"
            r["status"] = None
            r["reason"] = (f"R4: refutes unknown claim "
                           f"{claim.get('refutes')!r}")
            continue
        target["status"] = "refuted"
        target["refuted_by"] = claim["claim_id"]
        target["reason"] += f"; refuted by {claim['claim_id']}"
    # --- R4: conflicts -------------------------------------------------
    by_subject = {}
    for claim, r in zip(claims, results):
        if not isinstance(claim, dict) or r["verdict"] != "pass":
            continue
        by_subject.setdefault(claim["subject"], []).append((claim, r))
    for subject, members in by_subject.items():
        eqs = [(c, r) for c, r in members
               if c["predicate"]["op"] == "eq"]
        eq_vals = {json.dumps(c["predicate"].get("value")) for c, _ in eqs}
        if len(eq_vals) > 1:
            for c, r in eqs:
                r["verdict"] = "contested"
                r["status"] = "contested"
                r["reason"] = (f"R4: conflict on {subject} (eq): "
                               f"{sorted(eq_vals)}")
        ranges = [(c, r) for c, r in members
                  if c["predicate"]["op"] == "in_range"]
        rvals = [tuple(c["predicate"]["args"]) for c, _ in ranges]
        disjoint = any(hi1 < lo2 or hi2 < lo1
                       for i, (lo1, hi1) in enumerate(rvals)
                       for lo2, hi2 in rvals[i + 1:])
        if disjoint:
            for c, r in ranges:
                r["verdict"] = "contested"
                r["status"] = "contested"
                r["reason"] = (f"R4: conflict on {subject} (in_range): "
                               f"{rvals}")
        nes = [(c, r) for c, r in members
               if c["predicate"]["op"] == "ne"]
        ne_vals = {json.dumps(c["predicate"].get("value")) for c, _ in nes}
        if eq_vals & ne_vals:
            for c, r in eqs + nes:
                if json.dumps(c["predicate"].get("value")) \
                        in (eq_vals & ne_vals):
                    r["verdict"] = "contested"
                    r["status"] = "contested"
                    r["reason"] = (f"R4: eq/ne conflict on {subject}: "
                                   f"{sorted(eq_vals & ne_vals)}")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent_output", help="Agent output JSON file")
    ap.add_argument("--trace", required=True, help="trace JSON file")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--out", help="gate report JSON")
    ap.add_argument("--summary", help="human summary text")
    args = ap.parse_args(argv)

    try:
        schema = load_json(args.schema)
    except Exception as e:
        print(f"gate: cannot read schema: {e}", file=sys.stderr)
        return 2
    try:
        trace = load_json(args.trace)
    except Exception as e:
        print(f"gate: cannot read trace: {e}", file=sys.stderr)
        return 2
    try:
        agent = load_json(args.agent_output)
    except Exception as e:
        print(f"gate: cannot read agent output: {e}", file=sys.stderr)
        return 2
    claims = agent.get("claims") if isinstance(agent, dict) else agent
    if not isinstance(claims, list):
        print("gate: agent output must be a list or {'claims': [...]}",
              file=sys.stderr)
        return 2

    gate = Gate(trace, schema)
    results = check_claims(gate, claims)
    counts = {"pass": 0, "reject": 0, "opinion": 0, "contested": 0,
              "refuted": 0}
    for r in results:
        counts[r["verdict"]] += 1
        if r["status"] == "refuted":
            counts["refuted"] += 1
    failed = counts["reject"] + counts["contested"] > 0
    report = {
        "agent_output": str(args.agent_output),
        "trace": str(args.trace),
        "schema_version": schema.get("version"),
        "verdict": "fail" if failed else "pass",
        "counts": counts,
        "claims": results,
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8")
    lines = [f"gate: verdict={'fail' if failed else 'pass'} "
             f"pass={counts['pass']} reject={counts['reject']} "
             f"opinion={counts['opinion']} "
             f"contested={counts['contested']} "
             f"refuted={counts['refuted']}"]
    for r in results:
        if r["verdict"] != "pass" or r["status"] == "refuted":
            lines.append(f"  {r['verdict'].upper()} {r['claim_id']} "
                         f"({r['kind']}): {r['reason']}")
    summary = "\n".join(lines) + "\n"
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    print(summary, end="")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
