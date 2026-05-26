---
name: stage1_1_output_schema
description: Column-by-column semantics of reverse_signals_{preset}.csv
type: reference
---

# Output schema — `reverse_signals_{preset}.csv`

21 columns in fixed order. See [[signals-stage1_1-master]] §3 for the high-level spec; this card is the per-column quick reference.

## Columns

| # | Name | Type | Notes |
|---|---|---|---|
| 1  | `first_datetime`   | ISO-8601 string | anchor candle datetime, e.g. `2025-01-01T22:00:00` |
| 2  | `first_open`       | float | anchor candle open |
| 3  | `first_high`       | float | anchor candle high |
| 4  | `first_low`        | float | anchor candle low  |
| 5  | `first_close`      | float | anchor candle close — the reference price for `tp`/`sl` |
| 6  | `first_signal`     | enum  | `long` or `short` — the anchor's candle-level state |
| 7  | `first_box_id`     | string | semicolon-joined sorted `box_id`s from anchor candle's Stage 1 rows matching `first_signal` (see below) |
| 8  | `first_box_type`   | string | first-4-chars of each `;`-component of `first_box_id`, same order (see below) |
| 9  | `last_datetime`    | ISO-8601 string | reverse candle datetime |
| 10 | `last_open`        | float | reverse candle open |
| 11 | `last_high`        | float | reverse candle high |
| 12 | `last_low`         | float | reverse candle low |
| 13 | `last_close`       | float | reverse candle close |
| 14 | `last_signal`      | enum  | `long` or `short` — may match or oppose `first_signal` (4 pair classes) |
| 15 | `last_box_id`      | string | semicolon-joined sorted `box_id`s from reverse candle's Stage 1 rows matching `last_signal` (see below) |
| 16 | `last_box_type`    | string | first-4-chars of each `;`-component of `last_box_id`, same order (see below) |
| 17 | `window_high`      | float | `max(high)` across all candles in the window inclusive |
| 18 | `window_low`       | float | `min(low)` across all candles in the window inclusive  |
| 19 | `tp`               | float ≥ 0 | green anchor: `window_high − first_close`; red anchor: `first_close − window_low` |
| 20 | `sl`               | float ≥ 0 | green anchor: `first_close − window_low`;  red anchor: `window_high − first_close` |
| 21 | `holds_between`    | int ≥ 0   | hold candles strictly between anchor and reverse (excludes endpoints) |

## `first_signal` / `last_signal` enum

| Value | Meaning |
|---|---|
| `long`  | candle-level state was `long`  at this endpoint |
| `short` | candle-level state was `short` at this endpoint |

`first_signal` and `last_signal` are always opposites — guaranteed by [[reverse_signal_rule]].

## `first_box_id` / `last_box_id` format

