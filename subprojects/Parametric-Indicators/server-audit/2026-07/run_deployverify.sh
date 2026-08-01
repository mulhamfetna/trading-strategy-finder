#!/bin/bash
set -u
WSI=$HOME/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source $HOME/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" PYTHONPATH=.
exec python "$WSI/verify_best_deploy.py"
