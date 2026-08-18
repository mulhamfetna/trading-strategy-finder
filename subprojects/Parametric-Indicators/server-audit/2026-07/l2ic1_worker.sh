#!/usr/bin/env bash
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE='/home/dev/Mulham/wsg-i' WSG_DATA_ROOT='/home/dev/Mulham/wsg-i/data'
[ -f '/home/dev/Mulham/wsg-i/pg.env' ] && { set -a; . '/home/dev/Mulham/wsg-i/pg.env'; set +a; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '/home/dev/Mulham/wsg-i/Parametric-Indicators'
exec python3 -u -m optimize.l2.optimize --tf 4h --prefix l2ic1 --intracandle --trials 300 --min-trades 5
