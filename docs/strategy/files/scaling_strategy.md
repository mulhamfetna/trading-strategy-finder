---
name: scaling_strategy
description: src/strategy/scaling_strategy.py — owns the 1-1-2 ladder, fixed SL/TP exit lines, and the anchor_mode toggle
type: file
---

# scaling_strategy.py

Implements the **position-sizing** and **exit-line** machinery defined in [[strategy-master]] §3, §4, and §5.

## Responsibilities

- **1-1-2 ladder fills.** Watches 1-min candles after leg 1 fills. When price moves ≥ `ladder_step_1` adverse, fires leg 2 (1 contract). When price moves ≥ `ladder_step_2` adverse, fires leg 3 (2 contracts). See [[strategy-master]] §3.1.
- **SL vs ladder validation tier.** Computes which tier (`deactivated` / `partial` / `full`) the current `sl_soft_points` puts the trade in. See [[strategy-master]] §3.2.
- **Fixed SL/TP exit lines.** Soft SL (2-min close confirmation), hard SL (1-min close confirmation), TP target. See [[strategy-master]] §4.
- **Anchor mode.** `base` (lines fixed for trade lifetime) or `average` (lines re-anchor on every leg fill). See [[strategy-master]] §5.

## What it does **not** own

- The 4h direction decision (lives in [[box_strategy]]).
- Box selection (lives in [[box_lookup]]).
- Trade-lifecycle orchestration (lives in [[box_strategy]]).

## Key parameters (input)

| Parameter | Source | Used for |
|---|---|---|
| `sl_soft_points` | user (dashboard) | soft SL line distance |
| `sl_hard_points` | user (dashboard) | hard SL line distance |
| `tp_target_points` | user (dashboard) | TP line distance |
| `ladder_step_1` | user (default 100) | leg 2 trigger |
| `ladder_step_2` | user (default 150) | leg 3 trigger |
| `anchor_mode` | user (default `base`) | line re-anchoring |

## Key outputs

Per closed trade: contracts, fill prices per leg, exit reason ∈ {`TAKE PROFIT`, `STOP LOSS (SOFT)`, `STOP LOSS (HARD)`, `DIRECTION_FLIP`, `OPEN`}, exit price.

## Implementation notes

- `_anchor(position)` selects between `position.base_level` (when `anchor_mode='base'`, the default) and `position.avg_price` (when `anchor_mode='average'`). This single helper drives every exit-line computation in both `_check_exits` (4h-only path) and `_check_exits_subbar` (dual-timeframe path).
- `_maybe_fill_legs` always uses `position.base_level` to compute the leg-2 and leg-3 trigger prices, regardless of `anchor_mode`. The ladder shape is spec-locked.
- Construction validates `anchor_mode ∈ {'base', 'average'}` and raises `MissingParameterError` for any other value.
- The previously-deprecated `tp_watch_threshold_points` and `tp_confirmation_timeframe_minutes` fields have been **removed** from the dataclass and the Pydantic schema in lockstep with the frontend (no shim layer required).
