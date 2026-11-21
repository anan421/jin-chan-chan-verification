#!/usr/bin/env python3
"""Round 2 composite: transition model (base, from history) + Agent (fact adjustment).

Design (first principles, pre-specified BEFORE scoring):
- The transition model is the best history-only predictor (27/83), but it is
  structurally blind on kinds that have never appeared in the prefix
  (24 records are unguessable for it; ceiling 59/83).
- The Agent reads facts and can predict kinds history has never seen
  (search-first got 7/9 first-appearance kinds on its 24-question subset;
  plain Agent reasoned 3 energy questions that history could not see).
- Combination is a DECISION RULE, not a multiplication. Rounds 7 and 10
  proved multiplication crushes the prior (the utility spread is far wider
  than the prior spread, so the utility dominates). The Agent does not output
  a probability distribution anyway, so multiplication is not well-defined.
- Routing signals are observable before the answer: whether the Agent's
  predicted kind has appeared in the prefix, and whether it is among the
  transition model's top-3 candidates.

Primary rule (R-primary), from the task's two suggested mechanisms:
  1. If the Agent's predicted kind has NEVER appeared in the prefix
     (first-appearance kind; the transition model has zero counts for it):
     take the Agent. [Facts point to something history cannot see -> override.]
  2. Else if the Agent's predicted kind is among the transition model's top-3:
     take the Agent. [Agent picks among history-plausible candidates.]
  3. Else: take the transition model's top-1. [Agent's guess contradicts
     history and is not a first-appearance kind -> default to history.]

Conservative rule (R-conservative), for comparison:
  1. If the Agent's predicted kind has never appeared in the prefix: take Agent.
  2. Else: take the transition model's top-1.

Both rules are fixed BEFORE scoring. No threshold is tuned on the test set.
The headline is R-primary vs plain Agent alone (30/83).
"""
import json
import os
from collections import Counter

SHARED = "/home/hatch/workspace/verification"
TRANS_RESULTS = os.path.join(SHARED, "runs/transition-prototype-2026-11-21/results.json")
AGENT_PRED = os.path.join(SHARED, "runs/agent-prototype-2026-11-21/predictions.jsonl")
AGENT_ANS = os.path.join(SHARED, "runs/agent-prototype-2026-11-21/answers.jsonl")
TRACE = os.path.join(SHARED, "traces/trace-latest.json")
OUTDIR = "runs/composite-round2-2026-11-22"
OUT = os.path.join(OUTDIR, "results.json")


