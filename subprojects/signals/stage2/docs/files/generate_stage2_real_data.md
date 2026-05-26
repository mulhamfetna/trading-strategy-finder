---
name: generate_stage2_real_data
description: subprojects/signals/stage2/tests/test_generate_stage2_real_data.py — regression locks against signals_full.csv
type: file
---

# test_generate_stage2_real_data.py

Pins Stage 2 output to specific numeric values computed from `subprojects/signals/signals_full.csv`. Any drift means either the rule changed or the Stage 1 dataset did — both require deliberate regeneration.

The test module is `@pytest.mark.skipif`-guarded: if `signals_full.csv` is missing (gitignored on fresh clones), every test is skipped.

## Test inventory

| # | Test | What it pins |
|---|---|---|
| 1  | `test_total_window_count_locked` | `len(reverse_signals) == 372` |
| 2  | `test_direction_split_locked` | `first_signal.value_counts() == {long: 186, short: 186}` |
| 3  | `test_first_window_locked` | full first-row tuple (green/long anchor `2025-01-01T22:00:00` → short `2025-01-02T10:00:00`; first_box_id=`M-IH_2025-01-02`, first_box_type=`M-IH`, last_box_id=`M-IH_…;W-RL_…`, last_box_type=`M-IH;W-RL`; tp=101.0, sl=405.75, holds_between=2) |
| 4  | `test_last_window_locked` | full last-row tuple (red/short anchor `2026-05-15T14:00:00` → long `2026-05-18T14:00:00`; first_box_id=`M-TH_2026-05-15`, first_box_type=`M-TH`, last_box_id=`M-RH_…;W-IL_…`, last_box_type=`M-RH;W-IL`; tp=358.25, sl=313.75, holds_between=5) |
| 5  | `test_window_extremes_locked` | `window_high.max() == 29782.0`; `window_low.min() == 16480.0` |
| 6  | `test_tp_sl_maxima_locked` | `tp.max() == 628.0`; `sl.max() == 1038.75` |
| 7  | `test_per_direction_tp_sl_maxima_locked` | long anchors: tp.max=441.0, sl.max=1038.75; short anchors: tp.max=628.0, sl.max=1031.25 |
| 8  | `test_holds_between_locked` | `holds_between.max() == 22` |
| 9  | `test_output_schema_locked` | the 21-column order |
| 10 | `test_box_id_columns_always_populated` | every emitted row has non-empty `first_box_id`, `last_box_id`, `first_box_type`, `last_box_type` |
| 11 | `test_multi_box_id_row_counts_locked` | 80 rows have `;`-multi `first_box_id`, 95 rows have `;`-multi `last_box_id` |
| 12 | `test_box_type_matches_first_4_chars_per_component` | per-row exact-equality that `*_box_type` is the per-component first-4-chars slice of the parent `*_box_id` |
| 13 | `test_all_tp_sl_non_negative` | sign invariant — direction-aware formula yields ≥ 0 by construction |
| 14 | `test_direction_aware_tp_sl_formula` | per-row exact-equality check that tp/sl match the green/red branch of the formula |
| 15 | `test_first_last_signals_always_opposite` | endpoint invariant — every row has opposing endpoint states |
| 16 | `test_adjacent_windows_share_endpoint` | overlap invariant — at least one adjacent pair shares `last_datetime == next.first_datetime` |

## Module-scoped fixture

`reverse_signals` runs `generate(signals_df)` once per module. All 11 tests share the same DataFrame. Run time: ~1 second.

## When this test fails

1. **Total count off** → Stage 1 output changed (new candles, new boxes, or the Stage 1 rule was tightened/relaxed). Verify Stage 1 first.
2. **Distribution off** → likely a Stage 2 rule change; verify against [[reverse_signal_rule]].
3. **First or last window tuple off** → dataset start/end dates moved, or window-boundary discard behaviour changed.
4. **Schema off** → `_OUT_COLS` in [[generate_stage2]] was edited.
5. **Sign invariant fails** → the `tp`/`sl` formula lost its `abs(...)` wrapper.
6. **Opposite-signal invariant fails** → the rule scanner is emitting wrong-endpoint windows.

In every case, re-validate the new numbers manually, then update the locks. Do NOT loosen the tests to make them pass.
