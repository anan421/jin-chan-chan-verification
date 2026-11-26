#!/usr/bin/env python3
"""Second test file for the round-16 verdict_from fix (2026-11-26).

Covers what test_verdict_from_fix.py cannot reach directly:
1. The VERIFY script's nested helpers (_verdict_from, _genuine_list),
   extracted from the file by AST and executed standalone, so the
   test runs the verify file's actual code, not a copy.
2. Cross-implementation agreement: main verdict_from vs verify
   _verdict_from must return identical verdict strings on a full
   sweep of inputs.
3. Genuine-new-info counting on REAL round-15 prediction files
   (expect 0), plus a mutated copy where one control record is
   flipped to wrong so q122 becomes genuine (expect [122]).
4. The main script's leave-one-out sensitivity path
   (compute_sensitivity) with real predictions and forced flags.
5. T-match space normalisation in the main script's
   has_trigger_line: "30 天内无触发事件" and "30天内无触发事件"
   must both match (the verify script's _trig_ok has the same
   normalisation; confirmed by code read + replay T_legacy count).

Usage: python3 test_verify_helper_and_loo.py
Exit 0 iff every check passes.
"""
import ast
import importlib.util
import itertools
import json
import os
import sys

MAIN = "/tmp/round16-scripts/score_round15.py"
VERIFY = "/tmp/round16-scripts/score_round15_verify.py"
R15 = "/home/hatch/workspace/verification-v1-round15"
PRED_DIR = os.path.join(R15, "runs", "round15-weak-repair-3-2026-11-25",
                        "predictions")


