#!/usr/bin/env python3
"""Gemini A/B/C Phase 1 Task 1.3: second independent scorer.

Re-implemented from scratch (no import from eval_runner.py). Reads the locked
clean set and the nine prediction files, and recomputes: per-group per-batch
scores, total accuracy, per-class hit rates, pooled McNemar (exact two-sided
binomial), per-batch McNemar, noise band, threshold, gain, the six adoption
conditions (protocol section 6), the 49-question leakage sensitivity subset,
and the section 6.2 provisional/discard check.

Usage: python3 score_check.py [out.json]
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "runs", "gemini-abc-2026-11-25")
KINDS = ["model_release", "infra_capex", "capital_deal",
         "chip_supply", "policy_regulatory", "hold_defend"]
SENSITIVITY_DROP = {"Q012", "Q021", "Q025", "Q040", "Q054"}


def read(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def binom_pmf(n, k):
    return math.comb(n, k) * (0.5 ** n)


def mcnemar_exact(b, c):
    """Two-sided exact binomial p for discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    lo = min(b, c)
    p_lo = sum(binom_pmf(n, k) for k in range(0, lo + 1))
    return min(1.0, 2.0 * p_lo)


def group_scores(clean, preds_by_batch):
    """preds_by_batch: list of {qid: prediction} (3 batches)."""
    truth = {}
    for q in clean["questions"]:
        truth[q["question_id"]] = q["category"]
    totals = {}
    for cls in KINDS:
        totals[cls] = {"n": 0, "hits": [0, 0, 0]}
    for qid, cat in truth.items():
        totals[cat]["n"] += 1
    batch_correct = []
    for bi, preds in enumerate(preds_by_batch):
        ok = 0
        for qid, cat in truth.items():
            if preds.get(qid) == cat:
                ok += 1
                totals[cat]["hits"][bi] += 1
        batch_correct.append(ok)
    per_class = {}
    for cls in KINDS:
        n = totals[cls]["n"]
        hits = totals[cls]["hits"]
        per_class[cls] = {
            "n": n,
            "hits_per_batch": hits,
            "mean_hits": sum(hits) / 3.0,
            "mean_rate": (sum(hits) / 3.0) / n if n else 0.0,
        }
    mean_score = sum(batch_correct) / 3.0
    return {
        "batch_correct": batch_correct,
        "mean_correct": mean_score,
        "mean_accuracy": mean_score / len(truth),
        "per_class": per_class,
    }


def paired(b_preds, c_preds, truth, qids=None):
    """Pooled discordant counts over batches. b_preds/c_preds: lists of dicts."""
    b = c = 0
    win_qids = set()
    for bi in range(3):
        for qid in (qids or truth):
            bv = b_preds[bi].get(qid) == truth[qid]
            cv = c_preds[bi].get(qid) == truth[qid]
            if cv and not bv:
                b += 1
                win_qids.add(qid)
            elif bv and not cv:
                c += 1
    return {"b": b, "c": c, "p": mcnemar_exact(b, c),
            "win_qids": sorted(win_qids), "net": b - c}


