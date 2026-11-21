#!/usr/bin/env python3
"""Fit the post-hoc calibration (round 9, fruit 3) on the fit
window only, and write the fitted parameters to
rules/calibration.json.

Walk-forward discipline: the fit window is S1-S3, the test window
S4-S5 is never touched here. Each fit-window round is predicted
from its prefix only (no future information), exactly as
backtest.run_window does; the (stated probability, actual
outcome) pairs from those rounds are the fitting data. The
temperature T is fitted by minimising the mean negative
log-likelihood of the recorded kind (see calibration.py).
Only the fitted parameters are written to rules/calibration.json;
no parameter is hard-coded in predict.py or backtest.py.

The fit-window calibration (M6 before/after) is reported here to
prove the rescaling was learned on the fit window, not tuned on
the test window. The test-window effect is measured separately by
backtest.py after this file exists.

Re-fitting when new data arrives (fruit 3 asks for a re-fit every
time) is future work: this script is run by hand for now; the
re-fit mechanism is recorded in design/round-9-calibration.md,
not built in this round.

Usage:
    python3 fit_calibration.py [trace.json]
        [--payoff rules/payoff-model.json]
        [--out rules/calibration.json]
Exit: 0 fitted and written; 2 bad input.
"""
import argparse
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backtest as BT  # noqa: E402
import calibration as CAL  # noqa: E402
import predict as P  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fit post-hoc calibration.")
    ap.add_argument("trace", nargs="?",
                    default=str(HERE / "traces" / "trace-latest.json"))
    ap.add_argument("--payoff",
                    default=str(HERE / "rules" / "payoff-model.json"))
    ap.add_argument("--out",
                    default=str(HERE / "rules" / "calibration.json"))
    args = ap.parse_args(argv)

    trace = P.load_trace(args.trace)
    if trace is None:
        return 2
    payoff = P.load_json(args.payoff, "payoff model")
    if payoff is None or "parameters" not in payoff:
        print("fit_calibration: bad payoff model file", file=sys.stderr)
        return 2
    params = {k: v["value"] for k, v in payoff["parameters"].items()}
    tau = params.get("temperature", 1.0)
    thresholds = payoff.get("thresholds", {})
    margin_pp = thresholds.get("margin_pp", 10)
    tol = thresholds.get("m5_tolerance", 10)

    seasons = sorted(s["season"] for s in trace["seasons"])
    fit_seasons = seasons[:3]
    test_seasons = seasons[3:]
    if not test_seasons:
        print("fit_calibration: trace needs more than 3 seasons",
              file=sys.stderr)
        return 2

    # Walk-forward over the fit window only, raw distributions
    # (calibration=None): the fitting data must be what the model
    # actually said before any rescaling.
    records = BT.run_window(trace, params, tau, fit_seasons,
                            margin_pp, tol, calibration=None,
                            include_distributions=True)
    calib_before = BT.calibration(records)
    n_classifiable = sum(1 for r in records if r["m1_classifiable"])
    fit_items = []
    excluded = 0
    for r in records:
        if not r["m1_classifiable"]:
            continue
        dist = r.get("distribution", {})
        if r["recorded_action"] not in dist:
            # Recorded kind was banned that round, or never seen in
            # the prefix: the model gave it no probability, so it
            # carries no NLL signal. Counted, not silently dropped.
            excluded += 1
            continue
        fit_items.append((dist, r["recorded_action"]))

    fit = CAL.fit_temperature(fit_items)
    temp = fit["temperature"]
    cap = CAL.CAP
    cal_params = {"method": CAL.METHOD, "temperature": temp, "cap": cap}

    # Apply on the fit window and re-measure M6 there. The modal
    # action must not change: assert it on every record.
    post_records = []
    argmax_flips = 0
    for r in records:
        post = dict(r)
        dist = r.get("distribution", {})
        if dist:
            cal_dist = CAL.apply_calibration(dist, cal_params)
            modal = max(cal_dist, key=lambda k: (cal_dist[k], k))
            if modal != r["predicted_action"]:
                argmax_flips += 1
            post["modal_probability"] = cal_dist[r["predicted_action"]]
        post_records.append(post)
    calib_after = BT.calibration(post_records)
    nll_after, _ = CAL.nll_for_temperature(fit_items, temp)

    trace_sha = hashlib.sha256(
        Path(args.trace).read_bytes()).hexdigest()
    doc = {
        "version": 1,
        "method": CAL.METHOD,
        "temperature": temp,
        "cap": cap,
        "fit_window": [f"S{s}" for s in fit_seasons],
        "fit_date": datetime.date.today().isoformat(),
        "fit_trace": args.trace,
        "fit_trace_sha256": trace_sha,
        "fit_records_n": len(records),
        "fit_records_classifiable_n": n_classifiable,
        "fit_items_n": len(fit_items),
        "fit_excluded_n": excluded,
        "fit_excluded_reason": ("recorded kind not in the predicted "
                                "distribution (banned that round, or "
                                "never seen in the prefix): no NLL "
                                "signal, counted not dropped"),
        "nll_before": round(fit["nll_at_1"], 4),
        "nll_after": round(nll_after, 4),
        "m6_fit_window_before": calib_before["m6"],
        "m6_fit_window_after": calib_after["m6"],
        "m6_threshold": BT.M6_THRESHOLD,
        "fit_at_boundary": fit["at_boundary"],
        "fit_grid": list(fit["grid"]),
        "fitted_by": ("fit_calibration.py: walk-forward over the fit "
                      "window (S1-S3), each round predicted from its "
                      "prefix only; temperature fitted by minimising "
                      "mean NLL of the recorded kind"),
        "argmax_flips_on_fit_window": argmax_flips,
        "note": ("Post-hoc temperature scaling. It never changes a "
                 "modal action or a hit count, only the stated "
                 "probabilities, and no calibrated probability "
                 "exceeds the cap. The test window (S4-S5) was never "
                 "used for fitting. Re-fitting when new data arrives "
                 "is future work, not built in this round."),
    }
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False,
                                         indent=2), encoding="utf-8")

    print(f"fit_calibration: fit={[f'S{s}' for s in fit_seasons]} "
          f"test={[f'S{s}' for s in test_seasons]} "
          f"records={len(records)} "
          f"classifiable={n_classifiable} "
          f"fit_items={len(fit_items)} excluded={excluded}")
    print(f"fit_calibration: NLL at T=1: {fit['nll_at_1']:.4f} "
          f"-> NLL at T={temp:.4f}: {nll_after:.4f} "
          f"(mean uniform-limit log K over fit items: "
          f"{sum(math.log(len(d)) for d, _ in fit_items) / len(fit_items):.4f})"
          if fit_items else
          "fit_calibration: no fit items")
    print(f"fit_calibration: M6 fit window: {calib_before['m6']} "
          f"-> {calib_after['m6']} (threshold <{BT.M6_THRESHOLD})")
    for b in calib_before["buckets"]:
        print(f"  bucket before {b['bucket']}: n={b['n']} "
              f"mean_p={b['mean_predicted_p']} "
              f"hit={b['actual_hit_rate']} gap={b['gap']}")
    for b in calib_after["buckets"]:
        print(f"  bucket after  {b['bucket']}: n={b['n']} "
              f"mean_p={b['mean_predicted_p']} "
              f"hit={b['actual_hit_rate']} gap={b['gap']}")
    print(f"fit_calibration: argmax flips on fit window: "
          f"{argmax_flips} (must be 0)")
    print(f"fit_calibration: at_boundary={fit['at_boundary']} "
          f"(grid {fit['grid']})")
    print(f"fit_calibration: wrote {args.out} "
          f"(temperature={temp:.6f} cap={cap})")
    if argmax_flips:
        print("fit_calibration: ERROR: calibration flipped an argmax",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
