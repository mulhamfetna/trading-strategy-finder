#!/bin/bash
# Full recovery chain after the precision fix: wait for re-extraction, re-measure all three candidates,
# re-decide, rebuild the deployed set. Each stage stops the chain if it fails.
set -u
WSI=$HOME/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source $HOME/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" PYTHONPATH=.

step () { echo; echo "═══ $* ═══  $(date +%H:%M:%S)"; }

step "waiting for re-extraction"
while pgrep -f "reextract_[p]recise" > /dev/null; do sleep 10; done
grep -q REEXTRACT_DONE "$WSI/logs/reextract.log" || { echo "RE-EXTRACTION DID NOT COMPLETE"; exit 1; }
echo "    done"

step "sanity: did the precision actually change the low-priced markets?"
python - <<'PYEOF'
import json, os
RES = "optimize/results"
print(f"    {'slot':9} {'OLD sl_soft (4-dp)':>20} {'NEW sl_soft (12-sig)':>24}")
for inst, tf in (("NG","5m"), ("HG","2m"), ("SI","5m"), ("NQ","4h")):
    suf = "" if inst == "NQ" else f"_{inst}"
    o = json.load(open(f"{RES}/eod1_champions_full{suf}.json"))[tf]["box"]["sl_soft"]
    n = json.load(open(f"{RES}/eod1p_champions_full{suf}.json"))[tf]["box"]["sl_soft"]
    print(f"    {inst+'_'+tf:9} {o!r:>20} {n!r:>24}")
PYEOF

step "re-measuring all 3 candidates x 54 slots (causal, both windows)"
python "$WSI/measure_precise.py" || { echo "MEASURE FAILED"; exit 1; }

step "re-running the head-to-head on corrected numbers"
python "$WSI/decide_precise.py" || { echo "DECIDE FAILED"; exit 1; }

echo; echo "PRECISE_CHAIN_COMPLETE $(date +%H:%M:%S)"
