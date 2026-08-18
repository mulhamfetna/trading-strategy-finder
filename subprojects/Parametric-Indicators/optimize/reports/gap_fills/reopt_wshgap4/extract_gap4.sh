#!/bin/bash
# Extract the wshgap4 pareto fronts into champion files. Runs from ~/Mulham/code (branch dev), which
# HAS the precision fix: params are now persisted EXACTLY (`_exact`, no rounding at all — cadc18e).
# July's worktree still used round(x, 4), which is why those champions came out at 4 decimal places.
# ⚠️ The server must be `git pull`ed to today's dev BEFORE this runs, or extraction re-rounds them.
set -u
source /home/dev/Mulham/.venv/bin/activate
cd /home/dev/Mulham/code/subprojects/Parametric-Indicators
export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
export WSI_STUDY_PREFIX=wshgap4
R=optimize/results
for INST in NQ GC; do
  export WSI_INSTRUMENT=$INST
  echo "########## $INST: pareto export ##########"
  python3 -u optimize/report_wsi.py 2>&1 | grep -E "complete|wrote|front" | tail -8
  suf=""; [ "$INST" != "NQ" ] && suf="_$INST"
  echo "########## $INST: build champions -> wshgap4_champions_full${suf}.json ##########"
  python3 -u optimize/build_champions_from_pareto.py "$R/wshgap4_champions_full${suf}.json" 2>&1 | tail -8
done
echo "##### EXTRACT COMPLETE #####"
