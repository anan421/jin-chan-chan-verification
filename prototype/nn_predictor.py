"""Neural-network predictor prototype (loop/nn-prototype).

A small neural network (MLP, scikit-learn) learns from the trace and
predicts each player's next action kind. It is tested on the SAME 83
classifiable S4-S5 records the formula is tested on, so the scores are
directly comparable: formula 1/83, per-player rule 23/83.

Walk-forward discipline (same as backtest.py):
  - train on S1-S3 only, test on S4-S5 only;
  - every feature for a record uses only the trace prefix before that
    record's round (plus the record's own pre-move state fields
    hp_start / gold_start, which the prefix determines);
  - hyperparameters are picked on S3 (train S1-S2, validate S3), never
    on S4-S5;
  - the class vocabulary is the kinds present in the training split.

The live model is untouched: this script only reads
traces/trace-latest.json and writes runs/nn-prototype-2026-11-21/.

  python3 prototype/nn_predictor.py [--out DIR]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check  # noqa: E402  (repo rule resolver, for the banned-kind filter)

TRACE = Path("traces/trace-latest.json")
RANDOM_STATE = 0


# ---------------------------------------------------------------- data
def load_trace():
    with open(TRACE, encoding="utf-8") as f:
        return json.load(f)


def rounds_of(trace):
    """[(season, round_index)] in order, with the season's round count."""
    out = []
    for s in sorted(trace["seasons"], key=lambda x: x["season"]):
        for rnd in range(1, s["rounds"] + 1):
            out.append((s["season"], rnd))
    return out


def prefix_moves(moves, season, rnd):
    return [m for m in moves
            if (m["season"], m["round_index"]) < (season, rnd)]


def banned_kinds(trace, date, pid):
    base, overlays = check.resolve_rules(trace["rules"], date, pid)
    banned = set()
    if base is not None:
        banned |= set(base["params"].get("banned_action_kinds", []))
    for ov in overlays:
        banned |= set(ov["params"].get("banned_action_kinds", []))
    return banned


# ------------------------------------------------------------- features
class FeatureBuilder:
    """One feature row per (prefix, record). All inputs are prefix-only
    except the record's own pre-move state (hp_start, gold_start,
    population, win_streak, roster_stars), which the prefix fixes."""

    def __init__(self, vocab, versions):
        self.vocab = list(vocab)          # known kinds, sorted
        self.kidx = {k: i for i, k in enumerate(self.vocab)}
        self.versions = list(versions)
        self.vidx = {v: i for i, v in enumerate(self.versions)}
        self.n_player = 18

    @property
    def dim(self):
        v = len(self.vocab)
        return (self.n_player + 2 + 2 + 4 + v + v + v
                + len(self.versions) + 2 + 3)

    def chain_state(self, prefix):
        """player -> (hp, gold) after their last prefix move."""
        state = {}
        for m in prefix:
            state[m["player"]] = (m["hp_start"] + m["hp_delta"],
                                  m["gold_start"] + m["gold_delta"])
        return state

    def build(self, prefix, rec):
        pid = rec["player"]
        mine = [m for m in prefix if m["player"] == pid]
        state = self.chain_state(prefix)
        feats = []

        # 1. player one-hot
        oh = [0.0] * self.n_player
        oh[pid] = 1.0
        feats += oh
        # 2. pre-move state
        feats += [rec["hp_start"] / 100.0, rec["gold_start"] / 100.0]
        # 3. hp/gold percentile among the 18 players' current state
        hps = sorted(h for h, _ in state.values())
        golds = sorted(g for _, g in state.values())
        cur_hp, cur_gold = state.get(pid, (rec["hp_start"],
                                           rec["gold_start"]))
        feats += [hps.index(cur_hp) / max(1, len(hps) - 1),
                  golds.index(cur_gold) / max(1, len(golds) - 1)]
        # 4. recent trend: last-3 mean and last deltas
        last3 = mine[-3:]
        feats += [
            (sum(m["hp_delta"] for m in last3) / len(last3) / 10.0
             if last3 else 0.0),
            (sum(m["gold_delta"] for m in last3) / len(last3) / 10.0
             if last3 else 0.0),
            (mine[-1]["hp_delta"] / 10.0 if mine else 0.0),
            (mine[-1]["gold_delta"] / 10.0 if mine else 0.0),
        ]
        # 5. player's last kind one-hot
        last_oh = [0.0] * len(self.vocab)
        if mine:
            lk = mine[-1].get("semantic_kind")
            if lk in self.kidx:
                last_oh[self.kidx[lk]] = 1.0
        feats += last_oh
        # 6. per-player kind frequency over the prefix
        pf = [0.0] * len(self.vocab)
        pc = Counter(m.get("semantic_kind") for m in mine)
        tot = sum(pc[k] for k in self.vocab)
        for k in self.vocab:
            pf[self.kidx[k]] = pc[k] / tot if tot else 0.0
        feats += pf
        # 7. global kind frequency over the prefix
        gf = [0.0] * len(self.vocab)
        gc = Counter(m.get("semantic_kind") for m in prefix)
        tot = sum(gc[k] for k in self.vocab)
        for k in self.vocab:
            gf[self.kidx[k]] = gc[k] / tot if tot else 0.0
        feats += gf
        # 8. rules version one-hot
        voh = [0.0] * len(self.versions)
        if rec["rules_version"] in self.vidx:
            voh[self.vidx[rec["rules_version"]]] = 1.0
        feats += voh
        # 9. season / round
        feats += [rec["season"] / 5.0, rec["round_index"] / 7.0]
        # 10. state fields
        feats += [rec["population"] / 10.0,
                  min(rec["win_streak"], 5) / 5.0,
                  rec["roster_stars"] / 5.0]
        return np.array(feats, dtype=float)

    def allowed(self, trace, prefix, rec):
        """Candidate kinds: seen in the prefix, known to the model,
        not banned by the rules in effect (same discipline as the
        formula's candidate set in backtest.py)."""
        seen = {m.get("semantic_kind") for m in prefix} - {"unknown"}
        allowed = [k for k in self.vocab
                   if k in seen
                   and k not in banned_kinds(trace, rec["date"],
                                             rec["player"])]
        return allowed or list(self.vocab)


