#!/usr/bin/env python3
"""Independent re-check of round-12 scoring (score_round12.py output).

Re-reads testset-v7.json and all C1-C3 / E1-E3 prediction files from
scratch, with its own loops (no import of score_round12). Recomputes:
per-batch totals, old/new split, v7-A/v7-B split, weak-45 split,
weak-by-kind, per-kind, per-player, model-release 66, capex 10,
confidence (pooled + per batch), guidance/boundary citation rates,
roleplay execution, leakage-excluded (42-list) rescores, leaked-subset
scores, group means and spreads, weakest kind, gains (raw +
excluded42, new/old/A/B/weak/new-kinds), paired averages (raw +
excluded42), McNemar exact two-sided p per pair, decision-rule
booleans (protocol section 6.1), H-W fields. Compares every number
against runs/round12-weak-repair-2026-11-25/score-round12.json and
exits non-zero on any mismatch.

When no prediction files exist yet, only the reproduction gates and
the leakage-exclusion note are checked.

Usage: python3 score_round12_verify.py [SCORED_JSON]
"""
import glob
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, "runs", "round12-weak-repair-2026-11-25")
PRED_DIR = os.path.join(RUN, "predictions")
SCORE_PATH = os.path.join(RUN, "score-round12.json")
if len(sys.argv) > 1:
    SCORE_PATH = sys.argv[1]
    # The scored file lives in the run root; predictions live next to it.
    PRED_DIR = os.path.join(os.path.dirname(os.path.abspath(SCORE_PATH)),
                            "predictions")

MODEL = {"claude", "chatgpt", "gemini", "r1", "v3", "tongyi", "llama",
         "kimi", "muse", "glm", "minimax"}
NEW_KINDS = {"agent", "arr", "acquisition", "social", "partnership", "kimi",
             "math", "memory", "wallstreet", "talent", "video", "muse"}
WEAK_KINDS = ["acquisition", "arr", "partnership", "math", "wallstreet",
              "social"]
# Protocol section 11.3 list (42 questions). Copied here, not imported,
# so the two scripts cannot share a typo.
LEAK_42 = {0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
           19, 20, 24, 30, 31, 32, 35, 36, 37, 41, 42, 45, 49, 50, 61, 63,
           67, 69, 70, 74, 78, 89, 92, 98}

failures = []


def check(name, got, want, tol=1e-9):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        failures.append(f"{name}: verify={got!r} score-round12={want!r}")


