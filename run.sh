#!/usr/bin/env bash
# One-click verification run:
#   agent gate -> fast checker -> Lean proof -> merged report.
#   With --predict: after the history layers pass, prediction
#   (symbolic -> predict -> backtest -> agent_claims) runs and its
#   reports are merged as a separate prediction chapter. Prediction
#   runs only when gate, checker, gen and Lean all pass (exit 0);
#   otherwise it is recorded as not_run. A prediction failure never
#   changes this script's exit code, which reflects the history
#   layers only. A missing prediction tool or payoff file is
#   recorded as a missing report (prediction chapter: opinion), never
#   as a history failure.
# Usage: ./run.sh [--claims FILE] [--modular] [--predict]
#                 [--payoff FILE] [trace.json]
#   (default trace: traces/trace-latest.json)
#   (default payoff: rules/payoff-model.json)
# Gate runs first when --claims is given; a gate failure fails the
# whole run and the checker / Lean layers are recorded as not_run,
# but the merged report is still written.
# Modular mode also builds ProofsByPlayer / ProofsBySeason and
# verifies their .olean files; non-modular mode removes stale
# modular sources so they cannot be built by accident.
# Exit: 0 all layers pass; 1 any layer fails; 2 trace missing / bad input.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.elan/bin:$PATH"

CLAIMS=""
MODULAR=0
PREDICT=0
PAYOFF="$DIR/rules/payoff-model.json"
TRACE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --claims) CLAIMS="$2"; shift 2 ;;
    --modular) MODULAR=1; shift ;;
    --predict) PREDICT=1; shift ;;
    --payoff) PAYOFF="$2"; shift 2 ;;
    *) TRACE="$1"; shift ;;
  esac
done
TRACE="${TRACE:-$DIR/traces/trace-latest.json}"
RUN_ID="$(date +%Y-%m-%d_%H%M%S)"
RUN_DIR="$DIR/runs/$RUN_ID"
mkdir -p "$RUN_DIR"

if [ ! -f "$TRACE" ]; then
  echo "run: trace not found: $TRACE" >&2
  echo "run: extract first: python3 extract.py <raw-data.json>" >&2
  exit 2
fi
cp "$TRACE" "$RUN_DIR/trace.json"

GATE_RC=0
GATE_REPORT=""
if [ -n "$CLAIMS" ]; then
  echo "run: agent gate..."
  python3 "$DIR/gate.py" "$CLAIMS" --trace "$TRACE" \
    --out "$RUN_DIR/gate-report.json" \
    --summary "$RUN_DIR/gate-summary.txt"
  GATE_RC=$?
  GATE_REPORT="$RUN_DIR/gate-report.json"
  echo "run: agent gate exit=$GATE_RC"
else
  echo "run: no --claims given, agent gate skipped"
fi

