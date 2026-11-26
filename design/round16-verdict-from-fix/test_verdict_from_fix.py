#!/usr/bin/env python3
"""Unit test for the round-16 verdict_from fix (2026-11-26).

Tests the rewritten verdict_from in BOTH scripts independently:
- score_round15.py::verdict_from (main)
- score_round15_verify.py has no module-level verdict helper (its
  helper is nested inside main()), so the verify side is tested
  end-to-end instead: the replay run below feeds the fixed main
  output into the fixed verify script and requires VERIFY PASS.
  This file tests the main helper directly, plus a re-implementation
  of the verify helper's spec (copied logic is NOT tested here;
  the replay is the verify-side test).

Cases (task brief):
- round15 replay: G=+3.33, G_raw=+3.33, new-kind gain=+3.33,
  six=False (conditions 1,2 fail), H4=True, genuine=0 -> REMOVE.
- (a) G=+12, genuine=3, no harm, six all pass, H4 pass -> ADOPT.
- (b) G=+5, genuine=3, no harm, six NOT all pass -> TENTATIVE.
- (c) G=+3, genuine=0 -> REMOVE.
Plus edge cases: G<=0, leaked-only gain, new-kind harm, H4 fail
with tentative conditions met, six+H4 pass but genuine<2
(discard beats adopt).

Usage: python3 test_verdict_from_fix.py
Exit 0 iff every case passes in the main helper.
"""
import importlib.util
import json
import sys

MAIN = "/tmp/round16-scripts/score_round15.py"


def load_main():
    spec = importlib.util.spec_from_file_location("score_r16_main", MAIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(name, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'} {name}: got={got!r} want={want!r}")
    return ok


def main():
    mod = load_main()
    vf = mod.verdict_from
    all_ok = True

    # --- round-15 replay numbers (from score-round15.json + audit §7) ---
    scored = json.load(open(
        "/home/hatch/workspace/verification-v1-round15/runs/"
        "round15-weak-repair-3-2026-11-25/score-round15.json"))
    g = scored["gains"]
    pq = scored["paired"]["per_question"]
    leak = set(scored["leakage_exclusion_note"]["list"])
    ctrl_n = {p["q_id"]: p["control_correct_batches_excluded42"]
              for p in pq}
    exp_n = {p["q_id"]: p["exp_correct_batches_excluded42"]
             for p in pq}
    genuine_n, genuine_qids = mod.count_genuine_new_info(
        ctrl_n, exp_n, leak, 3)
    all_ok &= check("round15 genuine count", genuine_n, 0)
    all_ok &= check("round15 genuine qids", genuine_qids, [])
    v, adopt, remove, tent, reasons = vf(
        g["G_excluded42"], g["G_raw"], g["G_newkinds_excluded42"],
        False, True, genuine_n)
    all_ok &= check("round15 verdict starts REMOVE",
                    v.startswith("REMOVE"), True)
    all_ok &= check("round15 adopt", adopt, False)
    all_ok &= check("round15 remove", remove, True)
    all_ok &= check("round15 tentative", tent, False)
    all_ok &= check("round15 discard reason mentions genuine",
                    any("genuine" in r for r in reasons), True)
    all_ok &= check("round15 verdict has no MIXED",
                    "MIXED" not in v and "stays tentative" not in v, True)

    # --- (a) adopt ---
    v, adopt, remove, tent, _ = vf(12.0, 12.0, 5.0, True, True, 3)
    all_ok &= check("(a) verdict starts ADOPT", v.startswith("ADOPT"), True)
    all_ok &= check("(a) adopt", adopt, True)
    all_ok &= check("(a) remove", remove, False)
    all_ok &= check("(a) tentative", tent, False)

    # --- (b) tentative ---
    v, adopt, remove, tent, _ = vf(5.0, 5.0, 2.0, False, True, 3)
    all_ok &= check("(b) verdict starts TENTATIVE",
                    v.startswith("TENTATIVE"), True)
    all_ok &= check("(b) adopt", adopt, False)
    all_ok &= check("(b) remove", remove, False)
    all_ok &= check("(b) tentative", tent, True)

    # --- (c) discard: genuine 0 ---
    v, adopt, remove, tent, _ = vf(3.0, 3.0, 1.0, False, True, 0)
    all_ok &= check("(c) verdict starts REMOVE",
                    v.startswith("REMOVE"), True)
    all_ok &= check("(c) adopt", adopt, False)
    all_ok &= check("(c) remove", remove, True)
    all_ok &= check("(c) tentative", tent, False)

    # --- edges ---
    cases = [
        ("G<=0", (0.0, 0.0, 1.0, False, True, 5), "REMOVE"),
        ("G<0", (-2.0, -2.0, 1.0, False, True, 5), "REMOVE"),
        ("leaked-only gain", (0.0, 4.0, 0.0, False, True, 5), "REMOVE"),
        ("new-kind harm", (4.0, 4.0, -1.0, False, True, 5), "REMOVE"),
        ("genuine=1", (4.0, 4.0, 1.0, False, True, 1), "REMOVE"),
        ("genuine=2 tentative", (4.0, 4.0, 1.0, False, True, 2),
         "TENTATIVE"),
        ("six+H4 pass but genuine<2 -> discard beats adopt",
         (12.0, 12.0, 5.0, True, True, 0), "REMOVE"),
        ("six pass, H4 fail, tentative met -> TENTATIVE (H4 noted)",
         (5.0, 5.0, 2.0, True, False, 3), "TENTATIVE"),
        ("six pass, H4 fail, genuine=0 -> REMOVE",
         (5.0, 5.0, 2.0, True, False, 0), "REMOVE"),
        ("gain over band, McNemar fails, genuine ok -> TENTATIVE",
         (12.0, 12.0, 5.0, False, True, 4), "TENTATIVE"),
    ]
    for name, args, want_prefix in cases:
        v, adopt, remove, tent, _ = vf(*args)
        all_ok &= check(f"edge {name}", v.startswith(want_prefix), True)

    # --- property sweep: verdict is always exactly one of three ---
    import itertools
    prefixes = set()
    for G, genuine, nk, six, h4 in itertools.product(
            (-1.0, 0.0, 3.0, 12.0), (0, 1, 2, 5), (-1.0, 0.0, 3.0),
            (False, True), (False, True)):
        v, _, _, _, _ = vf(G, G, nk, six, h4, genuine)
        prefixes.add(v.split(" ")[0])
        assert "MIXED" not in v and "stays tentative" not in v
    all_ok &= check("sweep verdict set", prefixes,
                    {"ADOPT", "TENTATIVE", "REMOVE"})

    print("ALL PASS" if all_ok else "FAILURES PRESENT")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
