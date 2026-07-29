#!/bin/bash
set -u
source /home/dev/Mulham/.venv/bin/activate
cd /home/dev/Mulham/code/.worktrees/fundamental/subprojects/Parametric-Indicators
export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data
export WSI_STUDY_PREFIX=wshgap
R=optimize/results
for INST in NQ GC; do
  export WSI_INSTRUMENT=$INST
  echo "########## $INST: pareto export ##########"
  python3 -u optimize/report_wsi.py 2>&1 | grep -E "complete|wrote|front" | tail -8
  suf=""; [ "$INST" != "NQ" ] && suf="_$INST"
  echo "########## $INST: build champions -> wshgap_champions_full${suf}.json ##########"
  python3 -u optimize/build_champions_from_pareto.py "$R/wshgap_champions_full${suf}.json" 2>&1 | tail -8
done
echo "##### EXTRACT COMPLETE #####"
