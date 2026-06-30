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
# LOCAL MODE (WSH_LOCAL=1): the control dashboard runs ON the server, so commands execute locally (no SSH
# hop back to ourselves) and server.env (a laptop-side file) is optional. REMOTE_VENV must then come from the
# environment (dashboard.env). Default the SSH vars to harmless values so `set -u` doesn't trip on the unused
# SSH code path. Default (unset WSH_LOCAL): unchanged — source server.env and SSH to the server as before.
if [ -n "${WSH_LOCAL:-}" ]; then
  [ -f "$_SRVDIR/server.env" ] && source "$_SRVDIR/server.env" || true
  : "${SRV_HOST:=localhost}" "${SRV_PORT:=22}" "${SRV_USER:=${USER:-dev}}" "${SRV_KEY:=/dev/null}"
  : "${REMOTE_VENV:?WSH_LOCAL set but REMOTE_VENV unset — set REMOTE_VENV in dashboard.env}"
else
  source "$_SRVDIR/server.env"
fi

REPO="/mnt/data/projects/trading"
WSI="/home/dev/Mulham/wsg-i"                          # isolated WS-I scratch
CODE="$WSI/Parametric-Indicators"
LOCAL_RESULTS="$_HERE/../results"
LOCAL_LOGS="$_HERE/server_logs"
LOCAL_REPORTS="$_HERE/../reports"
# ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
# │  ⚠️  FULL-DATA OPTIMIZER RUNS **4h ONLY** (2026-06-15 user directive)                            │
# │  For time-saving + study focus, the full-data NSGA-III sweep optimizes ONLY the 4h timeframe and │
# │  CONCENTRATES ALL WORKERS on it (no spread across TFs). The other timeframes are HELD (not run). │
# │  >>> THIS APPLIES ONLY TO THE FULL-DATA OPTIMIZER SWEEP. <<<                                     │
# │  EVERY other process — parity tests, smoke tests, golden byte-match, and ALL engine/system       │
# │  development — STILL considers ALL timeframes. Only this production sweep is 4h-focused for now. │
# │  To resume the full all-TF sweep: set TFS=("${TFS_ALL[@]}") and restore the per-TF WORKERS map.  │
# └──────────────────────────────────────────────────────────────────────────────────────────────┘
TFS_ALL=(4h 2h 1h 15m 5m 2m)                          # full set (1-minute TF excluded) — restore to resume all-TF sweeps
# 4h ONLY by default (full-data focus); override with WSH_TFS="4h 2h 1h 15m 5m 2m" (or "all") for an all-TF sweep.
if [ "${WSH_TFS:-}" = "all" ]; then TFS=("${TFS_ALL[@]}"); elif [ -n "${WSH_TFS:-}" ]; then read -ra TFS <<< "$WSH_TFS"; else TFS=(4h); fi
PREFIX="${WSH_PREFIX:-wsh4}"                           # study prefix; override e.g. WSH_PREFIX=wsh5 for a fresh regime
SPLIT_ARG="${WSH_SPLIT:+--split-sltp}"                 # set WSH_SPLIT=1 to search SEPARATE long/short SL/TP (Q3/E2)
SAMPLER_ARG="${WSH_SAMPLER:+--sampler $WSH_SAMPLER}"   # optimizer brain (P2): nsga3*(default)|nsga2|tpe|motpe|gp; unset ⇒ nsga3 (unchanged)
OBJ_ARG="${WSH_OBJECTIVE:+--objective $WSH_OBJECTIVE}" # α: winrate*(default)|decision_pause; unset ⇒ winrate (unchanged)
EXCL_ARG="${WSH_EXCLUDE:+--exclude-indicators $WSH_EXCLUDE}"  # α: e.g. ifvg,breaker,cisd reverts to wsh4-era 15
DDCAP_ARG="${WSH_DD_CAP:+--dd-pnl-cap $WSH_DD_CAP}"    # α: relax the DD≤cap·P/L feasibility (e.g. 0.5) for shorter pauses
INSTRUMENT="${WSH_INSTRUMENT:-NQ}"                     # NQ (default) or ES; non-NQ → suffixed studies/champions
INST_ARG=""; [ "$INSTRUMENT" != "NQ" ] && INST_ARG="--instrument $INSTRUMENT"
RSUF=""; [ "$INSTRUMENT" != "NQ" ] && RSUF="_$INSTRUMENT"   # study/db filename suffix mirrored into launch.sh + readers
IND_ARGS="--ind-1min --study-prefix $PREFIX $SPLIT_ARG $SAMPLER_ARG $OBJ_ARG $EXCL_ARG $DDCAP_ARG $INST_ARG" # indicators read the 1-minute frame