def read_batch(d, prefix):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, prefix + "-*.json"))):
        data = json.load(open(f))
        for rec in data["predictions"]:
            assert rec["q_id"] not in out, f"dup q{rec['q_id']} in {f}"
            out[rec["q_id"]] = rec
    return out


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def main():
    ts = json.load(open(os.path.join(BASE, "testset-v7.json")))
    questions = ts["questions"]
    truth_kind = {q["q_id"]: q["kind"] for q in questions}
    truth_player = {q["q_id"]: q["player"] for q in questions}
    truth_split = {q["q_id"]: q["split"] for q in questions}
    qids = sorted(truth_kind)
    assert len(qids) == 215 and set(qids) == set(range(216)) - {79}, "testset shape"
    old_ids = [q for q in qids if q <= 98]
    new_ids = [q for q in qids if q >= 99]
    a_ids = [q for q in qids if truth_split[q] == "A"]
    b_ids = [q for q in qids if truth_split[q] == "B"]
    weak_ids = [q for q in qids if truth_kind[q] in WEAK_KINDS]
    capex_ids = [q for q in qids if truth_kind[q] == "capex"]
    dc_ids = [q for q in qids if truth_kind[q] == "datacenter"]
    model_ids = [q for q in qids if truth_kind[q] in MODEL]
    assert len(old_ids) == 98 and len(new_ids) == 117
    assert len(a_ids) == 108 and len(b_ids) == 107 and len(weak_ids) == 45
    assert len(capex_ids) == 10 and len(model_ids) == 66

    scored = json.load(open(SCORE_PATH))

    # ---- reproduction gates ----
    gates = scored.get("reproduction_gates")
    assert gates, "no reproduction_gates in scored file"
    for gkey in ("gate_0_round10_focus", "gate_1_v7_baseline_retest_audited",
                 "gate_2_round11_control_audited", "gate_2_gain_both_audited"):
        check(f"gates.{gkey}.status", gates[gkey]["status"], "PASS")
    check("gates.gate_1.got", gates["gate_1_v7_baseline_retest_audited"]["got"],
          {"C1": 96, "C2": 104, "C3": 93})
    check("gates.gate_2.got", gates["gate_2_round11_control_audited"]["got"],
          {"D1": 90, "D2": 94, "D3": 93})
    check("gates.gate_2.gain", gates["gate_2_gain_both_audited"]["got"], 5.33)

    # ---- leakage-exclusion note ----
    note = scored["leakage_exclusion_note"]
    check("leak_note.list", sorted(note["list"]), sorted(LEAK_42))
    check("leak_note.count_39_claim", note["protocol_sections_3_2_and_6_1_count"], 39)
    check("leak_note.count_11_3", note["protocol_section_11_3_list_count"], 42)
    check("leak_note.in_B", note["leak_in_split_B"],
          len([q for q in LEAK_42 if truth_split[q] == "B"]))
    check("leak_note.in_A", note["leak_in_split_A"],
          len([q for q in LEAK_42 if truth_split[q] == "A"]))

    ctrl = {b: read_batch(PRED_DIR, f"predictions-{b}") for b in ("C1", "C2", "C3")}
    exp = {b: read_batch(PRED_DIR, f"predictions-{b}") for b in ("E1", "E2", "E3")}
    present_ctrl = [b for b in ("C1", "C2", "C3") if ctrl[b]]
    present_exp = [b for b in ("E1", "E2", "E3") if exp[b]]
    if not present_ctrl and not present_exp:
        if failures:
            print(f"VERIFY FAIL: {len(failures)} mismatches")
            for f in failures[:50]:
                print("  ", f)
            sys.exit(1)
        print("VERIFY PASS (gates + leak note only; no predictions yet)")
        return
    for b in present_ctrl + present_exp:
        p = ctrl.get(b) or exp.get(b)
        assert set(p) == set(qids), f"{b} q set mismatch"

    def correct(preds, q):
        return preds[q].get("kind") == truth_kind[q]

    def cited(v):
        return isinstance(v, str) and v.strip() != ""

    def rp_ok(p):
        rt = p.get("roleplay_text")
        if not isinstance(rt, str) or not rt.strip():
            return False
        s25 = p.get("roleplay_step25")
        if isinstance(s25, str):
            if not s25.strip():
                return False
        elif isinstance(s25, dict):
            if "same" not in s25:
                return False
            if not isinstance(s25.get("note"), str) or not s25["note"].strip():
                return False
        else:
            return False
        fp = p.get("forecast_prop")
        if not isinstance(fp, str) or not fp.strip():
            return False
        prob = p.get("forecast_prob")
        if isinstance(prob, bool) or not isinstance(prob, (int, float)):
            return False
        return 0.0 <= prob <= 1.0

    def tot(preds, qs, excl=None):
        ex = excl or set()
        return sum(1 for q in qs if correct(preds, q) and q not in ex)

    # ---- per-batch raw ----
    for group, batches, preds in (("control", ("C1", "C2", "C3"), ctrl),
                                  ("experiment_raw", ("E1", "E2", "E3"), exp)):
        for b in batches:
            if b not in (present_ctrl if group == "control" else present_exp):
                continue
            p = preds[b]
            s = scored[group][b]
            check(f"{group}.{b}.total", tot(p, qids), s["total_215"][0])
            check(f"{group}.{b}.old", tot(p, old_ids), s["old_98"][0])
            check(f"{group}.{b}.new", tot(p, new_ids), s["new_117"][0])
            check(f"{group}.{b}.A", tot(p, a_ids), s["split_A_108"][0])
            check(f"{group}.{b}.B", tot(p, b_ids), s["split_B_107"][0])
            check(f"{group}.{b}.weak", tot(p, weak_ids), s["weak_45"][0])
            check(f"{group}.{b}.capex", tot(p, capex_ids), s["capex_10"][0])
            check(f"{group}.{b}.model", tot(p, model_ids), s["model_release_66"][0])
            for kind in WEAK_KINDS:
                kq = [q for q in qids if truth_kind[q] == kind]
                check(f"{group}.{b}.weak.{kind}", tot(p, kq), s["weak_by_kind"][kind][0])
            for level in ("high", "medium", "low"):
                qs = [q for q in qids if p[q].get("confidence") == level]
                c = sum(1 for q in qs if correct(p, q))
                check(f"{group}.{b}.conf.{level}", [c, len(qs)], s["confidence"][level]["correct_total"])
            check(f"{group}.{b}.G", sum(1 for q in capex_ids if cited(p[q].get("guidance_cited"))),
                  s["guidance_citation"][0])
            check(f"{group}.{b}.B", sum(1 for q in set(capex_ids) | set(dc_ids)
                                        if cited(p[q].get("boundary_cited"))),
                  s["boundary_citation"][0])
            check(f"{group}.{b}.R", sum(1 for q in qids if rp_ok(p[q])),
                  s["roleplay_execution"]["executed"][0])
            for kind in sorted(set(truth_kind.values())):
                kq = [q for q in qids if truth_kind[q] == kind]
                check(f"{group}.{b}.kind.{kind}", tot(p, kq), s["by_kind"][kind][0])
                check(f"{group}.{b}.kind.{kind}.total", len(kq), s["by_kind"][kind][1])
            for pl in sorted(set(truth_player.values())):
                pq = [q for q in qids if truth_player[q] == pl]
                check(f"{group}.{b}.player.{pl}", tot(p, pq), s["by_player"][pl][0])

    if len(present_ctrl) != 3 or len(present_exp) != 3:
        if failures:
            print(f"VERIFY FAIL: {len(failures)} mismatches")
            for f in failures[:50]:
                print("  ", f)
            sys.exit(1)
        print("VERIFY PASS (partial batches only; group comparisons not checked)")
        return

    # ---- excluded42 rescores ----
    for group, batches, preds, key in (
            ("control", ("C1", "C2", "C3"), ctrl, "control_excluded42"),
            ("experiment", ("E1", "E2", "E3"), exp, "experiment_excluded42")):
        for b in batches:
            p = preds[b]
            s = scored[key][b]
            check(f"{key}.{b}.total", tot(p, qids, LEAK_42), s["total_215"][0])
            check(f"{key}.{b}.old", tot(p, old_ids, LEAK_42), s["old_98"][0])
            check(f"{key}.{b}.new", tot(p, new_ids, LEAK_42), s["new_117"][0])
            check(f"{key}.{b}.A", tot(p, a_ids, LEAK_42), s["split_A_108"][0])
            check(f"{key}.{b}.B", tot(p, b_ids, LEAK_42), s["split_B_107"][0])
            check(f"{key}.{b}.weak", tot(p, weak_ids, LEAK_42), s["weak_45"][0])
            check(f"{key}.{b}.capex", tot(p, capex_ids, LEAK_42), s["capex_10"][0])
            check(f"{key}.{b}.model", tot(p, model_ids, LEAK_42), s["model_release_66"][0])
            for kind in sorted(set(truth_kind.values())):
                kq = [q for q in qids if truth_kind[q] == kind]
                check(f"{key}.{b}.kind.{kind}", tot(p, kq, LEAK_42),
                      s["by_kind"].get(kind, [0, 0])[0])

    # ---- leaked-subset scores ----
    ls = scored["leaked_subset_scores"]
    for b in ("C1", "C2", "C3"):
        check(f"leak_subset.control.{b}", tot(ctrl[b], sorted(LEAK_42)),
              ls["control"][b]["correct"])
    for b in ("E1", "E2", "E3"):
        check(f"leak_subset.experiment.{b}", tot(exp[b], sorted(LEAK_42)),
              ls["experiment"][b]["correct"])
    m_lc = sum(tot(ctrl[b], sorted(LEAK_42)) for b in ("C1", "C2", "C3")) / 3
    m_le = sum(tot(exp[b], sorted(LEAK_42)) for b in ("E1", "E2", "E3")) / 3
    check("leak_subset.gain", m_le - m_lc, ls["gain_on_leaked_only"])

    # ---- group means / spreads / weakest kind ----
    def grp_mean(preds, batches, qs, excl=None):
        return sum(tot(preds[b], qs, excl) for b in batches) / 3

    def grp_spread(preds, batches, qs, excl=None):
        vals = [tot(preds[b], qs, excl) for b in batches]
        return max(vals) - min(vals)

    cg = scored["control_group"]
    eg_raw = scored["experiment_raw_group"]
    cg_aud = scored["control_excluded42_group"]
    eg_aud = scored["experiment_excluded42_group"]
    check("control.mean", grp_mean(ctrl, ("C1", "C2", "C3"), qids), cg["mean"])
    check("control.spread", grp_spread(ctrl, ("C1", "C2", "C3"), qids), cg["spread"])
    check("control.A_mean", grp_mean(ctrl, ("C1", "C2", "C3"), a_ids), cg["split_A_108_mean"])
    check("control.B_mean", grp_mean(ctrl, ("C1", "C2", "C3"), b_ids), cg["split_B_107_mean"])
    check("control.weak_mean", grp_mean(ctrl, ("C1", "C2", "C3"), weak_ids), cg["weak_45_mean"])
    check("exp_raw.mean", grp_mean(exp, ("E1", "E2", "E3"), qids), eg_raw["mean"])
    check("control_excl.mean", grp_mean(ctrl, ("C1", "C2", "C3"), qids, LEAK_42), cg_aud["mean"])
    check("exp_excl.mean", grp_mean(exp, ("E1", "E2", "E3"), qids, LEAK_42), eg_aud["mean"])
    check("control_excl.spread", grp_spread(ctrl, ("C1", "C2", "C3"), qids, LEAK_42), cg_aud["spread"])
    check("exp_excl.spread", grp_spread(exp, ("E1", "E2", "E3"), qids, LEAK_42), eg_aud["spread"])
    for level in ("high", "medium", "low"):
        c = sum(sum(1 for q in qids if ctrl[b][q].get("confidence") == level and correct(ctrl[b], q))
                for b in ("C1", "C2", "C3"))
        n = sum(sum(1 for q in qids if ctrl[b][q].get("confidence") == level)
                for b in ("C1", "C2", "C3"))
        check(f"control.conf_pooled.{level}", [c, n], cg["confidence_pooled"][level]["correct_total"])
    # weakest kind, excluded42 (all kinds, and weak kinds only)
    def weakest(preds, batches, excl, kind_set=None):
        rates = {}
        for kind in sorted(set(truth_kind.values())):
            if kind_set is not None and kind not in kind_set:
                continue
            kq = [q for q in qids if truth_kind[q] == kind]
            rates[kind] = grp_mean(preds, batches, kq, excl) / len(kq)
        low = min(rates.values())
        return sorted(k for k, r in rates.items() if r == low), low
    wk_c, wk_c_rate = weakest(ctrl, ("C1", "C2", "C3"), LEAK_42)
    wk_e, wk_e_rate = weakest(exp, ("E1", "E2", "E3"), LEAK_42)
    check("weakest.ctrl", wk_c, cg_aud["weakest_kind"])
    check("weakest.ctrl.rate", wk_c_rate, cg_aud["weakest_kind_rate"])
    check("weakest.exp", wk_e, eg_aud["weakest_kind"])
    check("weakest.exp.rate", wk_e_rate, eg_aud["weakest_kind_rate"])
    wk_w_c, wk_w_c_rate = weakest(ctrl, ("C1", "C2", "C3"), LEAK_42, set(WEAK_KINDS))
    wk_w_e, wk_w_e_rate = weakest(exp, ("E1", "E2", "E3"), LEAK_42, set(WEAK_KINDS))
    check("weakest_weak.ctrl", wk_w_c, cg_aud["weakest_weak_kind"])
    check("weakest_weak.ctrl.rate", wk_w_c_rate, cg_aud["weakest_weak_kind_rate"])
    check("weakest_weak.exp", wk_w_e, eg_aud["weakest_weak_kind"])
    check("weakest_weak.exp.rate", wk_w_e_rate, eg_aud["weakest_weak_kind_rate"])

    # ---- gains ----
    g = scored["gains"]
    m_tc = grp_mean(ctrl, ("C1", "C2", "C3"), qids)
    m_te_raw = grp_mean(exp, ("E1", "E2", "E3"), qids)
    m_tc_a = grp_mean(ctrl, ("C1", "C2", "C3"), qids, LEAK_42)
    m_te_a = grp_mean(exp, ("E1", "E2", "E3"), qids, LEAK_42)
    check("gains.G_raw", m_te_raw - m_tc, g["G_raw"])
    check("gains.G_excluded42", m_te_a - m_tc_a, g["G_excluded42"])
    check("gains.G_new_excluded42",
          grp_mean(exp, ("E1", "E2", "E3"), new_ids, LEAK_42)
          - grp_mean(ctrl, ("C1", "C2", "C3"), new_ids, LEAK_42),
          g["G_new_excluded42"])
    check("gains.G_B_excluded42",
          grp_mean(exp, ("E1", "E2", "E3"), b_ids, LEAK_42)
          - grp_mean(ctrl, ("C1", "C2", "C3"), b_ids, LEAK_42),
          g["G_B_excluded42"])
    check("gains.G_weak_excluded42",
          grp_mean(exp, ("E1", "E2", "E3"), weak_ids, LEAK_42)
          - grp_mean(ctrl, ("C1", "C2", "C3"), weak_ids, LEAK_42),
          g["G_weak_excluded42"])
    nk_gain = 0.0
    for kind in NEW_KINDS:
        kq = [q for q in qids if truth_kind[q] == kind]
        nk_gain += (grp_mean(exp, ("E1", "E2", "E3"), kq, LEAK_42)
                    - grp_mean(ctrl, ("C1", "C2", "C3"), kq, LEAK_42))
    check("gains.G_newkinds_excluded42", nk_gain, g["G_newkinds_excluded42"])

    # ---- paired averages + McNemar ----
    for audited, key in ((False, "average_raw"), (True, "average_excluded42")):
        sums = {"both": 0, "exp_only": 0, "control_only": 0, "neither": 0}
        for cb, eb in zip(("C1", "C2", "C3"), ("E1", "E2", "E3")):
            for q in qids:
                cc = correct(ctrl[cb], q) and (q not in LEAK_42 if audited else True)
                ec = correct(exp[eb], q) and (q not in LEAK_42 if audited else True)
                if ec and cc:
                    sums["both"] += 1
                elif ec:
                    sums["exp_only"] += 1
                elif cc:
                    sums["control_only"] += 1
                else:
                    sums["neither"] += 1
        for k, v in sums.items():
            check(f"paired.{key}.{k}", v / 3, scored["paired"][key][k])
    for cb, eb in zip(("C1", "C2", "C3"), ("E1", "E2", "E3")):
        pair = next(p for p in scored["paired"]["per_batch_pair_excluded42"]
                    if p["pair"] == f"{cb}-vs-{eb}")
        eo = sum(1 for q in qids if correct(exp[eb], q) and q not in LEAK_42
                 and not (correct(ctrl[cb], q) and q not in LEAK_42))
        co = sum(1 for q in qids if correct(ctrl[cb], q) and q not in LEAK_42
                 and not (correct(exp[eb], q) and q not in LEAK_42))
        check(f"mcnemar.{cb}-vs-{eb}.exp_only", eo, pair["exp_only"])
        check(f"mcnemar.{cb}-vs-{eb}.control_only", co, pair["control_only"])
        check(f"mcnemar.{cb}-vs-{eb}.p", mcnemar_p(eo, co),
              pair["mcnemar_exact_two_sided_p"])
    check("mcnemar.all_significant",
          all(mcnemar_p(
              sum(1 for q in qids if correct(exp[eb], q) and q not in LEAK_42
                  and not (correct(ctrl[cb], q) and q not in LEAK_42)),
              sum(1 for q in qids if correct(ctrl[cb], q) and q not in LEAK_42
                  and not (correct(exp[eb], q) and q not in LEAK_42))) < 0.05
              for cb, eb in zip(("C1", "C2", "C3"), ("E1", "E2", "E3"))),
          scored["mcnemar"]["all_pairs_significant_0.05"])

    # ---- decision rules (section 6.1) ----
    dr = scored["decision_rules"]
    G = m_te_a - m_tc_a
    G_new = (grp_mean(exp, ("E1", "E2", "E3"), new_ids, LEAK_42)
             - grp_mean(ctrl, ("C1", "C2", "C3"), new_ids, LEAK_42))
    s_tc_a = grp_spread(ctrl, ("C1", "C2", "C3"), qids, LEAK_42)
    s_te_a = grp_spread(exp, ("E1", "E2", "E3"), qids, LEAK_42)
    contrib = {}
    for q in qids:
        e = sum(1 for b in ("E1", "E2", "E3") if correct(exp[b], q) and q not in LEAK_42) / 3
        c = sum(1 for b in ("C1", "C2", "C3") if correct(ctrl[b], q) and q not in LEAK_42) / 3
        contrib[q] = e - c
    pos = [q for q, c in contrib.items() if c > 0]
    check("decision.(1)", G > max(11, max(s_tc_a, s_te_a)),
          dr["(1) G > max(11, round noise band)"]["pass"])
    check("decision.(2)", scored["mcnemar"]["all_pairs_significant_0.05"],
          dr["(2) McNemar two-sided p < 0.05 for every batch pair"]["pass"])
    check("decision.(3)", G >= 3, dr["(3) G >= 3"]["pass"])
    check("decision.(4)", len(pos) >= 2 and max(contrib.values()) < G / 2,
          dr["(4) gain from >=2 questions, no single question > half of gain"]["pass"])
    check("decision.(5)", wk_e_rate >= wk_c_rate,
          dr["(5) weakest kind does not fall"]["pass"])
    check("decision.(6)", G > 0,
          dr["(6) gain not on leaked questions (excluded gain survives)"]["pass"])

    # ---- H-W (weakest among the six weak kinds only) ----
    hw = scored["hypothesis_H_W"]
    check("HW.weakest_weak_kind", wk_w_e, hw["weakest_weak_kind_exp"])
    check("HW.weakest_weak_kind_rate", wk_w_e_rate, hw["weakest_weak_kind_rate_exp"])
    check("HW.weakest_rate_ge_50", wk_w_e_rate >= 0.5, hw["weak_kind_rate_ge_50pct"])
    check("HW.total_not_falling", m_te_a >= m_tc_a, hw["total_not_falling"])
    check("HW.weak_gain_gt_0",
          grp_mean(exp, ("E1", "E2", "E3"), weak_ids, LEAK_42)
          - grp_mean(ctrl, ("C1", "C2", "C3"), weak_ids, LEAK_42) > 0,
          hw["weak_total_gain_gt_0"])
    check("HW.falsified",
          wk_w_e_rate < 0.5 or m_te_a < m_tc_a
          or grp_mean(exp, ("E1", "E2", "E3"), weak_ids, LEAK_42)
          - grp_mean(ctrl, ("C1", "C2", "C3"), weak_ids, LEAK_42) <= 0,
          hw["falsified"])

    if failures:
        print(f"VERIFY FAIL: {len(failures)} mismatches")
        for f in failures[:50]:
            print("  ", f)
        sys.exit(1)
    print("VERIFY PASS: all recomputed numbers match " + SCORE_PATH + " "
          "(totals, old/new, A/B, weak, kind, player, model, capex, "
          "confidence, G/B/R, excluded42 rescores, leaked subset, gains, "
          "paired averages, McNemar p, decision rules, H-W)")


if __name__ == "__main__":
    main()