CHECK_RC=0
GEN_RC=0
LEAN_RC=0
if [ "$GATE_RC" -eq 0 ]; then
  echo "run: fast checker..."
  python3 "$DIR/check.py" "$TRACE" \
    --out "$RUN_DIR/check-report.json" \
    --summary "$RUN_DIR/check-summary.txt"
  CHECK_RC=$?
  echo "run: fast checker exit=$CHECK_RC"

  # Failure classification (diagnostic only: it never changes this
  # script's exit code). Runs whenever a check report exists; the
  # failures log tracks recurrence across runs for mechanism detection.
  CLASSIFICATION_REPORT=""
  if [ -f "$RUN_DIR/check-report.json" ]; then
    echo "run: failure classification..."
    python3 "$DIR/classify.py" "$RUN_DIR/check-report.json" \
      --log "$DIR/runs/failures-log.jsonl" \
      --out "$RUN_DIR/classification.json"
    echo "run: classify exit=$?"
    [ -f "$RUN_DIR/classification.json" ] \
      && CLASSIFICATION_REPORT="$RUN_DIR/classification.json"
  fi

  echo "run: generating Trace.lean..."
  if [ "$MODULAR" -eq 1 ]; then
    python3 "$DIR/gen_trace_lean.py" "$TRACE" \
      --out "$DIR/lean/Verification/Trace.lean" --modular
  else
    rm -f "$DIR/lean/Verification/ProofsByPlayer.lean" \
          "$DIR/lean/Verification/ProofsBySeason.lean"
    python3 "$DIR/gen_trace_lean.py" "$TRACE" \
      --out "$DIR/lean/Verification/Trace.lean"
  fi
  GEN_RC=$?
  echo "run: trace gen exit=$GEN_RC"

  echo "run: Lean build..."
  (cd "$DIR/lean" && lake build > "$RUN_DIR/lean-build.log" 2>&1)
  LEAN_RC=$?
  echo "run: Lean build exit=$LEAN_RC"
  if [ "$MODULAR" -eq 1 ] && [ "$LEAN_RC" -eq 0 ]; then
    echo "run: Lean modular build..."
    (cd "$DIR/lean" && lake build Verification.ProofsByPlayer \
      Verification.ProofsBySeason >> "$RUN_DIR/lean-build.log" 2>&1)
    LEAN_RC=$?
    echo "run: Lean modular build exit=$LEAN_RC"
  fi
  # Guard against a vacuous build: each proof module must have produced
  # an .olean, newer than its source. A "Nothing to build" exit 0 is
  # a failure.
  check_olean() {
    local olean="$1" src="$2"
    if [ ! -f "$olean" ] || [ "$olean" -ot "$src" ]; then
      echo "run: Lean build produced no fresh $olean (vacuous build)" >&2
      LEAN_RC=1
    fi
  }
  if [ "$LEAN_RC" -eq 0 ]; then
    check_olean "$DIR/lean/.lake/build/lib/lean/Verification/Proofs.olean" \
                "$DIR/lean/Verification/Proofs.lean"
    if [ "$MODULAR" -eq 1 ]; then
      check_olean "$DIR/lean/.lake/build/lib/lean/Verification/ProofsByPlayer.olean" \
                  "$DIR/lean/Verification/ProofsByPlayer.lean"
      check_olean "$DIR/lean/.lake/build/lib/lean/Verification/ProofsBySeason.olean" \
                  "$DIR/lean/Verification/ProofsBySeason.lean"
    fi
  fi
else
  echo "run: gate failed, checker and Lean layers not run"
fi

