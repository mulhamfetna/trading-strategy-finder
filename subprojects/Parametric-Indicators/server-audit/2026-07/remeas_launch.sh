#!/usr/bin/env bash
set -u
WSI=/home/dev/Mulham/wsg-i; CODE=$WSI/Parametric-Indicators
PREFIX=l2remeas; TF=4h; W=16; L1C=optimize/results/wsh6cold_4h_champion.json
LOG=$WSI/logs/${PREFIX}_${TF}.log
pkill -9 -f 'l2/optimize.py --tf 4h --prefix l2remeas' >/dev/null 2>&1 || true; sleep 1
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data"
[ -f "$WSI/pg.env" ] && { set -a; . "$WSI/pg.env"; set +a; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd "$CODE" || exit 1; mkdir -p "$WSI/logs"
python3 -c "import optuna,os; optuna.create_study(study_name='${PREFIX}_${TF}', storage=os.environ['WSH_STORAGE_URL'], directions=['maximize','maximize','maximize'], load_if_exists=True)" >>"$LOG" 2>&1
for i in $(seq 1 $W); do
  python3 -u optimize/l2/optimize.py --tf "$TF" --prefix "$PREFIX" --l1-champion "$L1C" --trials 600 --min-trades 1 >>"$LOG" 2>&1 &
done
wait
