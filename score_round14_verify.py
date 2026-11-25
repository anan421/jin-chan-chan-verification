#!/usr/bin/env python3
"""Independent re-check of round-14 scoring (score_round14.py output).

Re-reads testset-v7.json and all C1-C3 / E1-E3 prediction files from
scratch, with its own loops (no import of score_round14). Recomputes:
per-batch totals, old/new split, v7-A/v7-B split, weak-45 split,
weak-by-kind, per-kind, per-player, model-release 66, capex 10,
claude 16, trap-kind counts (5 kinds), confidence (pooled + per
batch), guidance/boundary citation rates, roleplay execution,
forced-step execution rates (total / N-step / T-check-row, pooled
over the experiment group), legal-milestone guard, claude template
audit, sentinels q145/q195/q186, leakage-excluded (42-list)
rescores, leaked-subset scores, group means and spreads, weakest
kind, gains (raw + excluded42, new/old/A/B/weak/new-kinds),
paired averages (raw + excluded42), McNemar exact two-sided p per
pair, decision-rule booleans (protocol section 6.1 + H4 side-effect
gate), H-14 fields. Compares every number against
runs/round14-weak-repair-2-2026-11-25/score-round14.json and
exits non-zero on any mismatch.

When no prediction files exist yet, only the reproduction gates and
the leakage-exclusion note are checked.

Usage: python3 score_round14_verify.py [SCORED_JSON]
"""
import glob
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, "runs", "round14-weak-repair-2-2026-11-25")
PRED_DIR = os.path.join(RUN, "predictions")
SCORE_PATH = os.path.join(RUN, "score-round14.json")
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
NUMERIC_QIDS = set(range(121, 134)) | {213}
TRAP_KINDS = ["open_source", "ascend", "compliance", "generic",
              "openai_mar26"]
TREND_WORDS = ("涨", "跌", "持平", "上升", "下降", "增长", "减少", "趋势",
               "加速", "减速")

failures = []


