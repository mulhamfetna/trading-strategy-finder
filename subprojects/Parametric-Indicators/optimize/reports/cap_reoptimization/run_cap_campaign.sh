#!/bin/bash
# Re-optimize every market × every timeframe with the TWO new time-cap dimensions searched:
#     en_cap_bars (yes/no) -> cap_1min (how many traded 1-min bars)
#     en_cap_eod  (yes/no)   [both on => exit at whichever deadline lands first]
# Cold start (no warm-start seeding), 1-minute indicator frame, fresh study prefix `cap1`.
#
# NOTHING is skipped: a DB check confirmed ZERO trials in ANY existing study ever searched cap_mode,
# so all 9 x 6 = 54 slots need this. Prior studies (wsh4/hg1/cl1/ng1...) are untouched.
#
# Runs a WORK QUEUE (not waves): 54 jobs across N workers, each worker picks up the next job as it frees.
# Each campaign is single-core (~288 MB RSS measured), so thread pinning keeps them from oversubscribing.
set -u

WSI=~/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source ~/Mulham/.venv/bin/activate 2>/dev/null
export WSH_DATA_BASE="$WSI"
export WSG_DATA_ROOT="$WSI/data"
set -a; . "$WSI/pg.env"; set +a

# one core per campaign — numpy/BLAS must not fan out or 20 workers become 200 threads
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# Trial store: POSTGRES (default). JournalStorage was implemented and BENCHMARKED — and it LOST:
#   1 worker : postgres 188 tr/min  vs journal 164  (0.9x)
#   20 workers: postgres 2,286 total vs journal 1,867 (0.8x)
# Postgres' MVCC + connection pool beat a per-study append-only file, whose fsync-per-append costs more
# than it saves. The code remains available (JOURNAL=1) but is OFF: we do not ship a measured regression.
if [ "${JOURNAL:-0}" = "1" ]; then
    export WSH_JOURNAL_DIR="$WSI/journals"
    mkdir -p "$WSH_JOURNAL_DIR"
fi

PREFIX=${PREFIX:-cap1}
WORKERS=${WORKERS:-20}
LOGDIR="$WSI/caprun"
mkdir -p "$LOGDIR"

INSTS=${INSTS:-"NQ ES GC SI HG CL NG RTY YM"}
TFS=${TFS:-"4h 2h 1h 15m 5m 2m"}

run_one() {
    inst=$1; tf=$2
    log="$LOGDIR/${inst}_${tf}.log"
    # already finished (resumable): skip
    if grep -q "^__OK__" "$log" 2>/dev/null; then
        echo "SKIP $inst $tf (already complete)"
        return 0
    fi
    echo "START $inst $tf $(date +%H:%M:%S)"
    python3 optimize/optimizer.py "$tf" \
        --auto-trials \
        --study-prefix "$PREFIX" \
        --instrument "$inst" \
        --ind-1min \
        --no-warm-start \
        > "$log" 2>&1
    rc=$?
    if [ $rc -eq 0 ]; then
        echo "__OK__" >> "$log"
        # surface the champion line for the per-champion ping
        best=$(grep -E "P/L\(med\)" "$log" | tail -1)
        echo "CHAMPION $inst $tf $(date +%H:%M:%S) | $best"
    else
        echo "FAILED $inst $tf rc=$rc $(date +%H:%M:%S) -- see $log"
    fi
}
export -f run_one
export LOGDIR PREFIX

# build the 54-job list
JOBS="$LOGDIR/jobs.txt"
: > "$JOBS"
for i in $INSTS; do for t in $TFS; do echo "$i $t" >> "$JOBS"; done; done
TOTAL=$(wc -l < "$JOBS")

echo "==================================================================="
echo " CAP RE-OPTIMIZE — prefix=$PREFIX  cold-start  --ind-1min"
echo " searching: en_cap_bars + cap_1min + en_cap_eod  (none|bars|eod|both)"
echo " $TOTAL campaigns, $WORKERS parallel workers, 1 core each"
echo " started $(date '+%F %H:%M:%S')"
echo "==================================================================="

xargs -a "$JOBS" -P "$WORKERS" -n 2 bash -c 'run_one "$@"' _

echo "==================================================================="
echo "ALL CAP CAMPAIGNS COMPLETE $(date '+%F %H:%M:%S')"
echo "==================================================================="
