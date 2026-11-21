"""Online (re-train each round) NN variant + unrestricted baselines.

Follow-up to prototype/nn_predictor.py. Two corrections to the frozen
experiment:

1. The frozen NN was trained once on S1-S3, so its class vocabulary is
   the 20 kinds seen in S1-S3. But 48 of the 83 test records are kinds
   that NEVER appear in S1-S3 (stargate 15, energy 10, anthropic_ipo 8,
   r1 6, bis_rule 4, ...). The frozen NN's true ceiling is 35/83, not
   59/83. The formula's candidate set grows with the prefix, so the
   fair NN analog is to re-train at each round on the prefix so far
   (walk-forward, same as the formula's expectations). The model
   config is NOT re-tuned: MLP (16,) alpha=1.0 is the S3-validation
   winner from nn_predictor.py.

2. The harness baselines in nn_predictor.py were restricted to the
   same 20-kind vocab, so per-player mode scored 19/83 there, not the
   23/83 of round 10 (which uses the growing prefix). Here the
   baselines use the full prefix candidate set, like the formula.

Also: a feature ablation on the frozen S3 validation (which features
carry the signal?).

  python3 prototype/nn_online.py [--out DIR]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nn_predictor import (FeatureBuilder, build_split, load_trace,
                          make_model, m1_score, predict_restricted,
                          prefix_moves, rounds_of, banned_kinds)  # noqa: E402


def unrestricted_allowed(trace, prefix, rec):
    seen = {m.get("semantic_kind") for m in prefix} - {"unknown"}
    allowed = [k for k in sorted(seen)
               if k not in banned_kinds(trace, rec["date"], rec["player"])]
    return allowed or sorted(seen)


def mode_pick(counter, allowed, tie="alpha"):
    if tie == "alpha":
        return sorted(allowed, key=lambda k: (-counter.get(k, 0), k))[0]
    raise ValueError(tie)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/nn-prototype-2026-11-21")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    trace = load_trace()
    moves = trace["moves"]
    versions = sorted({m["rules_version"] for m in moves})

    # ---- unrestricted baselines on the test window -------------------
    base_pp, base_gl, meta_all = [], [], []
    for season, rnd in rounds_of(trace):
        if season < 4:
            continue
        prefix = prefix_moves(moves, season, rnd)
        if not prefix:
            continue
        per_player = {}
        glob = Counter()
        for m in prefix:
            k = m.get("semantic_kind")
            if k and k != "unknown":
                per_player.setdefault(m["player"], Counter())[k] += 1
                glob[k] += 1
        for rec in [m for m in moves
                    if m["season"] == season and m["round_index"] == rnd]:
            allowed = unrestricted_allowed(trace, prefix, rec)
            base_pp.append(mode_pick(per_player.get(rec["player"],
                                                    Counter()), allowed))
            base_gl.append(mode_pick(glob, allowed))
            meta_all.append({
                "season": season, "round": rnd,
                "player": rec["player"],
                "key": next(p["key"] for p in trace["players"]
                            if p["id"] == rec["player"]),
                "recorded": rec.get("semantic_kind") or "unknown",
                "allowed": allowed,
            })
    pp_hits, n83 = m1_score(base_pp, meta_all)
    gl_hits, _ = m1_score(base_gl, meta_all)
    print(f"unrestricted baselines: per-player mode {pp_hits}/{n83} | "
          f"global mode {gl_hits}/{n83}")

    # ---- online NN: re-train at each test round on the prefix -------
    specs = [("mlp", (16,), 1.0), ("mlp", (16,), 0.1),
             ("logreg", 1.0, True)]
    online_preds = {str(s): [] for s in specs}
    online_meta = []
    for season, rnd in rounds_of(trace):
        if season < 4:
            continue
        prefix = prefix_moves(moves, season, rnd)
        if not prefix:
            continue
        vocab = sorted({m.get("semantic_kind") for m in prefix
                        if m.get("semantic_kind") != "unknown"})
        fb = FeatureBuilder(vocab, versions)
        # training rows: every classifiable prefix move, features from
        # ITS OWN round prefix (walk-forward within the prefix too)
        Xtr, ytr, _ = [], [], []
        for s2, r2 in rounds_of(trace):
            if (s2, r2) >= (season, rnd):
                break
            p2 = prefix_moves(moves, s2, r2)
            if not p2:
                continue
            for rec in [m for m in moves
                        if m["season"] == s2 and m["round_index"] == r2]:
                k = rec.get("semantic_kind")
                if k and k != "unknown":
                    Xtr.append(fb.build(p2, rec))
                    ytr.append(k)
        Xtr = np.array(Xtr)
        test_recs = [m for m in moves
                     if m["season"] == season and m["round_index"] == rnd]
        Xte = np.array([fb.build(prefix, r) for r in test_recs])
        allowed = [unrestricted_allowed(trace, prefix, r)
                   for r in test_recs]
        for spec in specs:
            model = make_model(spec)
            model.fit(Xtr, ytr)
            online_preds[str(spec)].extend(
                predict_restricted(model, vocab, Xte, allowed))
        for rec in test_recs:
            online_meta.append({
                "season": season, "round": rnd,
                "player": rec["player"],
                "key": next(p["key"] for p in trace["players"]
                            if p["id"] == rec["player"]),
                "recorded": rec.get("semantic_kind") or "unknown",
            })
        print(f"  online round S{season} R{rnd}: train n={len(ytr)} "
              f"vocab={len(vocab)}")
    online_results = {}
    for spec in specs:
        preds = online_preds[str(spec)]
        hits, n = m1_score(preds, online_meta)
        distinct = len(set(preds[i] for i in range(len(preds))
                         if online_meta[i]["recorded"] != "unknown"))
        online_results[str(spec)] = {"hits": hits, "n": n,
                                     "distinct": distinct}
        print(f"ONLINE {spec}: {hits}/{n} distinct={distinct} "
              f"dist={dict(Counter(preds))}")

    # ---- feature ablation on frozen S3 validation --------------------
    fb_v = FeatureBuilder(
        sorted({m.get("semantic_kind") for m in moves
                if m["season"] in (1, 2)
                and m.get("semantic_kind") != "unknown"}),
        versions)
    Xtr, ytr, _ = build_split(trace, fb_v, {1, 2})
    Xva, yva, mva = build_split(trace, fb_v, {3})
    keep_tr = [i for i, y in enumerate(ytr) if y != "unknown"]
    Xtr_c, ytr_c = Xtr[keep_tr], [ytr[i] for i in keep_tr]
    V = len(fb_v.vocab)
    # column layout: player 0-17, state 18-19, pct 20-21, trend 22-25,
    # last-kind 26..26+V-1, player-freq, global-freq, versions, s/r, state3
    groups = {
        "player_onehot": list(range(0, 18)),
        "state_hp_gold": list(range(18, 20)),
        "percentiles": list(range(20, 22)),
        "trend": list(range(22, 26)),
        "last_kind": list(range(26, 26 + V)),
        "player_freq": list(range(26 + V, 26 + 2 * V)),
        "global_freq": list(range(26 + 2 * V, 26 + 3 * V)),
        "rules_version": list(range(26 + 3 * V, 34 + 3 * V)),
        "season_round": list(range(34 + 3 * V, 36 + 3 * V)),
        "state3": list(range(36 + 3 * V, 39 + 3 * V)),
    }
    all_cols = sorted(c for cols in groups.values() for c in cols)
    ablations = {
        "full": all_cols,
        "no_player_freq": [c for c in all_cols
                           if c not in groups["player_freq"]],
        "no_freq_vectors": [c for c in all_cols
                            if c not in groups["player_freq"]
                            and c not in groups["global_freq"]],
        "player_plus_freq_only": (groups["player_onehot"]
                                  + groups["player_freq"]
                                  + groups["global_freq"]),
        "state_only": (groups["state_hp_gold"] + groups["percentiles"]
                       + groups["trend"] + groups["season_round"]
                       + groups["state3"]),
        "no_player_identity": [c for c in all_cols
                               if c not in groups["player_onehot"]
                               and c not in groups["player_freq"]
                               and c not in groups["last_kind"]],
    }
    abl_results = {}
    for name, cols in ablations.items():
        model = make_model(("mlp", (16,), 1.0))
        model.fit(Xtr_c[:, cols], ytr_c)
        preds = predict_restricted(model, fb_v.vocab, Xva[:, cols],
                                   [m["allowed"] for m in mva])
        hits, n = m1_score(preds, mva)
        abl_results[name] = {"hits": hits, "n": n, "n_cols": len(cols)}
        print(f"  ablation {name}: {hits}/{n} (cols={len(cols)})")

    report = {
        "unrestricted_baselines": {
            "per_player_mode": pp_hits, "global_mode": gl_hits, "n": n83},
        "online": online_results,
        "online_records": [
            {**m, **{f"pred_{k}": v[i]
                     for k, v in online_preds.items()}}
            for i, m in enumerate(online_meta)],
        "ablation_S3": abl_results,
    }
    with open(out / "nn-online.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("wrote", out / "nn-online.json")


if __name__ == "__main__":
    main()
