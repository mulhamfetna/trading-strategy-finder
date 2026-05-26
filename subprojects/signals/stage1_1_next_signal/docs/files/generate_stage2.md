---
name: generate_stage2
description: subprojects/signals/stage1_1_next_signal/generate_stage2.py — Stage 1.1 next-signal generator
type: file
---

# generate_stage2.py

Reads a Stage 1 CSV, collapses per-(candle, level-pair) rows to candle-level state, scans the candle stream for reverse windows, and writes the unified output CSV + the four direction-pair-split CSVs. tp/sl are direction-aware, keyed to the anchor candle's color — see [[stage2_output_schema]] and [[next_signal_rule]].

## Public API

| Symbol | Purpose |
|---|---|
| `generate(signals_df: DataFrame) -> DataFrame` | core function: takes a Stage 1 DataFrame, returns the Stage 2 DataFrame |
| `generate_from_csv(signals_csv: str) -> DataFrame` | thin wrapper that reads the CSV first |
| `write_outputs(df, stage2_dir, preset) -> list[str]` | writes the unified file + the two `by_direction/` splits |
| `main()` | CLI entry: `--preset {full,2025,2026}`, `--signals-csv`, `--out-dir` |

## Internal pipeline

```
signals_df (Stage 1)
  │
  ▼
_collapse_to_candle_stream(signals_df)
  │  groupby('datetime'), agg first(OHLC) + state-collapse via _aggregate(group)
  │  also builds state_box_ids: sorted-and-joined box_ids of rows whose
  │  Stage 1 signal matches the derived candle_state ('' for hold candles)
  │  raises ValueError if any candle has both long and short rows
  ▼
candles (DataFrame: datetime, open, high, low, close, candle_state, state_box_ids)
  │
  ▼
_scan_windows(candles)
  │  linear scan per [[next_signal_rule]]
  │  yields one dict per closed window with first_box_id and last_box_id
  │  pulled directly from the anchor/reverse candle's state_box_ids
  ▼
DataFrame(rows, columns=_OUT_COLS)
  │  sorted by first_datetime ASC
  ▼
generate() return value
```

## Module constant `_OUT_COLS`

The 21 fixed column names in order. See [[stage2_output_schema]] for per-column semantics.

## Helper `_box_id_to_type(box_id_str)`

Pure-string transform: splits a `;`-separated `box_id` value into components, takes the first 4 characters of each, and re-joins with `;`. Used to derive `first_box_type` and `last_box_type` from their parent `*_box_id` columns. No regex, no parsing, no deduplication.

## CLI

```
python3 subprojects/signals/stage1_1_next_signal/generate_stage2.py --preset full
python3 subprojects/signals/stage1_1_next_signal/generate_stage2.py --preset 2025
python3 subprojects/signals/stage1_1_next_signal/generate_stage2.py --preset 2026
```

Outputs are written next to the script (`subprojects/signals/stage1_1_next_signal/`). The two split files land in `by_direction/`. Use `--out-dir` to redirect.

## Behaviour pinned by tests

- Branch coverage: [[generate_stage2_synthetic]] — 14 hand-built scenarios covering every clause of the rule.
- Real-data regression: [[generate_stage2_real_data]] — locks total counts, first/last window values, window extremes, tp/sl maxima, holds_between max, schema, sign invariants, and direction-pair invariants against `subprojects/signals/signals_full.csv`.
