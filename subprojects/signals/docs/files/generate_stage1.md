---
name: generate_stage1
description: subprojects/signals/generate_stage1.py — offline CLI that produces signals_{preset}.csv per the Stage 1 rule
type: file
---

# generate_stage1.py

Implements the per-(candle, box) labelling described in [[signals-master]] §2 and writes the output CSV described in [[signals-master]] §3.

## Responsibilities

- **Resolve preset paths.** Maps `--preset {full,2025,2026}` to the matching `(NQ_4h*, NQ_full_data*)` pair under `data/`. See `_resolve_box_paths`.
- **Load candles and boxes.** `load_data(...)` for the 4h CSV; raw `pd.read_csv(...)` + Date-normalisation for the box CSV.
- **Iterate candles, fan out rows.** For each candle, compute `box_date`, find the matching box row, walk every level pair in `_WEEKLY_LEVELS + _MONTHLY_LEVELS`, and apply the rule.
- **Sort and write.** Deterministic ordering, then `to_csv(..., index=False)`.

## What it does not own

- The actual rule branches — those are written inline in `_emit_rows`. There's no separate "rule engine" module; Stage 1 is small enough that one function holds the whole truth table.
- Box selection logic from the main engine — Stage 1 does NOT call `BoxLookup.signal()`. It only reuses the static constants and the date-mapping helper.
- Dataset preset definitions — that's the main project's dashboard concern. Stage 1 just hard-codes the three known presets.

## CLI

```bash
python3 subprojects/signals/generate_stage1.py --preset 2026
python3 subprojects/signals/generate_stage1.py --preset 2025
python3 subprojects/signals/generate_stage1.py --preset full
python3 subprojects/signals/generate_stage1.py --preset 2026 --out /custom/path.csv
```

Exit codes: `0` on success, `2` if either input CSV is missing.

## Data flow

```
NQ_4h_*.csv  ──(load_data)──> candles_df  ─┐
                                            ├─> _emit_rows ──> list[dict] ──> DataFrame ──> sort ──> .csv
NQ_full_data*.csv  ──(read_csv)──> box_df ─┘
```

`_emit_rows` is a generator — one yield per output row. The full pipeline is in-memory; on the full preset it produces ~20k rows, well below memory pressure.

## Reused project symbols

| Symbol | From | Purpose |
|---|---|---|
| `load_data` | `src/data/loader.py` | 4h CSV → DataFrame with canonical column names |
| `_WEEKLY_LEVELS`, `_MONTHLY_LEVELS` | `src/strategy/box_lookup.py` | the 16 level-pair definitions |
| `BoxLookup._candle_to_box_date` | `src/strategy/box_lookup.py` | NQ session-boundary date mapping |

The script does NOT import the main engine, the API layer, or any trading parameters.

## Locked counts (full preset, 2025-01-01 → 2026-05-19)

These are pinned by `test_total_row_count_locked` and `test_signal_distribution_locked` in [[generate_stage1_real_data]]:

| Metric | Value |
|---|---|
| Total rows | 20,322 |
| `hold` rows | 19,256 (94.8%) |
| `long` rows | 559 (2.8%) |
| `short` rows | 507 (2.5%) |
| Unique 4h candles | equal to row count of `NQ_4h.csv` |

The 2025 and 2026 preset counts (14,662 and 5,660 rows respectively) are not regression-locked because the underlying preset CSVs are derived from the full file and would re-derive on each regeneration.

## When locked values change

If the rule changes, if a new level-pair label is added to [[box_lookup]], or if the dataset is rebuilt, the locked counts in [[generate_stage1_real_data]] must be regenerated. Procedure:

1. Run `python3 subprojects/signals/generate_stage1.py --preset full`.
2. Update the locked `len(signals)` and the `value_counts` dict in [[generate_stage1_real_data]].
3. Refresh the "first long" / "first short" examples if those moved.