SSH_OPTS=(-p "$SRV_PORT" -i "$SRV_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
          -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
          -o ServerAliveInterval=30 -o ServerAliveCountMax=4)
srv() { if [ -n "${WSH_LOCAL:-}" ]; then bash -c "$*"; else ssh "${SSH_OPTS[@]}" "${SRV_USER}@${SRV_HOST}" "$@"; fi; }
RSYNC_E="ssh -p $SRV_PORT -i $SRV_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
log() { printf '\033[1;36m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }

# Tier 1: optional centralized store URL. Set WSH_STORAGE_URL (e.g. postgresql://wsh:***@localhost/wsh)
# in your shell before invoking; empty ⇒ the per-TF sqlite files (unchanged). Forwarded to the workers
# (launch.sh), the pre-create one-liner, and the readers (counts/pull) so all honour one source of truth.
STORAGE_URL="${WSH_STORAGE_URL:-}"
# Server-side store resolution: a local WSH_STORAGE_URL (forwarded as STORAGE_URL) wins; otherwise, if the
# server has a $WSI/pg.env (written by the Postgres provisioning), source it so the secret never leaves the
# box; otherwise empty ⇒ per-TF sqlite. Used by parity/counts/stats/pull and (mirrored) by launch.sh.
_PG_FALLBACK="[ -z \"\$WSH_STORAGE_URL\" ] && [ -f '$WSI/pg.env' ] && { set -a; . '$WSI/pg.env'; set +a; }"
REMOTE_ENV="source $REMOTE_VENV/bin/activate; export WSH_DATA_BASE='$WSI' WSG_DATA_ROOT='$WSI/data' WSH_STORAGE_URL='$STORAGE_URL' WSI_INSTRUMENT='$INSTRUMENT'; $_PG_FALLBACK"

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
  # Non-NQ instruments resolve candles+boxes via the all-stocks-signals registry under ALL_STOCKS/. The server
  # layout mirrors the repo at $WSI (WSH_DATA_BASE), so push both the registry and the data tree there.
  if [ "$INSTRUMENT" != "NQ" ]; then
    log "instrument=$INSTRUMENT → syncing the instrument registry (instruments.py only) + ALL_STOCKS data (~180MB)"
    srv "mkdir -p '$WSI/subprojects/all-stocks-signals' '$WSI/ALL_STOCKS'"
    # ONLY the registry file is imported (optimize.instruments._load_registry); the rest of all-stocks-signals
    # (its 6GB+ output/ delivery bundles) is NOT needed on the server — do not ship it.
    rsync -az --info=stats1 -e "$RSYNC_E" \
      "$REPO/subprojects/all-stocks-signals/instruments.py" "${SRV_USER}@${SRV_HOST}:$WSI/subprojects/all-stocks-signals/instruments.py"
    rsync -az --info=stats1 -e "$RSYNC_E" "$REPO/ALL_STOCKS/" "${SRV_USER}@${SRV_HOST}:$WSI/ALL_STOCKS/"
  fi
  log "push done."
}

cmd_parity() {
  log "running 4h parity test on the server (data/env sanity)"
  srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/test_parity.py"
}

