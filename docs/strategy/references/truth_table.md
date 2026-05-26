---
name: truth_table
description: Quick-reference card for the box-interaction entry direction rule
type: reference
---

# Box-Interaction Truth Table

The full version with derivation lives in [[strategy-master]] §2.1. This is a single-page reference card.

## Inputs

- **`price_direction`** = colour of the just-closed 4h candle. Green = `up`. Red = `down`. Open == close = `doji`.
- **`box_position`** = where the active box sits relative to the candle. For `up` direction the box is above; for `down` it's below. Selected per [[box_lookup]].
- **`reach_state`** = how far the candle's price travelled relative to the box edges. **All checks are close-based unless specified.**
  - **`miss`** — candle's high (long-bias) or low (short-bias) didn't cross the **near** box edge.
  - **`bounce`** — high/low crossed the near edge but the **close** ended inside the box.
  - **`traverse`** — the **close** ended beyond the **far** box edge.

## Decision

| price_direction | box_position | reach_state | → entry |
|---|---|---|---|
| `up` | above | miss | **`short`** (reversal — exhaustion) |
| `up` | above | bounce | `hold` |
| `up` | above | traverse | **`long`** (continuation) |
| `down` | below | miss | **`long`** (reversal — exhaustion) |
| `down` | below | bounce | `hold` |
| `down` | below | traverse | **`short`** (continuation) |
| `doji` | — | — | `hold` |

## Special cases

- **First 4h candle of the dataset:** the system watches; no entry. From the 2nd 4h onward, the first 4h is the "just-closed" candle.
- **Big-candle override** (default ON): if `|close − open| ≥ big_candle_threshold` (default 400 pts), **bypass this table**. Reverse direction (green→short, red→long) and enter 4 contracts at base immediately.
- **Nested boxes** (price inside both a monthly + weekly box): see [[strategy-master]] §2.2 — default is `hold` until both burned.
- **`hold` signal** does not close existing trades. Existing trades only exit via SL / TP / direction-flip.

## Wired to

[[box_strategy]] applies this table. [[box_lookup]] supplies `box_position`.
