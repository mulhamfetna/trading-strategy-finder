#!/usr/bin/env bash
set -u
WSI=/home/dev/Mulham/wsg-i; CODE=$WSI/Parametric-Indicators
TF=4h; L1C=optimize/results/wsh6cold_4h_champion.json; PREFIX=wsweep
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data"
[ -f "$WSI/pg.env" ] && { set -a; . "$WSI/pg.env"; set +a; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd "$CODE" || exit 1
python3 -c "import optuna,os; optuna.create_study(study_name='${PREFIX}_${TF}', storage=os.environ['WSH_STORAGE_URL'], directions=['maximize','maximize','maximize'], load_if_exists=True)" 2>/dev/null
tc(){ python3 optimize/trial_count.py $TF --prefix $PREFIX 2>/dev/null || echo 0; }
echo "worker-count sweep (candidate-L1 wsh6cold, memoized code):"
for W in 12 16 24 32; do
  for i in $(seq 1 $W); do python3 -u optimize/l2/optimize.py --tf $TF --prefix $PREFIX --l1-champion "$L1C" --trials 400 --min-trades 1 >/dev/null 2>&1 & done
  sleep 18   # ramp
  A=$(tc); T1=$(date +%s); sleep 60; B=$(tc); T2=$(date +%s)
  pkill -9 -f "l2/optimize.py --tf $TF --prefix $PREFIX" 2>/dev/null; sleep 3
  python3 -c "r=($B-$A)/($T2-$T1); print(f'  W={$W:>2}: {r*60:6.0f} completed/min  (load was: $(cut -d\" \" -f1 /proc/loadavg))')"
done
echo "sweep done"
