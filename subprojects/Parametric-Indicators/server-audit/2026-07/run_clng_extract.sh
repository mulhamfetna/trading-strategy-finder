#!/bin/bash
cd ~/Mulham/wsg-i/Parametric-Indicators
source ~/Mulham/.venv/bin/activate 2>/dev/null
export WSH_DATA_BASE=~/Mulham/wsg-i; export WSG_DATA_ROOT=~/Mulham/wsg-i/data
[ -f ~/Mulham/wsg-i/pg.env ] && set -a && . ~/Mulham/wsg-i/pg.env && set +a
set -e
for pair in "cl1:CL" "ng1:NG"; do
  pfx="${pair%%:*}"; inst="${pair##*:}"
  echo "=========== $inst report_wsi (prefix $pfx) ==========="
  WSI_STUDY_PREFIX=$pfx WSI_INSTRUMENT=$inst python3 optimize/report_wsi.py 4h 2h 1h 15m 5m 2m 2>&1 | grep -viE "^\[I |^\[W " | tail -20
  echo "=========== $inst build_champions ==========="
  WSI_INSTRUMENT=$inst python3 optimize/build_champions_from_pareto.py optimize/results/wsh4_champions_full_${inst}.json 4h 2h 1h 15m 5m 2m 2>&1 | tail -20
done
echo "EXTRACT COMPLETE"
