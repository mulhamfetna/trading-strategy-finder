---
name: generate_stage1_real_data
description: subprojects/signals/tests/test_generate_stage1_real_data.py — regression lock against the full preset CSVs
type: file
---

# test_generate_stage1_real_data.py

Pins the Stage 1 output to specific numeric values computed from `data/full_data/NQ_4h.csv` + `data/full_data/NQ_full_data.csv`. Any drift means either the rule changed or the dataset did — both require deliberate regeneration.

The test module is `@pytest.mark.skipif`-guarded: if either CSV is missing (gitignored on fresh clones), every test in the file is skipped.

## Test inventory

| # | Test | What it pins |
|---|---|---|
| 1 | `test_total_row_count_locked` | `len(signals) == 20322` |
| 2 | `test_signal_distribution_locked` | `value_counts() == {hold: 19256, long: 559, short: 507}` |
| 3 | `test_first_long_signal_locked` | (`2025-01-01T18:00:00`, `M-IH_2025-01-02`, close `21322.25`) |
| 4 | `test_first_short_signal_locked` | (`2025-01-02T10:00:00`, `W-RL_2025-01-02`, close `21047.5`) |
| 5 | `test_output_schema_locked` | the 10-column order |
| 6 | `test_every_candle_emits_at_least_one_row` | per [[signals-master]] §3 "at least one row per candle" |

## Module-scoped fixture

`signals` runs `generate(_CANDLES, _BOXES)` once per module — all six tests share the same DataFrame. Run time: ~1 second.

## When this test fails

1. **Total count off** → either the dataset gained/lost candles, a new level-pair label was added in [[box_lookup]], or the rule was tightened/relaxed.
2. **Distribution off** → almost certainly a rule change; verify against [[truth_table]].
3. **First long/short triplet off** → the dataset start date moved, or `_LEVEL_PAIRS` reordering changed which box gets evaluated first for the same candle.
4. **Schema off** → the column-order constant `_OUT_COLS` in [[generate_stage1]] was edited.

In every case, re-validate the new numbers manually, then update the locks. Do NOT loosen the tests to make them pass.
