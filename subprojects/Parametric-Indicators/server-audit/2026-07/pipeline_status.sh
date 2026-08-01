#!/bin/bash
# One-line status of the whole precision-recovery pipeline. Emitted repeatedly by the watcher.
WSI=$HOME/Mulham/wsg-i
L=$WSI/logs

stage="?"; detail=""
if pgrep -f "reextract_[p]recise" >/dev/null; then
    stage="1/4 RE-EXTRACT"
    n=$(grep -c " done" "$L/reextract.log" 2>/dev/null || echo 0)
    detail="$n/18 market-passes"
elif pgrep -f "measure_[p]recise" >/dev/null; then
    stage="2/4 RE-MEASURE"
    n=$(grep -cE "^\[" "$L/precise_chain.log" 2>/dev/null || echo 0)
    eta=$(grep -E "^PROGRESS" "$L/precise_chain.log" 2>/dev/null | tail -1 | sed 's/.*ETA //')
    detail="$n/54 slots (3 candidates each) · ETA ${eta:-?}"
elif pgrep -f "decide_[p]recise" >/dev/null; then
    stage="3/4 HEAD-TO-HEAD"
    detail="deciding winners on 2026"
elif grep -q PRECISE_CHAIN_COMPLETE "$L/precise_chain.log" 2>/dev/null; then
    stage="4/4 COMPLETE"
    detail=$(grep -E "BEST-PER-SLOT|slots won" "$L/precise_chain.log" 2>/dev/null | tr '\n' ' ' | tr -s ' ')
elif pgrep -f "run_precise_[c]hain" >/dev/null; then
    stage="1/4 RE-EXTRACT"
    detail="waiting on extraction"
else
    stage="STOPPED"
    detail="no pipeline process alive — $(tail -1 "$L/precise_chain.log" 2>/dev/null | cut -c1-70)"
fi

err=$(grep -cE "ERROR|Traceback|FAILED" "$L/precise_chain.log" 2>/dev/null | head -1 || echo 0)
load=$(uptime | sed 's/.*load average: //' | cut -d, -f1)
echo "[$(date +%H:%M)] $stage · $detail · errors=$err · load=$load"