def check(name, got, want, tol=1e-9):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        failures.append(f"{name}: verify={got!r} score-round14={want!r}")


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
    claude_ids = [q for q in qids if truth_kind[q] == "claude"]
    assert len(claude_ids) == 16
    assert len(old_ids) == 98 and len(new_ids) == 117
    assert len(a_ids) == 108 and len(b_ids) == 107 and len(weak_ids) == 45
    assert len(capex_ids) == 10 and len(model_ids) == 66

    scored = json.load(open(SCORE_PATH))

    # ---- reproduction gates ----
    gates = scored.get("reproduction_gates")
    assert gates, "no reproduction_gates in scored file"
    for gkey in ("gate_0_round10_focus", "gate_1_v7_baseline_retest_audited",
                 "gate_2_round11_control_audited", "gate_2_gain_both_audited",
                 "gate_3_round12_control_raw", "gate_4_round13_control_raw",
                 "gate_4_round13_control_excluded42"):
        check(f"gates.{gkey}.status", gates[gkey]["status"], "PASS")
    check("gates.gate_1.got", gates["gate_1_v7_baseline_retest_audited"]["got"],
          {"C1": 96, "C2": 104, "C3": 93})
    check("gates.gate_2.got", gates["gate_2_round11_control_audited"]["got"],
          {"D1": 90, "D2": 94, "D3": 93})
    check("gates.gate_2.gain", gates["gate_2_gain_both_audited"]["got"], 5.33)
    check("gates.gate_3.got", gates["gate_3_round12_control_raw"]["got"],
          {"C1": 63, "C2": 59, "C3": 64})
    check("gates.gate_4.raw.got", gates["gate_4_round13_control_raw"]["got"],
          {"C1": 73, "C2": 70, "C3": 66})
    check("gates.gate_4.excl.got", gates["gate_4_round13_control_excluded42"]["got"],
          {"C1": 62, "C2": 61, "C3": 61})

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
            check(f"{group}.{b}.claude", tot(p, claude_ids), s["claude_16"][0])
            check(f"{group}.{b}.trap_total",
                  sum(1 for q in qids if p[q].get("kind") in TRAP_KINDS),
                  s["trap_total"][0])
            for tk in TRAP_KINDS:
                check(f"{group}.{b}.trap.{tk}",
                      sum(1 for q in qids if p[q].get("kind") == tk),
                      s["trap_counts"][tk])
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
            check(f"{group}.{b}.generic",
                  sum(1 for q in qids if p[q].get("kind") == "generic"),
                  s["generic_guesses"][0])
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
            check(f"{key}.{b}.claude", tot(p, claude_ids, LEAK_42), s["claude_16"][0])
            check(f"{key}.{b}.trap_total",
                  sum(1 for q in qids if p[q].get("kind") in TRAP_KINDS
                      and q not in LEAK_42),
                  s["trap_total"][0])
            for tk in TRAP_KINDS:
                check(f"{key}.{b}.trap.{tk}",
                      sum(1 for q in qids if p[q].get("kind") == tk
                          and q not in LEAK_42),
                      s["trap_counts"][tk])
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
    check("control.generic_mean",
          sum(sum(1 for q in qids if ctrl[b][q].get("kind") == "generic")
              for b in ("C1", "C2", "C3")) / 3, cg["generic_guesses_mean"])
    check("exp_raw.mean", grp_mean(exp, ("E1", "E2", "E3"), qids), eg_raw["mean"])
    check("exp_raw.generic_mean",
          sum(sum(1 for q in qids if exp[b][q].get("kind") == "generic")
              for b in ("E1", "E2", "E3")) / 3, eg_raw["generic_guesses_mean"])
    check("control_excl.generic_mean",
          sum(sum(1 for q in qids if ctrl[b][q].get("kind") == "generic"
                  and q not in LEAK_42)
              for b in ("C1", "C2", "C3")) / 3, cg_aud["generic_guesses_mean"])
    check("exp_excl.generic_mean",
          sum(sum(1 for q in qids if exp[b][q].get("kind") == "generic"
                  and q not in LEAK_42)
              for b in ("E1", "E2", "E3")) / 3, eg_aud["generic_guesses_mean"])
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

    # ---- forced-step execution (independent re-implementation) ----
    import re as _re
    def _dates(text):
        found = set()
        rest = text or ""
        for pat in (_re.compile(r"\d{4}-\d{2}-\d{2}"),
                    _re.compile(r"\d{8}"),
                    _re.compile(r"\d{4}年\d{1,2}月\d{1,2}日"),
                    _re.compile(r"\d{4}年\d{1,2}月")):
            for m in pat.findall(rest):
                found.add(m)
            rest = pat.sub(" ", rest)
        for m in _re.findall(r"(?<!\d)\d{6}(?!\d)", rest):
            found.add(m)
        return found
    def _rule_o_ok(p):
        for f in ("problem_type", "weak_rule", "weak_evidence", "kind"):
            v = p.get(f)
            if not isinstance(v, str) or not v.strip():
                return False
        prob = p.get("probability")
        if isinstance(prob, bool) or not isinstance(prob, (int, float)):
            return False
        return 0.0 <= prob <= 1.0 and p.get("confidence") in ("high", "medium", "low")
    def _trig_ok(p):
        ev = p.get("weak_evidence")
        if not isinstance(ev, str) or not ev.strip() or "触发" not in ev:
            return False
        return bool(_dates(ev)) or ("30 天内无触发事件" in ev)
    def _n_ok(p):
        ev = p.get("weak_evidence")
        if not isinstance(ev, str) or not ev.strip():
            return False
        return len(_dates(ev)) >= 2 and any(w in ev for w in TREND_WORDS)
    fse = scored["forced_step_execution"]["experiment"]["pooled"]
    tot_e = sum(1 for b in ("E1", "E2", "E3") for q in weak_ids if _rule_o_ok(exp[b][q]))
    tot_t = sum(1 for b in ("E1", "E2", "E3") for q in weak_ids if _trig_ok(exp[b][q]))
    tot_n = sum(1 for b in ("E1", "E2", "E3") for q in sorted(NUMERIC_QIDS)
                if _n_ok(exp[b][q]))
    check("exec.total", tot_e, fse["total_exec"][0])
    check("exec.total_rate", tot_e / 135, fse["total_exec_rate"])
    check("exec.total_pass", tot_e / 135 >= 0.90, fse["total_exec_pass"])
    check("exec.n", tot_n, fse["n_exec"][0])
    check("exec.n_rate", tot_n / 42, fse["n_exec_rate"])
    check("exec.n_pass", tot_n / 42 >= 0.90, fse["n_exec_pass"])
    check("exec.trigger", tot_t, fse["trigger_present"][0])
    check("exec.trigger_rate", tot_t / 135, fse["trigger_rate"])
    check("exec.trigger_pass", tot_t / 135 >= 0.90, fse["trigger_pass"])
    check("exec.all_three",
          tot_e / 135 >= 0.90 and tot_n / 42 >= 0.90 and tot_t / 135 >= 0.90,
          scored["forced_step_execution"]["experiment"]["all_three_pass"])
    l_count = sum(1 for b in ("E1", "E2", "E3") for q in qids
                  if isinstance(exp[b][q].get("weak_evidence"), str)
                  and "里程碑" in exp[b][q]["weak_evidence"])
    lg = scored["forced_step_execution"]["legal_milestone_guard"]
    check("exec.L_records", l_count, lg["experiment_records"])
    check("exec.L_over", l_count > 3, lg["over_trigger"])
    # claude template audit
    tmpl = [(b, q) for b in ("E1", "E2", "E3") for q in claude_ids
            if "顺最近动作线" in (exp[b][q].get("reason") or "")]
    tmpl_c = sum(1 for b, q in tmpl if correct(exp[b], q))
    ta = scored["claude_template_audit"]
    check("template.records", len(tmpl), ta["template_records"])
    check("template.correct", tmpl_c, ta["template_correct"])
    check("template.rate", tmpl_c / len(tmpl) if tmpl else None,
          ta["template_correct_rate"])
    check("template.supported",
          len(tmpl) >= 12 and bool(tmpl) and tmpl_c / len(tmpl) < 0.50,
          ta["mechanism_supported"])
    # sentinels
    sent = scored["sentinels"]
    for qid, key in ((145, "q145"), (195, "q195"), (186, "q186")):
        check(f"sentinel.{key}.ctrl",
              sum(1 for b in ("C1", "C2", "C3") if correct(ctrl[b], qid)),
              sent[key]["control_correct_batches"])
        check(f"sentinel.{key}.exp",
              sum(1 for b in ("E1", "E2", "E3") if correct(exp[b], qid)),
              sent[key]["experiment_correct_batches"])
    # claude group means + trap group means
    check("claude_mean.ctrl_excl",
          grp_mean(ctrl, ("C1", "C2", "C3"), claude_ids, LEAK_42),
          cg_aud["claude_16_mean"])
    check("claude_mean.exp_excl",
          grp_mean(exp, ("E1", "E2", "E3"), claude_ids, LEAK_42),
          eg_aud["claude_16_mean"])
    check("trap_mean.exp_raw",
          sum(sum(1 for q in qids if exp[b][q].get("kind") in TRAP_KINDS)
              for b in ("E1", "E2", "E3")) / 3,
          eg_raw["trap_total_mean"])
    check("trap_mean.ctrl_raw",
          sum(sum(1 for q in qids if ctrl[b][q].get("kind") in TRAP_KINDS)
              for b in ("C1", "C2", "C3")) / 3,
          cg["trap_total_mean"])

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
    check("decision.(5)", wk_w_e_rate >= wk_w_c_rate,
          dr["(5) weakest kind does not fall"]["pass"])
    check("decision.(6)", G > 0,
          dr["(6) gain not on leaked questions (excluded gain survives)"]["pass"])
    check("decision.(H4)",
          grp_mean(exp, ("E1", "E2", "E3"), claude_ids, LEAK_42)
          >= grp_mean(ctrl, ("C1", "C2", "C3"), claude_ids, LEAK_42) - 2,
          dr["(H4) claude side-effect gate: exp claude mean >= control claude mean - 2"]["pass"])
    check("decision.adopt_all_six_plus_H4",
          all(dr[k]["pass"] for k in dr
              if isinstance(dr[k], dict) and "pass" in dr[k]),
          dr["adopt_all_six_plus_H4"])

    # ---- H-14 (weak repair; comparator is this round's control) ----
    h14 = scored["hypothesis_H_14"]
    s_tc_a2 = grp_spread(ctrl, ("C1", "C2", "C3"), qids, LEAK_42)
    s_te_a2 = grp_spread(exp, ("E1", "E2", "E3"), qids, LEAK_42)
    h1 = m_te_a - m_tc_a
    h2 = (grp_mean(exp, ("E1", "E2", "E3"), weak_ids, LEAK_42)
          - grp_mean(ctrl, ("C1", "C2", "C3"), weak_ids, LEAK_42))
    h3 = (tot_e / 135 >= 0.90 and tot_n / 42 >= 0.90 and tot_t / 135 >= 0.90)
    h4_ok = (grp_mean(exp, ("E1", "E2", "E3"), claude_ids, LEAK_42)
             >= grp_mean(ctrl, ("C1", "C2", "C3"), claude_ids, LEAK_42) - 2)
    check("H14.H1_gain", h1, h14["H1_gain_excluded42"])
    check("H14.H1_threshold", max(11, max(s_tc_a2, s_te_a2)),
          h14["H1_threshold_max_11_round_noise_band"])
    check("H14.H1_pass", h1 > max(11, max(s_tc_a2, s_te_a2)), h14["H1_pass"])
    check("H14.H2_weak_gain", h2, h14["H2_weak_gain"])
    check("H14.H2_pass", h2 >= 3, h14["H2_pass"])
    check("H14.H3_exec_pass", h3, h14["H3_execution_pass"])
    check("H14.H4_pass", h4_ok, h14["H4_pass"])
    check("H14.input_gain",
          grp_mean(ctrl, ("C1", "C2", "C3"), weak_ids) - 1.00,
          h14["weak_gain_decomposition_design_3_5"]["input_gain_weak"])
    check("H14.program_gain", h2,
          h14["weak_gain_decomposition_design_3_5"]["program_gain_weak"])
    check("H14.capex_exp_raw",
          grp_mean(exp, ("E1", "E2", "E3"), capex_ids),
          h14["capex_10_mean_exp_raw"])
    check("H14.capex_exp_excluded42_is_zero",
          grp_mean(exp, ("E1", "E2", "E3"), capex_ids, LEAK_42),
          h14["capex_10_mean_exp_excluded42"])
    check("H14.weakest_weak_kind", wk_w_e, h14["weakest_weak_kind_exp"])
    check("H14.weakest_weak_kind_rate", wk_w_e_rate, h14["weakest_weak_kind_rate_exp"])
    check("H14.weakest_all43", wk_e, h14["weakest_kind_all43_exp"])
    check("H14.weakest_all43_rate", wk_e_rate, h14["weakest_kind_all43_rate_exp"])
    check("H14.falsified",
          h1 <= max(11, max(s_tc_a2, s_te_a2)) or h2 < 3 or not h3 or not h4_ok,
          h14["falsified"])

    if failures:
        print(f"VERIFY FAIL: {len(failures)} mismatches")
        for f in failures[:50]:
            print("  ", f)
        sys.exit(1)
    print("VERIFY PASS: all recomputed numbers match " + SCORE_PATH + " "
          "(totals, old/new, A/B, weak, kind, player, model, capex, claude, "
          "trap, confidence, G/B/R, execution rates, template audit, "
          "sentinels, excluded42 rescores, leaked subset, gains, "
          "paired averages, McNemar p, decision rules, H-14)")


if __name__ == "__main__":
    main()
