#!/usr/bin/env bash
#
# browser_run.sh — Daily entrypoint using browser automation instead of Graph API.
# Runs: sync-elections → browser-monitor → browser-post → browser-reply
#
# Usage:
#   ./browser_run.sh              # headless (default)
#   ./browser_run.sh --headed     # visible browser for demos
#   ./browser_run.sh --dry-run    # log only, don't post anything
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
RUN_LOG="$LOG_DIR/browser_run.log"

mkdir -p "$LOG_DIR"

# Pass through flags
EXTRA_FLAGS="${*}"

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*" | tee -a "$RUN_LOG"
}

log "=== Vote Uncovered browser-based daily run starting ==="
log "Flags: ${EXTRA_FLAGS:-none}"

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

log "Step 2/4: browser-monitor"
python3 "$SCRIPT_DIR/browser_monitor.py" $EXTRA_FLAGS 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: browser-monitor failed"
}

log "Step 3/4: browser-post"
python3 "$SCRIPT_DIR/browser_post.py" $EXTRA_FLAGS 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: browser-post failed"
}

log "Step 4/4: browser-reply"
python3 "$SCRIPT_DIR/browser_reply.py" $EXTRA_FLAGS 2>&1 | tee -a "$RUN_LOG" || {
    log "ERROR: browser-reply failed"
}

log "=== Vote Uncovered browser-based daily run complete ==="
