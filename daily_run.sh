#!/usr/bin/env bash
# Daily loop: ingest today's events -> append a round -> recompute
# derived values -> full re-verification -> release only on pass.
#
#   ./daily_run.sh [--date YYYY-MM-DD] [--events FILE] [--trace FILE]
#                  [--data-json FILE] [--predict] [--claims FILE]
#                  [--release-dir DIR]
#
# Defaults: date = today (UTC); events = daily/events-<date>.json;
# trace = traces/trace-latest.json; release dir = traces.
# --data-json archives a snapshot of the page's data.json alongside the
# trace (the page's single source of truth). Without it, only the trace
# is archived.
#
# Steps:
#   0. Archive the pre-ingest snapshot (trace + data.json) by hash+date.
#   1. No events file -> log only, exit 0 (nothing to do today).
#   2. ingest.py: complete round required; exit 3 = incomplete round,
#      wait for the remaining players (log only, exit 0).
#   3. recompute.py: season_state / rankings / hp_series / spec from moves.
#   4. ./run.sh: full verification (gate -> checker -> Lean; classify.py
#      runs inside run.sh on every check report).
#   5. daily/triggers.py: alert vs log-only decision.
#   6. Release gate: pass -> the new trace becomes traces/trace-<date>.json
#      and traces/trace-latest.json; fail -> the page update is BLOCKED,
#      trace-latest.json is untouched, the failure is classified.
#   7. Archive the post-run snapshot (trace + merged report) with verdict.
#
# Exit: 0 released, or nothing to do (no events / incomplete round);
#       1 verification failed (blocked); 2 input error.
# This script never touches the page artifact and never schedules a cron.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.elan/bin:$PATH"

DATE="$(date -u +%Y-%m-%d)"
EVENTS=""
TRACE="$DIR/traces/trace-latest.json"
DATA_JSON=""
PREDICT=0
CLAIMS=""
RELEASE_DIR="$DIR/traces"
while [ $# -gt 0 ]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    --events) EVENTS="$2"; shift 2 ;;
    --trace) TRACE="$2"; shift 2 ;;
    --data-json) DATA_JSON="$2"; shift 2 ;;
    --predict) PREDICT=1; shift ;;
    --claims) CLAIMS="$2"; shift 2 ;;
    --release-dir) RELEASE_DIR="$2"; shift 2 ;;
    *) echo "daily_run: unknown arg: $1" >&2; exit 2 ;;
  esac
done
EVENTS="${EVENTS:-$DIR/daily/events-$DATE.json}"
DAILY_DIR="$DIR/daily"
ARCHIVE_DIR="$DIR/archive"
WORK_DIR="$DAILY_DIR/work/$DATE"
LOG_FILE="$DAILY_DIR/logs/$DATE.log"
mkdir -p "$WORK_DIR" "$DAILY_DIR/logs" "$ARCHIVE_DIR" "$RELEASE_DIR"

log() { echo "daily_run [$DATE]: $*" | tee -a "$LOG_FILE"; }

