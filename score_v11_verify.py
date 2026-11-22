#!/usr/bin/env python3
"""Independent re-check of round-11 scoring (score_v11.py output).

Re-reads testset-v7.json, all D1-D3 and C1-C3 prediction files, and the
audit exclusion list from scratch, with its own loops (no import of
score_v11). Recomputes: per-batch totals, old/new split, per-kind,
per-player, model-release 66, capex 10, confidence (pooled + per batch),
guidance/boundary citation rates, audited experiment scores, gains
(raw + audited), paired averages (raw + audited), decision-rule
booleans, roleplay-harm counts. Compares every number against
runs/round11-vision11-2026-11-22/score-v11.json and exits non-zero
on any mismatch.

Usage: python3 score_v11_verify.py
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
AUDIT_PATH = os.path.join(BASE, "runs", "baseline-retest-2026-11-22",
                          "audit-baseline-v7.json")

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
    print("VERIFY PASS: all recomputed numbers match score-v11.json "
          "(totals, old/new, kind, player, model, capex, confidence, G/B, "
          "audited scores, gains, paired averages, decision rules, harms)")


if __name__ == "__main__":
    main()
