---
name: generate_stage1_synthetic
description: subprojects/signals/tests/test_generate_stage1_synthetic.py — branch-coverage tests for every clause of the Stage 1 rule
type: file
---

# test_generate_stage1_synthetic.py

Tests each branch of the Stage 1 rule using tiny hand-crafted CSVs. No real data dependency; runs in <1 second.

## Test inventory

| # | Test | Rule branch covered |
|---|---|---|
| 1 | `test_candle_with_no_box_date_row_emits_single_hold` | candle's `box_date` is absent from box CSV → 1 hold row, NaN box columns |
| 2 | `test_candle_with_all_nan_level_pairs_emits_single_hold` | box row exists but every level pair is NaN → 1 hold row |
| 3 | `test_candle_entirely_above_box_is_hold` | range overlap fails (`low > box_upper`) → hold |
| 4 | `test_candle_entirely_below_box_is_hold` | range overlap fails (`high < box_lower`) → hold |
| 5 | `test_green_candle_touched_close_above_upper_is_long` | the LONG branch |
| 6 | `test_red_candle_touched_close_below_lower_is_short` | the SHORT branch |
| 7 | `test_touched_but_close_inside_box_is_hold` | touched, close inside box → hold (mismatch branch) |
| 8 | `test_doji_touched_close_above_is_hold` | doji is always hold even when other conditions would have fired |
| 9 | `test_close_exactly_on_upper_is_hold_strict` | close vs edge is strict — equality is hold |
| 10 | `test_touch_inclusive_at_lower_edge` | touch is inclusive — `high == box_lower` counts |
| 11 | `test_two_active_level_pairs_emit_two_rows` | row fan-out — one row per active level pair, evaluated independently |
| 12 | `test_session_mapping_hour_ge_18_uses_next_day` | NQ session-boundary mapping (`hour >= 18 → next day`) |

## Helpers

- `_write_candles(tmp_path, rows)` — writes a minimal candles CSV with the columns `load_data()` expects.
- `_write_boxes(tmp_path, rows)` — writes a box CSV with the full 52-column schema of `NQ_full_data.csv` so the loader can read it. Missing cells stay NaN.

## What this file does NOT cover

- Large-scale row counts and signal proportions — those are pinned by [[generate_stage1_real_data]].
- Output ordering across many candles — also pinned by the real-data test.
