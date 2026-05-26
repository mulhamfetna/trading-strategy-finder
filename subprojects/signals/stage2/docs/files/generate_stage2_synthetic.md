---
name: generate_stage2_synthetic
description: subprojects/signals/stage2/tests/test_generate_stage2_synthetic.py — branch-coverage tests for the Stage 2 rule
type: file
---

# test_generate_stage2_synthetic.py

Branch-coverage tests using hand-crafted Stage 1 DataFrames (no real data). Run time: <1 second.

## Test inventory

| # | Test | Rule branch covered |
|---|---|---|
| 1  | `test_empty_input_yields_empty_output` | empty stream → empty output, schema preserved |
| 2  | `test_only_holds_yields_empty_output` | all-holds stream → empty output |
| 3  | `test_single_long_never_reversed_yields_empty` | EOF with open anchor → drop silently (E2) |
| 4  | `test_immediate_long_to_short_zero_holds_between` | zero-hold window (E5) + green-anchor tp/sl formula |
| 5  | `test_long_two_holds_short_holds_between_is_two` | multi-hold window, `holds_between` counts correctly |
| 6  | `test_long_repeat_discards_first_anchor` | same-state repeat → discard (E3) |
| 7  | `test_long_hold_long_hold_short_anchor_is_second_long` | discard + then real reverse from new anchor |
| 8  | `test_long_short_long_emits_two_windows_with_shared_short` | adjacent-window endpoint sharing (Q4) |
| 9  | `test_green_anchor_tp_is_window_high_minus_close` | green anchor: `tp = window_high − first_close`, intermediate high spike |
| 10 | `test_green_anchor_sl_is_close_minus_window_low` | green anchor: `sl = first_close − window_low`, intermediate low dive |
| 11 | `test_red_anchor_tp_is_close_minus_window_low` | red anchor: `tp = first_close − window_low`, intermediate low dive |
| 12 | `test_red_anchor_sl_is_window_high_minus_close` | red anchor: `sl = window_high − first_close`, intermediate high spike |
| 13 | `test_nan_box_hold_rows_participate_in_window_extremes` | NaN-box hold candles count for window high/low (Q5) |
| 14 | `test_multi_row_anchor_candle_collapses_to_single_anchor` | per-(candle, level-pair) collapse + multi-box_id sort+join into `first_box_id` |
| 15 | `test_box_id_excludes_hold_rows_on_same_candle` | only same-state Stage 1 rows contribute to `first_box_id` / `last_box_id` |
| 16 | `test_leading_holds_are_skipped` | E1 |
| 17 | `test_output_schema_locked` | the 21 columns in fixed order |
| 18 | `test_box_type_strips_date_for_single_box` | single-box parent → 4-char type (date suffix stripped) |
| 19 | `test_box_type_preserves_order_and_count_in_multi_box` | multi-box parent → per-component first-4-chars, order and count preserved |
| 20 | `test_box_type_collapses_sub_labels_to_first_4_chars` | `_sub` label silently collapses (`M-TH_sub` → `M-TH`); duplicates not deduped |

## Helpers

- `_row(dt, o, h, l, c, signal, box, bu, bl)` — builds one Stage 1 row dict with default box values.
- `_stage1(rows)` — turns a list of row dicts into a DataFrame matching Stage 1's column order.

## What this file does NOT cover

- Real row counts and value extremes — those are pinned by [[generate_stage2_real_data]].
- CLI behaviour and direction-split file writing — those are integration tests pending if/when needed.
