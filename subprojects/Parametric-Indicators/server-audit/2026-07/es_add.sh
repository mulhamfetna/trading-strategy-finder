#!/usr/bin/env bash
# ADD extra detached workers to the coarse-TF ES studies (no pkill — existing workers keep running).
# Coarse TFs prune most full-SMC trials, so they need more workers to reach 10k COMPLETED trials.
LOGDIR=/home/dev/Mulham/wsg-i/logs; mkdir -p "$LOGDIR"
run_worker () {
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
# +9 for 4h (3→12), +6 for 2h (4→10): brings their completion rate up ~4x to match the fine TFs' finish window
for i in $(seq 1 9); do run_worker 4h; done
for i in $(seq 1 6); do run_worker 2h; done
sleep 1
echo "added coarse-TF workers; total ES python procs now: $(pgrep -fc '[p]ython3 -u optimize/optimizer.py' 2>/dev/null || echo 0)"
