#!/usr/bin/env python3
"""Failure classification + design reflection.

Verification failures split into two classes:
- data: a localized value error. One season / one player / one field is
  wrong; the rule and the formula are consistent everywhere else.
  Fix = correct the value.
- mechanism: the design itself is wrong. Signals: the same check fails
  across many players or seasons (systematic pattern); a rule or formula
  is undeclared (the model cannot express the data); a failure recurs
  after a data fix (tracked in the failures log); or the failure spans
  the same field in >= 2 seasons.

Mechanism failures must reflect on the design and iterate it, not just
patch data. This script emits the classification plus the design
question to ask for each mechanism cluster.

Usage:
    python3 classify.py <check-report.json> [--log runs/failures-log.jsonl]
                                           [--out classification.json]
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def classify(report, history):
    failures = report.get("failures", [])
    gaps = report.get("gaps", [])
    clusters = defaultdict(list)
    for f in failures:
        clusters[(f["check"], f["field"])].append(f)
    out = []
    for (check, field), fs in sorted(clusters.items()):
        players = {f["player"] for f in fs}
        seasons = {f["season"] for f in fs}
        recurred = 0
        for f in fs:
            key = (f["check"], f["season"], f["player"], f["field"])
            recurred += history.get(key, 0)
        # mechanism signals
        systematic = len(players) >= 3 or len(seasons) >= 2
        if systematic or recurred > 0:
            cls = "mechanism"
        else:
            cls = "data"
        if cls == "mechanism":
            if recurred > 0:
                note = ("same failure recurred after a previous fix: the "
                        "fix did not hold, the design assumption is wrong")
            elif len(seasons) >= 2:
                note = ("same field fails in >= 2 seasons: the rule or "
                        "formula is wrong, not the values")
            else:
                note = ("same check fails across >= 3 players: the "
                        "mechanism is wrong, not individual values")
            question = design_question(check, field)
        else:
            note = ("localized to one player/season: correct the value, "
                    "then re-verify")
            question = ""
        out.append({
            "check": check, "field": field, "class": cls,
            "count": len(fs), "players": sorted(p for p in players if p),
            "seasons": sorted(s for s in seasons if s),
            "recurred_times": recurred, "note": note,
            "design_question": question,
            "failures": fs,
        })
    for g in gaps:
        out.append({
            "check": g["check"], "field": "undeclared",
            "class": "mechanism", "count": 1, "players": [],
            "seasons": [], "recurred_times": 0,
            "note": "rule or formula undeclared: the model cannot express "
                    "the data; the design must add the rule",
            "design_question": design_question(g["check"], "undeclared"),
            "failures": [g],
        })
    return out


def design_question(check, field):
    qs = {
        "C2": ("is the HP cap applied per round or only at season end, "
               "and does the leverage penalty hit HP before or after "
               "the cap?"),
        "C3": ("is the leverage penalty deducted from gold, HP, or both, "
               "and is borrowed principal repaid within the season?"),
        "C4": ("does elimination end the player's season, or does the "
               "player return next season with a reset?"),
        "C5": ("did the rule version change on this date, and was the "
               "move legal under the version in effect then?"),
        "C6": ("is the card pool shared across seasons, or does each "
               "season have its own pool?"),
        "C7": ("is the fact stated in two places with two different "
               "stages (e.g. pricing-day vs post-greenshoe)?"),
        "C8": ("did a player join or leave between seasons, and is the "
               "roster per season or global?"),
        "C9": ("is the ranking derived from the moves, or is it an "
               "independent snapshot?"),
    }
    return qs.get(check, "which design assumption does this failure break?")


def main():
    ap = argparse.ArgumentParser(description="Classify verification failures.")
    ap.add_argument("report")
    ap.add_argument("--log", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    history = Counter()
    if args.log and Path(args.log).exists():
        for line in Path(args.log).read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            for f in e.get("failures", []):
                history[(f["check"], f["season"], f["player"],
                         f["field"])] += 1
    clusters = classify(report, history)
    payload = {"clusters": clusters,
               "mechanism_count": sum(1 for c in clusters
                                      if c["class"] == "mechanism"),
               "data_count": sum(1 for c in clusters
                                 if c["class"] == "data")}
    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False,
                                             indent=2), encoding="utf-8")
    for c in clusters:
        print(f"  {c['class'].upper()} {c['check']}/{c['field']} "
              f"x{c['count']} seasons={c['seasons']} "
              f"players={len(c['players'])}")
        print(f"    {c['note']}")
        if c["design_question"]:
            print(f"    design question: {c['design_question']}")
    # append this run to the failures log for recurrence detection
    if args.log and (report.get("failures") or report.get("gaps")):
        log = Path(args.log)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"failures": report.get("failures", []),
                                 "gaps": report.get("gaps", [])},
                                ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    main()
