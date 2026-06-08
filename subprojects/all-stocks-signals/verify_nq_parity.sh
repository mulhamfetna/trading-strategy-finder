#!/usr/bin/env bash
# WS-AS.4 — full NQ byte-parity gate: diff every regenerated NQ output (7 TF × 3 presets ×
# 5 artifacts) against the committed NQ_SIGNALS_DELIVERY. Exit non-zero on any mismatch.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/subprojects/all-stocks-signals/output/NQ"
DEL="$ROOT/NQ_SIGNALS_DELIVERY"
fail=0; ok=0
for tf in 1m 2m 5m 15m 1h 2h 4h; do
  for p in full 2025 2026; do
    declare -A pair=(
      ["$OUT/$tf/signals_NQ_${tf}_${p}.csv"]="$DEL/1_all_signals/NQ_${tf}_${p}.csv"
      ["$OUT/$tf/no_holds/signals_NQ_${tf}_${p}_no_holds.csv"]="$DEL/2_holds_dropped/NQ_${tf}_${p}.csv"
      ["$OUT/$tf/reverse_signals_NQ_${tf}_${p}.csv"]="$DEL/3_reverse_signals/NQ_${tf}_${p}.csv"
      ["$OUT/$tf/by_direction/long_to_short_NQ_${tf}_${p}.csv"]="$DEL/4_reverse_by_direction/long_to_short/NQ_${tf}_${p}.csv"
      ["$OUT/$tf/by_direction/short_to_long_NQ_${tf}_${p}.csv"]="$DEL/4_reverse_by_direction/short_to_long/NQ_${tf}_${p}.csv"
    )
    for a in "${!pair[@]}"; do
      if diff -q "$a" "${pair[$a]}" >/dev/null 2>&1; then ok=$((ok+1)); else
        echo "DIFFERS: $a  vs  ${pair[$a]}"; fail=$((fail+1)); fi
    done
    unset pair
  done
done
echo "parity: $ok identical, $fail differ"
exit $((fail > 0 ? 1 : 0))
