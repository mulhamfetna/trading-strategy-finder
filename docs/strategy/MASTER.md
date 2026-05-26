---
name: strategy-master
description: Integrated master specification for the box-driven 1-1-2 scaling strategy — entry direction, position sizing, exits, anchoring, vocabulary, and parameter discipline
type: master
---

# Master Strategy Specification

This document is the single source of truth for what the trading strategy does. It supersedes the prior `Strategy1.md` + `Strategy2.md` drafts and the deleted `SYSTEM_BLUEPRINT.md` / `MASTER_STRATEGY_GUIDE.md` / `Currunt_Strategy_Algo_for_Trading.md`.

The strategy has three concerns running on two timeframes:

| Concern | Timeframe | Output |
|---|---|---|
| **Entry direction** | end of each 4h candle | `long` / `short` / `hold` |
| **Position sizing (ladder)** | inside the 4h, sampled on 1-min | up to 4 contracts via 1-1-2 scaling |
| **Exit decision** | each 1-min close | `take_profit` / `stop_loss` / `open` |

The box system gates the entry direction. The 1-1-2 ladder builds the position. Soft/hard SL and a fixed TP target close the position.

---

## 1. Data shape

Only two timeframes are available to the engine:

- **4h candles** — used to fire entry-direction decisions at each bar boundary.
- **1-min candles** — used to fire exit checks and to trigger ladder follow-up legs.

There is no native 2-min, 5-min, 15-second, or tick data.

A "2-min close" referenced in the soft-SL rule is synthesised as **two consecutive 1-min closes** past the same line. This is the engine's only synthetic timeframe.

NQ session cycle: **18:00 prev day → 17:00 next day**, with hour ≥ 18 rolling forward by one calendar day (see [[box_lookup]]).

---

## 2. Entry decision — direction at each 4h boundary

The entry decision fires at the **boundary** between two 4h candles. The just-closed 4h candle is the **only** input (no look-ahead).

The output is one of three states:

- `long` — open or maintain a long position
- `short` — open or maintain a short position
- `hold` — do nothing this 4h; if a position is already open, leave it open

### 2.1 The box-interaction truth table

The full rule combines three inputs:

| Input | Values |
|---|---|
| `price_direction` | `up` (green 4h) / `down` (red 4h) / `doji` (open = close) |
| `box_position` | `above` (when `price_direction = up`) / `below` (when `price_direction = down`) |
| `reach_state` | `miss` / `bounce` / `traverse` |

`reach_state` is **close-based**:

- **`miss`** — the candle's high (long-bias case) or low (short-bias case) did not cross the near box edge.
- **`bounce`** — the high/low crossed the near edge but the **close** ended inside the box.
- **`traverse`** — the **close** ended beyond the far edge.

Decision table:

| price_direction | box_position | reach_state | → entry |
|---|---|---|---|
| `up` (green 4h) | above | miss | `short` (reversal) |
| `up` | above | bounce | `hold` |
| `up` | above | traverse | `long` |
| `down` (red 4h) | below | miss | `long` (reversal) |
| `down` | below | bounce | `hold` |
| `down` | below | traverse | `short` |
| `doji` (open == close) | — | — | `hold` |

The full table also lives in [[truth_table]] as a reference card.

### 2.2 Box selection

The system uses the static 16-level box CSV (8 weekly + 8 monthly) from `NQ_full_data.csv`. See [[box_lookup]] for the implementation.

- **The active box** at any 4h close is the **nearest unburned level on the correct side of the just-closed price**:
  - `up` direction → look at boxes **above** (closest weekly-or-monthly with lower edge ≥ close).
  - `down` direction → look at boxes **below** (closest weekly-or-monthly with upper edge ≤ close).
- A box is **burned** once price has fully traversed it. The selection skips burned levels and uses the next-nearest unburned box.
- **Nested-box edge case:** if price is inside two overlapping boxes (e.g., monthly + weekly), the decision depends on burn state:
  - Inside both, neither burned → `hold` (no signal)
  - Burned through both → action per the truth table
  - Burned through one, still inside the other → default `hold` (conservative). Dashboard can override to "weekly-only" or "monthly-only".

### 2.3 First-candle warm-up

The system does not act on the very first 4h candle of the dataset. It only watches. From the 2nd 4h boundary onward, the first 4h is treated as the "just-closed" candle and the truth table applies normally.

### 2.4 Big-candle override (≥ `big_candle_threshold` pts)

If the just-closed 4h candle has `|close − open| ≥ big_candle_threshold` (default **400 pts**), an opt-in **reversal rule** activates:

- Direction reverses: green-and-big → `short`; red-and-big → `long`.
- Entry is **immediate full position** (4 contracts at base), skipping the 1-1-2 ladder.
- Default state: **ON**. User can opt out via the dashboard.

When the big-candle override fires, the box-direction truth table is **bypassed** for this candle.

---

## 3. Position sizing — the 1-1-2 ladder

