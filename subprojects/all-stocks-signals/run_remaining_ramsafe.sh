#!/usr/bin/env bash
# WS-AS.5 — RAM-safe local run of the 5 remaining instruments on a box with ~5.3GB free.
# Peak RAM budget: one heavy instrument (ES ~3.5GB) may run only alongside LIGHT ones (~1GB).
# Schedule:
#   Phase 1: ES (heavy, solo-ish) || QQQ-RTH then SQQQ-RTH (light lane)   -> peak ~4.5GB
#   Phase 2 (after ES frees RAM): QQQ-ETH || SQQQ-ETH (medium ~2GB each)  -> peak ~4GB
set -u
cd "$(dirname "$0")/../.."
GEN="python3 subprojects/all-stocks-signals/generate_signals.py --instruments"
LOG=/tmp/as_run
mkdir -p "$LOG"

echo "[$(date +%H:%M:%S)] Phase 1: ES (heavy) + RTH light lane"
# light lane: the two small RTH ETFs, sequential, in background
( $GEN QQQ-RTH  > "$LOG/QQQ-RTH.log" 2>&1
  $GEN SQQQ-RTH > "$LOG/SQQQ-RTH.log" 2>&1 ) &
LIGHT=$!
# heavy: ES in the foreground of this script
$GEN ES > "$LOG/ES.log" 2>&1
echo "[$(date +%H:%M:%S)] ES done; waiting for RTH lane"
wait $LIGHT
echo "[$(date +%H:%M:%S)] Phase 1 complete"

echo "[$(date +%H:%M:%S)] Phase 2: ETH pair in parallel"
$GEN QQQ-ETH  > "$LOG/QQQ-ETH.log" 2>&1 &
P1=$!
$GEN SQQQ-ETH > "$LOG/SQQQ-ETH.log" 2>&1 &
P2=$!
wait $P1 $P2
echo "[$(date +%H:%M:%S)] Phase 2 complete — all 5 instruments generated"
echo "tails:"
for t in ES QQQ-RTH SQQQ-RTH QQQ-ETH SQQQ-ETH; do
  echo "--- $t ---"; tail -2 "$LOG/$t.log"
done
