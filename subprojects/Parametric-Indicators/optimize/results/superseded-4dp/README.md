# Superseded champion files — persisted at 4 DECIMAL PLACES (do not load)

These were written before the precision fix. Stop/target params were stored with `round(x, 4)` — four
DECIMAL places, not significant digits. Our markets span four orders of magnitude (the Dow trades near
$44,000, natural gas near $3.57), so four decimals leaves a natural-gas stop of **0.0008** with a single
significant digit.

On NG 5m that 1.1% distortion moved the champion's P/L by **$39,793 and flipped its sign**
(+$38,079 measured → −$1,714 as written), and it got **10 of the 54** head-to-head verdicts wrong.

Kept for provenance only. The live sets are `best_*` (deployed), `cap1p_*` (incumbents) and `eod1p_*`
(forced end-of-day) — all re-extracted with significant-digit precision.

`optimize/test_champion_sets.py` fails the build if any champion set is pointed back at these.