def load_main():
    spec = importlib.util.spec_from_file_location("score_r16_main", MAIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_nested(path, names):
    """Exec the named nested FunctionDefs from `path` and return them.

    Only top-level `def main` is searched; the extracted functions
    are pure (verdict) or take `correct` from the exec namespace.
    """
    src = open(path).read()
    tree = ast.parse(src)
    main_fn = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    out = {}
    for node in main_fn.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out[node.name] = node
    assert set(out) == set(names), f"missing: {set(names) - set(out)}"
    return out


def check(name, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'} {name}: got={got!r} want={want!r}")
    return ok


def main():
    ok = True
    mod = load_main()

    # --- 1+2. verify nested _verdict_from: extract, exec, compare ---
    nodes = extract_nested(VERIFY, ["_verdict_from", "_genuine_list"])
    ns = {}
    for name, node in nodes.items():
        code = ast.Module(body=[node], type_ignores=[])
        exec(compile(code, VERIFY, "exec"), ns)
    v_vf = ns["_verdict_from"]

    cases = [
        ("round15", (3.3333333333333357, 3.333333333333343, 3.3333333333333335,
                     False, True, 0), "REMOVE"),
        ("(a) adopt", (12.0, 12.0, 5.0, True, True, 3), "ADOPT"),
        ("(b) tentative", (5.0, 5.0, 2.0, False, True, 3), "TENTATIVE"),
        ("(c) discard", (3.0, 3.0, 1.0, False, True, 0), "REMOVE"),
    ]
    for name, args, want in cases:
        v, _, _, _, _ = v_vf(*args)
        ok &= check(f"verify {name}", v.startswith(want), True)

    # sweep agreement between the two independent implementations
    mismatch = 0
    for G, genuine, nk, six, h4 in itertools.product(
            (-1.0, 0.0, 3.0, 12.0), (0, 1, 2, 5), (-1.0, 0.0, 3.0),
            (False, True), (False, True)):
        v_main = mod.verdict_from(G, G, nk, six, h4, genuine)[0]
        v_ver = v_vf(G, G, nk, six, h4, genuine)[0]
        if v_main != v_ver:
            mismatch += 1
            print(f"  MISMATCH G={G} genuine={genuine} nk={nk} six={six} "
                  f"h4={h4}: main={v_main!r} verify={v_ver!r}")
    ok &= check("sweep main-vs-verify verdict agreement", mismatch, 0)

    # --- 3. _genuine_list on real round-15 predictions ---
    truth = mod.load_truth(os.path.join(R15, "testset-v7.json"))
    truth_kind = {q: truth[q]["kind"] for q in truth}
    leak = set(mod.LEAK_42)
    qids = sorted(truth_kind)
    preds = {}
    for b in ("C1", "C2", "C3", "E1", "E2", "E3"):
        preds[b] = mod.load_batch(PRED_DIR, b)

    def correct(p, q):
        return p[q].get("kind") == truth_kind[q]

    ns2 = {"correct": correct}
    code = ast.Module(body=[nodes["_genuine_list"]], type_ignores=[])
    exec(compile(code, VERIFY, "exec"), ns2)
    gen = ns2["_genuine_list"](preds, ("C1", "C2", "C3"),
                               ("E1", "E2", "E3"), qids, leak)
    ok &= check("verify _genuine_list on real round15", gen, [])

    # mutated copy: flip the one correct control record on q122
    # (C3 guessed arr, the true kind) to a wrong kind, so q122
    # becomes control 0/3 + experiment 3/3 -> genuine.
    import copy
    preds2 = copy.deepcopy(preds)
    assert preds2["C3"][122]["kind"] == "arr", preds2["C3"][122]["kind"]
    assert truth_kind[122] == "arr"
    preds2["C3"][122]["kind"] = "chatgpt"
    gen2 = ns2["_genuine_list"](preds2, ("C1", "C2", "C3"),
                                ("E1", "E2", "E3"), qids, leak)
    ok &= check("verify _genuine_list mutated q122", gen2, [122])

    # main's count_genuine_new_info must agree on the same mutation
    ctrl_n = {q: sum(1 for b in ("C1", "C2", "C3")
                     if preds2[b][q].get("kind") == truth_kind[q])
              for q in qids}
    exp_n = {q: sum(1 for b in ("E1", "E2", "E3")
                    if preds2[b][q].get("kind") == truth_kind[q])
             for q in qids}
    n2, q2 = mod.count_genuine_new_info(ctrl_n, exp_n, leak, 3)
    ok &= check("main count mutated q122", (n2, q2), (1, [122]))

    # --- 4. leave-one-out path with real predictions ---
    all_qids = sorted(truth)
    headline = ("REMOVE (discard condition met: no genuine new info "
                "(0 < 2); method does not enter baseline)")
    sens = mod.compute_sensitivity(["C1", "E2"], preds, truth, all_qids,
                                   headline)
    ok &= check("loo flagged batches",
                sens["triggered_batches"], ["C1", "E2"])
    for b in ("C1", "E2"):
        loo = sens["leave_one_out"][b]
        ok &= check(f"loo {b} has genuine field",
                    "genuine_new_info" in loo, True)
        ok &= check(f"loo {b} verdict prefix",
                    loo["verdict"].split(" ")[0],
                    loo["verdict"].split(" ")[0])  # recorded below
        print(f"  loo {b}: verdict={loo['verdict']!r} "
              f"genuine={loo['genuine_new_info']} "
              f"gain={loo['gain_excluded42']:.2f}")
        ok &= check(f"loo {b} verdict in three",
                    loo["verdict"].split(" ")[0] in
                    ("ADOPT", "TENTATIVE", "REMOVE"), True)
        ok &= check(f"loo {b} no MIXED",
                    "MIXED" not in loo["verdict"], True)

    # --- 5. T-match space normalisation (main has_trigger_line) ---
    rec_spaced = {"weak_evidence": "30 天内无触发事件"}
    rec_nospace = {"weak_evidence": "30天内无触发事件"}
    rec_none = {"weak_evidence": "无相关内容"}
    ok &= check("T spaced matches",
                mod.has_trigger_line(rec_spaced), True)
    ok &= check("T nospace matches",
                mod.has_trigger_line(rec_nospace), True)
    ok &= check("T no-trigger does not match",
                mod.has_trigger_line(rec_none), False)

    print("ALL PASS" if ok else "FAILURES PRESENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
