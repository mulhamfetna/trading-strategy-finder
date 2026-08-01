#!/usr/bin/env bash
# wshes1 — L1 optimizer with ES as a SEARCHABLE (unforced) cross-instrument contributor, over the full NQ
# signal set. Cold start (--no-warm-start). Watchdog/respawn pool against a SHARED Postgres study.
set -u
WSI=/home/dev/Mulham/wsg-i
CODE=$WSI/Parametric-Indicators
PREFIX=wshes1
TF=4h
TARGET=15000
W=16
LOG=$WSI/logs/${PREFIX}_${TF}.log

pkill -9 -f 'optimize/optimizer.py' >/dev/null 2>&1 || true
sleep 2
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data"
[ -f "$WSI/pg.env" ] && { set -a; . "$WSI/pg.env"; set +a; }   # sets WSH_STORAGE_URL → Postgres
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd "$CODE" || exit 1
mkdir -p "$WSI/logs" optimize/studies

echo "=== wshes1 launch $(date) :: TARGET=$TARGET W=$W TF=$TF (ES searchable, cold/no-warm-start) ===" >> "$LOG"
python3 -c "import optuna,os; n='${PREFIX}_${TF}'; url=os.environ['WSH_STORAGE_URL']; optuna.create_study(study_name=n, storage=url, directions=['maximize','maximize','maximize'], load_if_exists=True); print('study',n,'ready')" >> "$LOG" 2>&1

run_worker () {
  local done rem per
  while :; do
    done=$(python3 optimize/trial_count.py "$TF" --prefix "$PREFIX" 2>/dev/null || echo 0)
    rem=$(( TARGET - done ))
    if [ "$rem" -le 0 ]; then echo "[watchdog] reached $done/$TARGET — stop" >> "$LOG"; break; fi
    per=$(( (rem + W - 1) / W ))
    python3 -u optimize/optimizer.py "$TF" --contributors ES --ind-1min --no-warm-start \
      --trials "$per" --min-trades 5 --study-prefix "$PREFIX" >> "$LOG" 2>&1 || true
    echo "[watchdog] was $done/$TARGET; ran ~$per; re-checking" >> "$LOG"
  done
}
for i in $(seq 1 "$W"); do run_worker & done
wait
echo "=== wshes1 ALL WORKERS DONE $(date) ===" >> "$LOG"
