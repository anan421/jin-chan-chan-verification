#!/usr/bin/env python3
"""Independent re-check of round-11 scoring (score_v11.py output).

Re-reads testset-v7.json, all D1-D3 and C1-C3 prediction files, and the
audit exclusion list from scratch, with its own loops (no import of
score_v11). Recomputes: per-batch totals, old/new split, per-kind,
per-player, model-release 66, capex 10, confidence (pooled + per batch),
guidance/boundary citation rates, audited experiment scores, audited
control scores, gains (raw + mixed audited + both-audited), paired
averages (raw + mixed audited + both-audited), decision-rule
booleans, roleplay-harm counts. Compares every number against
runs/round11-vision11-2026-11-22/score-v11.json and exits non-zero
on any mismatch. The both-audited checks run only when the scored
file carries the new keys (score_v11.py writes them since 2026-11-25).

Usage: python3 score_v11_verify.py [SCORED_JSON]
"""
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, "runs", "round11-vision11-2026-11-22")
CTRL_DIR = os.path.join(RUN, "predictions")
EXP_DIR = os.path.join(BASE, "runs", "baseline-retest-2026-11-22", "predictions")
SCORE_PATH = os.path.join(RUN, "score-v11.json")
if len(sys.argv) > 1:
    SCORE_PATH = sys.argv[1]
AUDIT_PATH = os.path.join(BASE, "runs", "baseline-retest-2026-11-22",
                          "audit-baseline-v7.json")
AUDIT_CTRL_PATH = os.path.join(RUN, "audit-v11.json")

MODEL = {"claude", "chatgpt", "gemini", "r1", "v3", "tongyi", "llama",
         "kimi", "muse", "glm", "minimax"}
NEW_KINDS = {"agent", "arr", "acquisition", "social", "partnership", "kimi",
             "math", "memory", "wallstreet", "talent", "video", "muse"}

failures = []


def check(name, got, want, tol=1e-9):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        failures.append(f"{name}: verify={got!r} score-v11={want!r}")


def read_batch(d, prefix):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, prefix + "-*.json"))):
        data = json.load(open(f))
        for rec in data["predictions"]:
            assert rec["q_id"] not in out, f"dup q{rec['q_id']} in {f}"
            out[rec["q_id"]] = rec
    return out


