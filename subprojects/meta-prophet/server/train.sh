#!/usr/bin/env bash
# Launch a training script on the server, detached (survives SSH disconnect) under
# the forced-GPU env + thread caps. Returns immediately with the run_id and PID.
# Logs stream to REMOTE_LOGS/<run_id>.log; outputs go to REMOTE_RUNS/<run_id>/.
#
#   ./train.sh <run_id> <remote_script_rel_to_code> [script args...]
# e.g.
#   ./train.sh darts_nbeats_plain 09_darts_rnn.py --model nbeats --regressors none
#
# The script is run as:  python <script> --out REMOTE_RUNS/<run_id> [args...]
source "$(dirname "$0")/lib.sh"

run="${1:-}"; script="${2:-}"; shift 2 2>/dev/null || true
[ -z "$run" ] || [ -z "$script" ] && die "usage: train.sh <run_id> <script.py> [args...]"

out="$REMOTE_RUNS/$run"; logf="$REMOTE_LOGS/$run.log"
log "launching '$run' : $script $*"

# Build the remote command. setsid+nohup => fully detached; PID saved to <run>.pid.
# GPU_ENV + THREAD_ENV exported; PYTHONUNBUFFERED for live logs; stdout+stderr -> logfile.
remote_cmd=$(cat <<EOF
set -e
mkdir -p '$out' '$REMOTE_LOGS'
cd '$REMOTE_CODE'
export $GPU_ENV $THREAD_ENV PYTHONUNBUFFERED=1
echo "=== run=$run script=$script args=$* ===" > '$logf'
echo "=== started \$(date -Is) host=\$(hostname) ===" >> '$logf'
setsid nohup '$REMOTE_VENV/bin/python' '$script' --out '$out' $* >> '$logf' 2>&1 &
echo \$! > '$out/.pid'
echo "PID=\$(cat '$out/.pid')"
EOF
)
srv "$remote_cmd"
log "detached. follow with:  ./follow.sh $run     | results:  ./pull.sh $run"