def main():
    # --- load transition ---
    trans = json.load(open(TRANS_RESULTS))
    t_main = trans["per_record_main"]
    assert len(t_main) == 83, len(t_main)
    # --- load agent ---
    agent_pred = [json.loads(l) for l in open(AGENT_PRED) if l.strip()]
    agent_ans = [json.loads(l) for l in open(AGENT_ANS) if l.strip()]
    assert len(agent_pred) == 83 and len(agent_ans) == 83
    # --- join on (season, round_label, player) ---
    t_by_key = {(r["season"], r["round"], r["player"]): r for r in t_main}
    a_by_key = {(r["season"], r["round_label"], r["player"]): r for r in agent_pred}
    ans_by_key = {(r["season"], r["round_label"], r["player"]): r for r in agent_ans}
    assert set(t_by_key) == set(a_by_key) == set(ans_by_key), "key mismatch"
    for k in t_by_key:
        assert t_by_key[k]["true"] == ans_by_key[k]["semantic_kind"], (
            k, t_by_key[k]["true"], ans_by_key[k]["semantic_kind"])
    # --- prefix kind sets from trace ---
    trace = json.load(open(TRACE))
    moves = trace["moves"]
    label_to_idx = {}
    for m in moves:
        label_to_idx[(m["season"], m["round_label"])] = m["round_index"]
    rounds = sorted(set((m["season"], m["round_index"], m["round_label"]) for m in moves))
    kinds_by_round = {}
    for (s, ri, rl) in rounds:
        kinds_by_round[(s, ri, rl)] = set(
            m["semantic_kind"] for m in moves
            if m["season"] == s and m["round_index"] == ri
            and m["semantic_kind"] != "unknown")
    prefix_kinds = {}
    seen = set()
    for (s, ri, rl) in rounds:
        prefix_kinds[(s, ri, rl)] = set(seen)
        seen |= kinds_by_round[(s, ri, rl)]
    # --- per-question composite ---
    records = []
    for k in sorted(t_by_key.keys()):
        season, rnd, player = k
        t = t_by_key[k]
        a = a_by_key[k]
        true = t["true"]
        T = t["pred"]
        top3 = [kind for kind, _ in t["top3"]]
        A = a["predicted_kind"]
        conf = a["confidence"]
        ri = label_to_idx[(season, rnd)]
        pk = prefix_kinds[(season, ri, rnd)]
        A_in_history = A in pk
        A_in_top3 = A in top3
        # Guard: an "unknown" Agent guess can never be right; fall back to T.
        if A == "unknown":
            Rp, R_rule = T, "T-default(A-unknown)"
            Rc, Rc_rule = T, "T-default(A-unknown)"
        else:
            if not A_in_history:
                Rp, R_rule = A, "A-first-appearance"
            elif A_in_top3:
                Rp, R_rule = A, "A-in-top3"
            else:
                Rp, R_rule = T, "T-default"
            if not A_in_history:
                Rc, Rc_rule = A, "A-first-appearance"
            else:
                Rc, Rc_rule = T, "T-default"
        records.append({
            "season": season, "round": rnd, "player": player,
            "true": true, "unguessable": t["unguessable"],
            "T": T, "T_top3": top3, "T_correct": (T == true),
            "A": A, "A_conf": conf, "A_correct": (A == true),
            "A_in_history": A_in_history, "A_in_top3": A_in_top3,
            "R_primary": Rp, "R_primary_correct": (Rp == true), "R_primary_rule": R_rule,
            "R_cons": Rc, "R_cons_correct": (Rc == true), "R_cons_rule": Rc_rule,
        })
    # --- scores ---
    def score(field):
        return sum(1 for r in records if r[field])
    n = len(records)
    summary = {
        "n": n,
        "transition": score("T_correct"),
        "agent": score("A_correct"),
        "R_primary": score("R_primary_correct"),
        "R_conservative": score("R_cons_correct"),
        "unguessable_n": sum(1 for r in records if r["unguessable"]),
        "guessable_n": sum(1 for r in records if not r["unguessable"]),
        "transition_on_guessable": sum(1 for r in records if not r["unguessable"] and r["T_correct"]),
        "agent_on_guessable": sum(1 for r in records if not r["unguessable"] and r["A_correct"]),
        "transition_on_unguessable": sum(1 for r in records if r["unguessable"] and r["T_correct"]),
        "agent_on_unguessable": sum(1 for r in records if r["unguessable"] and r["A_correct"]),
        "R_primary_on_guessable": sum(1 for r in records if not r["unguessable"] and r["R_primary_correct"]),
        "R_primary_on_unguessable": sum(1 for r in records if r["unguessable"] and r["R_primary_correct"]),
        "R_cons_on_guessable": sum(1 for r in records if not r["unguessable"] and r["R_cons_correct"]),
        "R_cons_on_unguessable": sum(1 for r in records if r["unguessable"] and r["R_cons_correct"]),
        "both_correct": sum(1 for r in records if r["T_correct"] and r["A_correct"]),
        "T_only": sum(1 for r in records if r["T_correct"] and not r["A_correct"]),
        "A_only": sum(1 for r in records if r["A_correct"] and not r["T_correct"]),
        "neither": sum(1 for r in records if not r["T_correct"] and not r["A_correct"]),
        "R_primary_rule_counts": dict(Counter(r["R_primary_rule"] for r in records)),
        "R_primary_rule_correct": {rule: sum(1 for r in records if r["R_primary_rule"] == rule and r["R_primary_correct"]) for rule in set(r["R_primary_rule"] for r in records)},
        "R_cons_rule_counts": dict(Counter(r["R_cons_rule"] for r in records)),
        "R_cons_rule_correct": {rule: sum(1 for r in records if r["R_cons_rule"] == rule and r["R_cons_correct"]) for rule in set(r["R_cons_rule"] for r in records)},
        "A_in_history_false_n": sum(1 for r in records if not r["A_in_history"]),
        "A_in_top3_n": sum(1 for r in records if r["A_in_top3"]),
        "A_eq_T_n": sum(1 for r in records if r["A"] == r["T"]),
        "A_unknown_n": sum(1 for r in records if r["A"] == "unknown"),
    }
    # verify my prefix computation reproduces the transition "unguessable" flag
    mismatch = []
    for r in records:
        ri = label_to_idx[(r["season"], r["round"])]
        pk = prefix_kinds[(r["season"], ri, r["round"])]
        my_unguessable = r["true"] not in pk
        if my_unguessable != r["unguessable"]:
            mismatch.append((r["season"], r["round"], r["player"], r["true"], r["unguessable"], my_unguessable))
    summary["unguessable_flag_mismatch_n"] = len(mismatch)
    summary["unguessable_flag_mismatch"] = mismatch
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump({"summary": summary, "records": records}, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
