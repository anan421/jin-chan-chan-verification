#!/usr/bin/env python3
"""Scan method files for testset leaks (round 12 setup).

Equivalent of the Phase 4 cleanup scanner (/tmp/phase4-cleanup-scan.py,
no longer on disk). The Phase 4 protocol section 12.1 re-check standard:
full-text scan must be 0 hits.

Part 1: every testset event_name and action string as a substring of
    the method file text (exact match, plus a whitespace-normalised
    match). Any hit is a verbatim leak.
Part 2: same-line qid + kind. A line that names a question id (q<N>)
    and the true kind of that question on the same line is a
    pointing leak (protocol section 11, B level).
Part 3: same-line qid + player (same rule, player instead of kind).
Part 4: bare qid mentions. Listed for review only. A bare qid with no
    kind or player on the same line is not a leak by itself (Phase 4
    final review left 2 such status notes).
Part 5: longest common substring between each file line and each
    event_name / action, in characters. The Phase 4 standard is 8
    characters: a line sharing 8 or more consecutive characters with
    a testset event name or action is flagged for review.

Usage:
  python3 scan_method_leaks.py [FILE ...]
  python3 scan_method_leaks.py --testset PATH --out PATH [FILE ...]
Exit code 0 when Parts 1-3 are all 0 hits. Part 5 flags are reported
but do not change the exit code; they need a human look.
"""
import argparse
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TESTSET = os.path.join(BASE, "testset-v7.json")

QID_RE = re.compile(r"\bq(\d{1,3})\b")  # lowercase only: "Q4 2023"
# (a quarter label) must not match as question q4.


def norm(s):
    return re.sub(r"\s+", "", s)


def lcs_len(a, b):
    """Longest common substring length, in characters (dynamic program)."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ca = a[i - 1]
        for j in range(1, len(b) + 1):
            if ca == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def scan_file(path, truth, qid_kind, qid_player):
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    ntext = norm(text)
    out = {"file": path, "part1_event_name": [], "part1_action": [],
           "part2_qid_kind": [], "part3_qid_player": [],
           "part4_bare_qid_lines": [], "part5_lcs_ge8": []}
    for q in truth:
        for field, key in (("event_name", "part1_event_name"),
                           ("action", "part1_action")):
            s = q[field]
            if s and (s in text or norm(s) in ntext):
                out[key].append({"q_id": q["q_id"], field: s})
    for i, line in enumerate(lines, 1):
        for m in QID_RE.finditer(line):
            qid = int(m.group(1))
            if qid not in qid_kind:
                continue
            kind = qid_kind[qid]
            player = qid_player[qid]
            if kind in line:
                out["part2_qid_kind"].append(
                    {"line": i, "q_id": qid, "kind": kind, "text": line.strip()})
            elif player in line:
                out["part3_qid_player"].append(
                    {"line": i, "q_id": qid, "player": player, "text": line.strip()})
            else:
                out["part4_bare_qid_lines"].append(
                    {"line": i, "q_id": qid, "text": line.strip()})
    for i, line in enumerate(lines, 1):
        sline = line.strip()
        if len(sline) < 8:
            continue
        for q in truth:
            for field in ("event_name", "action"):
                s = q[field]
                if s and len(s) >= 8 and lcs_len(sline, s) >= 8:
                    out["part5_lcs_ge8"].append(
                        {"line": i, "q_id": q["q_id"], field: field,
                         "lcs": lcs_len(sline, s), "text": sline[:80]})
                    break
            else:
                continue
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--testset", default=DEFAULT_TESTSET)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    files = args.files or [
        os.path.join(BASE, "design", "search-boundary-tightened.md"),
        os.path.join(BASE, "design",
                     "method-vision6-forward-guidance-steps.md"),
        os.path.join(BASE, "design",
                     "method-vision6-datacenter-capex-boundary.md"),
        os.path.join(BASE, "design", "method-roleplay.md"),
    ]
    ts = json.load(open(args.testset, encoding="utf-8"))
    truth = ts["questions"] if isinstance(ts, dict) else ts
    qid_kind = {q["q_id"]: q["kind"] for q in truth}
    qid_player = {q["q_id"]: q["player"] for q in truth}
    results = []
    total_hits = 0
    for f in files:
        if not os.path.exists(f):
            results.append({"file": f, "missing": True})
            print(f"MISSING: {f}")
            continue
        r = scan_file(f, truth, qid_kind, qid_player)
        results.append(r)
        hits = (len(r["part1_event_name"]) + len(r["part1_action"])
                + len(r["part2_qid_kind"]) + len(r["part3_qid_player"]))
        total_hits += hits
        print(f"{os.path.basename(f)}: part1 event={len(r['part1_event_name'])} "
              f"action={len(r['part1_action'])} part2 qid+kind="
              f"{len(r['part2_qid_kind'])} part3 qid+player="
              f"{len(r['part3_qid_player'])} bare-qid lines="
              f"{len(r['part4_bare_qid_lines'])} lcs>=8 lines="
              f"{len(r['part5_lcs_ge8'])}")
        for key in ("part1_event_name", "part1_action", "part2_qid_kind",
                    "part3_qid_player"):
            for h in r[key]:
                print("  HIT", key, h)
        for h in r["part4_bare_qid_lines"]:
            print("  BARE-QID", h)
        for h in r["part5_lcs_ge8"]:
            print("  LCS>=8", h)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"testset": args.testset, "total_hits_parts1_3": total_hits,
                       "files": results}, fh, indent=2, ensure_ascii=False)
        print(f"wrote {args.out}")
    print(f"TOTAL hits (parts 1-3): {total_hits}")
    if total_hits:
        print("SCAN FAILED: leak hits remain. Do not start the round.")
        sys.exit(1)
    print("SCAN PASS: 0 hits in parts 1-3.")


if __name__ == "__main__":
    main()
