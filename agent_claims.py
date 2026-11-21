#!/usr/bin/env python3
"""Protocol checks for Agent outputs (agent_claims.py).

Four checks, all deterministic and independent of the gate verdict:

  (a) coverage: every event in trace["events"] is referenced by at
      least one claim. A reference is an evidence.ref that contains
      the event id, or a subject/note that mentions the event id.
      A trace with no events is a vacuous pass (0/0), stated so.
  (b) references: every claim's evidence pointer resolves, reusing
      Gate.evidence_resolves from gate.py.
  (c) reproducibility: a deterministic classifier (pure function,
      event -> (kind, subject)) is run twice over the event list,
      once in original order and once shuffled with a fixed seed
      (seed=0); the sorted outputs must agree.
  (d) decidability: every claim's predicate is decidable, reusing
      Gate.predicate_decidable from gate.py.

Deterministic classifier (fixed convention for this check only; it
is a reproducibility probe, not a semantic claim about the event).
It maps the event's `classification` field to a claim kind and a
subject template:

  classification 1 -> ("fact_correction", "rules/RV-2026-11/banned_action_kinds")
  classification 2 -> ("propose_action", "S5/PNVDA/hp_end")
  classification 3 -> ("evidence_downgrade", "facts/nvda/close_high_cents")
  any other / missing classification -> ("evidence_downgrade", "facts/ipo/base_usd_m")

The classifier takes only the event dict as input and returns the
same (kind, subject) pair for the same event every time; the check
verifies that property by running it in two orders.

Exit codes: 0 = all four checks pass; 1 = at least one check fails;
2 = bad input (unreadable file, invalid JSON, missing trace, claims
not a list, gate schema missing).

Usage:
    python3 agent_claims.py <agent_output.json> --trace <trace.json>
        [--out report.json] [--summary summary.txt]
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gate import Gate, load_json as gate_load_json  # noqa: E402

DEFAULT_SCHEMA = HERE / "rules" / "agent-claim-schema.json"

# Deterministic classifier: classification -> (kind, subject template).
CLASS_MAP = {
    1: ("fact_correction", "rules/RV-2026-11/banned_action_kinds"),
    2: ("propose_action", "S5/PNVDA/hp_end"),
    3: ("evidence_downgrade", "facts/nvda/close_high_cents"),
}
CLASS_DEFAULT = ("evidence_downgrade", "facts/ipo/base_usd_m")


def classify_event(event):
    """Pure function: event dict -> (kind, subject)."""
    if not isinstance(event, dict):
        return CLASS_DEFAULT
    return CLASS_MAP.get(event.get("classification"), CLASS_DEFAULT)


def event_id(event):
    if isinstance(event, dict):
        return event.get("event_id") or event.get("id")
    if isinstance(event, str):
        return event
    return None


def check_coverage(claims, events):
    """(a) Every event id is referenced by at least one claim."""
    ids = [event_id(e) for e in events]
    ids = [i for i in ids if isinstance(i, str) and i]
    if not ids:
        return {"verdict": "pass", "vacuous": True, "covered": 0,
                "total": 0, "coverage": None,
                "uncovered": [],
                "detail": "trace has no events; coverage is vacuous (0/0)"}
    uncovered = []
    for eid in ids:
        hit = False
        for c in claims:
            if not isinstance(c, dict):
                continue
            ev = c.get("evidence") or {}
            refs = [ev.get("ref") if isinstance(ev, dict) else None,
                    c.get("subject"), c.get("note")]
            if any(isinstance(r, str) and eid in r for r in refs):
                hit = True
                break
        if not hit:
            uncovered.append(eid)
    covered = len(ids) - len(uncovered)
    return {"verdict": "pass" if not uncovered else "fail",
            "vacuous": False, "covered": covered, "total": len(ids),
            "coverage": covered / len(ids) if ids else None,
            "uncovered": uncovered,
            "detail": f"{covered}/{len(ids)} events referenced by a claim"}


def check_references(gate, claims):
    """(b) Every claim's evidence pointer resolves."""
    unresolved = []
    checked = 0
    for c in claims:
        if not isinstance(c, dict):
            unresolved.append({"claim_id": None,
                               "reason": "claim is not an object"})
            continue
        checked += 1
        ev = c.get("evidence")
        if not isinstance(ev, dict) or "kind" not in ev \
                or "ref" not in ev:
            unresolved.append({"claim_id": c.get("claim_id"),
                               "reason": "evidence missing kind/ref"})
            continue
        if not gate.evidence_resolves(ev):
            unresolved.append({"claim_id": c.get("claim_id"),
                               "evidence": ev,
                               "reason": "evidence pointer does not resolve"})
    return {"verdict": "pass" if not unresolved else "fail",
            "checked": checked, "unresolved": unresolved,
            "detail": f"{checked - len(unresolved)}/{checked} claims have "
                      f"resolvable evidence"}