When a `long` or `short` signal fires (and big-candle override is not active), the engine opens **leg 1 only** at the 4h boundary. Follow-up legs fire inside the 4h on 1-min granularity, triggered by adverse price moves.

### 3.1 The ladder (default values, all dashboard-tunable)

| Leg | Trigger (long; mirrored for short) | Entry price | Contracts | Running avg entry |
|---|---|---|---|---|
| 1 | 4h close fires direction signal | `base` | 1 | `base` |
| 2 | price drops ≥ `ladder_step_1` (default 100) below `base` | `base − ladder_step_1` | 1 | `base − ladder_step_1 / 2` |
| 3 | price drops ≥ `ladder_step_2` (default 150) below `base` | `base − ladder_step_2` | 2 | `base − ladder_step_2 + (ladder_step_2 − ladder_step_1) / 4` |

For the defaults `ladder_step_1 = 100`, `ladder_step_2 = 150`:

- After leg 1 (1 contract): avg = `base`
- After leg 2 (2 contracts): avg = `base − 50`
- After leg 3 (4 contracts): avg = `base − 100`

`base` itself = the close of the 4h candle that fired the direction signal.

### 3.2 SL vs ladder validation (three tiers)

Because the ladder requires adverse price moves to fill, an SL set too tight defeats the ladder. The dashboard validates `sl_soft_points` (soft SL) against the ladder thresholds and exposes a warning:

| Soft SL distance | Tier | Effect |
|---|---|---|
| `sl_soft < ladder_step_1` | **Deactivated** | Trade stays single-contract; ladder never fires |
| `ladder_step_1 ≤ sl_soft < ladder_step_2` | **Partial** | Leg 2 fires; leg 3 cannot (SL would close trade first) |
| `sl_soft ≥ ladder_step_2` | **Full** | All legs available |

UI behaviour: the soft-SL number-box turns yellow with an inline note explaining the active tier. **Warn but allow** — the user can save the config; the engine respects the tier at runtime.

The TP target has **no** interaction with the ladder validation.

### 3.3 Edge case — 4h closes before the ladder finishes filling

Default behaviour: **continue the 1-1-2 ladder into the next 4h**, with the same `base` and the same trigger lines. The trade is not closed at the 4h boundary.

Two alternatives are exposed in the dashboard:

- `force_close` — close the trade at the 4h end and re-evaluate direction with fresh leg 1.
- `wait_for_zero` — keep the trade open and exit when price returns to the original `base` (zero P/L).

See [[edge_cases]] for the per-mode behaviour.

---

## 4. Exit decision — fixed SL and fixed TP

There is **no trail mechanism**, **no +50 watch line**, **no dynamic exit**. The exit system is three fixed lines:

| Line | Long-position formula | Short-position formula | Fire condition | Fill price |
|---|---|---|---|---|
| **Soft SL** | `anchor − sl_soft_points` | `anchor + sl_soft_points` | 2 consecutive 1-min closes past the line | the 2-min close |
| **Hard SL** | `anchor − sl_hard_points` | `anchor + sl_hard_points` | 1 single 1-min close past the line | the line price |
| **TP** | `anchor + tp_target_points` | `anchor − tp_target_points` | price reaches the line | the line price |

`anchor` is either `base` or the running average entry, controlled by the `anchor_mode` toggle (see §5).

### 4.1 Exit reasons

The trade-log `exit_reason` field uses exactly these values:

- `TAKE PROFIT` — TP line reached
- `STOP LOSS (SOFT)` — soft SL fired
- `STOP LOSS (HARD)` — hard SL fired
- `DIRECTION_FLIP` — see §4.3
- `OPEN` — trade is still open at end of dataset

### 4.2 Edge case — 4h closes without SL/TP hit

Default behaviour: **carry the trade open across the 4h boundary**. SL/TP/direction-flip rules continue to apply.

Two alternatives in the dashboard:

- `force_close` — close at the 4h boundary regardless of P/L.
- `wait_for_zero` — keep open until price returns to entry (zero P/L), then close.

### 4.3 Direction-flip mid-trade

When the next 4h close fires a direction opposite to the current open trade, the **default** is:

- Close the existing trade at the 4h boundary with `exit_reason = DIRECTION_FLIP`.
- Open a new trade in the new direction immediately, starting fresh leg 1.

Two alternatives in the dashboard:

- `ignore_flip` — keep the existing trade open; only SL/TP can close it.
- `wait_for_zero` — keep open until price returns to entry, then exit at zero P/L; then open the new trade.

### 4.4 Position-management interaction with HOLD

If the next 4h close fires `hold`, **existing trades stay open** — `hold` only blocks new entries. SL/TP/direction-flip remain the only exit mechanisms.

---

## 5. Anchoring — `base` vs `average`

The reference price (`anchor` in §4) is determined by the dashboard toggle `anchor_mode`:

