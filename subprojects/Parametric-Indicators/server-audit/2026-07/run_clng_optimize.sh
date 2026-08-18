#!/bin/bash
cd ~/Mulham/wsg-i/Parametric-Indicators
source ~/Mulham/.venv/bin/activate 2>/dev/null
export WSH_DATA_BASE=~/Mulham/wsg-i; export WSG_DATA_ROOT=~/Mulham/wsg-i/data
[ -f ~/Mulham/wsg-i/pg.env ] && set -a && . ~/Mulham/wsg-i/pg.env && set +a
for inst in CL NG; do
  pfx=$(echo $inst | tr A-Z a-z)1
  for tf in 4h 2h 1h 15m 5m 2m; do
    echo "==================== $inst $tf START $(date +%H:%M:%S) ===================="
    python3 optimize/optimizer.py $tf --auto-trials --study-prefix $pfx --instrument $inst --ind-1min 2>&1
    echo "==================== $inst $tf DONE $(date +%H:%M:%S) ===================="
  done
done
echo "ALL CL+NG TIMEFRAMES COMPLETE"
