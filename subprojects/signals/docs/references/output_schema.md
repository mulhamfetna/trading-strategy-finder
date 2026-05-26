---
name: output_schema
description: Column-by-column semantics of signals_{preset}.csv
type: reference
---

# Output schema — `signals_{preset}.csv`

Ten columns in fixed order. See [[signals-master]] §3 for the spec; this card is the per-column quick reference.

## Columns

| # | Name | Type | Always present? | Notes |
|---|---|---|---|---|
| 1 | `datetime` | ISO-8601 string | yes | from the 4h candle (e.g. `2025-01-01T18:00:00`) |
| 2 | `open` | float | yes | candle open price |
| 3 | `high` | float | yes | candle high price |
| 4 | `low` | float | yes | candle low price |
| 5 | `close` | float | yes | candle close price |
| 6 | `volume` | int | yes | candle volume; `0` if missing in source |
| 7 | `signal` | enum string | yes | one of `long` / `short` / `hold` (lowercase) |
| 8 | `box_id` | string | NaN for no-box-row | format `{label_with_underscores}_{box_date_iso}` |
| 9 | `box_upper` | float | NaN for no-box-row | upper edge of the level pair |
| 10 | `box_lower` | float | NaN for no-box-row | lower edge of the level pair |

## `signal` enum

| Value | Meaning |
|---|---|
| `long` | green candle + range overlaps box + close strictly above `box_upper` |
| `short` | red candle + range overlaps box + close strictly below `box_lower` |
| `hold` | every other case, including no-box-row, no-touch, doji, close-on-edge, and color/direction mismatch |

See [[truth_table]] for the full decision matrix.

## `box_id` format

`{label}_{box_date_iso}` where:

- `label` is one of the 16 active labels (`W-RH`, `W-IL`, `M-TH sub`, …); spaces in the label are replaced with underscores so a `box_id` never contains a literal space (e.g. `W-TH sub` → `W-TH_sub`).
- `box_date_iso` is the **box** date (the result of the NQ-session mapping), not the candle date. For a candle at `2025-01-04T18:00:00`, the mapped box date is `2025-01-05`, so the `box_id` reads `..._2025-01-05`.

Examples:

| Label | Box date | `box_id` |
|---|---|---|
| `W-RH` | 2025-01-15 | `W-RH_2025-01-15` |
| `M-TH sub` | 2025-03-01 | `M-TH_sub_2025-03-01` |
| `W-TL` | 2026-04-22 | `W-TL_2026-04-22` |

## Row counts

| Preset | Rows | Long | Short | Hold |
|---|---|---|---|---|
| `full` | 20,322 | 559 | 507 | 19,256 |
| `2025` | 14,662 | 382 | 348 | 13,932 |
| `2026` | 5,660 | 177 | 159 | 5,324 |

The `full` figures are regression-locked in [[generate_stage1_real_data]]. The per-year preset figures are derivatives and not locked.

## Ordering guarantee

Rows are sorted by:

1. `datetime` ASC
2. `box_upper` DESC (NaN last)
3. `box_lower` DESC (NaN last)

For a single 4h candle with K active level pairs, this means the K rows for that candle are clustered together and ordered widest-upper-edge first.
