---
name: box_strategy
description: src/strategy/box_strategy.py — owns the 4h direction decision, big-candle override, direction-flip handling, and the trade lifecycle
type: file
---

# box_strategy.py

Implements the **entry direction system** and orchestrates the **trade lifecycle** defined in [[strategy-master]] §2 and §4.

## Responsibilities

- **4h direction decision.** At each 4h candle close, applies the box-interaction truth table from [[strategy-master]] §2.1 (and [[truth_table]]) to produce `long` / `short` / `hold`.
- **Box selection.** Calls [[box_lookup]] with the just-closed price + current direction bias to get the active unburned box. Handles nested-box edge case per [[strategy-master]] §2.2.
- **First-candle warm-up.** Suppresses any action on the very first 4h candle of the dataset. See [[strategy-master]] §2.3.
- **Big-candle override.** When `|close − open| ≥ big_candle_threshold` and the toggle is on, reverses direction and fires immediate 4-contract entry, bypassing the truth table. See [[strategy-master]] §2.4.
- **Trade lifecycle.** Opens trades, hands off to [[scaling_strategy]] for ladder + exits, processes direction-flip at each subsequent 4h boundary per [[strategy-master]] §4.3, and emits the trade log.
- **HOLD handling.** A `hold` signal blocks new entries but does not close existing trades. See [[strategy-master]] §4.4.

## What it does **not** own

- Ladder fills, SL/TP exit lines, anchor mode — those live in [[scaling_strategy]].
- Box loading and selection rules — those live in [[box_lookup]].
- Sub-bar 1-min exit search — that lives in [[scaling_strategy]] (or a dedicated sub-bar module).

## Key parameters (input)

| Parameter | Source | Used for |
|---|---|---|
| `big_candle_threshold` | user (default 400) | threshold for big-candle override |
| `big_candle_override` | user (default on) | enable/disable big-candle rule |
| `direction_flip_mode` | user (default `flip`) | flip / ignore / wait-for-zero |
| `nested_box_edge` | user (default `hold`) | nested-box tiebreak rule |
| `partial_ladder_at_4h_end` | user (default `continue`) | what to do if ladder unfinished |
| `no_exit_at_4h_end` | user (default `carry_open`) | what to do if no SL/TP at 4h boundary |

## Key outputs

A trade log with one row per trade: entry_idx, exit_idx, direction, entry_signal_price, avg_entry_price, exit_close, exit_price, exit_time, contracts, profit_points, profit_dollars, exit_reason, legs, box_signal.

## Locked tests

[[blueprint_examples]] (`tests/test_blueprint_examples.py`) pins reference January-2025 trades. Any change to direction-rule logic, trade-lifecycle behaviour, or trail removal must regenerate those reference numbers.
