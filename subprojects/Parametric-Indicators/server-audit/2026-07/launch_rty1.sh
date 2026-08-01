#!/bin/bash
cd ~/Mulham/wsg-i/Parametric-Indicators
source /home/dev/Mulham/.venv/bin/activate
source ~/Mulham/wsg-i/pg.env
export WSH_DATA_BASE=$HOME/Mulham/wsg-i WSG_DATA_ROOT=$HOME/Mulham/wsg-i/data
mkdir -p ~/Mulham/wsg-i/logs
for tf in 2m 5m 15m 1h 2h 4h; do
  for w in 1 2 3 4; do
    setsid python3 optimize/optimizer.py $tf --trials 1425 --folds 5 --study-prefix rty1 --ind-1min --instrument RTY \
      > ~/Mulham/wsg-i/logs/rty1_${tf}_w${w}.log 2>&1 < /dev/null &
  done
done
echo "launched 24 GC workers (6 TF x 4 workers, 1425 trials each = 5700/TF)"