For each endpoint, we pull all Stage 1 rows on that candle whose `signal` matches the candle-level state (so for an anchor in state `long`, only the candle's `signal == 'long'` Stage 1 rows). We then take the `box_id` of each of those rows, sort the set alphabetically, and join with `;`.

Examples (from `next_signals_full.csv`):

| Row | Column | Value |
|---|---|---|
| 0 | `first_box_id` | `M-IH_2025-01-02` |
| 0 | `last_box_id` | `M-IH_2025-01-02;W-RL_2025-01-02` |
| 369 (last) | `first_box_id` | `W-IL_2026-05-19` |
| 369 (last) | `last_box_id` | `M-RH_2026-05-19;W-IL_2026-05-19;W-RL_2026-05-19` |

### Rules

- **Always non-empty.** Every emitted window has anchor and reverse states in `{long, short}`; the Stage 1 color rule guarantees at least one row of that state exists for each endpoint candle.
- **Hold-signal rows are excluded.** A candle that triggered long on `W-RH` and hold on `M-IL` records only `W-RH` in `first_box_id`.
- **Sorted alphabetically.** `M-IH_…;W-RL_…` is the only valid order, never `W-RL_…;M-IH_…`.
- **De-duplicated.** Each `box_id` appears once even if Stage 1 emits it twice for some reason.
- **`;` is the delimiter.** Labels with spaces are already underscore-replaced upstream in Stage 1 (e.g. `W-TH sub` → `W-TH_sub`), so there is no internal punctuation collision.

## `first_box_type` / `last_box_type` format

For each `;`-separated component of the parent `*_box_id`, take the **first 4 characters** and re-join with `;` in the same order. This is a literal slice — no parsing, no deduplication.

Examples (from `next_signals_full.csv`):

| Parent `*_box_id` | Derived `*_box_type` |
|---|---|
| `M-IH_2025-01-02` | `M-IH` |
| `M-IH_2025-01-02;W-RL_2025-01-02` | `M-IH;W-RL` |
| `M-RH_2026-05-19;W-IL_2026-05-19;W-RL_2026-05-19` | `M-RH;W-IL;W-RL` |

### Rules

- **Per-component slice.** `;` is the only delimiter; the slice is applied to each component independently.
- **No dedup.** If both `M-TH_…` and `M-TH_sub_…` fire on the same candle, both components keep their slot — the result is `M-TH;M-TH`, a real value that appears in the dataset. This is intentional: the `_sub` label-prefix collision is silently absorbed by the literal first-4-chars rule.
- **Order preserved.** The N-th component of `*_box_type` corresponds exactly to the N-th component of `*_box_id`.
- **Always non-empty** when the parent is non-empty (guaranteed for every emitted window — see above).

## `tp` and `sl` are direction-aware

The formula is keyed to the **anchor candle's color** (`first_close` vs `first_open`):

### Green anchor (`first_close > first_open` — long state)

| Quantity | Formula | Interpretation |
|---|---|---|
| `tp` | `window_high − first_close` | maximum favorable excursion (price moved up from the anchor close) |
| `sl` | `first_close − window_low`  | maximum adverse excursion (price moved down from the anchor close) |

### Red anchor (`first_close < first_open` — short state)

| Quantity | Formula | Interpretation |
|---|---|---|
| `tp` | `first_close − window_low`  | maximum favorable excursion (price moved down from the anchor close) |
| `sl` | `window_high − first_close` | maximum adverse excursion (price moved up from the anchor close) |

### Properties

- Both quantities are non-negative by construction:
  - green: `window_high ≥ first_high ≥ first_close > first_open ≥ first_low ≥ window_low` ⇒ both formulas yield ≥ 0.
  - red:   `window_high ≥ first_high ≥ first_open > first_close ≥ first_low ≥ window_low` ⇒ both formulas yield ≥ 0.
- A doji anchor (`first_open == first_close`) cannot occur — Stage 1's color rule guarantees a doji candle is always `hold` and therefore never an anchor.

## Row counts (preset `full` locked)

| Preset | Total | long→long | long→short | short→long | short→short |
|---|---|---|---|---|---|
| `full` | 828 | 258 | 186 | 186 | 198 |
| `2025` | 567 | 178 | 127 | 126 | 136 |
| `2026` | 260 |  80 |  59 |  59 |  62 |

The `full` figures are regression-locked in [[generate_stage2_real_data]]. The `long→short` and `short→long` totals (186 each) **exactly match** `stage1_0_reverse_signals`.

## Ordering guarantee

Rows are sorted by `first_datetime` ASC. Stage 1.1 has no discard branches, so **every** adjacent pair shares endpoints: `df.last_datetime.iloc[i] == df.first_datetime.iloc[i+1]` for all `i ∈ [0, len-2]`.

## Direction-split files

`by_direction/long_to_short_{preset}.csv` is `df[df.first_signal == 'long']` from the unified file. `by_direction/short_to_long_{preset}.csv` is the symmetric filter. Same schema, same column order, no row-count loss.
