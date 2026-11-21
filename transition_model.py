#!/usr/bin/env python3
"""Transition (Markov) model prototype for next-action prediction.

Classic probability model: learn P(next kind | player, prev kind, state)
directly from the trace. No utility formula, no predict.py.
Walk-forward: for each test record (S4-S5, classifiable), only moves in
earlier rounds are used. Hierarchical levels with add-k smoothing (k=1)
and linear interpolation (inactive levels are dropped, weights renormalised):

  L0 (player, prev2 kind, prev1 kind) -> kind   [second-order, ablation only]
  L1 (player, prev kind) -> kind
  L2 (player) -> kind
  L3 (prev kind) -> kind
  L4 (global) -> kind
  L5 (player, hp bin) -> kind                   [state, ablation only]
  L6 (player, gold bin) -> kind                 [state, ablation only]

A transition counts only when both kinds are known. A test record whose
true kind has never appeared in the prefix is unguessable (ceiling 59/83).
"""
import json
import os
from collections import Counter, defaultdict

TRACE = "traces/trace-latest.json"
OUTDIR = "runs/transition-prototype-2026-11-21"
ALPHA = 1.0  # add-k smoothing


def hp_bin(hp):
    if hp >= 80:
        return "high"
    if hp >= 60:
        return "mid"
    return "low"


def gold_bin(gold):
    if gold >= 70:
        return "high"
    if gold >= 40:
        return "mid"
    return "low"


def load_trace():
    with open(TRACE) as f:
        return json.load(f)


def round_positions(moves):
    rounds = sorted({(m["season"], m["round_index"]) for m in moves})
    return {r: i for i, r in enumerate(rounds)}


def build_counts(prefix_moves):
    """Counts from prefix moves only. A transition counts only when both
    kinds are known. Kind counts skip unknown moves."""
    c0, c0t = Counter(), Counter()   # (player, prev2, prev1, kind)
    c1, c1t = Counter(), Counter()   # (player, prev, kind)
    c2, c2t = Counter(), Counter()   # (player, kind)
    c3, c3t = Counter(), Counter()   # (prev, kind)
    c4, c4t = Counter(), 0           # (kind)
    c5, c5t = Counter(), Counter()   # (player, hp_bin, kind)
    c6, c6t = Counter(), Counter()   # (player, gold_bin, kind)
    by_player = defaultdict(list)
    for m in prefix_moves:
        by_player[m["player"]].append(m)
    for p, seq in by_player.items():
        seq.sort(key=lambda m: (m["season"], m["round_index"]))
        for m in seq:
            k = m["semantic_kind"]
            if k == "unknown":
                continue
            c2[(p, k)] += 1
            c2t[p] += 1
            c4[k] += 1
            c4t += 1
            c5[(p, hp_bin(m["hp_start"]), k)] += 1
            c5t[(p, hp_bin(m["hp_start"]))] += 1
            c6[(p, gold_bin(m["gold_start"]), k)] += 1
            c6t[(p, gold_bin(m["gold_start"]))] += 1
        for a, b in zip(seq, seq[1:]):
            pk, nk = a["semantic_kind"], b["semantic_kind"]
            if pk == "unknown" or nk == "unknown":
                continue
            c1[(p, pk, nk)] += 1
            c1t[(p, pk)] += 1
            c3[(pk, nk)] += 1
            c3t[pk] += 1
        for a, b, c in zip(seq, seq[1:], seq[2:]):
            p2, p1, nk = a["semantic_kind"], b["semantic_kind"], c["semantic_kind"]
            if p2 == "unknown" or p1 == "unknown" or nk == "unknown":
                continue
            c0[(p, p2, p1, nk)] += 1
            c0t[(p, p2, p1)] += 1
    return {"c0": c0, "c0t": c0t, "c1": c1, "c1t": c1t, "c2": c2, "c2t": c2t,
            "c3": c3, "c3t": c3t, "c4": c4, "c4t": c4t, "c5": c5, "c5t": c5t,
            "c6": c6, "c6t": c6t}


