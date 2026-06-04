#!/usr/bin/env bash
# WS-H remote runner — migrate the multi-timeframe parameter search to the AMD server,
# following the established playbook (subprojects/meta-prophet/server/). CPU-only (no GPU);
# runs all 7 timeframe studies in parallel, detached (setsid+nohup), disconnect-proof.
#
# Reuses the shared connection config (key auth, host) from meta-prophet/server/server.env.
# WS-H gets its OWN isolated scratch so it never touches the meta-prophet runs.
#
#   ./remote.sh push           rsync code + data → server scratch
#   ./remote.sh parity         run the TF=4h parity test on the server (env sanity)
#   ./remote.sh run [TRIALS]   launch all 7 TF searches in parallel, detached (default 1000)
#   ./remote.sh status         host load + per-TF alive/dead + last log lines
#   ./remote.sh pull           rsync results (Pareto CSV/PNG + leaderboard + logs) back
#   ./remote.sh stop           kill all WS-H jobs
set -euo pipefail

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_SRVDIR="$_HERE/../../../meta-prophet/server"        # shared connection toolkit
source "$_SRVDIR/server.env"                          # SRV_HOST/PORT/USER/KEY, THREADS

REPO="/mnt/data/projects/trading"
WSH="/home/dev/Mulham/wsg-h"                          # isolated WS-H scratch on the server
CODE="$WSH/wsg-strategy"
LOCAL_RESULTS="$_HERE/../results"
LOCAL_LOGS="$_HERE/server_logs"
TFS=(4h 2h 1h 15m 5m 2m 1m)

SSH_OPTS=(-p "$SRV_PORT" -i "$SRV_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
          -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
          -o ServerAliveInterval=30 -o ServerAliveCountMax=4)