| Mode | Behaviour |
|---|---|
| **`base`** (default) | All three exit lines stay fixed at `base ± thresholds` for the trade's lifetime. Legs 2 and 3 do not affect the lines. |
| **`average`** | All three exit lines re-anchor on every leg fill to the running average entry: `lines = avg ± thresholds`. |

In `average` mode, after each leg fill:

- The soft SL line moves further from `base` (more room for adverse moves).
- The hard SL line moves further from `base`.
- The TP line moves closer to current price (smaller required favourable recovery).

The two modes are mathematically distinct. The current code is `base`-anchored; `average` mode is tracked as a separate code task (see §9).

---

## 6. Vocabulary

| Domain | Values |
|---|---|
| Entry state | `long`, `short`, `hold` |
| Exit state | `take_profit`, `stop_loss`, `open` |
| `exit_reason` (in trade log) | `TAKE PROFIT`, `STOP LOSS (SOFT)`, `STOP LOSS (HARD)`, `DIRECTION_FLIP`, `OPEN` |
| `anchor_mode` (config) | `base`, `average` |
| Reach state (in box-interaction rule) | `miss`, `bounce`, `traverse` |
| Box-validation tier (ladder) | `deactivated`, `partial`, `full` |

The word `hold` belongs only to entry state. The word `open` belongs only to exit state. Do not mix them.

---

## 7. Parameter discipline

Parameters split into two classes:

### 7.1 Price values — dashboard-tunable

Every numeric quantity in the strategy that is measured in points is **user-configurable** via the dashboard. Defaults are the values written above.

| Parameter | Default | Used in |
|---|---|---|
| `sl_soft_points` | (user-set) | §3.2, §4 |
| `sl_hard_points` | (user-set) | §4 |
| `tp_target_points` | (user-set) | §4 |
| `ladder_step_1` | 100 | §3.1 (leg 2 trigger) |
| `ladder_step_2` | 150 | §3.1 (leg 3 trigger) |
| `big_candle_threshold` | 400 | §2.4 |

### 7.2 Time values — hardcoded for this iteration

| Parameter | Value | Used in |
|---|---|---|
| Entry-decision timeframe | 4h | §2 |
| Soft-SL confirmation | 2 consecutive 1-min closes | §4 |
| Hard-SL confirmation | 1 single 1-min close | §4 |
| 1-min sampling for ladder triggers | 1-min | §3 |
| NQ session window | 18:00 prev day → 17:00 next day | §1 |

Hardcoded means: changing these requires editing source code, not just dashboard fields.

### 7.3 Behaviour toggles — dashboard

| Toggle | Default | Effect |
|---|---|---|
| `anchor_mode` | `base` | §5 |
| `big_candle_override` | `on` | §2.4 |
| `partial_ladder_at_4h_end` | `continue` | §3.3 |
| `no_exit_at_4h_end` | `carry_open` | §4.2 |
| `direction_flip_mode` | `flip` | §4.3 |
| `nested_box_edge` | `hold` | §2.2 |

See [[dashboard_params]] for a flat parameter reference.

---

## 8. Implementation map

The strategy is implemented across three source files:

- [[scaling_strategy]] — `src/strategy/scaling_strategy.py` — owns the 1-1-2 ladder logic, fixed-SL/TP exit lines, and the `anchor_mode` toggle.
- [[box_strategy]] — `src/strategy/box_strategy.py` — owns the 4h direction decision (truth table from §2), big-candle override (§2.4), direction-flip (§4.3), and the trade lifecycle.
- [[box_lookup]] — `src/strategy/box_lookup.py` — owns box loading, the static 16-level model, NQ session mapping, and the nearest-unburned box selection.

Tests live in `tests/test_blueprint_examples.py` ([[blueprint_examples]]). Reference January-2025 trades are regenerated whenever the engine changes.

---

## 9. Implementation status

| Item | Status |
|---|---|
| Remove trail exit logic from the engine (no `TAKE PROFIT (TRAIL)`, no +50 watch, no `watch_armed`) | ✅ done |
| Regenerate locked blueprint fixtures (`tests/test_blueprint_examples.py`) for post-trail engine | ✅ done — Examples 1, 2, 3, 4 + total-count locked |
| Add `anchor_mode: Literal['base', 'average']` to the Pydantic schema (`src/api/schemas.py`) | ✅ done — default `'base'`, frontend-omittable |
| Add `anchor_mode` to `ScalingParams` dataclass (`src/strategy/scaling_strategy.py`) | ✅ done — required, validated at construction |
| Engine `_anchor(position)` helper switches between `base_level` / `avg_price` | ✅ done — drives both 4h-only and dual-timeframe exit paths |
| Dashboard `anchor_mode` toggle + ladder-tier warning in `SettingsPanel.vue`, `types.ts` defaults | ✅ done |
| `TradeList.vue` colour-codes the new `exit_reason` palette (TP / SL / DIRECTION_FLIP / OPEN) | ✅ done |
| Remove deprecated `tp_watch_threshold_points` / `tp_confirmation_timeframe_minutes` from dataclass, schema, types, and dashboard | ✅ done |
