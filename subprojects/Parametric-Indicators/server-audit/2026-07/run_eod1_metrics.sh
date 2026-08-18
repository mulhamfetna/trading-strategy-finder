#!/bin/bash
# Detached runner for the eod1 causal metrics pass. A bare `nohup python ... &` inside an ssh command has
# died twice here when the ssh session closed; a script launched with setsid gets its own session and cannot
# be reached by the SIGHUP.
set -u
WSI=$HOME/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source $HOME/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" PYTHONPATH=.
exec python "$WSI/eod1_verify.py"
