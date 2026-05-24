# Backtest Logic — Master Strategy (1-1-2 Scaling × Box Oracle, Dual-Timeframe)

> **Authoritative end-to-end behaviour:** `docs/SYSTEM_BLUEPRINT.md` (with real-data worked examples).
> **Strategy spec:** `docs/MASTER_STRATEGY_GUIDE.md` (rule citations + parameter table).
> This doc is the medium-depth walkthrough of how the engine actually executes per bar.

## 1. Data Pipeline

```
NQ_4h.csv       →  load_data()  →  filter_by_date_range()  ┐
NQ_1m.csv       →  load_data()  →  filter_by_date_range()  ├─→  BoxStrategy.backtest(df, df_1min)
NQ_full_data.csv →  BoxLookup(unified_path)                ┘
```

All three CSVs are required. `load_data` normalises the `datetime` column to `Date` (`pd.Timestamp`) and the OHLCV columns to Title Case. The 4h frame drives the outer loop (entry signals); the 1-min frame drives the inner SL/TP walker; the box CSV is the directional oracle.

The 4h CSV exports newest-first from the trading platform; `load_data` and the FastAPI endpoint sort ascending so candle index 0 is the oldest.

## 2. The Per-Bar Lifecycle

For every 4h candle, the engine executes five phases in order (`scaling_strategy.py::ScalingStrategy.backtest`):

```
1. _on_bar(idx, candle)               box-state machine observes EVERY bar
2. exit checks (if position open)     sub-bar walker on 1-min/2-min when df_1min is supplied,
                                      else 4h-close fallback
3. leg fills (if still open)          legs 2 / 3 pullback at base_level ± 100/150 pts on 4h H/L
4. entry decision (if flat)           BoxStrategy._maybe_open_position
5. arm watch (4h-only legacy path)    in dual-timeframe mode, arming happens inside the walker
```

## 3. Entry: How a Trade Opens

### Standard entry (per `BoxStrategy._maybe_open_position`)

The 4h candle's close is classified by `BoxLookup.get_signal_detail(close, ts)`:

```
'long'   ←  close traversed below→inside→above a box edge (after a prior 'below' state)
'short'  ←  mirror
'hold'   ←  no traversal (or first observation of this row/level)
```

Weekly priority: if the weekly stack fires `long`/`short`, that wins; else if the monthly stack fires, that wins. `conflict=True` flags weekly + monthly disagreement (weekly still wins the aggregate).

When the signal is directional and the candle is not a big candle (`|close − open| ≤ big_candle_threshold_points`), `Leg 1` fills at the signal candle's **close**:

```
Position(direction=signal, base_level=close, legs=[Leg(leg1_contracts, close, idx)])
```

### Big-candle exception (`|close − open| > 400 pts`)

Big bars are read as exhaustion, not continuation. The 1-1-2 distribution is abandoned:

```
bc_dir_raw = 'long' if close > open else 'short'
if big_candle_reverses_dir:
    bc_dir = the OPPOSITE direction      # default: green big bar → SHORT, red → LONG

# Conflict resolution (MASTER_STRATEGY_GUIDE §5)
if box_directional in (None, bc_dir):            chosen = bc_dir
elif big_candle_resolution == 'big_candle_wins': chosen = bc_dir         # default
elif big_candle_resolution == 'box_wins':        chosen = box_directional
elif big_candle_resolution == 'skip':            return None             # no trade

Leg(contracts=big_candle_full_contracts=4, price=close, candle_idx=idx)  # 4 contracts at close
```

## 4. Scaling In: Legs 2 and 3

Once Leg 1 is open, `_maybe_fill_legs` watches the **4h** candle's intra-bar range on each subsequent bar:

**LONG:**

```
Leg 2 fills when 4h Low ≤ base_level − leg2_pullback_points  (default 100)  →  1 contract at the target line
Leg 3 fills when 4h Low ≤ base_level − leg3_pullback_points  (default 150)  →  2 contracts at the target line
```

**SHORT:** mirror on 4h High and `base_level + ...`.

Both legs can fill on the same 4h bar if the range covers both levels. The recorded `leg.price` is the **synthetic target line** (e.g. `base − 100`), not the bar's actual low — modelling a limit order at that price.

**Important interaction with the sub-bar exit walker:** the exit check runs BEFORE `_maybe_fill_legs`. If a 1-min HARD SL fires inside the bar that would otherwise have filled leg 2, the position closes with leg 1 only.

### Average entry price

```
avg = Σ (leg.price × leg.contracts) / Σ leg.contracts
```

A fully-filled long fill (1 + 1 + 2 contracts at base / base−100 / base−150) gives `avg = base − 87.5` — 87.5 points in-the-money from the leg-1 fill's perspective.

## 5. Exits: Four Reasons, Asymmetric Fills

All SL/TP lines are anchored to `avg`:

```
sl_hard_line   = avg − sl_hard_points              (long)  | avg + sl_hard_points              (short)
sl_soft_line   = avg − sl_soft_points              (long)  | avg + sl_soft_points              (short)
tp_target_line = avg + tp_target_points            (long)  | avg − tp_target_points            (short)
tp_watch_line  = avg + tp_watch_threshold_points   (long)  | avg − tp_watch_threshold_points   (short)
```

| Exit reason | Where it fires (dual-timeframe) | Fill price recorded | Watch state |
|---|---|---|---|
| `STOP LOSS (HARD)` | First **1-min close** past `sl_hard_line` | **= `sl_hard_line`** (exact) | n/a |
| `TAKE PROFIT` (target) | First **1-min high (long) / low (short)** reaching `tp_target_line` | **= `tp_target_line`** (exact) | n/a |
| `STOP LOSS (SOFT)` | First **2-min close** past `sl_soft_line` | **= that 2-min close** (≤ sl_soft_line for long) | n/a |
| `TAKE PROFIT (TRAIL)` | Once watch is **armed**, the first **2-min close** back through `tp_watch_line` | **= that 2-min close** | armed when a 2-min close moves +`tp_watch_threshold_points` past `avg` |