def level_probs(counts, player, prev2, prev1, hp_b, gold_b, V):
    """Smoothed probability dict per level (None if the level has no
    observations for this context). V = candidate kinds seen in prefix."""
    nV = len(V)
    out = {}
    tot = counts["c0t"].get((player, prev2, prev1), 0)
    out["L0"] = ({k: (counts["c0"].get((player, prev2, prev1, k), 0) + ALPHA) / (tot + ALPHA * nV)
                  for k in V} if tot > 0 else None)
    tot = counts["c1t"].get((player, prev1), 0)
    out["L1"] = ({k: (counts["c1"].get((player, prev1, k), 0) + ALPHA) / (tot + ALPHA * nV)
                  for k in V} if tot > 0 else None)
    tot = counts["c2t"].get(player, 0)
    out["L2"] = ({k: (counts["c2"].get((player, k), 0) + ALPHA) / (tot + ALPHA * nV)
                  for k in V} if tot > 0 else None)
    tot = counts["c3t"].get(prev1, 0) if prev1 != "unknown" else 0
    out["L3"] = ({k: (counts["c3"].get((prev1, k), 0) + ALPHA) / (tot + ALPHA * nV)
                  for k in V} if tot > 0 else None)
    out["L4"] = ({k: (counts["c4"].get(k, 0) + ALPHA) / (counts["c4t"] + ALPHA * nV)
                  for k in V} if counts["c4t"] > 0 else None)
    tot = counts["c5t"].get((player, hp_b), 0)
    out["L5"] = ({k: (counts["c5"].get((player, hp_b, k), 0) + ALPHA) / (tot + ALPHA * nV)
                  for k in V} if tot > 0 else None)
    tot = counts["c6t"].get((player, gold_b), 0)
    out["L6"] = ({k: (counts["c6"].get((player, gold_b, k), 0) + ALPHA) / (tot + ALPHA * nV)
                  for k in V} if tot > 0 else None)
    return out


def combine(levels, weights):
    """Linear interpolation over active levels; inactive levels are
    dropped and remaining weights renormalised."""
    active = {lv: w for lv, w in weights.items()
              if w > 0 and levels.get(lv) is not None}
    if not active:
        return None
    s = sum(active.values())
    V = set()
    for lv in active:
        V |= set(levels[lv].keys())
    return {k: sum((active[lv] / s) * levels[lv].get(k, 0.0) for lv in active)
            for k in V}


def predict_interp(counts, player, prev2, prev1, hp_b, gold_b, weights):
    V = sorted(counts["c4"].keys())
    if not V:
        return None, {}, {}
    levels = level_probs(counts, player, prev2, prev1, hp_b, gold_b, V)
    combined = combine(levels, weights)
    if combined is None:
        return None, {}, levels
    l2 = levels.get("L2") or {}
    best = max(combined.keys(), key=lambda k: (combined[k], l2.get(k, 0.0), k))
    return best, combined, levels


def predict_backoff(counts, player, prev2, prev1, hp_b, gold_b, min_support=3):
    """Katz-style backoff: use the most specific level with at least
    min_support observations for the context, else fall back."""
    V = sorted(counts["c4"].keys())
    if not V:
        return None, {}, None
    levels = level_probs(counts, player, prev2, prev1, hp_b, gold_b, V)
    supports = [
        ("L0", counts["c0t"].get((player, prev2, prev1), 0)),
        ("L1", counts["c1t"].get((player, prev1), 0)),
        ("L2", counts["c2t"].get(player, 0)),
        ("L3", counts["c3t"].get(prev1, 0) if prev1 != "unknown" else 0),
        ("L4", counts["c4t"]),
    ]
    for lv, tot in supports:
        if tot >= min_support and levels.get(lv) is not None:
            dist = levels[lv]
            best = max(dist.keys(), key=lambda k: (dist[k], k))
            return best, dist, lv
    return None, {}, None


# Model variants: name -> ("interp", weights) or ("backoff", min_support)
VARIANTS = {
    "P_per_player": ("interp", {"L2": 1.0}),
    "T_global_transition": ("interp", {"L3": 1.0}),
    "G_global": ("interp", {"L4": 1.0}),
    "C_full_interp": ("interp", {"L1": 0.4, "L2": 0.3, "L3": 0.2, "L4": 0.1}),
    "Ceq_equal": ("interp", {"L1": 0.25, "L2": 0.25, "L3": 0.25, "L4": 0.25}),
    "C_state": ("interp", {"L1": 0.3, "L2": 0.25, "L3": 0.15, "L4": 0.1,
                           "L5": 0.1, "L6": 0.1}),
    "C_2nd_order": ("interp", {"L0": 0.3, "L1": 0.3, "L2": 0.2, "L3": 0.1, "L4": 0.1}),
    "B_backoff": ("backoff", 3),
}


