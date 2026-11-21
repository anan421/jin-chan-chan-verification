# Round 3: degeneracy guard (audit fix 3)

Date: 2026-11-21. Branch: `loop/round-3-degeneracy-guard` (merged to main).

## What changed

- `predict.py`: new `degeneracy_metrics()` + top-level `"degeneracy"` block
  in the prediction report. `degeneracy_rate` = share of round-1
  forecast players whose modal probability is exactly 1.0;
  `degenerate` when the rate exceeds 0.5; `modal_action_entropy_bits`
  = Shannon entropy (bits) of the modal-action distribution across
  players (0.0 bits when every player shares one modal action).
  Summary lines print the rate, the degenerate flag and the entropy.
- `merge_report.py`: prediction-chapter verdict gains the degeneracy
  guard. Priority: **guard fail > opinion**. Default is opinion
  (round 1); when `degeneracy_rate > 0.5` the chapter is fail: the
  prediction is unusable because its distribution collapsed, and
  M1–M5 are not consulted as a judgement (they stay listed as
  diagnostics). The priority is written in the module docstring,
  in a code comment at the verdict, and in the chapter text. The
  chapter renders a "### 退化守卫" readout (rate, flag, entropy,
  modal-action counts). The guard reads predict.py's `"degeneracy"`
  block and falls back to computing it from the per-player modal
  probabilities, so old prediction reports still render.
- `backtest.py`: new M6 calibration. Each test record now carries
  `modal_probability`. Records are bucketed by modal probability
  ([0, 0.5), [0.5, 0.8), [0.8, 0.9), [0.9, 0.99), [0.99, 1.0]) on
  the classifiable subset (same denominator as M1); per bucket: n,
  mean predicted p, actual M1 hit rate, gap = |mean p − hit rate|.
  M6 = largest gap over non-empty buckets; threshold M6 < 0.2.
  The top bucket [0.99, 1.0] holds the near-certain claims,
  including modal p = 1.0. M6 is reported as its own pass/fail; it
  does not change `threshold_verdict` / `below_threshold` (M1–M5
  keep their existing semantics). The merged report lists M6 and
  every bucket, and when the guard fires adds the forecast-anchored
  line: forecast asserts p = 1.0 vs backtest M1 hit rate.

No change to: page, data.json, check.py, Lean paths, run.sh,
rules/payoff-model.json (live stays placeholder v2).

## Verification

Full chain: `./run.sh --predict` exit 0, overall pass
(runs/2026-11-21_133910/). History layer: checker pass (3 passed,
0 failures, 0 gaps), Lean build exit 0. The prediction-chapter
fail does not touch the overall verdict or the run exit code
(overall is decided by history layers only).

## Live-run numbers (runs/2026-11-21_133910/)

- Degeneracy rate **0.0** (0/18 players p = 1.0), degenerate false,
  modal-action entropy **1.275163 bits** (v3×13, capex×2, r1×2,
  blackwell×1). Chapter verdict: **opinion** (guard did not fire).
- M6 **0.9971**, threshold < 0.2, **not passed**. Top bucket
  [0.99, 1.0]: n=28, mean predicted p 0.997141, actual hit rate
  0.0, gap 0.9971. Every bucket's actual hit rate is 0.0 (M1 0.0%
  on 83 classifiable records).

## Premise change (must be read before judging the acceptance)

The task was written against the 123045 run, where all 18 players
had modal anthropic_ipo at p = 1.0 (degeneracy rate 100%). That
distribution no longer exists: the semantic-kind integration in
predict.py (20:53, before round 3 was assigned) changed the
forecast — the tester already recorded the new distribution
(NVDA blackwell, OAI/MSFT/GOOG v3, …). The live run therefore
cannot exhibit a 100% degeneracy rate, and the guard correctly
does not fire on it. This is not a guard failure; it is the
guard measuring a distribution that has already changed.

## Guard-firing proof (degenerate inputs)

The guard was verified to fire on degenerate inputs, twice:

1. Old-format report: `merge_report.py --prediction-run` against
   runs/2026-11-21_121419/ (all 18 modal anthropic_ipo p = 1.0,
   no `"degeneracy"` block — exercises the fallback path).
   Result: prediction verdict **fail**, degeneracy_rate 1.0,
   degenerate true, entropy 0.0 bits, counts anthropic_ipo×18,
   overall still pass, merge exit 0
   (/tmp/guard-test-merged.json, /tmp/guard-test-merged.md).
2. New-format synthetic report: the live 133910 prediction report
   with all modal probabilities forced to 1.0 and a
   `"degeneracy"` block (rate 1.0). Result: prediction verdict
   **fail**, guard_fail true, M6 0.997 listed, forecast-anchored
   line present ("预测轮断言 p = 1.0，回测 M1 实际命中率 0.000，
   差距 1.000"), overall still pass, merge exit 0
   (/tmp/guard-test2.json, /tmp/guard-test2.md).

## Note on the "gap 1.0" expectation

The task expected the p = 1.0 bucket gap to be exactly 1.0. The
measured M6 is **0.9971**, not 1.0000: no backtest record has a
modal probability of exactly 1.0 (maximum 0.999956), so the top
bucket's mean predicted p is 0.997141 and its gap is 0.9971. The
exact 1.000 appears only in the forecast-anchored reading
(forecast asserts p = 1.0, backtest M1 = 0.0, gap 1.000), which
the merged report shows when the guard fires. Substance is the
same either way: the model asserts near-certainty and hits 0%.