The **asymmetry is intentional** (user rule 2026-05-24): hard tiers fill at the line (loss = exactly `sl_hard_points`, gain = exactly `tp_target_points` — disaster-stop + limit-target contract); soft tiers fill at the bar close (loss/gain depends on how far the close went past the threshold — the slow-confirmation cost).

### Priority within a 1-min bar

```
1-min HARD SL     →  1-min TP target    (checked first, on every 1-min bar)
↓ (after the 1-min checks, only at 2-min window ends)
2-min watch arm   →  2-min SOFT SL  →  2-min TRAIL (if armed)
```

The first trigger in time wins. Hard before soft on the same minute.

### 4h legacy fallback

If `ScalingStrategy.backtest(df, df_1min=None)`, the sub-bar walker is bypassed and the engine collapses to a 4h `_check_exits` on each bar's close. Used only by unit tests that build synthetic 4h candles. Production backtests always supply `df_1min`.

## 6. Re-Entry After a Profitable Exit

Triggers when:

- `reentry_enabled = true`, AND
- The exit reason was `'TAKE PROFIT'` (the hard target). Trailing exits do not arm re-entry.

When armed:

1. `cooldown_direction` = the closed trade's direction; `cooldown_base_level` = its `base_level`.
2. `cooldown_counter = reentry_cooldown_candles` (default 1).
3. During cooldown, no new entries fire.
4. When cooldown expires, the next box-signal traversal in any direction opens a fresh position with new legs and a fresh SL/TP frame.

A `'STOP LOSS (*)'` or `'TAKE PROFIT (TRAIL)'` exit clears the cooldown direction without arming re-entry.

## 7. P&L Calculation

```
profit_points  =  exit_price − avg_entry_price   (long)
profit_points  =  avg_entry_price − exit_price   (short)

profit_dollars =  profit_points × contracts × point_value
```

`point_value = 2.0` for NQ micro futures ($2/point/contract). Switch to 50 for ES, 5 for MES, etc. — the engine has no other instrument-specific math.

The `profit_*` fields always use `exit_price` (the algorithm-effective fill), never the candle-grounded `exit_close`. That keeps PnL consistent with what a real broker would have filled.

## 8. Trade Dict Emitted

Every closed trade carries both candle-grounded display fields AND algorithm-effective math fields:

```python
{
    'entry_idx': int,                   # 4h-bar index of the signal candle
    'exit_idx':  int,                   # 4h-bar index containing the exit sub-bar

    'direction': 'long' | 'short',

    'entry_signal_price': float,        # = legs[0].price = signal-bar's close (always in OHLC)
    'exit_close':         float,        # close of the sub-bar (or 4h-bar) that confirmed the exit

    'avg_entry_price':    float,        # weighted average across all filled legs (PnL math)
    'exit_price':         float,        # SL/TP line (HARD/TP) or sub-bar close (SOFT/TRAIL)

    'contracts':       int,
    'profit_points':   float,           # signed
    'profit_dollars':  float,           # profit_points × contracts × point_value

    'exit_reason': 'STOP LOSS (HARD)' | 'STOP LOSS (SOFT)' | 'TAKE PROFIT' | 'TAKE PROFIT (TRAIL)',

    'exit_time': "2025-01-03T15:47:00" | None,    # ISO sub-bar timestamp (None in 4h-only legacy)

    'legs': [{'contracts': n, 'price': p, 'candle_idx': i}, ...],

    'box_signal': {'signal': 'long'|'short',
                   'weekly_level': 'W-RL'|..., 'weekly_signal': str,
                   'monthly_level': 'M-IH'|None, 'monthly_signal': str,
                   'weekly_box_start': 'YYYY-MM-DD', 'monthly_box_start': 'YYYY-MM-DD',
                   'conflict': bool},
}
```

The dashboard's `TradeList.vue` renders `entry_signal_price` / `exit_close` as the primary Entry / Exit price columns; the algorithm-effective values surface in the hover tooltip when they differ (dotted-underline indicator).

## 9. Source Files

| File | Role |
|---|---|
| `src/strategy/scaling_strategy.py` | 1-1-2 execution + dual-timeframe sub-bar walker (`_check_exits_subbar`) |
| `src/strategy/box_strategy.py` | Production engine. Overrides entry decision; inherits leg fills, SL, TP, re-entry |
| `src/strategy/box_lookup.py` | Box directional oracle. Loads the unified W+M CSV; per-(row, level) state machine |
| `src/api/app.py` | FastAPI `/api/backtest/box` SSE endpoint; loads all three CSVs and threads them into the engine |
| `src/api/schemas.py` | Pydantic contracts. `BoxParamsModel._sl_ordering` enforces the strict SL invariants |

## 10. What's Still NOT Modelled

| Live rule | Engine handling |
|---|---|
| 15-second entry confirmation (3 candles for Entry 1, 1 for Entry 2/3) | Documented as params; not enforced. Every 4h close is treated as already confirmed. |
| Box-aware re-entry anchoring (using the firing box edge instead of `base_level`) | Not implemented; uses `base_level`. |
| Slippage and commissions | Not modelled. PnL is gross. |
| Intersected boxes (weekly ∩ monthly producing finer-grained zones) | Out of scope; single-box logic only. |

Everything else (Big-Candle vs Box conflict, dual-SL fills, dual-TP fills, sub-bar exit timing, no-fallback parameter contract, dashboard SL ordering validators) is shipped and locked by regression tests in `tests/`.
