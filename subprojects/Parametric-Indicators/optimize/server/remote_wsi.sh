#!/usr/bin/env bash
# WS-I.10 remote runner — run the all-timeframe NSGA-III INDICATOR search on the AMD server.
# Adapted from WS-H remote.sh: own scratch (wsg-i), Parametric-Indicators code, 3-objective study
# wsh3_<tf> + the full-period DD≤25%·P/L constraint, min-trades 5. CPU-only; key auth; detached.
#
#   ./remote_wsi.sh push          rsync Parametric-Indicators + data → server scratch
#   ./remote_wsi.sh parity        run the 4h parity test on the server (env/data sanity)
#   ./remote_wsi.sh run [TRIALS]  launch all 7 TF searches in parallel, detached (default 3000)
#   ./remote_wsi.sh status        host load + per-TF worker count + last log line
#   ./remote_wsi.sh pull          build the WS-I report on the server + rsync results/logs back
#   ./remote_wsi.sh stop          kill all WS-I jobs
set -euo pipefail

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_SRVDIR="$_HERE/../../../meta-prophet/server"
source "$_SRVDIR/server.env"

REPO="/mnt/data/projects/trading"
WSI="/home/dev/Mulham/wsg-i"                          # isolated WS-I scratch
CODE="$WSI/Parametric-Indicators"
LOCAL_RESULTS="$_HERE/../results"
LOCAL_LOGS="$_HERE/server_logs"
LOCAL_REPORTS="$_HERE/../reports"
TFS=(4h 2h 1h 15m 5m 2m)                              # 1-minute TIMEFRAME excluded from the sweep
PREFIX="wsh4"                                          # study prefix for the 1-min-indicators regime
IND_ARGS="--ind-1min --study-prefix $PREFIX"          # indicators read the 1-minute frame

SSH_OPTS=(-p "$SRV_PORT" -i "$SRV_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
          -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
          -o ServerAliveInterval=30 -o ServerAliveCountMax=4)
