#!/usr/bin/env python3
"""Symbolic dynamics: partition DState into finite symbolic cells,
build the over-approximate transfer graph by interval reasoning,
find SCCs (Tarjan) and sink-SCC attractors, and list rule-change
edge pruning.

Cell = HP segment x gold sign x eliminated x base rule version.
HP segments follow design section 3 (the page's own tiers):
king >=90, master 80-89, diamond 70-79, platinum 60-69, gold 50-59,
silver 40-49, bronze 30-39, iron <30. Gold sign: positive / zero /
negative (negative iff liability). Eliminated: alive / dead.

Over-approximation direction (write it in the report, not the
reverse): every concrete legal move corresponds to a graph edge,
so "unreachable on the graph" implies "unreachable in concreto".
The reverse does not hold: a graph path need not be a concrete
trajectory.

Usage:
    python3 symbolic.py <trace.json> [--out report.json]
                       [--summary summary.txt]
Exit: 0 success; 2 bad input.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

INF = float("inf")

HP_SEGMENTS = [
    ("king", 90, None),
    ("master", 80, 89),
    ("diamond", 70, 79),
    ("platinum", 60, 69),
    ("gold", 50, 59),
    ("silver", 40, 49),
    ("bronze", 30, 39),
    ("iron", None, 29),
]
GOLD_SIGNS = ["positive", "zero", "negative"]


def hp_segment(hp):
    for name, lo, hi in HP_SEGMENTS:
        if (lo is None or hp >= lo) and (hi is None or hp <= hi):
            return name
    return "iron"


def seg_range(name, floor, cap):
    for n, lo, hi in HP_SEGMENTS:
        if n == name:
            lo = floor if lo is None else max(lo, floor)
            hi = cap if hi is None else min(hi, cap)
            return (lo, hi)
    raise ValueError(name)


def gold_interval(sign):
    if sign == "positive":
        return (1, INF)
    if sign == "zero":
        return (0, 0)
    return (-INF, -1)


def intervals_overlap(a, b):
    return max(a[0], b[0]) <= min(a[1], b[1])


def load_trace(path):
    try:
        trace = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"symbolic: cannot parse trace: {e}", file=sys.stderr)
        return None
    for k in ("players", "moves", "rules", "season_state"):
        if k not in trace:
            print(f"symbolic: trace missing top-level field '{k}'",
                  file=sys.stderr)
            return None
    return trace


def cell_id(seg, gold, elim, rule_id):
    return f"{seg}|{gold}|{'dead' if elim else 'alive'}|{rule_id}"


def tarjan(nodes, edges):
    """edges: dict node -> set(node). Return list of SCCs (lists)."""
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = defaultdict(bool)
    result = []

    sys.setrecursionlimit(10000)

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in sorted(edges.get(v, ())):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack[w]:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                comp.append(w)
                if w == v:
                    break
            result.append(sorted(comp))

    for v in sorted(nodes):
        if v not in index:
            strongconnect(v)
    return result


def main():
    ap = argparse.ArgumentParser(description="Symbolic dynamics graph.")
    ap.add_argument("trace")
    ap.add_argument("--out", default=None)
    ap.add_argument("--summary", default=None)
    args = ap.parse_args()

    trace = load_trace(args.trace)
    if trace is None:
        return 2
    rules = trace["rules"]
    base_rules = [r for r in rules if not r.get("applies_to_players")]
    if not base_rules:
        print("symbolic: no base (global) rule in trace", file=sys.stderr)
        return 2
    base_rules.sort(key=lambda r: (r["effective_from"], r["rule_id"]))
    moves = trace["moves"]
    if not moves:
        print("symbolic: trace has no moves", file=sys.stderr)
        return 2

    # Observed per-kind delta intervals (interval reasoning input).
    kind_dhp = defaultdict(lambda: [None, None])
    kind_dgold = defaultdict(lambda: [None, None])
    for m in moves:
        k = m["action_kind"]
        for table, val in ((kind_dhp, m["hp_delta"]),
                           (kind_dgold, m["gold_delta"])):
            lo, hi = table[k]
            table[k] = (val if lo is None else min(lo, val),
                        val if hi is None else max(hi, val))
    kinds = sorted(kind_dhp)

    # --- cells --------------------------------------------------------
    cells = []
    cell_by_id = {}
    for rv in base_rules:
        params = rv["params"]
        floor, cap = params["hp_floor"], params["hp_cap"]
        for seg, _, _ in HP_SEGMENTS:
            lo, hi = seg_range(seg, floor, cap)
            if lo > hi:
                continue
            for gold in GOLD_SIGNS:
                for elim in (False, True):
                    cid = cell_id(seg, gold, elim, rv["rule_id"])
                    c = {"id": cid, "hp_segment": seg,
                         "hp_range": [lo, hi], "gold_sign": gold,
                         "eliminated": elim,
                         "rule_version": rv["rule_id"]}
                    cells.append(c)
                    cell_by_id[cid] = c

    # --- edges (same rule version; banned kinds excluded) ------------
    # Edge signature (rule-independent) for pruning comparison.
    edges = []
    edge_sigs_by_rule = {}
    adjacency = defaultdict(set)
    for rv in base_rules:
        params = rv["params"]
        floor, cap = params["hp_floor"], params["hp_cap"]
        banned = set(params.get("banned_action_kinds", []))
        sigs = set()
        for c in cells:
            if c["rule_version"] != rv["rule_id"] or c["eliminated"]:
                continue
            hp_lo, hp_hi = c["hp_range"]
            g_lo, g_hi = gold_interval(c["gold_sign"])
            for kind in kinds:
                if kind in banned:
                    continue
                dh_lo, dh_hi = kind_dhp[kind]
                dg_lo, dg_hi = kind_dgold[kind]
                img_hp = (max(floor, hp_lo + dh_lo),
                          min(cap, hp_hi + dh_hi))
                if img_hp[0] > img_hp[1]:
                    continue
                img_gold = (g_lo + dg_lo, g_hi + dg_hi)
                for seg2, _, _ in HP_SEGMENTS:
                    lo2, hi2 = seg_range(seg2, floor, cap)
                    if not intervals_overlap(img_hp, (lo2, hi2)):
                        continue
                    for gold2 in GOLD_SIGNS:
                        if not intervals_overlap(
                                img_gold, gold_interval(gold2)):
                            continue
                        # Alive target: image contains an hp > 0 in
                        # this segment. Dead target: image contains
                        # exactly hp == 0 and the segment is iron.
                        targets = []
                        if max(img_hp[0], lo2) > 0 or img_hp[1] > 0:
                            if intervals_overlap(
                                    (max(img_hp[0], 1), img_hp[1]),
                                    (lo2, hi2)):
                                targets.append(False)
                        if img_hp[0] <= 0 <= img_hp[1] and seg2 == "iron":
                            targets.append(True)
                        for elim2 in targets:
                            to = cell_id(seg2, gold2, elim2, rv["rule_id"])
                            edges.append({"from": c["id"], "to": to,
                                        "action_kind": kind,
                                        "rule_version": rv["rule_id"]})
                            adjacency[c["id"]].add(to)
                            sigs.add((c["hp_segment"], c["gold_sign"],
                                    c["eliminated"], kind, seg2, gold2,
                                    elim2))
        edge_sigs_by_rule[rv["rule_id"]] = sigs

    nodes = {c["id"] for c in cells}
    sccs = tarjan(nodes, adjacency)
    comp_of = {}
    for i, comp in enumerate(sccs):
        for n in comp:
            comp_of[n] = i
    attractors = []
    for comp in sccs:
        comp_set = set(comp)
        leaks = any(comp_of[w] != comp_of[v]
                    for v in comp for w in adjacency.get(v, ()))
        if leaks:
            continue
        # Closing kinds: every edge of that kind from the attractor
        # stays inside it (and at least one such edge exists).
        closing = []
        kinds_in = defaultdict(list)
        for e in edges:
            if e["from"] in comp_set:
                kinds_in[e["action_kind"]].append(e)
        for kind, es in sorted(kinds_in.items()):
            if all(e["to"] in comp_set for e in es):
                closing.append(kind)
        attractors.append({"cells": sorted(comp),
                           "closing_action_kinds": closing})

    # --- pruning: each rule version vs the previous one --------------
    pruning = []
    for prev, cur in zip(base_rules, base_rules[1:]):
        p_prev, p_cur = prev["params"], cur["params"]
        banned_added = sorted(
            set(p_cur.get("banned_action_kinds", []))
            - set(p_prev.get("banned_action_kinds", [])))
        removed = sorted(
            edge_sigs_by_rule[prev["rule_id"]]
            - edge_sigs_by_rule[cur["rule_id"]])
        pruning.append({
            "rule_version": cur["rule_id"],
            "previous_rule_version": prev["rule_id"],
            "banned_action_kinds_added": banned_added,
            "banned_action_kinds_removed": sorted(
                set(p_prev.get("banned_action_kinds", []))
                - set(p_cur.get("banned_action_kinds", []))),
            "hp_floor_change": [p_prev["hp_floor"], p_cur["hp_floor"]],
            "hp_cap_change": [p_prev["hp_cap"], p_cur["hp_cap"]],
            "removed_edges": [
                {"hp_segment": s[0], "gold_sign": s[1],
                 "eliminated": s[2], "action_kind": s[3],
                 "to_hp_segment": s[4], "to_gold_sign": s[5],
                 "to_eliminated": s[6]} for s in removed],
            "removed_edge_count": len(removed),
        })

    report = {
        "trace": args.trace,
        "verdict": "pass",
        "rule_versions": [r["rule_id"] for r in base_rules],
        "action_kinds": kinds,
        "cells": cells,
        "edges": edges,
        "sccs": sccs,
        "attractors": attractors,
        "pruning": pruning,
        "counts": {"cells": len(cells), "edges": len(edges),
                   "sccs": len(sccs), "attractors": len(attractors)},
        "notes": [
            "Over-approximation direction: every concrete legal move "
            "corresponds to a graph edge, so graph-unreachability "
            "implies concrete unreachability. The reverse does not "
            "hold: a graph path need not be a concrete trajectory.",
            "Edges are computed within one rule version; banned kinds "
            "are the base rule's banned_action_kinds for that version. "
            "Player-specific overlays are not in the cell partition "
            "and are ignored here.",
            "Dead cells have no outgoing edges (elimination is "
            "terminal, Dynamics.elim_no_move).",
            "Delta intervals are the observed min/max per action kind "
            "in this trace; they are not calibrated parameters.",
        ],
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8")
    lines = [
        f"symbolic: cells={len(cells)} edges={len(edges)} "
        f"sccs={len(sccs)} attractors={len(attractors)}",
        f"symbolic: rule versions: "
        f"{', '.join(r['rule_id'] for r in base_rules)}",
    ]
    live_attr = [a for a in attractors
                 if any("alive" in c for c in a["cells"])]
    for a in live_attr[:5]:
        lines.append(
            f"  attractor cells={len(a['cells'])} "
            f"closing_kinds={a['closing_action_kinds']}")
    if not live_attr:
        lines.append(
            "  attractors: all are single dead cells (elimination is "
            "terminal); no live attractor in this trace")
    elif len(live_attr) > 5:
        lines.append(f"  ... and {len(live_attr) - 5} more live attractors")
    for p in pruning:
        lines.append(
            f"  pruning {p['previous_rule_version']} -> "
            f"{p['rule_version']}: banned+={p['banned_action_kinds_added']} "
            f"hp_floor {p['hp_floor_change']} hp_cap {p['hp_cap_change']} "
            f"removed_edges={p['removed_edge_count']}")
    summary = "\n".join(lines)
    print(summary)
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
