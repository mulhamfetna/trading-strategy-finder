#!/bin/bash
# Extract the 54 eod1 (forced end-of-day, cold-start) champions: studies -> pareto CSVs -> champion JSONs.
# Writes to its OWN dir. The deployed champions are NOT touched -- these are UNVERIFIED until the causal
# engine says otherwise (the fast engine has lied 5 times: HG 2m, NG 15m x2, NG 2m).
set -u
WSI=~/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source ~/Mulham/.venv/bin/activate 2>/dev/null
export WSH_DATA_BASE="$WSI"; export WSG_DATA_ROOT="$WSI/data"
set -a; . "$WSI/pg.env"; set +a

OUT="$WSI/eod1_champions"
mkdir -p "$OUT"

INSTS="NQ ES GC SI HG CL NG RTY YM"
for I in $INSTS; do
    echo "═══════════ $I ═══════════"
    WSI_FORCE_EOD=1 WSI_STUDY_PREFIX=eod1 WSI_INSTRUMENT=$I \
        python3 optimize/report_wsi.py 4h 2h 1h 15m 5m 2m 2>&1 | grep -E "^  [0-9a-z]+:|wrote"
    WSI_INSTRUMENT=$I \
        python3 optimize/build_champions_from_pareto.py "$OUT/eod1_champions_$I.json" 4h 2h 1h 15m 5m 2m 2>&1 | grep -E "median|wrote"
    echo
done
echo "=== eod1 champion files ==="
ls -la "$OUT"/
echo "EXTRACT_DONE"