def main():
    ts = json.load(open(os.path.join(BASE, "testset-v7.json")))
    questions = ts["questions"]
    truth_kind = {q["q_id"]: q["kind"] for q in questions}
    truth_player = {q["q_id"]: q["player"] for q in questions}
    qids = sorted(truth_kind)
    assert len(qids) == 215 and set(qids) == set(range(216)) - {79}, "testset shape"
    old_ids = [q for q in qids if q <= 98]
    new_ids = [q for q in qids if q >= 99]
    assert len(old_ids) == 98 and len(new_ids) == 117
    capex_ids = [q for q in qids if truth_kind[q] == "capex"]
    dc_ids = [q for q in qids if truth_kind[q] == "datacenter"]
    model_ids = [q for q in qids if truth_kind[q] in MODEL]
    assert len(capex_ids) == 10 and len(model_ids) == 66

    scored = json.load(open(SCORE_PATH))
    audit = json.load(open(AUDIT_PATH))
    excl = audit["leakage_exclusion"]["by_batch"]
    audit_ctrl = json.load(open(AUDIT_CTRL_PATH))
    excl_ctrl = {"D1": [], "D2": [], "D3": []}
    for rec in audit_ctrl["exclusions"]["exclude"]:
        excl_ctrl[rec["batch"]].append(rec["q_id"])

    ctrl = {b: read_batch(CTRL_DIR, f"predictions-{b}") for b in ("D1", "D2", "D3")}
    exp = {b: read_batch(EXP_DIR, f"predictions-{b}") for b in ("C1", "C2", "C3")}
    for b, p in list(ctrl.items()) + list(exp.items()):
        assert set(p) == set(qids), f"{b} q set mismatch"

    def correct(preds, q):
        return preds[q].get("kind") == truth_kind[q]

    def cited(v):
        return isinstance(v, str) and v.strip() != ""

    # ---- per-batch control + experiment raw ----
    for group, batches, preds in (("control", ("D1", "D2", "D3"), ctrl),
                                  ("experiment_raw", ("C1", "C2", "C3"), exp)):
        for b in batches:
            p = preds[b]
            s = scored[group][b]
            tot = sum(1 for q in qids if correct(p, q))
            check(f"{group}.{b}.total", tot, s["total_215"][0])
            check(f"{group}.{b}.old", sum(1 for q in old_ids if correct(p, q)), s["old_98"][0])
            check(f"{group}.{b}.new", sum(1 for q in new_ids if correct(p, q)), s["new_117"][0])
            check(f"{group}.{b}.capex", sum(1 for q in capex_ids if correct(p, q)), s["capex_10"][0])
            check(f"{group}.{b}.model", sum(1 for q in model_ids if correct(p, q)), s["model_release_66"][0])
            for level in ("high", "medium", "low"):
                qs = [q for q in qids if p[q].get("confidence") == level]
                c = sum(1 for q in qs if correct(p, q))
                check(f"{group}.{b}.conf.{level}", [c, len(qs)], s["confidence"][level]["correct_total"])
            check(f"{group}.{b}.G", sum(1 for q in capex_ids if cited(p[q].get("guidance_cited"))),
                  s["guidance_citation"][0])
            check(f"{group}.{b}.B", sum(1 for q in set(capex_ids) | set(dc_ids)
                                        if cited(p[q].get("boundary_cited"))),
                  s["boundary_citation"][0])
            # per-kind
            for kind in sorted(set(truth_kind.values())):
                kq = [q for q in qids if truth_kind[q] == kind]
                c = sum(1 for q in kq if correct(p, q))
                check(f"{group}.{b}.kind.{kind}", c, s["by_kind"][kind][0])
                check(f"{group}.{b}.kind.{kind}.total", len(kq), s["by_kind"][kind][1])
            # per-player
            for pl in sorted(set(truth_player.values())):
                pq = [q for q in qids if truth_player[q] == pl]
                c = sum(1 for q in pq if correct(p, q))
                check(f"{group}.{b}.player.{pl}", c, s["by_player"][pl][0])

    # ---- audited experiment ----
    for b in ("C1", "C2", "C3"):
        p = exp[b]
        s = scored["experiment_audited"][b]
        ex = set(excl[b])
        tot = sum(1 for q in qids if correct(p, q) and q not in ex)
        check(f"audited.{b}.total", tot, s["total_215"][0])
        check(f"audited.{b}.old", sum(1 for q in old_ids if correct(p, q) and q not in ex), s["old_98"][0])
        check(f"audited.{b}.new", sum(1 for q in new_ids if correct(p, q) and q not in ex), s["new_117"][0])
        check(f"audited.{b}.capex", sum(1 for q in capex_ids if correct(p, q) and q not in ex), s["capex_10"][0])
        check(f"audited.{b}.model", sum(1 for q in model_ids if correct(p, q) and q not in ex), s["model_release_66"][0])
        for kind in sorted(set(truth_kind.values())):
            kq = [q for q in qids if truth_kind[q] == kind]
            c = sum(1 for q in kq if correct(p, q) and q not in ex)
            check(f"audited.{b}.kind.{kind}", c, s["by_kind"].get(kind, [0, 0])[0])

    # ---- audited control (both-audited caliber) ----
    # Same convention as the experiment audit: denominator stays 215,
    # an excluded record counts as not correct. Only checked when the
    # scored file carries the new keys.
    if "control_audited" in scored:
        for b in ("D1", "D2", "D3"):
            p = ctrl[b]
            s = scored["control_audited"][b]
            ex = set(excl_ctrl[b])
            tot = sum(1 for q in qids if correct(p, q) and q not in ex)
            check(f"control_audited.{b}.total", tot, s["total_215"][0])
            check(f"control_audited.{b}.old", sum(1 for q in old_ids if correct(p, q) and q not in ex), s["old_98"][0])
            check(f"control_audited.{b}.new", sum(1 for q in new_ids if correct(p, q) and q not in ex), s["new_117"][0])
            check(f"control_audited.{b}.capex", sum(1 for q in capex_ids if correct(p, q) and q not in ex), s["capex_10"][0])
            check(f"control_audited.{b}.model", sum(1 for q in model_ids if correct(p, q) and q not in ex), s["model_release_66"][0])
            for kind in sorted(set(truth_kind.values())):
                kq = [q for q in qids if truth_kind[q] == kind]
                c = sum(1 for q in kq if correct(p, q) and q not in ex)
                check(f"control_audited.{b}.kind.{kind}", c, s["by_kind"].get(kind, [0, 0])[0])
        cg_aud = scored["control_audited_group"]
        check("control_audited.mean",
              sum(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                  for b in ("D1", "D2", "D3")) / 3, cg_aud["mean"])
        check("control_audited.spread",
              max(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                  for b in ("D1", "D2", "D3"))
              - min(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                      for b in ("D1", "D2", "D3")), cg_aud["spread"])
        check("control_audited.old_mean",
              sum(sum(1 for q in old_ids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                  for b in ("D1", "D2", "D3")) / 3, cg_aud["old_98_mean"])
        check("control_audited.new_mean",
              sum(sum(1 for q in new_ids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                  for b in ("D1", "D2", "D3")) / 3, cg_aud["new_117_mean"])

    # ---- group means ----
    cg = scored["control_group"]
    check("control.mean", sum(sum(1 for q in qids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")) / 3,
          cg["mean"])
    check("control.spread",
          max(sum(1 for q in qids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3"))
          - min(sum(1 for q in qids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")),
          cg["spread"])
    check("control.old_mean",
          sum(sum(1 for q in old_ids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")) / 3,
          cg["old_98_mean"])
    check("control.new_mean",
          sum(sum(1 for q in new_ids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")) / 3,
          cg["new_117_mean"])
    # pooled confidence, control
    for level in ("high", "medium", "low"):
        c = sum(sum(1 for q in qids if ctrl[b][q].get("confidence") == level and correct(ctrl[b], q))
                for b in ("D1", "D2", "D3"))
        n = sum(sum(1 for q in qids if ctrl[b][q].get("confidence") == level)
                for b in ("D1", "D2", "D3"))
        check(f"control.conf_pooled.{level}", [c, n], cg["confidence_pooled"][level]["correct_total"])

    # ---- gains ----
    g = scored["gains"]
    m_td = sum(sum(1 for q in qids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")) / 3
    m_te_raw = sum(sum(1 for q in qids if correct(exp[b], q)) for b in ("C1", "C2", "C3")) / 3
    m_te_aud = sum(sum(1 for q in qids if correct(exp[b], q) and q not in set(excl[b]))
                   for b in ("C1", "C2", "C3")) / 3
    check("gains.G_raw", m_te_raw - m_td, g["G_raw"])
    check("gains.G_audited", m_te_aud - m_td, g["G_audited"])
    m_te_new_raw = sum(sum(1 for q in new_ids if correct(exp[b], q)) for b in ("C1", "C2", "C3")) / 3
    m_te_new_aud = sum(sum(1 for q in new_ids if correct(exp[b], q) and q not in set(excl[b]))
                     for b in ("C1", "C2", "C3")) / 3
    m_td_new = sum(sum(1 for q in new_ids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")) / 3
    check("gains.G_new_raw", m_te_new_raw - m_td_new, g["G_new_raw"])
    check("gains.G_new_audited", m_te_new_aud - m_td_new, g["G_new_audited"])
    # ---- both-audited caliber (report G): only in new output ----
    if "G_both_audited" in g:
        m_td_aud = sum(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                       for b in ("D1", "D2", "D3")) / 3
        m_td_old_aud = sum(sum(1 for q in old_ids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                           for b in ("D1", "D2", "D3")) / 3
        m_td_new_aud = sum(sum(1 for q in new_ids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                           for b in ("D1", "D2", "D3")) / 3
        m_te_old_aud = sum(sum(1 for q in old_ids if correct(exp[b], q) and q not in set(excl[b]))
                           for b in ("C1", "C2", "C3")) / 3
        check("gains.M_TD_audited", m_td_aud, g["M_TD_audited"])
        check("gains.G_both_audited", m_te_aud - m_td_aud, g["G_both_audited"])
        check("gains.G_mixed_alias", m_te_aud - m_td, g["G_mixed_audited_exp_raw_control"])
        check("gains.G_new_both_audited", m_te_new_aud - m_td_new_aud, g["G_new_both_audited"])
        check("gains.G_old_both_audited", m_te_old_aud - m_td_old_aud, g["G_old_both_audited"])
        check("gains.caliber_difference", (m_te_aud - m_td_aud) - (m_te_aud - m_td),
              scored["gain_calibers"]["difference_B_minus_A"])
        check("gains.caliber_difference_is_control_adjustment", m_td - m_td_aud,
              scored["gain_calibers"]["difference_B_minus_A"])

    # ---- paired averages ----
    for audited in (False, True):
        key = "average_audited" if audited else "average_raw"
        sums = {"both": 0, "exp_only": 0, "control_only": 0, "neither": 0}
        for db, eb in zip(("D1", "D2", "D3"), ("C1", "C2", "C3")):
            for q in qids:
                dc = correct(ctrl[db], q)
                ec = correct(exp[eb], q) and (q not in set(excl[eb]) if audited else True)
                if ec and dc:
                    sums["both"] += 1
                elif ec:
                    sums["exp_only"] += 1
                elif dc:
                    sums["control_only"] += 1
                else:
                    sums["neither"] += 1
        for k, v in sums.items():
            check(f"paired.{key}.{k}", v / 3, scored["paired"][key][k])

    # ---- paired averages, both-audited ----
    if "average_both_audited" in scored["paired"]:
        sums = {"both": 0, "exp_only": 0, "control_only": 0, "neither": 0}
        for db, eb in zip(("D1", "D2", "D3"), ("C1", "C2", "C3")):
            for q in qids:
                dc = correct(ctrl[db], q) and q not in set(excl_ctrl[db])
                ec = correct(exp[eb], q) and q not in set(excl[eb])
                if ec and dc:
                    sums["both"] += 1
                elif ec:
                    sums["exp_only"] += 1
                elif dc:
                    sums["control_only"] += 1
                else:
                    sums["neither"] += 1
        for k, v in sums.items():
            check(f"paired.average_both_audited.{k}", v / 3,
                  scored["paired"]["average_both_audited"][k])

    # ---- decision rules (audited primary) ----
    dr = scored["decision_rules"]["audited_primary"]
    G = m_te_aud - m_td
    G_new = m_te_new_aud - m_td_new
    s_td = max(sum(1 for q in qids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3")) \
        - min(sum(1 for q in qids if correct(ctrl[b], q)) for b in ("D1", "D2", "D3"))
    s_te_aud = max(sum(1 for q in qids if correct(exp[b], q) and q not in set(excl[b])) for b in ("C1", "C2", "C3")) \
        - min(sum(1 for q in qids if correct(exp[b], q) and q not in set(excl[b])) for b in ("C1", "C2", "C3"))
    contrib = {}
    for q in qids:
        e = sum(1 for b in ("C1", "C2", "C3") if correct(exp[b], q) and q not in set(excl[b])) / 3
        d = sum(1 for b in ("D1", "D2", "D3") if correct(ctrl[b], q)) / 3
        contrib[q] = e - d
    pos = [q for q, c in contrib.items() if c > 0]
    check("decision.audited.(a)", G > max(s_td, s_te_aud), dr["(a) G > max(S_TD,S_TE)"]["pass"])
    check("decision.audited.(b)", G >= 3, dr["(b) G >= 3"]["pass"])
    check("decision.audited.(c)", G_new > 0, dr["(c) G_new > 0"]["pass"])
    check("decision.audited.(d)", len(pos) >= 2 and max(contrib.values()) < G / 2,
          dr["(d) gain from >=2 questions, no single question > half of gain"]["pass"])

    # ---- decision rules, both-audited caliber (report G) ----
    if "both_audited" in scored["decision_rules"]:
        dr_b = scored["decision_rules"]["both_audited"]
        G_b = m_te_aud - (sum(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                              for b in ("D1", "D2", "D3")) / 3)
        m_td_new_aud = sum(sum(1 for q in new_ids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                           for b in ("D1", "D2", "D3")) / 3
        G_new_b = m_te_new_aud - m_td_new_aud
        s_td_aud = (max(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                        for b in ("D1", "D2", "D3"))
                    - min(sum(1 for q in qids if correct(ctrl[b], q) and q not in set(excl_ctrl[b]))
                          for b in ("D1", "D2", "D3")))
        contrib_b = {}
        for q in qids:
            e = sum(1 for b in ("C1", "C2", "C3") if correct(exp[b], q) and q not in set(excl[b])) / 3
            d = sum(1 for b in ("D1", "D2", "D3") if correct(ctrl[b], q) and q not in set(excl_ctrl[b])) / 3
            contrib_b[q] = e - d
        pos_b = [q for q, c in contrib_b.items() if c > 0]
        check("decision.both_audited.(a)", G_b > max(s_td_aud, s_te_aud),
              dr_b["(a) G > max(S_TD,S_TE)"]["pass"])
        check("decision.both_audited.(b)", G_b >= 3, dr_b["(b) G >= 3"]["pass"])
        check("decision.both_audited.(c)", G_new_b > 0, dr_b["(c) G_new > 0"]["pass"])
        check("decision.both_audited.(d)", len(pos_b) >= 2 and max(contrib_b.values()) < G_b / 2,
              dr_b["(d) gain from >=2 questions, no single question > half of gain"]["pass"])

    # ---- roleplay harms ----
    rh = scored["roleplay_harms"]
    strict = [q for q in qids if truth_kind[q] in NEW_KINDS
              and sum(1 for b in ("C1", "C2", "C3") if correct(exp[b], q) and q not in set(excl[b])) == 0
              and sum(1 for b in ("D1", "D2", "D3") if correct(ctrl[b], q)) >= 1]
    check("harms.strict_new_kind.count", len(strict), rh["counts"]["strict_new_kind"])
    check("harms.strict_new_kind.qids", sorted(strict),
          sorted(p["q_id"] for p in rh["strict_exp0_control_ge1_new_kind"]))

    if failures:
        print(f"VERIFY FAIL: {len(failures)} mismatches")
        for f in failures[:50]:
            print("  ", f)
        sys.exit(1)
    print("VERIFY PASS: all recomputed numbers match " + SCORE_PATH + " "
          "(totals, old/new, kind, player, model, capex, confidence, G/B, "
          "audited scores, gains incl. both-audited caliber, paired averages, "
          "decision rules, harms)")


if __name__ == "__main__":
    main()