def main():
    clean = read(os.path.join(HERE, "datasets", "clean_s4_s5.json"))
    truth = {q["question_id"]: q["category"] for q in clean["questions"]}
    groups = {}
    for g in ("A", "B", "C"):
        batches = []
        for n in (1, 2, 3):
            rows = read(os.path.join(RUN, f"{g}-batch{n}.json"))
            assert len(rows) == 54, f"{g}-batch{n} has {len(rows)} rows"
            assert {r["question_id"] for r in rows} == set(truth), f"{g}-batch{n} qids"
            batches.append({r["question_id"]: r["prediction"] for r in rows})
        groups[g] = batches

    res = {}
    for g in ("A", "B", "C"):
        res[g] = group_scores(clean, groups[g])
    a_scores = res["A"]["batch_correct"]
    noise_band = max(a_scores) - min(a_scores)
    res["noise_band"] = noise_band
    res["threshold"] = max(11, noise_band)

    # Pooled McNemar B vs C (all 54) and per-batch.
    paired_all = paired(groups["B"], groups["C"], truth)
    res["mcnemar_pooled"] = {k: v for k, v in paired_all.items()}
    res["mcnemar_per_batch"] = [
        _single(groups["B"][bi], groups["C"][bi], truth) for bi in range(3)
    ]
    # Exact per-qid win counts for condition 4.
    from collections import Counter
    win_cnt = Counter()
    for bi in range(3):
        for qid, cat in truth.items():
            if groups["C"][bi].get(qid) == cat and groups["B"][bi].get(qid) != cat:
                win_cnt[qid] += 1
    net = paired_all["net"]
    max_share = (max(win_cnt.values()) / net) if net > 0 and win_cnt else 0.0
    res["condition4_detail"] = {
        "distinct_win_qids": sorted(win_cnt),
        "win_counts_per_qid": dict(sorted(win_cnt.items())),
        "max_single_qid_share_of_net": max_share,
    }

    # Sensitivity subset: drop the 5 flagged questions, recompute B/C means.
    sub_qids = [q for q in truth if q not in SENSITIVITY_DROP]
    sub_truth = {q: truth[q] for q in sub_qids}
    sub_b = group_scores(
        {"questions": [{"question_id": q, "category": truth[q]} for q in sub_qids]},
        groups["B"],
    )
    sub_c = group_scores(
        {"questions": [{"question_id": q, "category": truth[q]} for q in sub_qids]},
        groups["C"],
    )
    sub_paired = paired(groups["B"], groups["C"], sub_truth, qids=sub_qids)
    sub_gain = sub_c["mean_correct"] - sub_b["mean_correct"]
    sub_weakest_b = min(v["mean_rate"] for v in sub_b["per_class"].values())
    sub_weakest_c = min(v["mean_rate"] for v in sub_c["per_class"].values())
    res["sensitivity_49"] = {
        "dropped": sorted(SENSITIVITY_DROP),
        "B_mean": sub_b["mean_correct"],
        "C_mean": sub_c["mean_correct"],
        "gain": sub_gain,
        "mcnemar": {k: v for k, v in sub_paired.items()},
        "weakest_B": sub_weakest_b,
        "weakest_C": sub_weakest_c,
        "B_per_class": sub_b["per_class"],
        "C_per_class": sub_c["per_class"],
    }

    gain = res["C"]["mean_correct"] - res["B"]["mean_correct"]
    res["gain_C_minus_B"] = gain
    weakest_b = min(v["mean_rate"] for v in res["B"]["per_class"].values())
    weakest_c = min(v["mean_rate"] for v in res["C"]["per_class"].values())
    res["weakest_B"] = weakest_b
    res["weakest_C"] = weakest_c
    thr = res["threshold"]
    # Condition 6: subset re-check of conditions 1-5 on 49 questions.
    sub_cond1 = bool(sub_gain > thr)
    sub_cond2 = bool(sub_paired["p"] < 0.05)
    sub_cond3 = bool(sub_gain >= 3)
    sub_win = {q for q in sub_paired["win_qids"]}
    sub_cond4 = len(sub_win) >= 2
    sub_cond5 = bool(sub_weakest_c >= sub_weakest_b)
    cond6 = sub_cond1 and sub_cond2 and sub_cond3 and sub_cond4 and sub_cond5
    cond4 = (len(win_cnt) >= 2) and (net <= 0 or max_share <= 0.5)
    conds = {
        "1_gain_gt_threshold": bool(gain > thr),
        "2_mcnemar_p_lt_0.05": bool(paired_all["p"] < 0.05),
        "3_gain_ge_3": bool(gain >= 3),
        "4_gain_from_ge_2_questions": bool(cond4),
        "5_weakest_not_worse": bool(weakest_c >= weakest_b),
        "6_gain_not_on_leakage": bool(cond6),
        "6_subset_detail": {
            "cond1": sub_cond1, "cond2": sub_cond2, "cond3": sub_cond3,
            "cond4": sub_cond4, "cond5": sub_cond5,
        },
    }
    res["conditions"] = conds
    res["adopt"] = all(conds[k] for k in
                       ("1_gain_gt_threshold", "2_mcnemar_p_lt_0.05",
                        "3_gain_ge_3", "4_gain_from_ge_2_questions",
                        "5_weakest_not_worse", "6_gain_not_on_leakage"))
    # Section 6.2 provisional check.
    b_all_wrong_c_all_right = []
    for qid, cat in truth.items():
        if all(groups["B"][bi].get(qid) != cat for bi in range(3)) and \
           all(groups["C"][bi].get(qid) == cat for bi in range(3)):
            b_all_wrong_c_all_right.append(qid)
    harm = {}
    for cls in KINDS:
        d = res["C"]["per_class"][cls]["mean_hits"] - res["B"]["per_class"][cls]["mean_hits"]
        harm[cls] = d
    systematic_harm = any(v <= -2 for v in harm.values())
    res["section_6_2"] = {
        "gain_positive": bool(gain > 0),
        "true_new_info_qids": b_all_wrong_c_all_right,
        "true_new_info_count": len(b_all_wrong_c_all_right),
        "per_class_C_minus_B_hits": harm,
        "systematic_harm": systematic_harm,
        "provisional": bool(gain > 0 and gain <= thr
                            and len(b_all_wrong_c_all_right) >= 2
                            and not systematic_harm),
    }
    res["verdict"] = ("adopt" if res["adopt"] else
                      "provisional" if res["section_6_2"]["provisional"] else "discard")

    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RUN, "scores-check.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    print(json.dumps({
        "A": res["A"]["batch_correct"],
        "B": res["B"]["batch_correct"],
        "C": res["C"]["batch_correct"],
        "noise_band": noise_band, "threshold": thr, "gain": gain,
        "mcnemar_pooled": {"b": paired_all["b"], "c": paired_all["c"], "p": paired_all["p"]},
        "conditions": conds, "verdict": res["verdict"],
    }, ensure_ascii=False, indent=2))
    return 0


def _single(b_pred, c_pred, truth):
    b = c = 0
    for qid, cat in truth.items():
        bv = b_pred.get(qid) == cat
        cv = c_pred.get(qid) == cat
        if cv and not bv:
            b += 1
        elif bv and not cv:
            c += 1
    return {"b": b, "c": c, "p": mcnemar_exact(b, c), "net": b - c}


if __name__ == "__main__":
    sys.exit(main())
