#!/usr/bin/env bash
# Launcher for the wshent1 campaign: NQ · 4h · COLD start (--no-warm-start) · L1 only ·
# objective=entries (maximise median-fold trade count; objectives = median P/L, -worst DD, median entries).
# Pre-creates the shared Postgres study, fires WORKERS setsid-detached watchdog workers, then EXITS.
# Workers survive SSH/session close. Stop with: pkill -f wshent1_worker.sh   (kill workers; they don't respawn from here)
set -u
CODE=/home/dev/Mulham/wsg-i/Parametric-Indicators
WSI=/home/dev/Mulham/wsg-i
VENV=/home/dev/Mulham/.venv
PREFIX=wshent1; TF=4h; TARGET=50000; WORKERS=30   # 30 == cores-2 (oversubscription guard limit on the 32c box)
LOG="$WSI/logs/${PREFIX}_${TF}.log"; mkdir -p "$WSI/logs"
cd "$CODE" || exit 1
source "$VENV/bin/activate"
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" WSI_INSTRUMENT=NQ
set -a; . "$WSI/pg.env"; set +a
python3 -c "import optuna,os; optuna.create_study(study_name='${PREFIX}_${TF}', storage=os.environ['WSH_STORAGE_URL'], directions=['maximize','maximize','maximize'], load_if_exists=True)" >> "$LOG" 2>&1
echo "[launch $(date +%F_%H:%M:%S)] ${PREFIX}_${TF} target=${TARGET} workers=${WORKERS} NQ cold objective=entries" >> "$LOG"
for i in $(seq 1 "$WORKERS"); do
  setsid bash "$WSI/wshent1_worker.sh" "$i" >/dev/null 2>&1 < /dev/null &
done
echo "[launch] fired ${WORKERS} workers" >> "$LOG"
