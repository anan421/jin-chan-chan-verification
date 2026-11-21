#!/usr/bin/env python3
"""Post-hoc calibration of prediction distributions (round 9,
fruit 3 of design/how-others-predict.md).

The model states near-certain probabilities and hits ~1% of the
time. That is a calibration failure, not a knowledge failure:
the stated probabilities are wrong, so they are rescaled after
the fact against what actually happened.

Method: temperature scaling (one global parameter T), fitted on
the fit window only (S1-S3, walk-forward) by minimising the mean
negative log-likelihood of the recorded kind; see
fit_calibration.py. Temperature scaling is monotone, so it never
changes any player's modal action (argmax) or any hit count: it
only changes how confident the stated probabilities look. A
Platt map fitted on the modal probability alone was not used:
rescaling the modal probability down while renormalising the
rest proportionally can flip the argmax when the map pulls the
modal probability below a rival kind, which would change the
predictions themselves -- outside this round's scope.

Cap: no calibrated probability is ever output above CAP (0.99).
Temperature scaling with T > 1 already pulls every modal
probability far below the cap; the cap is a guarantee, not the
mechanism. If a raw distribution is degenerate (one kind at
p = 1.0), the cap puts that kind at 0.99 and shares the remaining
0.01 equally over the other kinds.

Parameters live in rules/calibration.json, never hard-coded here.
predict.py (live forecast) and backtest.py (test measurement)
both call apply_calibration() through predict.best_response(),
so there is one implementation. When the file is absent,
load_calibration() returns None and distributions pass through
unchanged (raw probabilities, uncalibrated).

Re-fitting on new data (fruit 3 asks for a re-fit every time new
data arrives) is future work: this round is "fit on the fit
window, apply on the test window". See design/round-9-calibration.md.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PATH = HERE / "rules" / "calibration.json"

METHOD = "temperature"
CAP = 0.99


def load_calibration(path=None):
    """Load calibration parameters from rules/calibration.json.
    Returns the parameter dict, or None when the file is absent
    or unusable (distributions then pass through unchanged)."""
    p = Path(path) if path is not None else DEFAULT_PATH
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"calibration: cannot parse {p}: {e}", file=sys.stderr)
        return None
    if not isinstance(doc, dict) or doc.get("method") != METHOD:
        print(f"calibration: {p} is not a {METHOD} calibration file",
              file=sys.stderr)
        return None
    try:
        temp = float(doc["temperature"])
        cap = float(doc.get("cap", CAP))
    except (TypeError, ValueError, KeyError):
        print(f"calibration: {p} has no numeric temperature",
              file=sys.stderr)
        return None
    if not (temp > 0.0) or not (0.0 < cap < 1.0):
        print(f"calibration: {p} has temperature={temp} cap={cap}; "
              "need temperature > 0 and 0 < cap < 1", file=sys.stderr)
        return None
    return {"method": METHOD, "temperature": temp, "cap": cap,
            "fit_window": doc.get("fit_window"),
            "fit_date": doc.get("fit_date"),
            "source_file": str(p)}


def apply_calibration(dist, params):
    """Rescale one action distribution. params is a
    load_calibration() dict, or None for a pass-through.
    Temperature scaling: p'_i proportional to p_i ** (1/T).
    Then the cap: no probability above cap (0.99). The argmax
    never changes: the power map is increasing in p, and capping
    the modal kind down to 0.99 leaves the other kinds summing
    to 0.01, each below 0.99. Returns a new dict; the input is
    untouched. Probabilities that do not sum to 1 (rounding) are
    normalised as part of the rescaling."""
    if params is None:
        return dict(dist)
    temp = params["temperature"]
    cap = params.get("cap", CAP)
    if not dist:
        return {}
    inv = 1.0 / temp
    weights = {}
    total = 0.0
    for k, p in dist.items():
        w = (p ** inv) if p > 0.0 else 0.0
        weights[k] = w
        total += w
    if total <= 0.0:
        # Every probability is 0 (should not happen): fall back to
        # uniform over the kinds, so the result is still a
        # distribution and the argmax rule below still applies.
        n = len(dist)
        return {k: 1.0 / n for k in dist}
    out = {k: w / total for k, w in weights.items()}
    modal = max(out, key=lambda k: (out[k], k))
    if out[modal] > cap:
        if len(out) == 1:
            # A single-kind distribution has nowhere to put the
            # remaining mass; leave it (structural, not a claim).
            return out
        rest = 1.0 - cap
        others = [k for k in out if k != modal]
        # Sum the other kinds directly: 1.0 - out[modal] would
        # cancel catastrophically when the modal kind is near 1.0.
        rest_total = sum(out[k] for k in others)
        if rest_total <= 0.0:
            share = rest / len(others)
            return {k: (cap if k == modal else share) for k in out}
        scale = rest / rest_total
        return {k: (cap if k == modal else out[k] * scale)
                for k in out}
    return out


def modal_after_calibration(dist, params):
    """Modal (action, probability) of a distribution after
    calibration. Convenience for measurement code that only needs
    the modal claim, not the whole distribution."""
    cal = apply_calibration(dist, params)
    if not cal:
        return None, 0.0
    modal = max(cal, key=lambda k: (cal[k], k))
    return modal, cal[modal]


# --- fitting (used by fit_calibration.py, not by predict/backtest)
def nll_for_temperature(fit_items, temp):
    """Mean negative log-likelihood of the recorded kind under
    temperature scaling. fit_items: list of (distribution,
    recorded_kind) with the recorded kind present in the
    distribution. Returns (mean_nll, n)."""
    if temp <= 0.0 or not fit_items:
        return float("inf"), 0
    inv = 1.0 / temp
    total = 0.0
    for dist, recorded in fit_items:
        denom = 0.0
        p_true = 0.0
        for k, p in dist.items():
            w = (p ** inv) if p > 0.0 else 0.0
            denom += w
            if k == recorded:
                p_true = w
        if denom <= 0.0 or p_true <= 0.0:
            return float("inf"), len(fit_items)
        total += -math.log(p_true / denom)
    return total / len(fit_items), len(fit_items)


def fit_temperature(fit_items, lo=0.5, hi=500.0, coarse=300,
                    refine_rounds=80):
    """Fit T by minimising mean NLL over fit_items (see
    nll_for_temperature). Coarse log-spaced grid, then a
    golden-section refine on log T around the best bracket.
    Returns {"temperature": T, "nll": mean NLL at T,
    "nll_at_1": mean NLL at T = 1 (uncalibrated),
    "n": number of items, "at_boundary": True when the best
    coarse point sat on the grid edge (the NLL keeps falling
    toward the uniform limit: the ranking carries no usable
    signal, so T is capped at the edge rather than chased to
    infinity), "grid": (lo, hi)}."""
    nll_1, _ = nll_for_temperature(fit_items, 1.0)
    if not fit_items:
        return {"temperature": 1.0, "nll": nll_1, "nll_at_1": nll_1,
                "n": 0, "at_boundary": False, "grid": (lo, hi)}
    import math as _math
    lo_l, hi_l = _math.log(lo), _math.log(hi)
    best_t, best_nll = None, float("inf")
    for i in range(coarse + 1):
        t = _math.exp(lo_l + (hi_l - lo_l) * i / coarse)
        nll, _ = nll_for_temperature(fit_items, t)
        if nll < best_nll:
            best_t, best_nll = t, nll
    at_boundary = best_t is None or best_t <= lo * 1.0001 or \
        best_t >= hi * 0.9999
    # Golden-section refine on log T around the best coarse point.
    step = (hi_l - lo_l) / coarse
    a = max(lo_l, _math.log(best_t) - step)
    b = min(hi_l, _math.log(best_t) + step)
    gr = (_math.sqrt(5.0) - 1.0) / 2.0
    x1 = b - gr * (b - a)
    x2 = a + gr * (b - a)
    f1, _ = nll_for_temperature(fit_items, _math.exp(x1))
    f2, _ = nll_for_temperature(fit_items, _math.exp(x2))
    for _ in range(refine_rounds):
        if f1 > f2:
            a, x1, f1 = x1, x2, f2
            x2 = a + gr * (b - a)
            f2, _ = nll_for_temperature(fit_items, _math.exp(x2))
        else:
            b, x2, f2 = x2, x1, f1
            x1 = b - gr * (b - a)
            f1, _ = nll_for_temperature(fit_items, _math.exp(x1))
    t_ref = _math.exp((a + b) / 2.0)
    nll_ref, _ = nll_for_temperature(fit_items, t_ref)
    if nll_ref <= best_nll:
        best_t, best_nll = t_ref, nll_ref
    return {"temperature": best_t, "nll": best_nll, "nll_at_1": nll_1,
            "n": len(fit_items), "at_boundary": at_boundary,
            "grid": (lo, hi)}