def build_split(trace, fb, seasons):
    """All records in `seasons` with a non-empty prefix.
    Returns (X, y, meta) with y = semantic_kind or None for unknown."""
    moves = trace["moves"]
    X, y, meta = [], [], []
    for season, rnd in rounds_of(trace):
        if season not in seasons:
            continue
        prefix = prefix_moves(moves, season, rnd)
        if not prefix:
            continue
        for rec in [m for m in moves
                    if m["season"] == season and m["round_index"] == rnd]:
            X.append(fb.build(prefix, rec))
            y.append(rec.get("semantic_kind") or "unknown")
            meta.append({
                "season": season, "round": rnd,
                "player": rec["player"],
                "key": next(p["key"] for p in trace["players"]
                            if p["id"] == rec["player"]),
                "recorded": rec.get("semantic_kind") or "unknown",
                "allowed": fb.allowed(trace, prefix, rec),
            })
    return np.array(X), y, meta


# ------------------------------------------------------------ baselines
def mode_baseline(meta, prefix_kinds_per_player, prefix_kinds_global):
    """Per-player mode and global mode, same prefix rule.
    Tie-break: most recent occurrence, then alphabetical."""
    out_pp, out_gl = [], []
    for m in meta:
        cands = m["allowed"]
        pc = prefix_kinds_per_player[m["player"]]
        gc = prefix_kinds_global
        def pick(counter):
            best = sorted(cands,
                          key=lambda k: (-counter.get(k, 0), k))
            return best[0] if best else None
        out_pp.append(pick(pc))
        out_gl.append(pick(gc))
    return out_pp, out_gl


def prefix_kind_counts(trace, season, rnd):
    moves = trace["moves"]
    prefix = prefix_moves(moves, season, rnd)
    per_player = defaultdict(Counter)
    glob = Counter()
    for m in prefix:
        k = m.get("semantic_kind")
        if k and k != "unknown":
            per_player[m["player"]][k] += 1
            glob[k] += 1
    return per_player, glob


# --------------------------------------------------------------- models
def make_model(spec):
    from sklearn.neural_network import MLPClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    kind = spec[0]
    if kind == "mlp":
        _, hidden, alpha = spec
        return make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=hidden, alpha=alpha,
                          max_iter=2000, random_state=RANDOM_STATE))
    if kind == "logreg":
        _, c, balanced = spec
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(C=c, max_iter=2000,
                               class_weight="balanced" if balanced
                               else None,
                               random_state=RANDOM_STATE))
    if kind == "hgb":
        _, depth, lr, iters = spec
        return HistGradientBoostingClassifier(
            max_depth=depth, learning_rate=lr, max_iter=iters,
            random_state=RANDOM_STATE)
    raise ValueError(spec)


