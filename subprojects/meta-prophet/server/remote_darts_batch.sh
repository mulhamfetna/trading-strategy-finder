#!/usr/bin/env bash
# RUNS ON THE SERVER (rsynced into mp/). Trains the remaining Darts models on the GPU,
# one at a time, continuing past any failure so one broken model can't block the rest.
# 11_darts_nbeats_plain is already done; this covers the other five.
set -u
cd /home/dev/Mulham/meta-prophet/mp
export HSA_OVERRIDE_GFX_VERSION=10.3.0 CUDA_VISIBLE_DEVICES=0 MP_ACCELERATOR=gpu \
       OMP_NUM_THREADS=30 MKL_NUM_THREADS=30 PYTHONUNBUFFERED=1
LOG=/home/dev/Mulham/meta-prophet/logs
PY=/home/dev/Mulham/.venv/bin/python

MODELS=(09_darts_rnn_plain 13_darts_tft_plain 10_darts_rnn_regressors 12_darts_nbeats_regressors 14_darts_tft_regressors)

echo "=== DARTS BATCH START $(date -Is) ==="
for m in "${MODELS[@]}"; do
  echo "--- $m START $(date -Is) ---"
  if $PY "scripts/$m.py" > "$LOG/$m.log" 2>&1; then
    tail -6 "$LOG/$m.log" | grep -E "wrote|rmse|lift_vs_naive" || true
    echo "$m: OK"
  else
    rc=$?
    echo "$m: FAILED rc=$rc -> last lines:"
    grep -vE "litlogger|Tip:|Tensor Cores" "$LOG/$m.log" | tail -8
  fi
done
echo "=== DARTS BATCH DONE $(date -Is) ==="
