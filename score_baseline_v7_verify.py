#!/usr/bin/env python3
"""Independent recount for the baseline retest on testset-v7 (215 q).

Re-reads testset-v7.json and the prediction files from scratch and
recomputes every number in score-baseline-v7.json with separate code
(this file imports nothing from score_baseline_v7.py). Any disagreement
exits non-zero. Also independently re-checks the round-10 reproduction
gate (control 31, 31, 31; experiment 32, 32 out of 32 focus questions,
truth testset-v6.json).

Usage:
  python3 score_baseline_v7_verify.py [--pred-dir DIR] [--score-file FILE]
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(BASE, "runs", "baseline-retest-2026-11-22", "predictions")
R10_BASE = os.path.join(
    os.path.expanduser("~"), "workspace", "verification-v1-round10")
R10_PRED_DIR = os.path.join(
    R10_BASE, "runs", "round10-vision10-2026-11-22", "predictions")

R10_FOCUS = {6, 7, 11, 12, 13, 14, 16, 17, 18, 19, 20, 23, 25, 27, 30, 31,
             36, 37, 45, 48, 51, 58, 61, 62, 67, 70, 72, 74, 86, 89, 93, 94}
R10_EXPECTED = {"C1": 31, "C2": 31, "C3": 31, "E1": 32, "E2": 32}
BATCHES = ["C1", "C2", "C3"]
MODEL_KINDS = ["claude", "chatgpt", "gemini", "r1", "v3", "tongyi",
               "llama", "kimi", "muse", "glm", "minimax"]


def close(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) < 1e-9
    return a == b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-dir", default=PRED_DIR)
    ap.add_argument("--score-file", default=None)
    args = ap.parse_args()
    score_file = args.score_file or os.path.join(args.pred_dir,
                                                 "score-baseline-v7.json")
    if not os.path.exists(score_file):
        print(f"no score file yet: {score_file}")
        sys.exit(2)
    scored = json.load(open(score_file))
    ts = json.load(open(os.path.join(BASE, "testset-v7.json")))
    truth = {q["q_id"]: q for q in ts["questions"]}
    all_qids = sorted(truth)
    problems = []

    def check(label, got, want):
        if isinstance(want, float) or isinstance(got, float):
            if not close(got, want):
                problems.append(f"{label}: verify={got} score={want}")
        elif got != want:
            problems.append(f"{label}: verify={got} score={want}")

    def load_preds(pred_dir, batch):
        d = {}
        for fn in sorted(glob.glob(os.path.join(
                pred_dir, f"predictions-{batch}-*.json"))):
            raw = json.load(open(fn))
            recs = raw["predictions"] if isinstance(raw, dict) else raw
            for rec in recs:
                d[rec["q_id"]] = rec
        return d

    def guess(rec):
        return rec.get("kind", rec.get("predicted_kind"))

    # ---- independent round-10 gate recount ----
    ts6 = json.load(open(os.path.join(R10_BASE, "testset-v6.json")))
    truth6 = {q["q_id"]: q["kind"] for q in ts6["questions"]}
    gate10 = {}
    for b in ["C1", "C2", "C3", "E1", "E2"]:
        d = load_preds(R10_PRED_DIR, b)
        gate10[b] = sum(1 for q in R10_FOCUS
                        if guess(d[q]) == truth6[q])
    check("gate round10_focus",
          scored.get("reproduction_gate", {}).get("round10_focus"), gate10)
    if gate10 != R10_EXPECTED:
        problems.append(f"gate10 recount itself off: {gate10} "
                        f"(expected {R10_EXPECTED})")
    check("gate status",
          scored.get("reproduction_gate", {}).get("status"), "PASS")

    # ---- independent v7 recount ----
    old_qids = [q for q in all_qids if q <= 98]
    new_qids = [q for q in all_qids if q >= 99]
    capex_qids = [q for q in all_qids if truth[q]["kind"] == "capex"]
    dc_qids = [q for q in all_qids if truth[q]["kind"] == "datacenter"]
    model_qids = [q for q in all_qids if truth[q]["kind"] in MODEL_KINDS]

    for batch in BATCHES:
        if batch not in scored:
            problems.append(f"{batch}: missing from score file")
            continue
        got = load_preds(args.pred_dir, batch)
        want = scored[batch]
        if set(got) != set(all_qids):
            problems.append(f"{batch}: q_id set != testset (n={len(got)})")
            continue
        ok = lambda q: guess(got[q]) == truth[q]["kind"]

        def sub(qs):
            n = sum(1 for q in qs if ok(q))
            return [n, len(qs)], sorted(q for q in qs if ok(q))

        check(f"{batch} total_215", want["total_215"], sub(all_qids)[0])
        check(f"{batch} correct_qids", want["correct_qids"], sub(all_qids)[1])
        check(f"{batch} old_98", want["old_98"], sub(old_qids)[0])
        check(f"{batch} old_98_correct_qids",
              want["old_98_correct_qids"], sub(old_qids)[1])
        check(f"{batch} new_117", want["new_117"], sub(new_qids)[0])
        check(f"{batch} new_117_correct_qids",
              want["new_117_correct_qids"], sub(new_qids)[1])
        check(f"{batch} capex_10", want["capex_10"], sub(capex_qids)[0])
        check(f"{batch} capex_correct_qids",
              want["capex_correct_qids"], sub(capex_qids)[1])
        check(f"{batch} capex_qids", want["capex_qids"], capex_qids)
        check(f"{batch} datacenter_qids", want["datacenter_qids"], dc_qids)
        check(f"{batch} model_release_66", want["model_release_66"],
              sub(model_qids)[0])
        check(f"{batch} model_release_correct_qids",
              want["model_release_correct_qids"], sub(model_qids)[1])
        for kind in MODEL_KINDS:
            kq = [q for q in all_qids if truth[q]["kind"] == kind]
            check(f"{batch} model kind {kind}",
                  want["model_release_by_kind"][kind], sub(kq)[0])
        # per-kind table (all 43 kinds)
        kinds = sorted({truth[q]["kind"] for q in all_qids})
        by_kind = {}
        for k in kinds:
            kq = [q for q in all_qids if truth[q]["kind"] == k]
            by_kind[k] = sub(kq)[0]
        check(f"{batch} by_kind", want["by_kind"], by_kind)
        # per-player table (every player label in the testset)
        players = sorted({truth[q]["player"] for q in all_qids})
        by_player = {}
        for p in players:
            pq = [q for q in all_qids if truth[q]["player"] == p]
            by_player[p] = sub(pq)[0]
        check(f"{batch} by_player", want["by_player"], by_player)
        # confidence
        for level in ("high", "medium", "low"):
            qs = [q for q in all_qids if got[q].get("confidence") == level]
            n = sum(1 for q in qs if ok(q))
            check(f"{batch} confidence {level} correct_total",
                  want["confidence"][level]["correct_total"], [n, len(qs)])
            acc = (n / len(qs)) if qs else None
            check(f"{batch} confidence {level} accuracy",
                  want["confidence"][level]["accuracy"], acc)
        # roleplay execution: four fields all present and well-formed
        exec_qids = []
        for q in all_qids:
            r = got[q]
            rt = r.get("roleplay_text")
            s25 = r.get("roleplay_step25")
            fp = r.get("forecast_prop")
            prob = r.get("forecast_prob")
            if isinstance(s25, str):
                s25_ok = bool(s25.strip())
            elif isinstance(s25, dict):
                s25_ok = ("same" in s25 and isinstance(s25.get("note"), str)
                          and bool(s25["note"].strip()))
            else:
                s25_ok = False
            good = (isinstance(rt, str) and bool(rt.strip()) and s25_ok
                    and isinstance(fp, str) and bool(fp.strip())
                    and isinstance(prob, (int, float))
                    and not isinstance(prob, bool)
                    and 0.0 <= prob <= 1.0)
            if good:
                exec_qids.append(q)
        check(f"{batch} roleplay_execution executed",
              want["roleplay_execution"]["executed"], [len(exec_qids), 215])
        check(f"{batch} roleplay_execution rate",
              want["roleplay_execution"]["rate"], len(exec_qids) / 215)
        check(f"{batch} roleplay_execution executed_qids",
              want["roleplay_execution"]["executed_qids"], exec_qids)
        check(f"{batch} roleplay_execution not_executed_qids",
              want["roleplay_execution"]["not_executed_qids"],
              sorted(set(all_qids) - set(exec_qids)))
        # guidance: capex predictions with non-empty guidance_cited
        def nonempty(v):
            if v is None:
                return False
            if isinstance(v, str):
                return len(v.strip()) > 0
            if isinstance(v, dict):
                return len(v) > 0
            return True
        cg = sum(1 for q in capex_qids
                 if nonempty(got[q].get("guidance_cited")))
        check(f"{batch} guidance_citation",
              want["guidance_citation"], [cg, len(capex_qids)])
        check(f"{batch} guidance_citation_rate",
              want["guidance_citation_rate"], cg / len(capex_qids))
        # boundary: capex + datacenter predictions with non-empty boundary
        bset = sorted(set(capex_qids) | set(dc_qids))
        cb = sum(1 for q in bset
                 if nonempty(got[q].get("boundary_cited")))
        check(f"{batch} boundary_citation",
              want["boundary_citation"], [cb, len(bset)])
        check(f"{batch} boundary_citation_rate",
              want["boundary_citation_rate"], cb / len(bset))
        check(f"{batch} guesses", want["guesses"],
              {str(q): guess(got[q]) for q in all_qids})

    # ---- group summary recount (from the score file's batch numbers) ----
    if "group_summary" in scored:
        g = scored["group_summary"]
        c = [scored[b]["total_215"][0] for b in BATCHES]
        check("group control_total", g["control_total"], c)
        check("group M_TC", g["M_TC"], sum(c) / 3)
        check("group spread_S_T", g["spread_S_T"], max(c) - min(c))
        kinds = sorted({truth[q]["kind"] for q in all_qids})
        for k in kinds:
            check(f"group per_kind_mean {k}", g["per_kind_mean_correct"][k],
                  sum(scored[b]["by_kind"][k][0] for b in BATCHES) / 3)
            check(f"group per_kind_total {k}", g["per_kind_total"][k],
                  scored["C1"]["by_kind"][k][1])
        players = sorted({truth[q]["player"] for q in all_qids})
        for p in players:
            check(f"group per_player_mean {p}",
                  g["per_player_mean_correct"][p],
                  sum(scored[b]["by_player"][p][0] for b in BATCHES) / 3)
        check("group old_98_mean", g["old_98_mean"],
              sum(scored[b]["old_98"][0] for b in BATCHES) / 3)
        check("group new_117_mean", g["new_117_mean"],
              sum(scored[b]["new_117"][0] for b in BATCHES) / 3)
        check("group capex_10_mean", g["capex_10_mean"],
              sum(scored[b]["capex_10"][0] for b in BATCHES) / 3)
        check("group model_release_66_mean", g["model_release_66_mean"],
              sum(scored[b]["model_release_66"][0] for b in BATCHES) / 3)
        for k in MODEL_KINDS:
            check(f"group model kind mean {k}",
                  g["model_release_by_kind_mean"][k],
                  sum(scored[b]["model_release_by_kind"][k][0]
                      for b in BATCHES) / 3)
        for level in ("high", "medium", "low"):
            check(f"group confidence_mean {level}",
                  g["confidence_mean"][level],
                  sum(scored[b]["confidence"][level]["correct_total"][0]
                      for b in BATCHES) / 3)
            check(f"group confidence_total_mean {level}",
                  g["confidence_total_mean"][level],
                  sum(scored[b]["confidence"][level]["correct_total"][1]
                      for b in BATCHES) / 3)
        check("group R_mean", g["R_mean"],
              sum(scored[b]["roleplay_execution"]["rate"]
                  for b in BATCHES) / 3)
        check("group G_mean", g["G_mean"],
              sum(scored[b]["guidance_citation_rate"]
                  for b in BATCHES) / 3)
        check("group B_mean", g["B_mean"],
              sum(scored[b]["boundary_citation_rate"]
                  for b in BATCHES) / 3)

    if problems:
        print("VERIFY FAILED:")
        for p in problems:
            print("  MISMATCH:", p)
        sys.exit(1)
    print(f"VERIFY PASS: score file {score_file} agrees with independent "
          f"recount on every number "
          f"(batches checked: {[b for b in BATCHES if b in scored] or 'none yet'}).")


if __name__ == "__main__":
    main()
