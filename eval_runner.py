#!/usr/bin/env python3
"""Gemini A/B/C Phase 1 Task 1.3: eval runner.

Builds per-question material packs (B = player audit history strictly before
prediction date; C = B + forward-guidance entries strictly before prediction
date), computes group A (scripted history-mode baseline, 3 identical batches),
writes prediction files for A, and runs the date / leakage audit.

Rules are frozen in design/gemini-abc-phase1-run-2026-11-25.md. This script
implements them; it never invents material and never reads the web.
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
RUN_DIR = os.path.join(ROOT, "runs", "gemini-abc-2026-11-25")
MAT_DIR = os.path.join(RUN_DIR, "materials")
GUIDANCE_DIR = os.path.expanduser(
    "~/workspace/verification-v1-guidance/runs/forward-guidance-vision1-2026-11-22"
)
GUIDANCE_FILES = ["guidance-S4.json", "guidance-S5-early.json", "guidance-S5-late.json"]

CLASSES = [
    "model_release",
    "infra_capex",
    "capital_deal",
    "chip_supply",
    "policy_regulatory",
    "hold_defend",
]
CLASS_ORDER = {c: i for i, c in enumerate(CLASSES)}

# Guidance ticker -> clean-set player name.
PLAYER_MAP = {
    "MSFT": "微软",
    "META": "Meta",
    "NVDA": "英伟达",
    "OAI": "OpenAI",
    "ORCL": "甲骨文",
    "SFTB": "软银",
    "TSMC": "台积电",
    "GOOG": "谷歌",
    "ANTH": "Anthropic",
    "MUSK": "马斯克 · xAI",
    "ALI": "阿里 · 阿里云",
    "TCE": "腾讯 · 腾讯云",
    "BIDU": "百度 · 百度智能云",
    "HUAWEI": "华为 · 昇腾",
    "DPSK": "DeepSeek",
    "BYTE": "字节跳动",
}

# B-material exclusion: same-event passive entry that would hand Q054 its answer.
B_EXCLUDE = {("Q054", "S5-R11-036")}

# C-guidance leak exclusions, keyed by (question_id, guidance date, ticker).
# Identified by date+ticker+statement prefix; see run doc section 3.3.
LEAK_EXCLUDE = {
    ("Q012", "2024-12-04", "MUSK"),
    ("Q021", "2025-03-10", "ORCL"),
    ("Q025", "2025-02-12", "OAI"),
    ("Q040", "2026-07-31", "DPSK"),
}


def date_int(iso):
    return int(iso.replace("-", ""))


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_xai_relevant(statement):
    """MUSK entries split: only xAI / Colossus / Grok count for xAI questions.
    Tesla and SpaceX entries are different companies and are excluded."""
    if "特斯拉" in statement or "Tesla" in statement:
        return False
    if "SpaceX" in statement or "数据中心卫星" in statement:
        return False
    return True


def build_packs(clean, audit_entries, guidance_entries):
    """Return {qid: pack}. Pack holds NO answer: no category, no evidence,
    no source_move_id. Only player / round / date / history / guidance."""
    packs = {}
    for q in clean["questions"]:
        qid = q["question_id"]
        qd = date_int(q["date"])
        history = []
        for e in audit_entries:
            if e["player"] != q["player"]:
                continue
            if e["date"] >= qd:
                continue
            if (qid, e["move_id"]) in B_EXCLUDE:
                continue
            history.append(
                {
                    "date": str(e["date"]),
                    "round": e["round"],
                    "nature": e["action_nature"],
                    "raw_action": e["raw_action"],
                }
            )
        history.sort(key=lambda h: (h["date"], h["round"]))
        guidance = []
        for g in guidance_entries:
            if PLAYER_MAP.get(g["player"]) != q["player"]:
                continue
            if date_int(g["date"]) >= qd:
                continue
            if g["player"] == "MUSK" and not is_xai_relevant(g["statement"]):
                continue
            if (qid, g["date"], g["player"]) in LEAK_EXCLUDE:
                continue
            guidance.append(
                {"date": g["date"], "type": g["type"], "statement": g["statement"]}
            )
        guidance.sort(key=lambda h: h["date"])
        packs[qid] = {
            "question_id": qid,
            "player": q["player"],
            "round": q["round"],
            "date": q["date"],
            "history": history,
            "guidance": guidance,
        }
    return packs


def mode_with_tiebreak(counter, global_counter):
    """Most frequent; ties -> higher global frequency -> fixed class order."""
    best = None
    best_key = None
    for cls, cnt in counter.items():
        key = (cnt, global_counter.get(cls, 0), -CLASS_ORDER[cls])
        if best_key is None or key > best_key:
            best_key = key
            best = cls
    return best


def compute_A(clean):
    """Group A: per-question mode of same player's earlier clean-set categories
    (date strictly earlier). Fallbacks per run doc section 2."""
    qs = clean["questions"]
    global_counter = Counter(q["category"] for q in qs)
    preds = {}
    for q in qs:
        qd = date_int(q["date"])
        player_hist = Counter(
            o["category"]
            for o in qs
            if o["player"] == q["player"] and date_int(o["date"]) < qd
        )
        if player_hist:
            pred, rule = mode_with_tiebreak(player_hist, global_counter), "player-mode"
        else:
            earlier = Counter(
                o["category"] for o in qs if date_int(o["date"]) < qd
            )
            if earlier:
                pred, rule = mode_with_tiebreak(earlier, global_counter), "global-mode-fallback"
            else:
                pred, rule = "model_release", "empty-fallback"
        preds[q["question_id"]] = {"prediction": pred, "rule": rule}
    return preds


def score(preds, clean):
    """preds: {qid: category}. Returns (correct, total, per_class dict)."""
    answers = {q["question_id"]: q["category"] for q in clean["questions"]}
    per_class = {c: {"n": 0, "hit": 0} for c in CLASSES}
    correct = 0
    for qid, ans in answers.items():
        per_class[ans]["n"] += 1
        if preds.get(qid) == ans:
            correct += 1
            per_class[ans]["hit"] += 1
    return correct, len(answers), per_class


def audit_packs(packs, clean):
    """Date audit + leakage re-check. Returns audit dict."""
    violations = []
    for q in clean["questions"]:
        qid = q["question_id"]
        qd = date_int(q["date"])
        pack = packs[qid]
        for h in pack["history"]:
            if int(h["date"]) >= qd:
                violations.append({"qid": qid, "kind": "history-date", "item": h})
        for g in pack["guidance"]:
            if date_int(g["date"]) >= qd:
                violations.append({"qid": qid, "kind": "guidance-date", "item": g})
    # "2200" must appear in no pack at all.
    leak2200 = [qid for qid, p in packs.items()
                if "2200" in json.dumps(p, ensure_ascii=False)]
    # Excluded guidance must be absent from the named packs.
    leak_excluded_present = []
    for (qid, gdate, ticker) in LEAK_EXCLUDE:
        for g in packs[qid]["guidance"]:
            if g["date"] == gdate:
                leak_excluded_present.append({"qid": qid, "date": gdate})
    # S5-R11-036 must be absent from Q054 pack.
    s036_present = any(
        h["raw_action"].startswith("募资已到账") for h in packs["Q054"]["history"]
    )
    # Q044 C-guidance must be empty (no AMZN guidance exists).
    q044_guidance_n = len(packs["Q044"]["guidance"])
    return {
        "date_violations": violations,
        "date_violation_count": len(violations),
        "packs_containing_2200": leak2200,
        "leak_excluded_present": leak_excluded_present,
        "S5-R11-036_in_Q054_pack": s036_present,
        "Q044_guidance_count": q044_guidance_n,
    }


def exact_mcnemar_p(b, c):
    """Two-sided exact binomial p for discordant counts b, c (stdlib only)."""
    import math
    n = b + c
    if n == 0:
        return 1.0
    lo = min(b, c)
    p_lo = sum(math.comb(n, k) * (0.5 ** n) for k in range(lo + 1))
    return min(1.0, 2.0 * p_lo)


def score_all():
    """Score all nine prediction files and write scores-primary.json."""
    clean = load_json(os.path.join(ROOT, "datasets", "clean_s4_s5.json"))
    truth = {q["question_id"]: q["category"] for q in clean["questions"]}
    groups = {}
    for g in ("A", "B", "C"):
        batches = []
        for n in (1, 2, 3):
            rows = load_json(os.path.join(RUN_DIR, f"{g}-batch{n}.json"))
            assert len(rows) == 54
            batches.append({r["question_id"]: r["prediction"] for r in rows})
        groups[g] = batches
    out = {}
    for g in ("A", "B", "C"):
        batch_correct = []
        per_class = {c: {"n": 0, "hits": [0, 0, 0]} for c in CLASSES}
        for qid, cat in truth.items():
            per_class[cat]["n"] += 1
        for bi, preds in enumerate(groups[g]):
            ok = 0
            for qid, cat in truth.items():
                if preds.get(qid) == cat:
                    ok += 1
                    per_class[cat]["hits"][bi] += 1
            batch_correct.append(ok)
        pc = {}
        for c in CLASSES:
            n = per_class[c]["n"]
            hits = per_class[c]["hits"]
            pc[c] = {"n": n, "hits_per_batch": hits,
                     "mean_hits": sum(hits) / 3.0,
                     "mean_rate": (sum(hits) / 3.0) / n if n else 0.0}
        out[g] = {"batch_correct": batch_correct,
                  "mean_correct": sum(batch_correct) / 3.0,
                  "mean_accuracy": (sum(batch_correct) / 3.0) / len(truth),
                  "per_class": pc}
    a_bc = out["A"]["batch_correct"]
    noise_band = max(a_bc) - min(a_bc)
    out["noise_band"] = noise_band
    out["threshold"] = max(11, noise_band)
    # Pooled McNemar over 162 question-batch pairs.
    # cw = C right / B wrong; bw = B right / C wrong. Net = cw - bw must
    # equal 3 * (C mean - B mean) in questions.
    cw = bw = 0
    win_counts = {}
    for bi in range(3):
        for qid, cat in truth.items():
            bv = groups["B"][bi].get(qid) == cat
            cv = groups["C"][bi].get(qid) == cat
            if cv and not bv:
                cw += 1
                win_counts[qid] = win_counts.get(qid, 0) + 1
            elif bv and not cv:
                bw += 1
    out["mcnemar_pooled"] = {"C_right_B_wrong": cw, "B_right_C_wrong": bw,
                             "p": exact_mcnemar_p(cw, bw),
                             "net": cw - bw}
    out["mcnemar_per_batch"] = []
    for bi in range(3):
        bb = cc = 0
        for qid, cat in truth.items():
            bv = groups["B"][bi].get(qid) == cat
            cv = groups["C"][bi].get(qid) == cat
            if cv and not bv:
                bb += 1
            elif bv and not cv:
                cc += 1
        out["mcnemar_per_batch"].append(
            {"C_right_B_wrong": bb, "B_right_C_wrong": cc,
             "p": exact_mcnemar_p(bb, cc), "net": bb - cc})
    gain = out["C"]["mean_correct"] - out["B"]["mean_correct"]
    out["gain_C_minus_B"] = gain
    weakest_b = min(v["mean_rate"] for v in out["B"]["per_class"].values())
    weakest_c = min(v["mean_rate"] for v in out["C"]["per_class"].values())
    out["weakest_B"] = weakest_b
    out["weakest_C"] = weakest_c
    # Sensitivity subset: drop the 5 flagged questions.
    drop = {"Q012", "Q021", "Q025", "Q040", "Q054"}
    sub_truth = {q: c for q, c in truth.items() if q not in drop}
    sub_b = sub_c = 0.0
    for bi in range(3):
        sub_b += sum(1 for q, c in sub_truth.items()
                     if groups["B"][bi].get(q) == c)
        sub_c += sum(1 for q, c in sub_truth.items()
                     if groups["C"][bi].get(q) == c)
    sub_b /= 3.0
    sub_c /= 3.0
    sub_gain = sub_c - sub_b
    sb = sc = 0
    for bi in range(3):
        for q, c in sub_truth.items():
            if groups["C"][bi].get(q) == c and groups["B"][bi].get(q) != c:
                sb += 1
            elif groups["B"][bi].get(q) == c and groups["C"][bi].get(q) != c:
                sc += 1
    sub_p = exact_mcnemar_p(sb, sc)
    # Weakest class on the subset (mean rates).
    def weakest_on(subset, grp):
        worst = 1.0
        for cls in CLASSES:
            qs = [q for q, c in subset.items() if c == cls]
            if not qs:
                continue
            hits = sum(sum(1 for q in qs if grp[bi].get(q) == cls)
                       for bi in range(3)) / 3.0
            worst = min(worst, hits / len(qs))
        return worst
    sub_wb = weakest_on(sub_truth, groups["B"])
    sub_wc = weakest_on(sub_truth, groups["C"])
    sub_win_qids = {q for q in sub_truth
                    if any(groups["C"][bi].get(q) == sub_truth[q]
                           and groups["B"][bi].get(q) != sub_truth[q]
                           for bi in range(3))}
    out["sensitivity_49"] = {
        "dropped": sorted(drop), "B_mean": sub_b, "C_mean": sub_c,
        "gain": sub_gain,
        "mcnemar": {"C_right_B_wrong": sb, "B_right_C_wrong": sc,
                    "p": sub_p, "net": sb - sc},
        "weakest_B": sub_wb, "weakest_C": sub_wc,
        "distinct_win_qids": sorted(sub_win_qids),
    }
    thr = out["threshold"]
    net = out["mcnemar_pooled"]["net"]
    max_share = (max(win_counts.values()) / net) if net > 0 and win_counts else 0.0
    cond4 = len(win_counts) >= 2 and (net <= 0 or max_share <= 0.5)
    sub_cond = {
        "cond1": bool(sub_gain > thr), "cond2": bool(sub_p < 0.05),
        "cond3": bool(sub_gain >= 3),
        "cond4": len(sub_win_qids) >= 2,
        "cond5": bool(sub_wc >= sub_wb),
    }
    conds = {
        "1_gain_gt_threshold": bool(gain > thr),
        "2_mcnemar_p_lt_0.05": bool(out["mcnemar_pooled"]["p"] < 0.05),
        "3_gain_ge_3": bool(gain >= 3),
        "4_gain_from_ge_2_questions": bool(cond4),
        "5_weakest_not_worse": bool(weakest_c >= weakest_b),
        "6_gain_not_on_leakage": bool(all(sub_cond.values())),
        "6_subset_detail": sub_cond,
    }
    out["conditions"] = conds
    out["condition4_detail"] = {
        "distinct_win_qids": sorted(win_counts),
        "win_counts_per_qid": dict(sorted(win_counts.items())),
        "max_single_qid_share_of_net": max_share,
    }
    out["adopt"] = all(conds[k] for k in (
        "1_gain_gt_threshold", "2_mcnemar_p_lt_0.05", "3_gain_ge_3",
        "4_gain_from_ge_2_questions", "5_weakest_not_worse",
        "6_gain_not_on_leakage"))
    new_info = [q for q, c in truth.items()
                if all(groups["B"][bi].get(q) != c for bi in range(3))
                and all(groups["C"][bi].get(q) == c for bi in range(3))]
    harm = {cls: out["C"]["per_class"][cls]["mean_hits"]
            - out["B"]["per_class"][cls]["mean_hits"] for cls in CLASSES}
    systematic_harm = any(v <= -2 for v in harm.values())
    out["section_6_2"] = {
        "gain_positive": bool(gain > 0),
        "true_new_info_qids": new_info,
        "true_new_info_count": len(new_info),
        "per_class_C_minus_B_hits": harm,
        "systematic_harm": systematic_harm,
        "provisional": bool(gain > 0 and gain <= thr
                            and len(new_info) >= 2 and not systematic_harm),
    }
    out["verdict"] = ("adopt" if out["adopt"] else
                      "provisional" if out["section_6_2"]["provisional"]
                      else "discard")
    with open(os.path.join(RUN_DIR, "scores-primary.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "A": out["A"]["batch_correct"], "B": out["B"]["batch_correct"],
        "C": out["C"]["batch_correct"], "noise_band": noise_band,
        "threshold": thr, "gain": gain,
        "mcnemar_pooled": out["mcnemar_pooled"],
        "conditions": conds, "verdict": out["verdict"],
    }, ensure_ascii=False, indent=2))
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "score":
        return score_all()
    clean = load_json(os.path.join(ROOT, "datasets", "clean_s4_s5.json"))
    audit = load_json(os.path.join(ROOT, "datasets", "s4_s5_action_audit.json"))
    guidance_entries = []
    for fn in GUIDANCE_FILES:
        d = load_json(os.path.join(GUIDANCE_DIR, fn))
        for e in d["entries"]:
            e = dict(e)
            e["_file"] = fn
            guidance_entries.append(e)
    print(f"clean questions: {len(clean['questions'])}")
    print(f"audit entries: {len(audit['entries'])}")
    print(f"guidance entries: {len(guidance_entries)}")

    os.makedirs(MAT_DIR, exist_ok=True)
    packs = build_packs(clean, audit["entries"], guidance_entries)
    for qid, pack in packs.items():
        with open(os.path.join(MAT_DIR, f"{qid}.json"), "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=2)

    # Group A: deterministic; write 3 identical batch files.
    a_preds = compute_A(clean)
    for b in (1, 2, 3):
        out = [
            {
                "question_id": qid,
                "prediction": v["prediction"],
                "rule": v["rule"],
                "reason": "script: history mode per run doc section 2",
            }
            for qid, v in a_preds.items()
        ]
        with open(os.path.join(RUN_DIR, f"A-batch{b}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    correct, total, per_class = score(
        {k: v["prediction"] for k, v in a_preds.items()}, clean
    )
    print(f"A batches (identical): {correct}/{total} = {correct/total:.4f}")
    for c in CLASSES:
        pc = per_class[c]
        print(f"  {c}: {pc['hit']}/{pc['n']}")

    audit_res = audit_packs(packs, clean)
    print("audit:", json.dumps(audit_res, ensure_ascii=False))
    with open(os.path.join(RUN_DIR, "audit.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "packs": len(packs),
                "guidance_total": len(guidance_entries),
                "leak_exclusions_applied": sorted(
                    f"{qid}|{d}|{t}" for (qid, d, t) in LEAK_EXCLUDE
                ),
                "b_exclusions_applied": sorted(
                    f"{qid}|{m}" for (qid, m) in B_EXCLUDE
                ),
                **audit_res,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    # Hard fail on any audit violation.
    assert audit_res["date_violation_count"] == 0, "date violations found"
    assert not audit_res["packs_containing_2200"], "2200 found in packs"
    assert not audit_res["leak_excluded_present"], "leaked guidance present"
    assert not audit_res["S5-R11-036_in_Q054_pack"], "S5-R11-036 in Q054 pack"
    assert audit_res["Q044_guidance_count"] == 0, "Q044 has guidance entries"
    print("audit PASS: 0 date violations, 0 leaks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
