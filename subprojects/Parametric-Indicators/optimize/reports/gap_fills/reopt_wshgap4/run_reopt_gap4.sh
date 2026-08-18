#!/bin/bash
# Issue #2 — honest-fill re-optimization, CORRECTED re-run (prefix wshgap2).
#
# What is different from the July `wshgap` run, which is retracted:
#   1. Warm start now seeds from the DEPLOYED set (best_*). The old run seeded from wsh4_*, retired
#      since 2026-07-14, so Optuna's "front >= seed" guarantee held against the wrong incumbent.
#   2. --train-window 2025 => the optimizer CANNOT see 2026, making a later window=2026 score a genuine
#      holdout. The old run trained on the whole series and then reported 2026 as "OOS".
#   3. Runs from ~/Mulham/code (branch dev), so deployed == committed. The old run used a worktree that
#      predated the champion-precision fix.
#   4. gap_fills is the default (True) since 2026-07-20 — no flag needed, honest fills are the model.
#
# INDICATOR SCOPE (--only-indicators, added on the relaunch). The first attempt let --auto-trials size the
# search over the whole 165-indicator registry: 471 dimensions, 47,100 recommended trials, ~20 HOURS for
# NQ 4h alone (~10 days for twelve studies). July's run searched only the ORIGINAL 18 — 59 dims, 5,900
# trials, 44 minutes — so the two were never comparable either. Restricting to the original 18 both makes
# the re-run tractable and matches the adopt gate's verdict (#14): the 143-indicator library is
# DEFAULT-OFF, so a champion re-optimization has no business selecting from it. Verified: every indicator
# in every deployed NQ champion is inside these 18.
set -u
ONLY_INDS="ema_trend,sma_trend,macd,vwap,keltner,obv,cci,rsi,stochastic,mfi,bollinger,adx,structure_trend,order_block,fvg,ifvg,breaker,cisd"
source /home/dev/Mulham/.venv/bin/activate
cd /home/dev/Mulham/code/subprojects/Parametric-Indicators

export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data

# The engine's P/L changed since the cache was written (#62 indicator acceleration, #75 cross-series
# wiring). A stale L1 cache would silently serve pre-change results.
rm -f /tmp/wsh_l1_cache/*.pkl 2>/dev/null

R=/home/dev/Mulham/gap4
mkdir -p "$R"
ST="$R/STATUS.txt"
: > "$ST"

echo "$(date +%H:%M:%S)  CAMPAIGN START  prefix=wshgap4 train-window=2025 only-inds=original18 (2026 held out)" | tee -a "$ST"
echo "$(date +%H:%M:%S)  engine commit: $(git -C /home/dev/Mulham/code log --oneline -1)" | tee -a "$ST"

for INST in NQ GC; do
  for TF in 4h 2h 1h 15m 5m 2m; do
    echo "$(date +%H:%M:%S)  START  $INST $TF" | tee -a "$ST"
    t0=$(date +%s)
    python3 -u optimize/optimizer.py "$TF" --instrument "$INST" --ind-1min --auto-trials \
        --train-window 2025 --study-prefix wshgap4 --only-indicators "$ONLY_INDS" > "$R/${INST}_${TF}.log" 2>&1
    rc=$?
    el=$(( ($(date +%s) - t0) / 60 ))
    # Prove which champion file actually seeded this study — the whole point of the re-run. If this line
    # is missing or says LEGACY, the run is not floored by the deployed champion and must not be trusted.
    seed=$(grep -m1 '\[warm-start\]' "$R/${INST}_${TF}.log" 2>/dev/null | sed 's/.*seeded from //')
    if [ $rc -eq 0 ]; then
      echo "$(date +%H:%M:%S)  DONE   $INST $TF  (${el}m, rc=0)  seed: ${seed:-NONE FOUND}" | tee -a "$ST"
    else
      echo "$(date +%H:%M:%S)  FAILED $INST $TF  (${el}m, rc=$rc) -- see ${INST}_${TF}.log" | tee -a "$ST"
    fi
  done
done
echo "$(date +%H:%M:%S)  ##### CAMPAIGN COMPLETE #####" | tee -a "$ST"
