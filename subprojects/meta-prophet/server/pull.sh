#!/usr/bin/env bash
# Pull a run's outputs (and logs) back to local. Results+docs live locally.
#   ./pull.sh <run_id>      -> mirrors REMOTE_RUNS/<run_id>/ into LOCAL_RUNS/<run_id>/
#                              and REMOTE_LOGS/<run_id>.log into LOCAL_LOGS/
#   ./pull.sh --all         -> mirrors the entire runs/ + logs/ tree
source "$(dirname "$0")/lib.sh"

run="${1:-}"; [ -z "$run" ] && die "usage: pull.sh <run_id> | --all"
mkdir -p "$LOCAL_RUNS" "$LOCAL_LOGS"

if [ "$run" = "--all" ]; then
  log "pull ALL runs + logs"
  pull "$REMOTE_RUNS/" "$LOCAL_RUNS/"
  pull "$REMOTE_LOGS/" "$LOCAL_LOGS/"
else
  log "pull run '$run'"
  mkdir -p "$LOCAL_RUNS/$run"
  pull "$REMOTE_RUNS/$run/" "$LOCAL_RUNS/$run/"
  pull "$REMOTE_LOGS/$run.log" "$LOCAL_LOGS/" 2>/dev/null || log "(no logfile $run.log yet)"
fi
log "mirrored to $LOCAL_RUNS"
