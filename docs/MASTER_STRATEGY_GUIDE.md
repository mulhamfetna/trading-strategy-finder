# Master Strategy Guide

**Authoritative consolidation of:**
- `Currunt_Strategy_Algo_for_Trading.md` — the 1-1-2 Scaling execution framework
- `BOXES_Strategy.md` (raw spec) + `docs/BOX_STRATEGY.md` (confirmed spec) — the TradingView Box directional oracle
- `docs/STRATEGY_INTEGRATION_ANALYSIS.md` — why and how the two integrate

This is the single source of truth for *what the trading system does and why*. The two prior playbooks remain for historical context; future edits should land here. All numeric and behavioural decisions described below are exposed as user-tunable parameters in the dashboard — nothing in this guide is hard-coded inside the engine.

---

## 1. Architectural overview

The system runs **one master strategy** built from two layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                    EXECUTION FRAMEWORK (1-1-2 Scaling)                 │
│   How a trade is sized, scaled, stopped out, taken profit, re-entered. │
│   Source: Currunt_Strategy_Algo_for_Trading.md                         │
└────────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ direction
                                  │
┌────────────────────────────────────────────────────────────────────────┐
│              DIRECTIONAL ORACLE — TradingView Box                      │
│  Direction = which box edge the 4h close crossed (weekly priority).    │
│  Source: BOXES_Strategy.md / §2 of this guide.                         │
└────────────────────────────────────────────────────────────────────────┘
```

The execution framework is silent about direction; the directional oracle is silent about size/SL/TP. They were written to layer, and the master strategy uses them together — no toggle, no mode selection. The Box CSVs are required.

**Code mapping:**
- `src/strategy/scaling_strategy.py::ScalingStrategy` — execution framework. Owns the full per-candle lifecycle. Direct use is **only for unit tests**; production never instantiates this class.
- `src/strategy/box_strategy.py::BoxStrategy(ScalingStrategy)` — production engine. Overrides `_maybe_open_position` to consult `BoxLookup`.
- `src/strategy/box_lookup.py::BoxLookup` — pure directional oracle, loads weekly/monthly box CSVs and answers "long / short / none" for a (close, timestamp) pair.

> **Historical note:** an earlier iteration of the dashboard exposed a "Scaling vs Box" radio toggle. That toggle was retired — the `close > prev_close` rule of the scaling-only mode was a placeholder that pre-dated the Box oracle. The current dashboard has no strategy choice; the master strategy always uses the Box.

---

## 2. The directional oracle (TradingView Box)

For every 4h candle close, ask `BoxLookup.get_signal_detail(close, timestamp)`:

1. Look up the **active weekly box** — the most recent row in `NQ_week_data_shifted.csv` where `date_shifted ≤ candle_date < date_shifted + weekly_window_days`.
2. Look up the **active monthly box** — same logic with `monthly_window_days`.
3. For each box level (RH / IH / IL / RL / TH / TL with optional sub-levels TH1/TH2, TL1/TL2):
   - `close > upper_edge + box_tick_threshold` ⇒ LONG candidate
   - `close < lower_edge − box_tick_threshold` ⇒ SHORT candidate
   - Otherwise ⇒ no fire from that level
4. The **closest firing level** wins for each timeframe (weekly / monthly), separately.
5. Aggregate using the **single-box weekly-priority rule** (current policy):
   - If weekly fires, take the weekly direction.
   - Else if monthly fires, take the monthly direction.
   - Else no trade.
6. If both fire opposite directions, set `conflict = True` on the trade so the UI can flag it; the aggregate still uses weekly priority.

The 0.75-point `box_tick_threshold` is **3 NQ ticks** of 0.25 each. It's a noise filter — price must clear the edge meaningfully, not just wick through it.

### 2.1 Box data — files and preprocessing

| File | Window | Columns |
|---|---|---|
| `NQ_week_data.csv` | 7 days starting at `Date` | WRHU/D, WIHU/D, WILU/D, WRLU/D, WTHU/D, WTH1/2, WTLU/D, WTL1/2, wOpen |
| `NQ_month_data.csv` | 30 days starting at `Date` | M-prefixed equivalents + mOpen |

Column naming:

```
[W/M]  [BoxType]  [U/D or 1/2]
  │       │           │
  │       │           └─ U=upper edge, D=lower edge, 1/2=sub-levels of TH/TL
  │       └── RH = Reversal High        IH = Intermediate High
  │           IL = Intermediate Low     RL = Reversal Low
  │           TH = Trending High        TL = Trending Low
  └── W = Weekly, M = Monthly
