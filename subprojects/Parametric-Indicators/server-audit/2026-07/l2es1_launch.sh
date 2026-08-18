#!/usr/bin/env bash
# l2es1 — cross-instrument L2 optimizer (ES contributor) on the cold wsh6cold L1 residuals.
# Watchdog/respawn worker pool against a SHARED Postgres study (mirrors the L1 launch.sh pattern).
set -u
WSI=/home/dev/Mulham/wsg-i
CODE=$WSI/Parametric-Indicators
PREFIX=l2es1
TF=4h
TARGET=20000
W=16
L1C=optimize/results/wsh6cold_4h_champion.json
LOG=$WSI/logs/${PREFIX}_${TF}.log

pkill -9 -f 'optimize/l2/optimize.py' >/dev/null 2>&1 || true
sleep 2
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data"
[ -f "$WSI/pg.env" ] && { set -a; . "$WSI/pg.env"; set +a; }   # sets WSH_STORAGE_URL → Postgres
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd "$CODE" || exit 1
mkdir -p "$WSI/logs" optimize/studies

echo "=== l2es1 launch $(date) :: TARGET=$TARGET W=$W TF=$TF L1=$L1C ===" >> "$LOG"
# pre-create the shared 3-objective study (idempotent)
python3 -c "import optuna,os; n='${PREFIX}_${TF}'; url=os.environ['WSH_STORAGE_URL']; optuna.create_study(study_name=n, storage=url, directions=['maximize','maximize','maximize'], load_if_exists=True); print('study',n,'ready')" >> "$LOG" 2>&1

run_worker () {
  local done rem per
  while :; do
    done=$(python3 optimize/trial_count.py "$TF" --prefix "$PREFIX" 2>/dev/null || echo 0)
    rem=$(( TARGET - done ))
    if [ "$rem" -le 0 ]; then echo "[watchdog] reached $done/$TARGET — stop" >> "$LOG"; break; fi
    per=$(( (rem + W - 1) / W ))
    python3 -u optimize/l2/optimize.py --tf "$TF" --prefix "$PREFIX" \
      --contributors ES --l1-champion "$L1C" --trials "$per" --min-trades 5 >> "$LOG" 2>&1 || true
    echo "[watchdog] was $done/$TARGET; ran ~$per; re-checking" >> "$LOG"
  done
}
for i in $(seq 1 "$W"); do run_worker & done
wait
echo "=== l2es1 ALL WORKERS DONE $(date) ===" >> "$LOG"