def predict_restricted(model, vocab, X, allowed_list):
    """argmax over predict_proba, restricted to each row's allowed set."""
    proba = model.predict_proba(X)
    classes = list(model.classes_) if hasattr(model, "classes_") \
        else list(model[-1].classes_)
    col = {c: i for i, c in enumerate(classes)}
    preds = []
    for row, allowed in zip(proba, allowed_list):
        best, best_p = None, -1.0
        for k in allowed:
            p = row[col[k]] if k in col else 0.0
            if p > best_p:
                best, best_p = k, p
        preds.append(best)
    return preds


def m1_score(preds, meta):
    cls = [i for i, m in enumerate(meta) if m["recorded"] != "unknown"]
    hits = sum(1 for i in cls if preds[i] == meta[i]["recorded"])
    return hits, len(cls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/nn-prototype-2026-11-21")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    trace = load_trace()
    moves = trace["moves"]
    versions = sorted({m["rules_version"] for m in moves})

    # ---- vocabularies per split (no leakage: vocab = kinds in train)
    def vocab_for(seasons):
        return sorted({m.get("semantic_kind") for m in moves
                       if m["season"] in seasons
                       and m.get("semantic_kind") != "unknown"})

    # ================= validation: train S1-S2, validate S3 ============
    fb_v = FeatureBuilder(vocab_for({1, 2}), versions)
    Xtr, ytr, mtr = build_split(trace, fb_v, {1, 2})
    Xva, yva, mva = build_split(trace, fb_v, {3})
    keep_tr = [i for i, y in enumerate(ytr) if y != "unknown"]
    keep_va = [i for i, y in enumerate(yva) if y != "unknown"]
    Xtr_c, ytr_c = Xtr[keep_tr], [ytr[i] for i in keep_tr]
    print(f"validation: train S1-S2 classifiable n={len(ytr_c)} "
          f"classes={len(set(ytr_c))} | S3 classifiable n={len(keep_va)}")

    # harness baselines on the S3 validation records
    pp_c, gl_c = [], []
    for m in mva:
        per_player, glob = prefix_kind_counts(trace, m["season"],
                                              m["round"])
        pc = Counter({k: v for k, v in per_player[m["player"]].items()
                      if k in fb_v.vocab})
        gc = Counter({k: v for k, v in glob.items()
                      if k in fb_v.vocab})
        def pick(counter, allowed):
            return sorted(allowed,
                          key=lambda k: (-counter.get(k, 0), k))[0]
        pp_c.append(pick(pc, m["allowed"]))
        gl_c.append(pick(gc, m["allowed"]))
    print(f"validation baselines S3: per-player mode "
          f"{sum(1 for i in keep_va if pp_c[i] == mva[i]['recorded'])}/"
          f"{len(keep_va)} | global mode "
          f"{sum(1 for i in keep_va if gl_c[i] == mva[i]['recorded'])}/"
          f"{len(keep_va)}")

    specs = [
        ("mlp", (16,), 1.0), ("mlp", (32,), 1.0),
        ("mlp", (16,), 0.1), ("mlp", (16,), 10.0),
        ("mlp", (16, 8), 1.0),
        ("logreg", 1.0, True), ("logreg", 0.1, True),
        ("hgb", 2, 0.1, 100), ("hgb", 3, 0.05, 200),
    ]
    val_results = []
    for spec in specs:
        model = make_model(spec)
        model.fit(Xtr_c, ytr_c)
        preds = predict_restricted(model, fb_v.vocab, Xva,
                                   [m["allowed"] for m in mva])
        hits, n = m1_score(preds, mva)
        distinct = len(set(preds[i] for i in keep_va))
        val_results.append({"spec": str(spec), "hits": hits, "n": n,
                            "distinct_predicted": distinct})
        print(f"  val {spec}: {hits}/{n} distinct={distinct}")
    best = max(val_results, key=lambda r: (r["hits"],
                                           r["distinct_predicted"]))
    print("validation winner:", best)

    # ================= final: retrain winner on S1-S3, test S4-S5 ====
    fb = FeatureBuilder(vocab_for({1, 2, 3}), versions)
    Xtr, ytr, mtr = build_split(trace, fb, {1, 2, 3})
    Xte, yte, mte = build_split(trace, fb, {4, 5})
    keep_tr = [i for i, y in enumerate(ytr) if y != "unknown"]
    Xtr_c, ytr_c = Xtr[keep_tr], [ytr[i] for i in keep_tr]
    print(f"final: train S1-S3 classifiable n={len(ytr_c)} "
          f"classes={len(set(ytr_c))} features={Xtr.shape[1]} | "
          f"test S4-S5 n={len(yte)} "
          f"classifiable={sum(1 for y in yte if y != 'unknown')}")

    # ceiling: classifiable test records whose kind was already seen
    # in the prefix before their round
    seen_before = set()
    ceiling = 0
    for (season, rnd) in rounds_of(trace):
        if season < 4:
            seen_before |= {m.get("semantic_kind") for m in moves
                            if m["season"] == season
                            and m["round_index"] == rnd} - {"unknown"}
            continue
        for m in [x for x in moves if x["season"] == season
                  and x["round_index"] == rnd]:
            if m.get("semantic_kind") not in ("unknown", None) \
                    and m["semantic_kind"] in seen_before:
                ceiling += 1
        seen_before |= {m.get("semantic_kind") for m in moves
                        if m["season"] == season
                        and m["round_index"] == rnd} - {"unknown"}
    print(f"ceiling (kind already seen in prefix): {ceiling}/83")

    # test-set harness baselines
    pp_te, gl_te = [], []
    for m in mte:
        per_player, glob = prefix_kind_counts(trace, m["season"],
                                              m["round"])
        pc = Counter({k: v for k, v in per_player[m["player"]].items()
                      if k in fb.vocab})
        gc = Counter({k: v for k, v in glob.items() if k in fb.vocab})
        def pick(counter, allowed):
            return sorted(allowed,
                          key=lambda k: (-counter.get(k, 0), k))[0]
        pp_te.append(pick(pc, m["allowed"]))
        gl_te.append(pick(gc, m["allowed"]))
    pp_hits, n83 = m1_score(pp_te, mte)
    gl_hits, _ = m1_score(gl_te, mte)
    print(f"test baselines: per-player mode {pp_hits}/{n83} | "
          f"global mode {gl_hits}/{n83}")

    # winner model, retrained on all of S1-S3
    winner_spec = eval(best["spec"])
    model = make_model(winner_spec)
    model.fit(Xtr_c, ytr_c)
    preds = predict_restricted(model, fb.vocab, Xte,
                               [m["allowed"] for m in mte])
    hits, n = m1_score(preds, mte)
    from collections import Counter as C
    dist = C(preds[i] for i in range(len(preds))
             if mte[i]["recorded"] != "unknown")
    print(f"TEST winner {winner_spec}: {hits}/{n} "
          f"distinct={len(dist)} dist={dict(dist)}")

    # also score every validation-grid spec on the test set, for the
    # report's honest comparison (they were all picked without S4-S5)
    test_all = []
    for spec in specs:
        mdl = make_model(spec)
        mdl.fit(Xtr_c, ytr_c)
        pr = predict_restricted(mdl, fb.vocab, Xte,
                                [m["allowed"] for m in mte])
        h, _ = m1_score(pr, mte)
        d = len(set(pr[i] for i in range(len(pr))
                  if mte[i]["recorded"] != "unknown"))
        test_all.append({"spec": str(spec), "hits": h, "n": n,
                         "distinct_predicted": d})
        print(f"  test {spec}: {h}/{n} distinct={d}")

    records = []
    for i, m in enumerate(mte):
        records.append({**m, "predicted": preds[i],
                        "hit": preds[i] == m["recorded"]
                        and m["recorded"] != "unknown",
                        "per_player_mode": pp_te[i],
                        "global_mode": gl_te[i]})
    report = {
        "trace_sha256": trace["meta"]["trace_sha256"],
        "vocab_train": fb.vocab,
        "n_features": int(Xtr.shape[1]),
        "train_n": len(ytr_c),
        "train_class_counts": dict(Counter(ytr_c)),
        "validation_S3": val_results,
        "validation_winner": best,
        "test_ceiling_seen_in_prefix": ceiling,
        "test_baselines": {"per_player_mode": pp_hits,
                           "global_mode": gl_hits, "n": n83},
        "test_all_specs": test_all,
        "test_winner": {"spec": str(winner_spec), "hits": hits, "n": n,
                        "distribution": dict(dist)},
        "records": records,
    }
    with open(out / "nn-results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("wrote", out / "nn-results.json")


if __name__ == "__main__":
    main()