srv() { ssh "${SSH_OPTS[@]}" "${SRV_USER}@${SRV_HOST}" "$@"; }
RSYNC_E="ssh -p $SRV_PORT -i $SRV_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
log() { printf '\033[1;36m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }

REMOTE_ENV="source $REMOTE_VENV/bin/activate; export WSH_DATA_BASE='$WSI' WSG_DATA_ROOT='$WSI/data'"

cmd_push() {
  log "creating scratch + pushing code/data → $WSI"
  srv "mkdir -p '$WSI' '$CODE'"
  rsync -az --info=stats1 -e "$RSYNC_E" \
    --exclude '__pycache__' --exclude '*.pyc' --exclude 'optimize/studies' \
    --exclude 'optimize/results' --exclude 'optimize/server/server_logs' \
    --exclude 'docs/charts/*.html' \
    "$REPO/subprojects/Parametric-Indicators/" "${SRV_USER}@${SRV_HOST}:$CODE/"
  rsync -az --info=stats1 -e "$RSYNC_E" "$REPO/Full_Canldes_Data/" "${SRV_USER}@${SRV_HOST}:$WSI/Full_Canldes_Data/"
  rsync -az --info=stats1 -e "$RSYNC_E" "$REPO/data/" "${SRV_USER}@${SRV_HOST}:$WSI/data/"
  log "push done."
}

cmd_parity() {
  log "running 4h parity test on the server (data/env sanity)"
  srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/test_parity.py"
}

# GIL-bound (~1 core/process); multiple workers/study share trials via SQLite. With 1-minute
# indicators each trial costs ~similar across TFs (the 1-min indicator compute dominates), so workers
# are spread ~evenly over the 6 TFs with a mild tilt to the finer ones; sum ≈ 30 (2 left for the OS).
declare -A WORKERS=( [2m]=6 [5m]=6 [15m]=5 [1h]=5 [2h]=4 [4h]=4 )

cmd_run() {
  local total="${1:-3000}"; local only="${2:-}"
  local tfs=("${TFS[@]}"); [ -n "$only" ] && read -ra tfs <<< "$only"
  log "launching NSGA-III search ($PREFIX, 1-minute indicators): $total trials/TF [${tfs[*]}] (min-trades 5) ..."
  local spec=""; for tf in "${tfs[@]}"; do spec+="$tf:${WORKERS[$tf]:-1} "; done
  srv "cat > '$WSI/launch.sh' <<'EOS'
#!/usr/bin/env bash
pkill -9 -f optimize/optimizer.py >/dev/null 2>&1 || true
sleep 2
source $REMOTE_VENV/bin/activate
export WSH_DATA_BASE='$WSI' WSG_DATA_ROOT='$WSI/data'
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '$CODE'; mkdir -p optimize/studies '$WSI/logs'
TOTAL=$total
for pair in $spec; do
  tf=\${pair%%:*}; w=\${pair##*:}; per=\$(( (TOTAL + w - 1) / w ))
  python3 -c \"import optuna; optuna.create_study(study_name='${PREFIX}_\$tf', storage='sqlite:///optimize/studies/wsh.db', directions=['maximize','maximize','maximize'], load_if_exists=True)\"
  for i in \$(seq 1 \$w); do
    setsid bash -c \"python3 -u optimize/optimizer.py \$tf --trials \$per --folds 5 --min-trades 5 $IND_ARGS >> '$WSI/logs/\$tf.log' 2>&1\" < /dev/null &
  done
  echo \"\$tf: \$w workers x \$per trials\"
done
EOS
chmod +x '$WSI/launch.sh'; setsid bash '$WSI/launch.sh' < /dev/null > '$WSI/launch.out' 2>&1 & echo launcher-started"
  sleep 8
  log "workers now running:"; srv "pgrep -fc optimize/optimizer.py || echo 0; cat '$WSI/launch.out' 2>/dev/null"
}

cmd_status() {
  srv "echo '== load =='; uptime; echo; cd '$WSI/logs' 2>/dev/null && for tf in ${TFS[*]}; do \
       n=\$(pgrep -fc \"optimizer.py \$tf \" || true); \
       printf '%-4s %s | ' \"\$tf\" \"\$([ \"\${n:-0}\" -gt 0 ] && echo RUNNING || echo done/idle)\"; \
       tail -n1 \"\$tf.log\" 2>/dev/null || echo '(no log)'; done"
}

cmd_counts() {  # per-TF completed-trial counts in the shared DB
  srv "$REMOTE_ENV; cd '$CODE'; python3 - <<'PY'
import optuna; optuna.logging.set_verbosity(optuna.logging.WARNING)
for tf in '${TFS[*]}'.split():
    try:
        s=optuna.load_study(study_name=f'${PREFIX}_{tf}', storage='sqlite:///optimize/studies/wsh.db')
        c=[t for t in s.trials if t.values is not None]
        feas=sum(1 for t in c if (t.user_attrs.get('full_pnl',0) or 0)>0 and t.user_attrs.get('full_dd',9e9)<=0.25*t.user_attrs.get('full_pnl',0))
        print(f'  {tf:4s} trials={len(s.trials):5d} complete={len(c):4d} feasible={feas:3d}')
    except Exception as e: print(f'  {tf}: {e}')
PY"
}

cmd_pull() {
  mkdir -p "$LOCAL_RESULTS" "$LOCAL_LOGS" "$LOCAL_REPORTS"
  log "building WS-I report on server then pulling results + logs"
  srv "$REMOTE_ENV; export WSI_STUDY_PREFIX=$PREFIX; cd '$CODE' && python3 optimize/report_wsi.py ${TFS[*]} || true"
  rsync -az -e "$RSYNC_E" "${SRV_USER}@${SRV_HOST}:$CODE/optimize/results/" "$LOCAL_RESULTS/"
  rsync -az -e "$RSYNC_E" "${SRV_USER}@${SRV_HOST}:$CODE/optimize/reports/WS-I_RESULTS.md" "$LOCAL_REPORTS/" 2>/dev/null || true
  rsync -az -e "$RSYNC_E" "${SRV_USER}@${SRV_HOST}:$WSI/logs/" "$LOCAL_LOGS/"
  log "pulled → $LOCAL_RESULTS, $LOCAL_REPORTS, $LOCAL_LOGS"
}

cmd_stop() { srv "pkill -f 'optimize/optimizer.py' || true"; log "stop signal sent."; }

case "${1:-}" in
  push) cmd_push ;; parity) cmd_parity ;; run) shift; cmd_run "${1:-3000}" "${2:-}" ;;
  status) cmd_status ;; counts) cmd_counts ;; pull) cmd_pull ;; stop) cmd_stop ;;
  *) echo "usage: remote_wsi.sh {push|parity|run [trials]|status|counts|pull|stop}"; exit 1 ;;
esac