# --- Prediction layer (only on a fully passing history) -----------
PREDICTION_RUN=0
PREDICTION_REPORT=""
BACKTEST_REPORT=""
SYMBOLIC_REPORT=""
PROTOCOL_REPORT=""
if [ "$PREDICT" -eq 1 ]; then
  if [ "$GATE_RC" -eq 0 ] && [ "$CHECK_RC" -eq 0 ] \
      && [ "$GEN_RC" -eq 0 ] && [ "$LEAN_RC" -eq 0 ]; then
    PREDICTION_RUN=1
    echo "run: prediction layer..."
    if [ -f "$DIR/symbolic.py" ]; then
      echo "run: symbolic..."
      python3 "$DIR/symbolic.py" "$TRACE" \
        --out "$RUN_DIR/symbolic-report.json" \
        --summary "$RUN_DIR/symbolic-summary.txt"
      echo "run: symbolic exit=$?"
      [ -f "$RUN_DIR/symbolic-report.json" ] \
        && SYMBOLIC_REPORT="$RUN_DIR/symbolic-report.json"
    else
      echo "run: symbolic.py missing, symbolic report not produced" >&2
    fi
    if [ -f "$DIR/predict.py" ]; then
      echo "run: predict..."
      PREDICT_ARGS=(python3 "$DIR/predict.py" "$TRACE"
        --payoff "$PAYOFF"
        --out "$RUN_DIR/prediction-report.json"
        --summary "$RUN_DIR/prediction-summary.txt")
      if [ -n "$CLAIMS" ]; then
        PREDICT_ARGS+=(--claims "$CLAIMS")
        if [ -n "$GATE_REPORT" ]; then
          PREDICT_ARGS+=(--gate-report "$GATE_REPORT")
        fi
      fi
      "${PREDICT_ARGS[@]}"
      echo "run: predict exit=$?"
      [ -f "$RUN_DIR/prediction-report.json" ] \
        && PREDICTION_REPORT="$RUN_DIR/prediction-report.json"
    else
      echo "run: predict.py missing, prediction report not produced" >&2
    fi
    if [ -f "$DIR/backtest.py" ]; then
      echo "run: backtest..."
      python3 "$DIR/backtest.py" "$TRACE" \
        --payoff "$PAYOFF" \
        --out "$RUN_DIR/backtest-report.json" \
        --summary "$RUN_DIR/backtest-summary.txt"
      echo "run: backtest exit=$?"
      [ -f "$RUN_DIR/backtest-report.json" ] \
        && BACKTEST_REPORT="$RUN_DIR/backtest-report.json"
    else
      echo "run: backtest.py missing, backtest report not produced" >&2
    fi
    if [ -n "$CLAIMS" ] && [ -f "$DIR/agent_claims.py" ]; then
      echo "run: agent protocol checks..."
      python3 "$DIR/agent_claims.py" "$CLAIMS" --trace "$TRACE" \
        --out "$RUN_DIR/protocol-report.json" \
        --summary "$RUN_DIR/protocol-summary.txt"
      echo "run: agent_claims exit=$?"
      [ -f "$RUN_DIR/protocol-report.json" ] \
        && PROTOCOL_REPORT="$RUN_DIR/protocol-report.json"
    elif [ -n "$CLAIMS" ]; then
      echo "run: agent_claims.py missing, protocol report not produced" >&2
    else
      echo "run: no --claims given, agent protocol checks skipped"
    fi
  else
    echo "run: history layer did not pass, prediction not run"
  fi
fi

MERGE_ARGS=(
  --lean-rc "$LEAN_RC" --gen-rc "$GEN_RC" --gate-rc "$GATE_RC"
  --trace "$TRACE"
  --out-json "$RUN_DIR/merged-report.json"
  --out-md "$RUN_DIR/merged-report.md"
)
if [ "$PREDICTION_RUN" -eq 1 ]; then
  MERGE_ARGS+=(--prediction-run)
fi
if [ -n "$PREDICTION_REPORT" ]; then
  MERGE_ARGS+=(--prediction-report "$PREDICTION_REPORT")
fi
if [ -n "$BACKTEST_REPORT" ]; then
  MERGE_ARGS+=(--backtest-report "$BACKTEST_REPORT")
fi
if [ -n "$SYMBOLIC_REPORT" ]; then
  MERGE_ARGS+=(--symbolic-report "$SYMBOLIC_REPORT")
fi
if [ -n "$PROTOCOL_REPORT" ]; then
  MERGE_ARGS+=(--protocol-report "$PROTOCOL_REPORT")
fi
if [ -f "$RUN_DIR/check-report.json" ]; then
  MERGE_ARGS+=(--check-report "$RUN_DIR/check-report.json")
fi
if [ -n "${CLASSIFICATION_REPORT:-}" ]; then
  MERGE_ARGS+=(--classification-report "$CLASSIFICATION_REPORT")
fi
if [ -f "$RUN_DIR/lean-build.log" ]; then
  MERGE_ARGS+=(--lean-log "$RUN_DIR/lean-build.log")
fi
if [ -n "$GATE_REPORT" ]; then
  MERGE_ARGS+=(--gate-report "$GATE_REPORT")
fi
python3 "$DIR/merge_report.py" "${MERGE_ARGS[@]}"
MERGE_RC=$?
echo "run: report -> $RUN_DIR/merged-report.md"
[ "$GATE_RC" -eq 0 ] && [ "$CHECK_RC" -eq 0 ] && [ "$GEN_RC" -eq 0 ] \
  && [ "$LEAN_RC" -eq 0 ] && [ "$MERGE_RC" -eq 0 ]
exit $?
