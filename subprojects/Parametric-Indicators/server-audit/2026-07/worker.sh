#!/usr/bin/env bash
tf="$1"; cd '/home/dev/Mulham/wsg-i/Parametric-Indicators' || exit 1
source /home/dev/Mulham/.venv/bin/activate
export WSH_DATA_BASE='/home/dev/Mulham/wsg-i' WSG_DATA_ROOT='/home/dev/Mulham/wsg-i/data' WSH_STORAGE_URL='postgresql://wsh:b4246c04d257332a4eb3d282d64ff0dd@127.0.0.1:55432/wsh' WSI_INSTRUMENT='NQ'
[ -z "$WSH_STORAGE_URL" ] && [ -f '/home/dev/Mulham/wsg-i/pg.env' ] && { set -a; . '/home/dev/Mulham/wsg-i/pg.env'; set +a; }   # else Postgres from pg.env
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
TARGET=10; log="/home/dev/Mulham/wsg-i/logs/$tf.log"
while :; do
  done=$(python3 optimize/trial_count.py "$tf" --prefix wsh4 2>/dev/null || echo 0)
  if [ "${done:-0}" -ge "$TARGET" ]; then echo "[watchdog] $tf reached $done/$TARGET — stop" >> "$log"; break; fi
  echo "[watchdog] $tf $done/$TARGET → +chunk $(date +%H:%M:%S)" >> "$log"
  python3 -u optimize/optimizer.py "$tf" --trials 300 --folds 5 --min-trades 5 --ind-1min --study-prefix wsh4 --split-sltp --sampler nsga3   --only-indicators cisd,ifvg,fvg,breaker,order_block,adx,structure_trend,kalman,ichimoku_chikou   --no-warm-start --dd-pnl-cap 10  >> "$log" 2>&1 || true
done
