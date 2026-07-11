#!/bin/bash
# Extract the 54 cap1 champions: studies -> pareto CSVs -> champion JSONs.
#
# SAFETY: the deployed champion files (wsh4_champions_full_*.json) are VERIFIED and are what the dashboard
# serves as defaults. The cap1 champions are NOT verified yet -- twice now the optimizer has lied (HG 2m,
# NG 15m, the latter actually LOSING money). So we:
#   1. back the deployed files up first,
#   2. write cap1 champions to a SEPARATE dir,
#   3. only swap them into place for the UI-verify pass,
#   4. keep, per-slot, whichever champion actually verifies better.
set -u
WSI=~/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source ~/Mulham/.venv/bin/activate 2>/dev/null
export WSH_DATA_BASE="$WSI"; export WSG_DATA_ROOT="$WSI/data"
set -a; . "$WSI/pg.env"; set +a

RES="$WSI/Parametric-Indicators/optimize/results"
BAK="$WSI/deployed_champions_backup"
CAP="$WSI/cap1_champions"
mkdir -p "$BAK" "$CAP"

echo "=== backing up the DEPLOYED (verified) champions ==="
for f in "$RES"/wsh4_champions_full*.json; do
    [ -f "$f" ] && cp -n "$f" "$BAK/$(basename "$f")" && echo "  backed up $(basename "$f")"
done
echo

INSTS="NQ ES GC SI HG CL NG RTY YM"
for I in $INSTS; do
    echo "═══════════ $I ═══════════"
    # NQ studies are unsuffixed (cap1_<tf>); the rest are cap1_<tf>_<INST>.
    WSI_STUDY_PREFIX=cap1 WSI_INSTRUMENT=$I \
        python3 optimize/report_wsi.py 4h 2h 1h 15m 5m 2m 2>&1 | grep -E "^  [0-9a-z]+:|wrote"
    WSI_INSTRUMENT=$I \
        python3 optimize/build_champions_from_pareto.py "$CAP/cap1_champions_$I.json" 4h 2h 1h 15m 5m 2m 2>&1 | grep -E "median|wrote"
    echo
done

echo "=== cap1 champion files written ==="
ls -la "$CAP"/
echo "EXTRACT_DONE"
