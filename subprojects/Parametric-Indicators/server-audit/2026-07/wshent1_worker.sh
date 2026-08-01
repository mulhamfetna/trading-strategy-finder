#!/usr/bin/env bash
# Per-worker watchdog loop for the wshent1 (NQ 4h cold, objective=entries) L1 campaign.
# Loops the optimizer in fixed chunks against the SHARED Postgres study until TARGET completed
# trials is reached (idempotent), then exits. Each worker is fired setsid-detached by the launcher.
set -u
id="${1:-0}"
CODE=/home/dev/Mulham/wsg-i/Parametric-Indicators
WSI=/home/dev/Mulham/wsg-i
VENV=/home/dev/Mulham/.venv
PREFIX=wshent1; TF=4h; TARGET=50000
LOG="$WSI/logs/${PREFIX}_${TF}.log"
cd "$CODE" || exit 1
source "$VENV/bin/activate"
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" WSI_INSTRUMENT=NQ
set -a; . "$WSI/pg.env"; set +a
while :; do
  done=$(python3 optimize/trial_count.py "$TF" --prefix "$PREFIX" 2>/dev/null || echo 0)
  if [ "${done:-0}" -ge "$TARGET" ]; then
    echo "[w$id] reached ${done}/${TARGET} — stop $(date +%H:%M:%S)" >> "$LOG"; break
  fi
  python3 -u optimize/optimizer.py "$TF" --trials 300 --folds 5 --min-trades 5 \
    --ind-1min --no-warm-start --objective entries --study-prefix "$PREFIX" >> "$LOG" 2>&1 || true
done