# GIL-bound (~1 core/process); multiple workers/study share trials via the store. With 1-minute
# indicators each trial costs ~similar across TFs (the 1-min indicator compute dominates), so workers
# are spread ~evenly over the 6 TFs with a mild tilt to the finer ones; sum ≈ 30 (2 left for the OS).
#
# CAPACITY FORMULA (Tier 4.3): total workers ≈ (cores − 2). On SQLite the *write-lock* caps useful
# concurrency — ~5 writers/DB file is comfortable (per-TF DBs from Tier 0.3 give 6 files ⇒ ~30 total) and
# the Tier-3 `smoke` gate must pass at the chosen count. PostgreSQL (set WSH_STORAGE_URL) removes the
# write-lock cap via MVCC, so the only ceiling becomes cores − 2; scale this map up accordingly there.
# 4h gets ALL workers (box has 32 cores; leave 2 for OS/Postgres). The other entries are kept for when the
# full all-TF sweep is resumed (TFS=TFS_ALL); they are inert while TFS=(4h). (Was spread 6/6/5/5/4/4 across TFs.)
declare -A WORKERS=( [4h]=30 [2h]=4 [1h]=5 [15m]=5 [5m]=6 [2m]=6 )
# Override the per-TF worker counts for an all-TF sweep, e.g. WSH_WORKERS="4h:3 2h:4 1h:5 15m:8 5m:10"
# (favours the slow fine TFs). On Postgres (WSH_STORAGE_URL) the sqlite write-lock cap is gone, so the
# only ceiling is cores−2. Unset ⇒ the default map above (4h-focus) is used unchanged.
if [ -n "${WSH_WORKERS:-}" ]; then declare -A WORKERS=(); for _kv in $WSH_WORKERS; do WORKERS[${_kv%%:*}]=${_kv##*:}; done; fi

# Print the dimension-proportional trial plan for the current TFs (dry run — never launches).
cmd_plan() {
  local tfs=("${TFS[@]}")
  log "search-space plan ($PREFIX, split=${WSH_SPLIT:+on}${WSH_SPLIT:-off}) — trials scale ∝ dimensions:"
  for tf in "${tfs[@]}"; do
    srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/optimizer.py '$tf' --plan $SPLIT_ARG $INST_ARG" || true
  done
}

cmd_run() {
  local tfs=("${TFS[@]}"); [ -n "${2:-}" ] && read -ra tfs <<< "$2"
  # Dimension-proportional budget (anti 'bigger space, fewer samples' trap — see the superset-paradox report):
  # default TARGET = recommended_trials(dims) for the current split mode; pass an explicit number to override.
  local split_py="False"; [ -n "${WSH_SPLIT:-}" ] && split_py="True"
  local rec; rec=$(srv "$REMOTE_ENV; cd '$CODE' && python3 -c \"from optimize import optimizer as O; print(O.recommended_trials($split_py))\"" 2>/dev/null | tr -dc '0-9')
  local total="${1:-auto}"; { [ "$total" = "auto" ] || [ -z "$total" ]; } && total="${rec:-5000}"
  log "PLAN: prefix=$PREFIX  TFs=[${tfs[*]}]  split=${WSH_SPLIT:+on}${WSH_SPLIT:-off}  warm-start=ON"
  log "      recommended ${rec:-?} trials/TF (∝ dimensions)  →  TARGET ${total} trials/TF"
  cmd_plan
  # Acceptance gate: report the budget and require a yes (or WSH_CONFIRM=1 to skip in automation).
  if [ -z "${WSH_CONFIRM:-}" ]; then
    read -rp "Launch this run with TARGET ${total} trials/TF? [y/N] " _ans </dev/tty 2>/dev/null || _ans=""
    case "$_ans" in [yY]*) ;; *) log "aborted — not launched (set WSH_CONFIRM=1 to skip this prompt)"; return 1 ;; esac
  fi
  log "launching NSGA-III search ($PREFIX, 1-minute indicators): target $total trials/TF (idempotent, watchdog/respawn, warm-started) [${tfs[*]}] (min-trades 5) ..."
  local spec=""; for tf in "${tfs[@]}"; do spec+="$tf:${WORKERS[$tf]:-1} "; done
  # (1) Self-contained watchdog WORKER (one process per worker; tf = \$1). Sets up its OWN env so each worker
  #     is INDEPENDENTLY setsid-detached and survives launcher/session death. Loops the optimizer in fixed
  #     chunks, topping the SHARED study up to TARGET (idempotent); stops when target is reached.
  srv "cat > '$WSI/worker.sh' <<'EOS'
