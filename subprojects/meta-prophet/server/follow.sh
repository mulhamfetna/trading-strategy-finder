#!/usr/bin/env bash
# Live-stream a run's remote log to the terminal AND mirror it to a local file.
# This is the "continuous log transfer" — one long-lived follower, not per-iteration
# rsync. Exits when the remote process is gone and the log stops growing.
#   ./follow.sh <run_id>
source "$(dirname "$0")/lib.sh"

run="${1:-}"; [ -z "$run" ] && die "usage: follow.sh <run_id>"
mkdir -p "$LOCAL_LOGS"
local_log="$LOCAL_LOGS/$run.log"
log "following $run  (mirroring -> $local_log)  Ctrl-C to detach (job keeps running)"

# tail -f the remote log over ssh; --pid makes tail exit when the training PID dies.
srv "pid=\$(cat '$REMOTE_RUNS/$run/.pid' 2>/dev/null || echo 1); tail -n +1 -f --pid=\$pid '$REMOTE_LOGS/$run.log'" \
  | tee "$local_log"
log "stream ended (process exited). Final log saved to $local_log"