```

`wOpen` / `mOpen` are reference values only — they do **not** generate signals.

TH and TL boxes can have null edges (~42% present in real data) when price never reached those extremes. `BoxLookup._best_level` skips null cells.

**One-time preprocessing** (`scripts/preprocess_boxes.py`): subtract 2 calendar days from every `Date`, save as `NQ_*_data_shifted.csv`. Reason: the raw exports record the box's defining day but the box is active starting from the prior session. Run once; commit results; never re-run.

### 2.2 Stacked boxes and re-fires

Boxes stack vertically. As price rises through a tracked range, it can cross multiple upper edges in sequence (WRHU then WIHU, then WTHU). Each crossing is a fresh signal — the same row can produce multiple LONG signals over successive 4h closes as price walks up through nested boxes.

Intersected boxes (where weekly and monthly boundaries overlap to create a finer-grained zone) are **out of scope for this iteration** — single-box logic only. The legacy "both must agree" rule was abandoned on 2026-05-23.

---

## 3. The execution framework (1-1-2 Scaling)

Once direction has been chosen by the oracle, the execution framework owns the trade. Every numeric value below is a user parameter (`ScalingParams.*` / `BoxStrategyParams.*`).

### §1 — Entry distribution and position sizing

A trade enters across up to **3 legs** with a 1-1-2 contract distribution:

| Leg | Contracts | Trigger price |
|---|---|---|
| 1 | `leg1_contracts = 1` | `base_level` (the close that fired the signal) |
| 2 | `leg2_contracts = 1` | `base_level − leg2_pullback_points` (long) / `+ leg2_pullback_points` (short) |
| 3 | `leg3_contracts = 2` | `base_level − leg3_pullback_points` (long) / `+ leg3_pullback_points` (short) |

`total_contracts = 4` is the documented sum; the engine actually sums `leg1+leg2+leg3` at fill time, so adjusting one leg requires checking the sum.

Average price is the weighted average of filled legs. With the default 1-1-2 at 100/150 pt pullbacks, **a fully-filled trade has its average ~100 points below the base level** (long case). The playbook's claim of "~75 points away" is an approximation; the engine uses the exact weighted average for SL/TP math.

### §2 — Big-candle exception

If the trigger candle's body size (`abs(close − open)`) exceeds `big_candle_threshold_points = 400`, the 1-1-2 distribution is abandoned:

- Enter the **full size** `big_candle_full_contracts = 4` immediately at the close.
- If `big_candle_reverses_dir = true`, take the **opposite** direction of the candle (huge green ⇒ short, huge red ⇒ long) — the playbook reads a 400-pt bar as exhaustion, not continuation.

**This rule can conflict with the Box directional oracle.** See §5 below for the explicit resolution policy.

### §3 — Entry-trigger confirmation (15-second chart)

The playbook prescribes time-based confirmation on a 15-second chart to avoid fake-outs:

- **Entry 1:** Price must touch the entry level and wait for `entry1_confirmation_candles = 3` consecutive 15-second candles to close at or beyond the level.
- **Entries 2 & 3:** Only `entry23_confirmation_candles = 1` 15-second candle close required (price is moving fast against us, less time to wait).
- The confirmation timeframe is `entry_confirmation_timeframe_seconds = 15`.

**Backtest-mode caveat:** the engine runs on 4h bars. The 15-second confirmation is **stored as a parameter** but **not enforced** — every 4h close is treated as already-confirmed. A dual-timeframe engine could enforce these natively; the parameters are kept so a future build doesn't need new fields.

### §4 — Stop loss (dual-SL system)

Two stop-loss tiers run simultaneously:

| Tier | Distance | Confirmation rule |
|---|---|---|
| Soft SL | `sl_soft_points = 200` from `avg_price` | A `soft_sl_confirmation_timeframe_minutes = 2`-minute candle closes beyond the line |
| Hard SL | `sl_hard_points = 300` from `avg_price` | A `hard_sl_confirmation_timeframe_seconds = 5`-second candle closes beyond the line |

A wick that does not close beyond the line **does not** trigger the SL. In 4h-only backtest mode both confirmations collapse to the 4h close — the engine exits on whichever line is closed beyond first, calling it `'STOP LOSS (SOFT)'` or `'STOP LOSS (HARD)'`.

Hard SL is placed further away than soft SL by construction; the dashboard enforces `sl_hard_points ≥ sl_soft_points` with an inline validation message.

### §5 — Take profit

Two-stage TP:

1. **Hard target:** `tp_target_points = 150` from `avg_price`. If the candle's high/low reaches this level, exit with `'TAKE PROFIT'`.
2. **Watch trail:** once the candle's close moves at least `tp_watch_threshold_points = 50` in favour of the position, the watch is *armed*. Once armed, if a later candle closes back below (long) or above (short) the watch line — measured on the `tp_confirmation_timeframe_minutes = 2` timeframe — exit with `'TAKE PROFIT (TRAIL)'`.

The watch can only arm; it cannot disarm. Once a position has been in profit by +50 pts, the trail rule stays active for the remainder of the trade.

### §5b — Re-entry

If `reentry_enabled = true` and the previous exit was a `'TAKE PROFIT'`, the engine arms a re-entry watch for `reentry_cooldown_candles = 1` bars. If the next signal fires in the **same direction** within the cooldown, the engine treats it as a fresh trade (new legs, fresh SL/TP) — riding the continuation of a winning move.

Re-entry semantics are anchored to `base_level` (the original entry price); a future "box-aware" re-entry could anchor to the firing box edge instead. Not implemented.

### §0 — Instrument constants

PnL math:

```
profit_points  = (exit_price − avg_price)         for long
profit_points  = (avg_price − exit_price)         for short
profit_dollars = profit_points × contracts × point_value
```

`point_value = 2.0` is the NQ futures convention ($2 per point per contract). Switch to 50 for ES, 5 for MES, etc. — the engine has no other hard-coded instrument assumption.

---

## 4. The integration contract

The two layers meet at exactly one method: `ScalingStrategy._maybe_open_position(idx, opn, high, low, close, prev_close) → _Position | None`.

The master strategy uses **one implementation only**: `BoxStrategy._maybe_open_position` — which consults `BoxLookup` for the directional read and falls through to the inherited 1-1-2 execution for sizing, leg fills, SL, TP, and re-entry.

Future directional oracles (a daily-box variant, a tick-imbalance signal, an ML model, ...) can plug in by subclassing `ScalingStrategy` and overriding the same seam. The current implementation has only the Box subclass.

---

## 5. The Big-Candle vs Box conflict (the one real edge case)

When **both** of the following are true on the same 4h bar:

1. `abs(close − open) > big_candle_threshold_points`
2. `BoxLookup.get_signal_detail` returns a non-null signal

… the §2 Big-Candle Exception and the box's directional read can **disagree**. Example: a +500-pt green bar that closes above the weekly RHU edge — §2 says SHORT (reversal), Box says LONG (breakout).

This is the only real policy choice in the master strategy. It's exposed as `BoxStrategyParams.big_candle_resolution`:

| Value | Behaviour | When to choose |
|---|---|---|
| `big_candle_wins` (default) | §2 reverses; box ignored | Trust the playbook's mean-reversion bias on outsized bars |
| `box_wins` | Take box direction with full big-candle size | Trust level crosses over candle-color heuristics |
| `skip` | No trade when the two disagree | Conservative — wait for unambiguous setups |

The default is `big_candle_wins` — the legacy behaviour from when the Big-Candle Exception was the only direction rule on outsized bars.

---

## 6. Parameter reference

Every numeric/boolean decision in this guide is a field on `ScalingParams` (Python) / `ScalingParamsModel` (Pydantic) / `ScalingParams` (TypeScript) and is exposed in the dashboard.

| § | Field | Default | Range / type | UI section |
|---|---|---|---|---|
| §1 | `total_contracts` | 4 | int ≥ 1 | Entry distribution |
| §1 | `leg1_contracts` | 1 | int ≥ 0 | Entry distribution |
| §1 | `leg2_contracts` | 1 | int ≥ 0 | Entry distribution |
| §1 | `leg3_contracts` | 2 | int ≥ 0 | Entry distribution |
| §1 | `leg2_pullback_points` | 100.0 | float ≥ 0.25 | Entry distribution |
| §1 | `leg3_pullback_points` | 150.0 | float ≥ 0.25 (must exceed `leg2_pullback_points`) | Entry distribution |
| §0 | `point_value` | 2.0 | float ≥ 0.01 (NQ=2, ES=50, MES=5) | Entry distribution |
| §2 | `big_candle_threshold_points` | 400.0 | float ≥ 0.25 | Big candle exception |
| §2 | `big_candle_full_contracts` | 4 | int ≥ 0 | Big candle exception |
| §2 | `big_candle_reverses_dir` | true | bool | Big candle exception |
| §3 | `entry_confirmation_timeframe_seconds` | 15 | int ≥ 1 (documented; not enforced in 4h-only) | Entry trigger |
| §3 | `entry1_confirmation_candles` | 3 | int ≥ 1 | Entry trigger |
| §3 | `entry23_confirmation_candles` | 1 | int ≥ 1 | Entry trigger |
| §4 | `sl_soft_points` | 200.0 | float ≥ 0.25 | Stop loss |
| §4 | `sl_hard_points` | 300.0 | float ≥ `sl_soft_points` | Stop loss |
| §4 | `soft_sl_confirmation_timeframe_minutes` | 2 | int ≥ 1 (4h-only collapses to candle close) | Stop loss |
| §4 | `hard_sl_confirmation_timeframe_seconds` | 5 | int ≥ 1 (same) | Stop loss |
| §5 | `tp_target_points` | 150.0 | float ≥ 0.25 | Take profit |
| §5 | `tp_watch_threshold_points` | 50.0 | float ≥ 0.25 | Take profit |
| §5 | `tp_confirmation_timeframe_minutes` | 2 | int ≥ 1 | Take profit |
| §5b | `reentry_enabled` | true | bool | Re-entry |
| §5b | `reentry_cooldown_candles` | 1 | int ≥ 0 | Re-entry |

**Box-layer fields** (`BoxStrategyParams` extends `ScalingParams`):

| Field | Default | Notes | UI section |
|---|---|---|---|
| `box_tick_threshold` | 0.75 (= 3 NQ ticks × 0.25) | Noise filter: required margin past the edge | Box-rule decisions |
| `weekly_window_days` | 7 | How many days a weekly box covers | Box-rule decisions |
| `monthly_window_days` | 30 | How many days a monthly box covers | Box-rule decisions |
| `big_candle_resolution` | `'big_candle_wins'` | §5 conflict policy: `big_candle_wins` \| `box_wins` \| `skip` | Box-rule decisions |
| `week_data_path` | `NQ_week_data_shifted.csv` | File path | Data |
| `month_data_path` | `NQ_month_data_shifted.csv` | File path | Data |

---

## 7. Backtest semantics

### 7.1 Data files (gitignored)

| File | Purpose | Format |
|---|---|---|
| `NQ_4h.csv` | Primary signal data, ascending | single `datetime` column + Open/High/Low/Close/Volume |
| `NQ_week_data_shifted.csv` | Weekly box edges (preprocessed) | `Date` + level columns |
| `NQ_month_data_shifted.csv` | Monthly box edges (preprocessed) | `Date` + level columns |

### 7.2 PnL formula

```
profit_dollars = profit_points × contracts × point_value
```

Fees and slippage are not modelled (no `total_fees` deduction in `_box_metrics`). The "Net Profit" card is therefore pre-fee. If fees are reintroduced later, EV/PF/Sharpe formulas must update in lockstep.

### 7.3 Trade shape emitted to the frontend

```json
{
  "entry_idx": <bar index of the signal candle>,
  "exit_idx":  <bar index of the exit candle>,
  "direction": "long" | "short",
  "avg_entry_price": <weighted-average of filled legs>,
  "exit_price": <SL line, TP line, or trail close>,
  "contracts": <legs sum or big-candle size>,
  "profit_points": <signed>,
  "profit_dollars": <profit_points × contracts × point_value>,
  "exit_reason": "TAKE PROFIT" | "TAKE PROFIT (TRAIL)" | "STOP LOSS (SOFT)" | "STOP LOSS (HARD)",
  "legs": [ { "contracts": n, "price": p, "candle_idx": i }, ... ],
  "exit_time": <ISO string, dual-timeframe only>,
  "box_signal": { ... }   // present only in Box mode
}
```

Both modes emit the same fields; `box_signal` is the only optional one (present only when the directional oracle was the BoxLookup).

### 7.4 Metrics emitted

`profit_factor` and `sharpe_ratio` are `null` when mathematically undefined (no losses for PF; <2 trades or zero variance for Sharpe). The frontend renders `"N/A"` in that case. See BUG-011 in the bug bounty knowledge base.

---

## 8. Dashboard mapping

The SettingsPanel mirrors this guide's section numbering:

| UI section | Maps to |
|---|---|
| Data | `data_path`, `week_data_path`, `month_data_path`, `start`, `end` |
| §1 Entry distribution & sizing (1-1-2) | All §1 + §0 params |
| §2 Big candle exception (>400 pts) | All §2 params |
| §3 Entry trigger (15-sec confirmation) | All §3 params |
| §4 Stop loss (dual SL system) | All §4 params |
| §5 Take profit | All §5 params |
| §5b Re-entry | All §5b params |
| Box-rule decisions | `box_tick_threshold`, `weekly_window_days`, `monthly_window_days`, `big_candle_resolution` |
| Indicators | EMA / RSI / volume display |

The "Reset to playbook defaults" button at the bottom restores every field to the values in this guide.

---

## 9. Out of scope (current iteration)

These are explicit non-goals — items the playbooks mention but the engine does not yet honour:

| Item | Source | Status |
|---|---|---|
| Intersected boxes (weekly ∩ monthly producing finer zones) | BOXES_Strategy.md / docs/BOX_STRATEGY.md | Deferred; single-box only |
| Daily (D-prefix) boxes | implied | No daily CSV provided |
| Average retracement / break-even stop management | implied | Not implemented |
| Multi-timeframe tick confirmation (15-sec, 2-min, 5-sec) | 1-1-2 §3 / §4 / §5 | Params exist, enforcement deferred to dual-timeframe build |
| Live trading | — | Backtest engine only |
| Fees / commissions / slippage modelling | — | `point_value × profit_points` only |
| Box-aware re-entry anchoring | §5b discussion | Not implemented; uses `base_level` |
| `big_candle_resolution` explicit conflict policy | §5 of this guide | Default behaviour matches `big_candle_wins`; flag not yet exposed |
| Walk-forward / out-of-sample validation reports | swarm audit FIX-04 | Not implemented |

---

## 10. Source documents (history)

- `Currunt_Strategy_Algo_for_Trading.md` — original 1-1-2 playbook (kept as historical reference).
- `BOXES_Strategy.md` — raw brainstorming dump of the Box system (kept as historical reference).
- `docs/BOX_STRATEGY.md` — structured/confirmed Box spec (kept as historical reference).
- `docs/STRATEGY_INTEGRATION_ANALYSIS.md` — full reasoning behind the integration architecture.
- `docs/bug-checklist-revision-history.md` — bug bounty knowledge base; BUG-014/019/020 relate to strategy-label drift.
- `docs/revisions/REVISION_LOG.md` — round-by-round revision history.

**Going forward, edit this file (`MASTER_STRATEGY_GUIDE.md`) — the four source documents above are frozen reference material.**
