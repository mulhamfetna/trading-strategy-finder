#!/bin/bash
# Build the shareable bundle for the DEPLOYED (best-per-slot) champion set.
# Each stage refuses to proceed on bad input; the chain stops at the first that does.
set -u
WSI=$HOME/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source $HOME/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" PYTHONPATH=.
export WSH_CHAMP_SET=best

step () { echo; echo "═══ $* ═══  $(date +%H:%M:%S)"; }

step "1/6 browser sweep: dashboard snapshot + exact preset, 54 slots (set=best)"
python "$WSI/best_snap.py" || { echo "SNAP FAILED"; exit 1; }

step "2/6 merging measured numbers by winner (32 kept + 19 eod1 + 3 bolt-on)"
python "$WSI/best_playbook_metrics.py" || { echo "METRICS MERGE REFUSED"; exit 1; }

step "3/6 building 54 playbook PDFs"
python build_playbooks.py "$WSI/playbook_metrics_best.json" || { echo "PDF BUILD FAILED"; exit 1; }
echo "    PDFs: $(ls "$WSI/playbooks_best"/*.pdf 2>/dev/null | wc -l)"

step "4/6 generating the shareable champion set"
python "$WSI/best_gen_bundle.py" || { echo "BUNDLE GEN REFUSED"; exit 1; }

step "5/6 verifying the backtester reproduces all 54 (headline + 2026)"
python "$WSI/best_bundle_verify.py" || { echo "BUNDLE VERIFY FAILED"; exit 1; }

step "6/6 packaging"
python "$WSI/best_package.py" || { echo "PACKAGE FAILED"; exit 1; }

echo; echo "BEST_CHAIN_COMPLETE $(date +%H:%M:%S)"
