#!/usr/bin/env bash
# l2v4 = L2 optimizer (cold start — L2 has no warm-seed) scored on the LATEST L1's residuals: the wsh6cold
# cap=448 verified champion (vs l2v3 which used the FROZEN production L1). --l1-champion reconstructs that L1
# (ind_1min forced True) and L2 trades its 569 dropped/vetoed signals. Watchdog/respawn to TARGET.
source /home/dev/Mulham/.venv/bin/activate
set -a; . /home/dev/Mulham/wsg-i/pg.env; set +a            # WSH_STORAGE_URL (secret) from pg.env only
export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd /home/dev/Mulham/wsg-i/Parametric-Indicators; mkdir -p /home/dev/Mulham/wsg-i/logs
TARGET=11400; PREFIX=l2v4; TF=4h; W=24
CHAMP=optimize/results/wsh6cold_4h_champion.json
run_worker () {
  local log=/home/dev/Mulham/wsg-i/logs/${PREFIX}_${TF}.log done rem per
  while :; do
    done=$(python3 optimize/trial_count.py "$TF" --prefix "$PREFIX" 2>/dev/null || echo 0)
    rem=$(( TARGET - done ))
    if [ "$rem" -le 0 ]; then echo "[watchdog] $done/$TARGET reached — stop" >> "$log"; break; fi
    per=$(( (rem + W - 1) / W ))
    python3 -u -m optimize.l2.optimize --tf "$TF" --prefix "$PREFIX" --trials "$per" \
            --l1-champion "$CHAMP" >> "$log" 2>&1 || true
  done
}
for i in $(seq 1 $W); do run_worker & done
wait
