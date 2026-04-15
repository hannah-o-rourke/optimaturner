#!/usr/bin/env bash
#
# run.sh — Daily entrypoint for Vote Uncovered.
# Runs: sync-elections → monitor → post → reply
# Intended for cron: 0 9 * * * /path/to/run.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
RUN_LOG="$LOG_DIR/run.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*" | tee -a "$RUN_LOG"
}

log "=== Vote Uncovered daily run starting ==="

# Activate venv if present
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

cd "$PROJECT_DIR"

log "Step 1/4: sync-elections"
python3 "$SCRIPT_DIR/sync_elections.py" 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: sync-elections failed"
    exit 1
}

log "Step 2/4: monitor"
python3 "$SCRIPT_DIR/monitor.py" 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: monitor failed"
}

log "Step 3/4: post"
python3 "$SCRIPT_DIR/post.py" 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: post failed"
}

log "Step 4/4: reply"
python3 "$SCRIPT_DIR/reply.py" 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: reply failed"
}

log "=== Vote Uncovered daily run complete ==="
