#!/usr/bin/env bash
# ES L1 all-TF campaign launcher (server-side). Fires N fully-detached setsid watchdog workers per TF and
# EXITS immediately (no wait → the launching SSH returns cleanly; workers persist independently).
# Each worker loops optimizer.py to TARGET trials. Cold-start, full SMC, --ind-1min. Idempotent/resumable.
LOGDIR=/home/dev/Mulham/wsg-i/logs; mkdir -p "$LOGDIR"
pkill -9 -f "optimizer.py.*--instrument ES" 2>/dev/null; sleep 2

run_worker () {                                   # $1 = tf — one fully-detached watchdog worker
  local tf="$1" log="$LOGDIR/ES_$1.log"
  setsid bash -c '
    cd /home/dev/Mulham/wsg-i/Parametric-Indicators || exit 1
    source /home/dev/Mulham/.venv/bin/activate
    set -a; . /home/dev/Mulham/wsg-i/pg.env; set +a
    export WSI_INSTRUMENT=ES WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
    tf="'"$tf"'"; TARGET=10000; PREFIX=wsh4; CHUNK=300
    while :; do
      d=$(python3 optimize/trial_count.py "$tf" --prefix "$PREFIX" 2>/dev/null || echo 0)
      if [ "${d:-0}" -ge "$TARGET" ]; then echo "[$tf] reached $d/$TARGET — stop $(date +%H:%M:%S)"; break; fi
      echo "[$tf] $d/$TARGET -> +$CHUNK $(date +%H:%M:%S)"
      python3 -u optimize/optimizer.py "$tf" --instrument ES --trials "$CHUNK" --folds 5 --min-trades 3 \
        --study-prefix "$PREFIX" --no-warm-start --ind-1min || true
    done
  ' </dev/null >>"$log" 2>&1 &
}

declare -A W=( [4h]=3 [2h]=4 [1h]=5 [15m]=8 [5m]=10 )    # 30 workers; slow TFs favoured (box has 32 cores)
for tf in 4h 2h 1h 15m 5m; do for i in $(seq 1 "${W[$tf]}"); do run_worker "$tf"; done; done
sleep 1
echo "fired ES workers; now running: $(pgrep -fc 'optimizer.py.*--instrument ES' 2>/dev/null || echo 0)"