def main():
    trace = load_trace()
    moves = trace["moves"]
    players = {p["id"]: p["key"] for p in trace["players"]}
    rpos = round_positions(moves)
    for m in moves:
        m["_rpos"] = rpos[(m["season"], m["round_index"])]

    # test records: S4-S5, classifiable, in chronological order
    test = [m for m in moves if m["season"] in (4, 5) and m["semantic_kind"] != "unknown"]
    test.sort(key=lambda m: (m["_rpos"], m["player"]))
    assert len(test) == 83, f"expected 83 test records, got {len(test)}"

    # previous move per (player) by round position
    prev_map = {}   # (player, rpos) -> move in previous round
    prev2_map = {}  # (player, rpos) -> move two rounds back
    by_player = defaultdict(list)
    for m in moves:
        by_player[m["player"]].append(m)
    for p, seq in by_player.items():
        seq.sort(key=lambda m: m["_rpos"])
        for i, m in enumerate(seq):
            if i >= 1:
                prev_map[(p, m["_rpos"])] = seq[i - 1]
            if i >= 2:
                prev2_map[(p, m["_rpos"])] = seq[i - 2]

    # counts per round position (prefix = all moves with smaller rpos)
    counts_by_rpos = {}
    for rp in sorted(set(m["_rpos"] for m in moves)):
        prefix = [m for m in moves if m["_rpos"] < rp]
        counts_by_rpos[rp] = build_counts(prefix)

    results = {}
    detail = []  # per-record rows for the main model
    for name, (kind, spec) in VARIANTS.items():
        hits = 0
        rows = []
        for m in test:
            rp = m["_rpos"]
            counts = counts_by_rpos[rp]
            prev1 = prev_map.get((m["player"], rp))
            prev2 = prev2_map.get((m["player"], rp))
            pk1 = prev1["semantic_kind"] if prev1 else "unknown"
            pk2 = prev2["semantic_kind"] if prev2 else "unknown"
            hp_b = hp_bin(m["hp_start"])
            gold_b = gold_bin(m["gold_start"])
            if kind == "interp":
                pred, dist, _ = predict_interp(counts, m["player"], pk2, pk1, hp_b, gold_b, spec)
                used = None
            else:
                pred, dist, used = predict_backoff(counts, m["player"], pk2, pk1, hp_b, gold_b, spec)
            true = m["semantic_kind"]
            ok = (pred == true)
            hits += 1 if ok else 0
            unguessable = true not in counts["c4"]
            rows.append({"season": m["season"], "round": m["round_label"],
                         "player": players[m["player"]], "prev_kind": pk1,
                         "prev2_kind": pk2, "true": true, "pred": pred,
                         "correct": ok, "unguessable": unguessable,
                         "n_candidates": len(counts["c4"]),
                         "top3": sorted(dist.items(), key=lambda kv: -kv[1])[:3] if dist else [],
                         "level_used": used})
        results[name] = {"hits": hits, "n": len(test), "rows": rows}
        if name == "C_full_interp":
            detail = rows

    # random baseline: mean of 1/|candidates| over the test records
    rand = sum(1.0 / r["n_candidates"] for r in detail) / len(detail)
    unguessable_n = sum(1 for r in detail if r["unguessable"])
    print(f"test n = {len(test)}; unguessable (true kind never seen in prefix) = {unguessable_n}; ceiling = {len(test) - unguessable_n}")
    print(f"random baseline (mean 1/|candidates|) = {rand:.4f}  (~{rand * len(test):.1f}/{len(test)})")
    print()
    print(f"{'variant':<22}{'hits':>6}  {'pct':>6}  vs formula 1/83  vs per-player 23/83")
    for name in VARIANTS:
        h = results[name]["hits"]
        print(f"{name:<22}{h:>6}  {h / 83 * 100:>5.1f}%  {h - 1:+d} vs formula, {h - 23:+d} vs per-player")

    # main model breakdowns
    main = results["C_full_interp"]["rows"]
    print()
    print("== C_full_interp by season ==")
    for s in (4, 5):
        rs = [r for r in main if r["season"] == s]
        print(f"  S{s}: {sum(r['correct'] for r in rs)}/{len(rs)}")
    print("== C_full_interp by player (hits / n) ==")
    for p in sorted({r["player"] for r in main}):
        rs = [r for r in main if r["player"] == p]
        print(f"  {p:<6} {sum(r['correct'] for r in rs)}/{len(rs)}")
    print("== C_full_interp misses by true kind ==")
    miss = Counter(r["true"] for r in main if not r["correct"])
    for k, v in miss.most_common():
        print(f"  {k:<18} missed {v}")
    print("== C_full_interp: what did it predict when wrong? (pred kind) ==")
    wrong_pred = Counter(r["pred"] for r in main if not r["correct"])
    for k, v in wrong_pred.most_common():
        print(f"  predicted {k:<18} {v} times (wrong)")

    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "results.json"), "w") as f:
        json.dump({"random_baseline": rand, "unguessable": unguessable_n,
                   "ceiling": len(test) - unguessable_n,
                   "variants": {n: {"hits": v["hits"], "n": v["n"]} for n, v in results.items()},
                   "per_record_main": main,
                   "per_record_all": {n: v["rows"] for n, v in results.items()}},
                  f, indent=1, ensure_ascii=False)
    print()
    print("saved:", os.path.join(OUTDIR, "results.json"))


if __name__ == "__main__":
    main()
