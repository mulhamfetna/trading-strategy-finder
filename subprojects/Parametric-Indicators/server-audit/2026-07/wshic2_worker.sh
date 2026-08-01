#!/usr/bin/env bash
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE='/home/dev/Mulham/wsg-i' WSG_DATA_ROOT='/home/dev/Mulham/wsg-i/data'
[ -f '/home/dev/Mulham/wsg-i/pg.env' ] && { set -a; . '/home/dev/Mulham/wsg-i/pg.env'; set +a; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '/home/dev/Mulham/wsg-i/Parametric-Indicators'
exec python3 -u optimize/optimizer.py 4h --trials 300 --folds 5 --min-trades 5 \
  --ind-1min --intracandle-on --freeze-indicators --objective entries --study-prefix wshic2
