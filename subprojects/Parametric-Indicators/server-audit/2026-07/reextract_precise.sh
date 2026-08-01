#!/bin/bash
# Re-extract BOTH champion sets with the precision fix (significant digits, not decimal places).
# Writes to fresh files: cap1p_* and eod1p_*  ("p" = precise). Nothing deployed is overwritten.
set -u
WSI=$HOME/Mulham/wsg-i
cd "$WSI/Parametric-Indicators" || exit 1
source $HOME/Mulham/.venv/bin/activate
export WSH_DATA_BASE="$WSI" WSG_DATA_ROOT="$WSI/data" PYTHONPATH=.
set -a; . "$WSI/pg.env"; set +a
RES="$WSI/Parametric-Indicators/optimize/results"
INSTS="NQ ES GC SI HG CL NG RTY YM"

for SPEC in "cap1:cap1p:0" "eod1:eod1p:1"; do
  SRC="${SPEC%%:*}"; REST="${SPEC#*:}"; DST="${REST%%:*}"; FEOD="${REST##*:}"
  echo; echo "══════════ re-extracting ${SRC} -> ${DST}  (force_eod=${FEOD}) ══════════"
  for I in $INSTS; do
    SUF=""; [ "$I" != "NQ" ] && SUF="_$I"
    WSI_FORCE_EOD=$FEOD WSI_STUDY_PREFIX=$SRC WSI_INSTRUMENT=$I \
      python optimize/report_wsi.py 4h 2h 1h 15m 5m 2m > /dev/null 2>&1
    WSI_INSTRUMENT=$I \
      python optimize/build_champions_from_pareto.py "$RES/${DST}_champions_full${SUF}.json" \
        4h 2h 1h 15m 5m 2m > /dev/null 2>&1
    echo "  $I done"
  done
done
echo; echo "REEXTRACT_DONE"
