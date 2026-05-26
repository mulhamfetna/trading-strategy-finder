---
name: dashboard_params
description: Flat reference of every dashboard parameter and toggle exposed by the strategy, with defaults and the spec section that defines each
type: reference
---

# Dashboard Parameter Reference

Flat list of every dashboard-exposed parameter and toggle. Each entry links to the section of [[strategy-master]] that defines its semantics.

## Price parameters (numeric, points)

| Parameter | Default | Spec | Validation |
|---|---|---|---|
| `sl_soft_points` | user-set | [[strategy-master]] §4 | Must satisfy `sl_soft < sl_hard` |
| `sl_hard_points` | user-set | [[strategy-master]] §4 | Must satisfy `sl_hard > sl_soft` |
| `tp_target_points` | user-set | [[strategy-master]] §4 | No interaction with ladder |
| `ladder_step_1` | 100 | [[strategy-master]] §3.1 | Leg 2 trigger distance |
| `ladder_step_2` | 150 | [[strategy-master]] §3.1 | Leg 3 trigger distance; must be > `ladder_step_1` |
| `big_candle_threshold` | 400 | [[strategy-master]] §2.4 | 4h `|close − open|` threshold |

### Ladder-tier warning (derived)

The dashboard computes the tier from `sl_soft_points` against `ladder_step_1` / `ladder_step_2` and shows:

| Soft SL distance | Tier | UI |
|---|---|---|
| `< ladder_step_1` | **Deactivated** | yellow box + "Ladder will not fire — soft SL fires before leg 2 trigger" |
| `[ladder_step_1, ladder_step_2)` | **Partial** | yellow box + "Only leg 2 can fire — leg 3 trigger is beyond soft SL" |
| `≥ ladder_step_2` | **Full** | green box + no note |

Warn-but-allow; the user can save any value.

## Behaviour toggles

| Toggle | Default | Values | Spec |
|---|---|---|---|
| `anchor_mode` | `base` | `base` / `average` | [[strategy-master]] §5 |
| `big_candle_override` | `on` | `on` / `off` | [[strategy-master]] §2.4 |
| `partial_ladder_at_4h_end` | `continue` | `continue` / `force_close` / `wait_for_zero` | [[strategy-master]] §3.3 |
| `no_exit_at_4h_end` | `carry_open` | `carry_open` / `force_close` / `wait_for_zero` | [[strategy-master]] §4.2 |
| `direction_flip_mode` | `flip` | `flip` / `ignore_flip` / `wait_for_zero` | [[strategy-master]] §4.3 |
| `nested_box_edge` | `hold` | `hold` / `weekly_only` / `monthly_only` | [[strategy-master]] §2.2 |

## Data inputs

| Field | Required | Description |
|---|---|---|
| `candles_4h_path` | yes | 4h OHLCV CSV |
| `candles_1m_path` | yes | 1-min OHLCV CSV (for sub-bar exits + ladder triggers) |
| `box_data_path` | yes | `NQ_full_data.csv` (16-level unified box CSV) |
| `start_date` / `end_date` | optional | range filter |

## Hardcoded (not exposed)

| Constant | Value | Why hardcoded |
|---|---|---|
| Entry-decision timeframe | 4h | Strategy is defined on 4h boundaries |
| Soft-SL confirmation | 2 consecutive 1-min closes | "2-min close" synthesis |
| Hard-SL confirmation | 1 single 1-min close | Engine timeframe |
| NQ session start | 18:00 prev day | NQ market structure |
| NQ session end | 17:00 next day | NQ market structure |
| `tick_threshold` (box validity) | 0.75 | Internal to [[box_lookup]] |

Changing any of the hardcoded values requires editing source code, not just the dashboard.
