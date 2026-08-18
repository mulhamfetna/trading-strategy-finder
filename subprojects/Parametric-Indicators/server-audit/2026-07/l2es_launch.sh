#!/usr/bin/env bash
# ES L2 cold-start optimizer — one detached setsid process per TF, scoring L2 on the ES L1 champions'
# residuals (--l1-champion). Each runs a fixed n_trials then exports its champion + exits (no watchdog).
cd /home/dev/Mulham/wsg-i/Parametric-Indicators || exit 1
source /home/dev/Mulham/.venv/bin/activate
set -a; . /home/dev/Mulham/wsg-i/pg.env; set +a
export WSI_INSTRUMENT=ES WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
CH=optimize/results/wsh4_champions_full_ES.json
LOGDIR=/home/dev/Mulham/wsg-i/logs; mkdir -p "$LOGDIR"
# drop the throwaway smoke study
python3 - <<'PY' 2>/dev/null || true
import optuna, os
try: optuna.delete_study(study_name="l2es_smoke_4h_ES", storage=os.environ["WSH_STORAGE_URL"])
except Exception: pass
PY
for tf in 4h 2h 1h 15m 5m; do
  setsid python3 -u optimize/l2/optimize.py --instrument ES --tf "$tf" --l1-champion "$CH" \
    --prefix l2es1 --trials 5000 --min-trades 3 </dev/null >> "$LOGDIR/L2ES_$tf.log" 2>&1 &
done
sleep 1
echo "fired L2 ES workers (l2/optimize procs): $(pgrep -fc 'l2/optimize.py.*--instrument ES')"