def check_reproducibility(events):
    """(c) Deterministic classifier, original order vs seed=0 shuffle."""
    first = sorted(classify_event(e) for e in events)
    shuffled = list(events)
    random.Random(0).shuffle(shuffled)
    second = sorted(classify_event(e) for e in shuffled)
    equal = first == second
    return {"verdict": "pass" if equal else "fail",
            "runs_equal": equal, "seed": 0,
            "events": len(events),
            "first_run_sorted": [list(x) for x in first],
            "second_run_sorted": [list(x) for x in second],
            "detail": "classifier outputs agree across original order "
                      "and seed=0 shuffle" if equal
                      else "classifier outputs differ across orders"}


def check_decidability(gate, claims):
    """(d) Every claim's predicate is decidable."""
    undecidable = []
    checked = 0
    for c in claims:
        if not isinstance(c, dict):
            undecidable.append({"claim_id": None,
                                "reason": "claim is not an object"})
            continue
        checked += 1
        pred = c.get("predicate")
        if not isinstance(pred, dict):
            undecidable.append({"claim_id": c.get("claim_id"),
                                "reason": "predicate missing or not an object"})
            continue
        decidable, why = gate.predicate_decidable(pred)
        if not decidable:
            undecidable.append({"claim_id": c.get("claim_id"),
                                "predicate": pred, "reason": why})
    return {"verdict": "pass" if not undecidable else "fail",
            "checked": checked, "undecidable": undecidable,
            "detail": f"{checked - len(undecidable)}/{checked} claims have "
                      f"decidable predicates"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent_output", help="Agent output JSON file")
    ap.add_argument("--trace", required=True, help="trace JSON file")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--out", help="protocol report JSON")
    ap.add_argument("--summary", help="human summary text")
    args = ap.parse_args(argv)

    try:
        schema = gate_load_json(args.schema)
    except Exception as e:
        print(f"agent_claims: cannot read schema: {e}", file=sys.stderr)
        return 2
    try:
        trace = gate_load_json(args.trace)
    except Exception as e:
        print(f"agent_claims: cannot read trace: {e}", file=sys.stderr)
        return 2
    try:
        agent = gate_load_json(args.agent_output)
    except Exception as e:
        print(f"agent_claims: cannot read agent output: {e}", file=sys.stderr)
        return 2
    claims = agent.get("claims") if isinstance(agent, dict) else agent
    if not isinstance(claims, list):
        print("agent_claims: agent output must be a list or "
              "{'claims': [...]}", file=sys.stderr)
        return 2

    gate = Gate(trace, schema)
    events = trace.get("events", [])
    if not isinstance(events, list):
        print("agent_claims: trace 'events' must be a list",
              file=sys.stderr)
        return 2

    checks = {
        "coverage": check_coverage(claims, events),
        "references": check_references(gate, claims),
        "reproducibility": check_reproducibility(events),
        "decidability": check_decidability(gate, claims),
    }
    failed = [k for k, v in checks.items() if v["verdict"] != "pass"]
    report = {
        "agent_output": str(args.agent_output),
        "trace": str(args.trace),
        "schema_version": schema.get("version"),
        "verdict": "fail" if failed else "pass",
        "checks": checks,
        "failed_checks": failed,
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8")
    lines = [f"agent_claims: verdict={'fail' if failed else 'pass'} "
             + " ".join(f"{k}={v['verdict']}"
                        for k, v in checks.items())]
    for k, v in checks.items():
        lines.append(f"  {k}: {v['verdict']} — {v['detail']}")
        if k == "coverage" and v.get("uncovered"):
            lines.append(f"    uncovered: {', '.join(v['uncovered'])}")
        if k == "references" and v.get("unresolved"):
            for u in v["unresolved"]:
                lines.append(f"    unresolved: {u.get('claim_id')}: "
                             f"{u.get('reason')}")
        if k == "decidability" and v.get("undecidable"):
            for u in v["undecidable"]:
                lines.append(f"    undecidable: {u.get('claim_id')}: "
                             f"{u.get('reason')}")
    summary = "\n".join(lines) + "\n"
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    print(summary, end="")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