srv() { ssh "${SSH_OPTS[@]}" "${SRV_USER}@${SRV_HOST}" "$@"; }
RSYNC_E="ssh -p $SRV_PORT -i $SRV_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
log() { printf '\033[1;36m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }

# remote env prelude: activate venv, point the code at the synced data, cap threads per job
REMOTE_ENV="source $REMOTE_VENV/bin/activate; export WSH_DATA_BASE='$WSH' WSG_DATA_ROOT='$WSH/data'"

cmd_push() {
  log "creating scratch + pushing code/data → $WSH"
  srv "mkdir -p '$WSH' '$CODE'"
  rsync -az --info=stats1 -e "$RSYNC_E" \
    --exclude '__pycache__' --exclude '*.pyc' --exclude 'optimize/studies' \
    --exclude 'optimize/results' --exclude 'optimize/server/server_logs' \
    "$REPO/subprojects/wsg-strategy/" "${SRV_USER}@${SRV_HOST}:$CODE/"
  rsync -az --info=stats1 -e "$RSYNC_E" "$REPO/Full_Canldes_Data/" "${SRV_USER}@${SRV_HOST}:$WSH/Full_Canldes_Data/"
  rsync -az --info=stats1 -e "$RSYNC_E" "$REPO/data/" "${SRV_USER}@${SRV_HOST}:$WSH/data/"
  log "push done."
}

cmd_parity() {
  log "running TF=4h parity test on the server (pandas $(srv "$REMOTE_ENV; python3 -c 'import pandas;print(pandas.__version__)'"))"
  srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/test_parity.py"
}

# Workers per TF — the engine is GIL-bound (≈1 core/process), so we run MULTIPLE worker processes
# per study (they share trials through the SQLite DB), weighted by cost so all 32 threads are used
# and the slow fine TFs finish in ~the same wall-clock as the cheap ones. Sum ≈ 30 (2 left for OS).
declare -A WORKERS=( [1m]=12 [2m]=8 [5m]=4 [15m]=2 [1h]=2 [2h]=1 [4h]=1 )

cmd_run() {
  local total="${1:-1200}"                  # target trials PER timeframe (split across its workers)
  local only="${2:-}"                       # optional: launch only these TFs (space-sep), else all
  local tfs=("${TFS[@]}"); [ -n "$only" ] && read -ra tfs <<< "$only"
  log "launching parallel search: $total trials/TF [${tfs[*]}] across weighted workers ..."
  # Build a SINGLE server-side launcher script (one SSH call, returns immediately). Spawning all
  # workers from one srv call avoids the per-worker SSH-channel hang of `ssh host 'nohup … &'`.
  local spec=""
  for tf in "${tfs[@]}"; do spec+="$tf:${WORKERS[$tf]:-1} "; done
  srv "cat > '$WSH/launch.sh' <<'EOS'
#!/usr/bin/env bash
# idempotent: clear any existing workers + stale launchers first so a double-invocation
# can never oversubscribe (we always end with exactly the worker map below)
pkill -9 -f optimize/optimizer.py >/dev/null 2>&1 || true
sleep 2
source $REMOTE_VENV/bin/activate
export WSH_DATA_BASE='$WSH' WSG_DATA_ROOT='$WSH/data'
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '$CODE'; mkdir -p optimize/studies '$WSH/logs'
TOTAL=$total
for pair in $spec; do
  tf=\${pair%%:*}; w=\${pair##*:}; per=\$(( (TOTAL + w - 1) / w ))
  python3 -c \"import optuna; optuna.create_study(study_name='wsh_\$tf', storage='sqlite:///optimize/studies/wsh.db', directions=['maximize','maximize'], load_if_exists=True)\"
  for i in \$(seq 1 \$w); do
    setsid bash -c \"python3 -u optimize/optimizer.py \$tf --trials \$per --folds 5 --min-trades 3 >> '$WSH/logs/\$tf.log' 2>&1\" < /dev/null &
  done
  echo \"\$tf: \$w workers x \$per trials\"
done
EOS
chmod +x '$WSH/launch.sh'; setsid bash '$WSH/launch.sh' < /dev/null > '$WSH/launch.out' 2>&1 & echo launcher-started"
  sleep 6
  log "launcher kicked off; current worker count:"
  srv "pgrep -fc optimize/optimizer.py || echo 0; cat '$WSH/launch.out' 2>/dev/null"
}

cmd_status() {
  srv "echo '== load =='; uptime; echo; cd '$WSH/logs' 2>/dev/null && for tf in ${TFS[*]}; do \
       n=\$(pgrep -fc \"optimizer.py \$tf \" || true); \
       printf '%-4s %s | ' \"\$tf\" \"\$([ \"\${n:-0}\" -gt 0 ] && echo RUNNING || echo done/idle)\"; \
       tail -n1 \"\$tf.log\" 2>/dev/null || echo '(no log)'; done"
}

cmd_pull() {
  mkdir -p "$LOCAL_RESULTS" "$LOCAL_LOGS"
  log "building outputs on server then pulling results + logs"
  srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/report.py ${TFS[*]} || true"
  rsync -az -e "$RSYNC_E" "${SRV_USER}@${SRV_HOST}:$CODE/optimize/results/" "$LOCAL_RESULTS/"
  rsync -az -e "$RSYNC_E" "${SRV_USER}@${SRV_HOST}:$WSH/logs/" "$LOCAL_LOGS/"
  log "pulled → $LOCAL_RESULTS and $LOCAL_LOGS"
}

cmd_stop() { srv "pkill -f 'optimize/optimizer.py' || true"; log "stop signal sent."; }

case "${1:-}" in
  push) cmd_push ;;
  parity) cmd_parity ;;
  run) shift; cmd_run "${1:-1200}" "${2:-}" ;;
  status) cmd_status ;;
  pull) cmd_pull ;;
  stop) cmd_stop ;;
  *) echo "usage: remote.sh {push|parity|run [trials]|status|pull|stop}"; exit 1 ;;
esac