#!/usr/bin/env bash
tf=\"\$1\"; cd '$CODE' || exit 1
source $REMOTE_VENV/bin/activate
export WSH_DATA_BASE='$WSI' WSG_DATA_ROOT='$WSI/data' WSH_STORAGE_URL='$STORAGE_URL' WSI_INSTRUMENT='$INSTRUMENT'
[ -z \"\$WSH_STORAGE_URL\" ] && [ -f '$WSI/pg.env' ] && { set -a; . '$WSI/pg.env'; set +a; }   # else Postgres from pg.env
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
TARGET=$total; log=\"$WSI/logs/\$tf.log\"
while :; do
  done=\$(python3 optimize/trial_count.py \"\$tf\" --prefix ${PREFIX} 2>/dev/null || echo 0)
  if [ \"\${done:-0}\" -ge \"\$TARGET\" ]; then echo \"[watchdog] \$tf reached \$done/\$TARGET — stop\" >> \"\$log\"; break; fi
  echo \"[watchdog] \$tf \$done/\$TARGET → +chunk \$(date +%H:%M:%S)\" >> \"\$log\"
  python3 -u optimize/optimizer.py \"\$tf\" --trials 300 --folds 5 --min-trades 5 $IND_ARGS >> \"\$log\" 2>&1 || true
done
EOS
chmod +x '$WSI/worker.sh'"
  # (2) Launcher: pre-create each study, fire W detached setsid workers per TF, then EXIT (no 'wait'). The
  #     launching SSH returns immediately (nothing holds the channel open) and the workers persist on their own.
  srv "cat > '$WSI/launch.sh' <<'EOS'
#!/usr/bin/env bash
pkill -9 -f optimize/optimizer.py >/dev/null 2>&1 || true
sleep 2
source $REMOTE_VENV/bin/activate
export WSH_DATA_BASE='$WSI' WSG_DATA_ROOT='$WSI/data' WSH_STORAGE_URL='$STORAGE_URL' WSI_INSTRUMENT='$INSTRUMENT'
[ -z \"\$WSH_STORAGE_URL\" ] && [ -f '$WSI/pg.env' ] && { set -a; . '$WSI/pg.env'; set +a; }
cd '$CODE'; mkdir -p optimize/studies '$WSI/logs'
for pair in $spec; do
  tf=\${pair%%:*}; w=\${pair##*:}
  python3 -c \"import optuna,sqlite3,os; n='${PREFIX}_\${tf}${RSUF}'; per='optimize/studies/wsh_\${tf}${RSUF}.db'; sh='optimize/studies/wsh.db'; h=lambda d:(os.path.exists(d) and n in [r[0] for r in sqlite3.connect(d).execute('SELECT study_name FROM studies')]); db=(sh if (not os.path.exists(per) and h(sh)) else per); url=(os.environ.get('WSH_STORAGE_URL') or 'sqlite:///'+db); optuna.create_study(study_name=n, storage=url, directions=['maximize','maximize','maximize'], load_if_exists=True); print('study',n,'->',url)\"
  for i in \$(seq 1 \$w); do setsid bash '$WSI/worker.sh' \"\$tf\" </dev/null >> \"$WSI/logs/\${tf}.log\" 2>&1 & done
  echo \"\$tf: \$w setsid workers → target $total (independent, watchdog/respawn, idempotent)\"
done
# NO wait — each worker is its own setsid session and persists independently; the launcher exits here.
EOS
chmod +x '$WSI/launch.sh'; setsid bash '$WSI/launch.sh' < /dev/null > '$WSI/launch.out' 2>&1 & echo launcher-started"
  sleep 8
  log "workers now running:"; srv "pgrep -fc optimize/optimizer.py || echo 0; tail -4 '$WSI/launch.out' 2>/dev/null"
}

# P3 two-stage decomposition launch (dashboard engine=two_stage). Unlike cmd_run's watchdog/respawn loop
# (which tops up a SHARED store study until it reaches a TARGET trial-count), two_stage runs FINITE
# in-memory Optuna studies with no countable target — so it is launched ONCE, detached, with NO respawn
# (a respawn would loop forever). Per-TF stages: A (discrete indicator pick) → top-K → B (continuous tune).
# Tunables via env: WSH_STAGE_B(cmaes|gp) WSH_STAGE_A_TRIALS WSH_STAGE_B_TRIALS WSH_TOP_K; WSH_SPLIT honoured.
cmd_two_stage() {
  local tfs=("${TFS[@]}"); [ -n "${1:-}" ] && read -ra tfs <<< "$1"
  local stage_b="${WSH_STAGE_B:-cmaes}"
  local sa="${WSH_STAGE_A_TRIALS:-200}" sb="${WSH_STAGE_B_TRIALS:-100}" tk="${WSH_TOP_K:-3}"
  local ts_args="--stage-b $stage_b --stage-a-trials $sa --stage-b-trials $sb --top-k $tk --ind-1min $SPLIT_ARG"
  log "TWO-STAGE (P3) launch: TFs=[${tfs[*]}]  stage-B=$stage_b  A=$sa B=$sb topK=$tk  split=${WSH_SPLIT:+on}${WSH_SPLIT:-off}"
  # Acceptance gate (mirrors cmd_run): require a yes, or WSH_CONFIRM=1 to skip in automation/the dashboard.
  if [ -z "${WSH_CONFIRM:-}" ]; then
    read -rp "Launch TWO-STAGE on [${tfs[*]}]? [y/N] " _ans </dev/tty 2>/dev/null || _ans=""
    case "$_ans" in [yY]*) ;; *) log "aborted — not launched (set WSH_CONFIRM=1 to skip this prompt)"; return 1 ;; esac
  fi
  local tflist="${tfs[*]}"
  srv "cat > '$WSI/two_stage.sh' <<'EOS'
#!/usr/bin/env bash
pkill -9 -f 'optimize.two_stage' >/dev/null 2>&1 || true
sleep 2
source $REMOTE_VENV/bin/activate
export WSH_DATA_BASE='$WSI' WSG_DATA_ROOT='$WSI/data' WSH_STORAGE_URL='$STORAGE_URL' WSI_INSTRUMENT='$INSTRUMENT'
[ -z \"\$WSH_STORAGE_URL\" ] && [ -f '$WSI/pg.env' ] && { set -a; . '$WSI/pg.env'; set +a; }   # else Postgres from pg.env
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '$CODE'; mkdir -p '$WSI/logs'
# Each TF is a single FINITE run (no watchdog) appended to the same per-TF log the dashboard SSE tails.
for tf in $tflist; do
  ( echo \"[\$(date +%H:%M:%S)] [two-stage] \$tf START ($ts_args)\"; \
    python3 -u -m optimize.two_stage \"\$tf\" $ts_args; \
    echo \"[\$(date +%H:%M:%S)] [two-stage] \$tf DONE\" ) >> \"$WSI/logs/\$tf.log\" 2>&1 &
done
wait
EOS
chmod +x '$WSI/two_stage.sh'; setsid bash '$WSI/two_stage.sh' < /dev/null > '$WSI/two_stage.out' 2>&1 & echo launcher-started"
  sleep 6
  log "two-stage workers now running:"; srv "pgrep -fc 'optimize.two_stage' || echo 0; cat '$WSI/two_stage.out' 2>/dev/null"
}

cmd_status() {
  srv "echo '== load =='; uptime; echo; cd '$WSI/logs' 2>/dev/null && for tf in ${TFS[*]}; do \
       n=\$(pgrep -fc \"optimizer.py \$tf \" || true); \
       printf '%-4s %s | ' \"\$tf\" \"\$([ \"\${n:-0}\" -gt 0 ] && echo RUNNING || echo done/idle)\"; \
       tail -n1 \"\$tf.log\" 2>/dev/null || echo '(no log)'; done"
}

cmd_counts() {  # per-TF completed-trial counts; per-TF DB file, falling back to the shared wsh.db
  srv "$REMOTE_ENV; cd '$CODE'; python3 - <<'PY'
import optuna, sqlite3, os
optuna.logging.set_verbosity(optuna.logging.WARNING)
def _has(db, n):
    if not os.path.exists(db): return False
    try:
        c=sqlite3.connect(db); r=[x[0] for x in c.execute('SELECT study_name FROM studies')]; c.close(); return n in r
    except Exception: return False
def _db(tf, n):
    per='optimize/studies/wsh_%s${RSUF}.db'%tf; sh='optimize/studies/wsh.db'
    if _has(per, n): return per
    if _has(sh, n): print(f'  ⚠️  FALLBACK {tf}: per-TF file absent, reading shared wsh.db'); return sh
    return per
for tf in '${TFS[*]}'.split():
    try:
        n=f'${PREFIX}_{tf}${RSUF}'
        s=optuna.load_study(study_name=n, storage=(os.environ.get('WSH_STORAGE_URL') or 'sqlite:///'+_db(tf, n)))
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

# Bracket the first char so the pattern never matches pkill's OWN command line (in local mode srv runs the
# string via `bash -c`, whose argv would otherwise contain the literal pattern and self-terminate).
cmd_stop() { srv "pkill -f '[o]ptimize/optimizer.py' || true; pkill -f '[o]ptimize.two_stage' || true"; log "stop signal sent (single + two-stage)."; }

# Tier 3 — observability + pre-flight gate.
cmd_stats() {  # live COMPLETE / RUNNING / FAIL / pruned per study (a contention storm = rising FAIL)
  # Forward extra args (e.g. --json, which the dashboard's control.status() needs to parse the output).
  srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/study_stats.py ${TFS[*]} --prefix $PREFIX $*"
}
cmd_smoke() {  # pre-flight contention probe BEFORE a multi-hour sweep — must report ZERO lock deaths
  local w="${1:-30}" k="${2:-20}"
  log "pre-flight contention smoke: $w workers × $k trials (store = ${STORAGE_URL:-per-TF sqlite})"
  srv "$REMOTE_ENV; cd '$CODE' && python3 optimize/contention_smoke.py --workers $w --trials $k ${STORAGE_URL:+--url '$STORAGE_URL'}"
}

case "${1:-}" in
  push) cmd_push ;; parity) cmd_parity ;; run) shift; cmd_run "${1:-3000}" "${2:-}" ;;
  two-stage) shift; cmd_two_stage "${1:-}" ;;
  status) cmd_status ;; counts) cmd_counts ;; stats) shift; cmd_stats "$@" ;; smoke) shift; cmd_smoke "${1:-30}" "${2:-20}" ;;
  pull) cmd_pull ;; stop) cmd_stop ;; plan) cmd_plan ;;
  *) echo "usage: remote_wsi.sh {push|parity|smoke [workers] [trials]|plan|run [target|auto]|two-stage [tfs]|status|counts|stats|pull|stop}"; exit 1 ;;
esac
