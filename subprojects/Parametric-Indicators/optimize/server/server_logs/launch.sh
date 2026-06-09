#!/usr/bin/env bash
pkill -9 -f optimize/optimizer.py >/dev/null 2>&1 || true
sleep 2
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE='/home/dev/Mulham/wsg-i' WSG_DATA_ROOT='/home/dev/Mulham/wsg-i/data'
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '/home/dev/Mulham/wsg-i/Parametric-Indicators'; mkdir -p optimize/studies '/home/dev/Mulham/wsg-i/logs'
TOTAL=3000
for pair in 4h:1 2h:1 1h:2 15m:2 5m:4 2m:8 1m:12 ; do
  tf=${pair%%:*}; w=${pair##*:}; per=$(( (TOTAL + w - 1) / w ))
  python3 -c "import optuna; optuna.create_study(study_name='wsh3_$tf', storage='sqlite:///optimize/studies/wsh.db', directions=['maximize','maximize','maximize'], load_if_exists=True)"
  for i in $(seq 1 $w); do
    setsid bash -c "python3 -u optimize/optimizer.py $tf --trials $per --folds 5 --min-trades 5 >> '/home/dev/Mulham/wsg-i/logs/$tf.log' 2>&1" < /dev/null &
  done
  echo "$tf: $w workers x $per trials"
done
