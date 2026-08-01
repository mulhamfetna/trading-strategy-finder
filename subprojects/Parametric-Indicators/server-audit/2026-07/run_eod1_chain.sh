#!/bin/bash
# Wait for the metrics pass, then run the rest of the bundle chain back to back, so there is no idle gap.
# Each stage REFUSES to proceed on bad input; the chain stops at the first one that does.
set -u
WSI=$HOME/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source $HOME/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" PYTHONPATH=.
export WSH_CHAMP_SET=eod1

step () { echo; echo "═══ $* ═══"; echo "    started $(date +%H:%M:%S)"; }

# 0. wait for the metrics pass to finish (it is already running under its own session)
step "waiting for the causal metrics pass"
while pgrep -f "python .*eod1_[v]erify" > /dev/null; do sleep 10; done
grep -q VERIFY_DONE "$WSI/logs/eod1_verify.log" || { echo "METRICS DID NOT COMPLETE — stopping"; exit 1; }
echo "    metrics done"

# 1. snapshots + presets (browser, full window only — the dashboard's boxes are window-independent)
step "browser sweep: dashboard snapshot + exact preset, 54 slots"
python "$WSI/eod1_snap.py" || { echo "SNAP FAILED"; exit 1; }

# 2. merge measured numbers + captured presets (refuses on any fabricated/missing number)
step "assembling playbook metrics"
python "$WSI/eod1_playbook_metrics.py" || { echo "METRICS MERGE REFUSED — stopping"; exit 1; }

# 3. the 54 PDFs
step "building 54 playbook PDFs"
python build_playbooks.py "$WSI/playbook_metrics_eod1.json" || { echo "PDF BUILD FAILED"; exit 1; }
ls "$WSI/playbooks_eod1"/*.pdf | wc -l | xargs echo "    PDFs:"

# 4. the champion set for the standalone backtester
step "generating the shareable champion set"
python "$WSI/eod1_gen_bundle.py" || { echo "BUNDLE GEN REFUSED — stopping"; exit 1; }

# 5. the backtester must reproduce every headline AND every 2026 figure, to the dollar
step "verifying the bundle reproduces all 54 (headline + 2026)"
python "$WSI/eod1_bundle_verify.py" || { echo "BUNDLE VERIFY FAILED"; exit 1; }

# 6. package
step "packaging"
python "$WSI/eod1_package.py" || { echo "PACKAGE FAILED"; exit 1; }

echo; echo "CHAIN_COMPLETE $(date +%H:%M:%S)"
