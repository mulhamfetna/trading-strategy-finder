#!/bin/bash
source /home/dev/Mulham/.venv/bin/activate
source ~/Mulham/wsg-i/pg.env
export WSH_DATA_BASE=$HOME/Mulham/wsg-i WSG_DATA_ROOT=$HOME/Mulham/wsg-i/data
cd ~/Mulham/wsg-i/Parametric-Indicators
exec python3 server.py --port 8200