# --- archive one snapshot --------------------------------------------
# archive_snapshot <kind> <trace-file> <verdict> <run-id> [report-file]
archive_snapshot() {
  local kind="$1" trace_file="$2" verdict="$3" run_id="$4"
  local report_file="${5:-}"
  if [ ! -f "$trace_file" ]; then
    log "archive: no trace file to archive ($trace_file), skipped"
    return 0
  fi
  local sha short dir
  sha="$(sha256sum "$trace_file" | cut -d' ' -f1)"
  short="${sha:0:12}"
  dir="$ARCHIVE_DIR/${DATE}_${short}"
  mkdir -p "$dir"
  cp "$trace_file" "$dir/trace.json"
  local data_sha=""
  if [ -n "$DATA_JSON" ] && [ -f "$DATA_JSON" ]; then
    cp "$DATA_JSON" "$dir/data.json"
    data_sha="$(sha256sum "$DATA_JSON" | cut -d' ' -f1)"
  fi
  if [ -n "$report_file" ] && [ -f "$report_file" ]; then
    cp "$report_file" "$dir/merged-report.md"
  fi
  local source
  source="$(python3 -c "import json,sys; print(json.load(open('$trace_file')).get('meta',{}).get('source','daily_run'))" 2>/dev/null || echo daily_run)"
  python3 - "$ARCHIVE_DIR/manifest.jsonl" <<EOF
import json, sys
rec = {"date": "$DATE", "kind": "$kind",
       "trace_sha256": "$sha", "data_sha256": "$data_sha",
       "path": "archive/${DATE}_${short}", "verdict": "$verdict",
       "run_id": "$run_id", "source": "$source"}
with open(sys.argv[1], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
EOF
  log "archive: $kind -> archive/${DATE}_${short} (trace $short, verdict $verdict)"
  echo "$dir"
}

log "start (base trace $TRACE, events $EVENTS)"
if [ ! -f "$TRACE" ]; then
  log "ERROR: base trace not found: $TRACE" >&2
  exit 2
fi

# Step 0: pre-ingest snapshot.
archive_snapshot pre-ingest "$TRACE" pre-ingest - >> "$LOG_FILE"

# Step 1: no events -> log only.
if [ ! -f "$EVENTS" ]; then
  log "no events file for $DATE; log only"
  python3 "$DIR/daily/triggers.py" --old-trace "$TRACE" \
    --new-trace "$TRACE" --config "$DIR/daily/triggers.json" \
    --date "$DATE" --out "$DAILY_DIR/decision-$DATE.json" \
    >> "$LOG_FILE" 2>&1
  log "decision -> daily/decision-$DATE.json (no_events, log only)"
  exit 0
fi

# Step 2: ingest (complete round required).
CANDIDATE="$WORK_DIR/candidate-trace.json"
log "ingest..."
python3 "$DIR/ingest.py" "$TRACE" "$EVENTS" \
  --map "$DIR/daily/event-map.json" --out "$CANDIDATE" 2>&1 | tee -a "$LOG_FILE"
INGEST_RC=${PIPESTATUS[0]}
if [ "$INGEST_RC" -eq 3 ]; then
  log "incomplete round: waiting for the remaining players' events"
  python3 "$DIR/daily/triggers.py" --old-trace "$TRACE" \
    --new-trace "$TRACE" --events "$EVENTS" \
    --config "$DIR/daily/triggers.json" --date "$DATE" \
    --out "$DAILY_DIR/decision-$DATE.json" >> "$LOG_FILE" 2>&1
  log "decision -> daily/decision-$DATE.json (incomplete_round, log only)"
  exit 0
fi
if [ "$INGEST_RC" -ne 0 ]; then
  log "ERROR: ingest failed (exit $INGEST_RC)" >&2
  exit 2
fi

# Step 3: recompute derived values from moves.
RECOMPUTED="$WORK_DIR/recomputed-trace.json"
log "recompute..."
python3 "$DIR/recompute.py" "$CANDIDATE" --out "$RECOMPUTED" 2>&1 | tee -a "$LOG_FILE"
if [ "${PIPESTATUS[0]}" -ne 0 ]; then
  log "ERROR: recompute failed" >&2
  exit 2
fi

# Step 4: full verification.
log "run.sh..."
RUN_ARGS=("$RECOMPUTED")
if [ "$PREDICT" -eq 1 ]; then RUN_ARGS+=(--predict); fi
if [ -n "$CLAIMS" ]; then RUN_ARGS+=(--claims "$CLAIMS"); fi
touch "$WORK_DIR/before-run"
"$DIR/run.sh" "${RUN_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
RUN_RC=${PIPESTATUS[0]}
log "run.sh exit=$RUN_RC"
RUN_DIR="$(find "$DIR/runs" -mindepth 1 -maxdepth 1 -type d -newer "$WORK_DIR/before-run" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
RUN_ID="$(basename "${RUN_DIR:-none}")"
MERGED_REPORT="$RUN_DIR/merged-report.md"

# Step 5: triggers (alert vs log-only).
TRIGGER_ARGS=(--old-trace "$TRACE" --new-trace "$RECOMPUTED"
  --events "$EVENTS" --config "$DIR/daily/triggers.json"
  --date "$DATE" --out "$DAILY_DIR/decision-$DATE.json")
if [ -f "$RUN_DIR/backtest-report.json" ]; then
  TRIGGER_ARGS+=(--backtest-report "$RUN_DIR/backtest-report.json")
fi
if [ -f "$RUN_DIR/prediction-report.json" ]; then
  TRIGGER_ARGS+=(--prediction-report "$RUN_DIR/prediction-report.json")
fi
PREV_DECISION="$(ls -t "$DAILY_DIR"/decision-*.json 2>/dev/null | head -2 | tail -1)"
if [ -n "$PREV_DECISION" ] && [ "$PREV_DECISION" != "$DAILY_DIR/decision-$DATE.json" ]; then
  TRIGGER_ARGS+=(--previous-decision "$PREV_DECISION")
fi
if [ "$RUN_RC" -ne 0 ]; then
  TRIGGER_ARGS+=(--run-failed)
  if [ -f "$RUN_DIR/classification.json" ]; then
    TRIGGER_ARGS+=(--classification "$RUN_DIR/classification.json")
  fi
fi
log "triggers..."
python3 "$DIR/daily/triggers.py" "${TRIGGER_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"

# Step 6: release gate.
if [ "$RUN_RC" -eq 0 ]; then
  cp "$RECOMPUTED" "$RELEASE_DIR/trace-$DATE.json"
  cp "$RECOMPUTED" "$RELEASE_DIR/trace-latest.json"
  python3 - "$DAILY_DIR/release-$DATE.json" <<EOF
import json, sys
rec = {"date": "$DATE", "released": True,
       "trace": "traces/trace-$DATE.json", "run_id": "$RUN_ID",
       "verdict": "pass",
       "decision": "daily/decision-$DATE.json"}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(rec, fh, ensure_ascii=False, indent=2)
EOF
  log "RELEASED: traces/trace-$DATE.json (+ trace-latest.json)"
  archive_snapshot daily-run "$RECOMPUTED" pass "$RUN_ID" "$MERGED_REPORT" >> "$LOG_FILE"
  log "done"
  exit 0
else
  python3 - "$DAILY_DIR/release-$DATE.json" <<EOF
import json, sys
rec = {"date": "$DATE", "released": False,
       "trace": None, "run_id": "$RUN_ID", "verdict": "fail",
       "reason": "verification failed; page update blocked",
       "decision": "daily/decision-$DATE.json",
       "classification": "$RUN_DIR/classification.json"}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(rec, fh, ensure_ascii=False, indent=2)
EOF
  log "BLOCKED: verification failed; trace-latest.json untouched"
  archive_snapshot daily-run "$RECOMPUTED" fail "$RUN_ID" "$MERGED_REPORT" >> "$LOG_FILE"
  log "done (blocked)"
  exit 1
fi
