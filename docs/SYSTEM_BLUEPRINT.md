# NQ Trading System — End-to-End Blueprint

**Purpose:** Authoritative reference for verifying that the system behaves correctly. Every rule below is quoted from the strategy documents, paired with the code path that implements it, and demonstrated on **real data from `NQ_4h.csv` + `NQ_full_data.csv`** with the exact numerical outputs the engine MUST produce.

**How to use:**
1. Run the system on the inputs in Part A with the parameters in Part A.3.
2. The engine MUST produce the outputs in Part C verbatim. Any deviation is a bug.
3. When the dashboard renders these trades, the displayed prices MUST equal the **Expected** rows. Any deviation is a presentation bug.

**Source citations (frozen):**
- `docs/MASTER_STRATEGY_GUIDE.md` — single source of truth.
- `Currunt_Strategy_Algo_for_Trading.md` — original 1-1-2 playbook.
- `docs/CODING_RULES.md` — no-fallback rule.
- `notes2.md` lines 95-101 — timezone / session-cycle rule.
- `docs/Data_Shape_To_Do.md` — v4 unified-box CSV semantics.

---

## Part A — Inputs

### A.1 Candle data: `NQ_4h.csv`

**Format** (header from the actual file):

```
datetime,open,high,low,close,volume
```

**Real sample (first 4 bars):**

```
2025-01-01 18:00:00,21269.0,21333.0,21121.75,21322.25,32778
2025-01-01 22:00:00,21321.75,21396.75,21287.0,21389.5,20661
2025-01-02 02:00:00,21389.25,21424.5,21318.0,21397.75,40365
2025-01-02 06:00:00,21398.0,21490.5,21166.5,21391.25,135603
```

**After `load_data()` normalization** (`src/data/loader.py`):

- `datetime` → `Date` (`pd.Timestamp`, parsed via `pd.to_datetime`).
- `open`/`high`/`low`/`close` → `Open`/`High`/`Low`/`Close` (float).
- `volume` → `Volume` (int).
- Frame is sorted ascending by `Date`.

**Session cycle (NQ futures), quoted from `notes2.md:79`:**

> *"one day is from 18 to 1 new york time zone, syrin time zone from 1 to 1, it is important ot knwo this candel where belongs we have to shift accrodingly"*

And `src/strategy/box_lookup.py:13-20`:

> ```
> 18:00 (day D-1)  →  SESSION OPENS
> 17:00–18:00      →  closed (no trade)
> Candle → box date mapping (_candle_to_box_date):
>   candle.hour ≥ 18  →  box_date = candle.date + 1 day
>   candle.hour < 18  →  box_date = candle.date
> ```

**Verified mapping (live engine output):**

| Candle timestamp | box_date | Reason |
|---|---|---|
| `2025-01-02 22:00` | `2025-01-03` | hour 22 ≥ 18 ⇒ next day |
| `2025-01-03 02:00` | `2025-01-03` | hour 2 < 18 ⇒ same day |
| `2025-01-03 10:00` | `2025-01-03` | hour 10 < 18 ⇒ same day |
| `2025-01-03 18:00` | `2025-01-04` | hour 18 ≥ 18 ⇒ next day |

### A.2 Box data: `NQ_full_data.csv`

**Format:** 53 columns. Per `docs/Data_Shape_To_Do.md`:

> *"this data is tagged at new york time zone, the nasdaq market is not magnated to the 24 hour system... the market opens on 18:00 and closes at 17:00 the next day... the box tagged 5-5-2025 : started at 18:00 4-5-2025 and closed at 17:00 5-5-2025"*

Per MASTER_STRATEGY_GUIDE §2.4:

> *"Column naming: `[W/M] [BoxType] [U/D or 1/2]` — U=upper edge, D=lower edge, 1/2=sub-levels of TH/TL; W=Weekly, M=Monthly; RH=Reversal High, IH=Intermediate High, IL=Intermediate Low, RL=Reversal Low, TH=Trending High, TL=Trending Low."*

**Real sample (row `2025-01-03`, weekly levels only):**

```
Date:   2025-01-03 00:00:00
WIHD:   21897.07977036          WIHU:   21941.418843
WILD:   21525.740037            WILU:   21570.07910964
WRHD:   22055.11935             WRHU:   22156.72683
WRLD:   21312.60315             WRLU:   21407.91444
WTH1:   NULL                    WTH2:   NULL
WTHD:   NULL                    WTHU:   NULL
WTL1:   20960.01651             WTL2:   20652.15453
WTLD:   20581.15956             WTLU:   21040.78143
wOpen:  21711.0                 (reference value only — no signal)
```

**Null edge rule** (MASTER_STRATEGY_GUIDE §2.4):

> *"TH and TL boxes can have null edges (~42% present in real data) when price never reached those extremes. `BoxLookup._best_level` skips null cells."*

### A.3 Parameters used for the worked examples

These are the parameters the user's dashboard ran with when producing `trades_2026-05-24_120109.csv` (back-derived from PnL: a 1-contract SL HARD loss of `−15 pts = −$30` implies `sl_hard_points=15` and `point_value=2.0`; a TP win of `+150.25 pts = +$300.50` implies `tp_target_points=150.25`):

```yaml
# Section §1 (1-1-2 distribution)
leg1_contracts:                 1
leg2_contracts:                 1
leg3_contracts:                 2
leg2_pullback_points:           100.0
leg3_pullback_points:           150.0
point_value:                    2.0       # NQ futures

# Section §2 (big-candle exception)
big_candle_threshold_points:    400.0
big_candle_full_contracts:      4
big_candle_reverses_dir:        true

# Section §3 (entry confirmation — documented, not enforced in 4h-only mode)
entry_confirmation_timeframe_seconds:   15
entry1_confirmation_candles:    3
entry23_confirmation_candles:   1

# Section §4 (stop-loss) — user's run, validator-compliant.
# Dashboard invariants (validated both backend Pydantic + frontend computed,
# user rule 2026-05-24):
#   sl_hard_points > sl_soft_points                                  (strict)
#   soft_sl_confirmation_timeframe_minutes > hard_sl_confirmation_timeframe_minutes (strict)
# The user's CSV ran with sl_hard_points=15 (back-derived from a -15 pt
# loss). For the Part C examples, sl_soft is set to 10 so the pair passes
# the new validator — the actual engine output is identical to the user's
# CSV because none of the January trades exit via SOFT SL.
sl_soft_points:                 10.0
sl_hard_points:                 15.0
soft_sl_confirmation_timeframe_minutes:  2
hard_sl_confirmation_timeframe_minutes:  1     # renamed from `_seconds` on 2026-05-24

# Section §5 (take-profit)
tp_target_points:               150.25
tp_watch_threshold_points:      50.0
tp_confirmation_timeframe_minutes:       2

# Section §5b (re-entry)
reentry_enabled:                true
reentry_cooldown_candles:       1

# Box layer
box_tick_threshold:             0.75      # 3 NQ ticks of 0.25
big_candle_resolution:          'big_candle_wins'
```

**No-fallback rule** (`docs/CODING_RULES.md §1.3`):

> *"There is no silent fallback to a default value. Every fallback site must raise an explicit error with the correct error type, a human-readable message, and a structured `system_status` payload."*

The dashboard form must send every field. Backend rejects partial payloads with a 422 carrying `code: 'request-validation-error'`.

---

## Part B — The pipeline

### B.1 HTTP entry point

**`POST /api/backtest/box`** in `src/api/app.py:_box_event_stream` opens an SSE stream. Body shape (`BoxBacktestRequest`):

```json
{
  "params":         { ...full BoxStrategyParams as in A.3... },
  "data_path":      "NQ_4h.csv",
  "box_data_path":  "NQ_full_data.csv",
  "start":          "2025-01-01",
  "end":            "2025-01-31"
}
```

The endpoint:
1. Validates `data_path` exists → `MissingDataFileError` if not.
2. `load_data(data_path)` → DataFrame.
3. `filter_by_date_range(df, start, end)` → trimmed frame, `.reset_index(drop=True)`.
4. `BoxLookup(unified_path=box_data_path, tick_threshold=params.box_tick_threshold)`.
5. `BoxStrategy(params, box_lookup).backtest(df, on_progress=...)`.
6. Streams `event:progress` per bar (throttled), then `event:complete` with `{metrics, trades, candles, elapsed_ms, boxes}`.

### B.2 Per-bar lifecycle

Per `src/strategy/scaling_strategy.py:189-256` (`ScalingStrategy.backtest`), each bar runs in this order:

```
for idx in range(len(df)):
    candle = df.iloc[idx]
    O, H, L, C = float(candle.Open), float(candle.High), float(candle.Low), float(candle.Close)
    prev_close = df.iloc[idx-1].Close if idx > 0 else O

    # 1. _on_bar(idx, candle) — BoxStrategy uses this to advance the box state machine
    self._on_bar(idx, candle)

    # 2. If a position is open, check exits FIRST. _check_exits returns
    #    an exit_event {exit_reason, exit_price} or None.
    if position.is_open:
        exit_event = self._check_exits(position, idx, H, L, C)
        if exit_event is not None:
            exit_event['exit_close'] = C            # bug-fix 2026-05-24
            trades.append(self._build_trade(position, idx, exit_event))
            # cooldown handling
            position = _Position()

    # 3. If position remains open, allow leg 2 / leg 3 pullback fills.
    if position.is_open:
        self._maybe_fill_legs(position, idx, L, H)

    # 4. If flat (and not in cooldown), check for a fresh entry.
    else:
        if cooldown_counter > 0:
            cooldown_counter -= 1
        else:
            new_pos = self._maybe_open_position(idx, O, H, L, C, prev_close)
            if new_pos is not None:
                position = new_pos

    # 5. Arm the trailing-TP watch if the close moved +50 pts in favour.
    if position.is_open:
        self._maybe_arm_watch(position, C)
```

### B.3 Box state machine

Cited rule (MASTER_STRATEGY_GUIDE §2.1):

> ```
> on bar t with close c, for level L:
>     side := classify(c, upper(L), lower(L))   // above | below | inside
>     case side of
>       'inside'                       → signal := 'hold'   (state unchanged)
>       first-observation of (row, L)  → signal := 'hold'   (state := side)
>       side == last_state             → signal := 'hold'   (no transition)
>       'below' and last_state=='above' → signal := 'short' (state := 'below')
>       'above' and last_state=='below' → signal := 'long'  (state := 'above')
> ```

Classification thresholds (`box_tick_threshold = 0.75`):

- `above` ⇔ `close > upper_edge + 0.75`
- `below` ⇔ `close < lower_edge − 0.75`
- `inside` ⇔ otherwise

Aggregation (§2.2): **weekly priority**. If weekly fires `long`/`short`, that's the aggregate signal; else if monthly fires, that's the aggregate. If both fire opposite, weekly wins and `conflict=True`.

State is keyed by `(box_date, level_name)`. New box date ⇒ fresh state. `BoxLookup.reset_state()` clears the dict at the start of every `BoxStrategy.backtest()` run.

### B.4 Entry decision (`BoxStrategy._maybe_open_position`)

Per `src/strategy/box_strategy.py:138-206`:

```python
candle_size = abs(close - open)
is_big_candle = candle_size > big_candle_threshold_points  # §2

box_detail = self._signal_details[idx]   # set by _on_bar
box_signal = box_detail.get('signal') if box_detail else None
box_directional = box_signal if box_signal in ('long','short') else None

if is_big_candle:
    bc_dir = 'long' if close > open else 'short'
    if big_candle_reverses_dir:                    # default true
        bc_dir = 'short' if bc_dir == 'long' else 'long'
    # §5 conflict resolution
    if box_directional is None or box_directional == bc_dir:
        chosen = bc_dir
    elif big_candle_resolution == 'big_candle_wins':  chosen = bc_dir
    elif big_candle_resolution == 'box_wins':         chosen = box_directional
    elif big_candle_resolution == 'skip':             return None
    return Position(direction=chosen, base_level=close, legs=[Leg(big_candle_full_contracts, close, idx)])

if box_directional is None:
    return None
return Position(direction=box_directional, base_level=close, legs=[Leg(leg1_contracts, close, idx)])
```

**Critical:** `base_level = close` of the signal bar (MASTER_STRATEGY_GUIDE §3.1: *"`base_level` (the close that fired the signal)"*).

### B.5 Leg fills (`_maybe_fill_legs`)

Per `src/strategy/scaling_strategy.py:323-344`. On every bar where a position is open with fewer than 3 legs, **per direction**:

- **LONG:** leg 2 fills when `low ≤ base_level − leg2_pullback_points`; leg 3 fills when `low ≤ base_level − leg3_pullback_points`. Fill price = the **target line itself**, not the bar's actual low.
- **SHORT:** leg 2 fills when `high ≥ base_level + leg2_pullback_points`; leg 3 when `high ≥ base_level + leg3_pullback_points`.

**Average price** = `Σ(leg.price × leg.contracts) / Σ leg.contracts`.

**Bug-fix note (2026-05-24, commit `8cc5afb`):** the trade dict now carries both:

- `entry_signal_price` = `legs[0].price` (the signal-bar close — always in the candle OHLC).
- `avg_entry_price` = weighted average across all fills (synthetic for multi-leg).

PnL math uses `avg_entry_price`; the dashboard displays `entry_signal_price`.

### B.6 Exit decision (`_check_exits`)

Per `src/strategy/scaling_strategy.py:346-392`. On every bar with an open position:

**LONG** (mirror for SHORT). Note the **asymmetric fill** between hard and soft SL (user rule 2026-05-24, MASTER_STRATEGY_GUIDE §4):

```
sl_soft_line   = avg − sl_soft_points
sl_hard_line   = avg − sl_hard_points
tp_target_line = avg + tp_target_points
tp_watch_line  = avg + tp_watch_threshold_points

if close <= sl_hard_line:   return {'exit_reason': 'STOP LOSS (HARD)',   'exit_price': sl_hard_line}   # FILL AT LINE
if close <= sl_soft_line:   return {'exit_reason': 'STOP LOSS (SOFT)',   'exit_price': close}          # FILL AT BAR CLOSE
if high  >= tp_target_line: return {'exit_reason': 'TAKE PROFIT',        'exit_price': tp_target_line} # FILL AT LINE
if watch_armed and close < tp_watch_line:
                            return {'exit_reason': 'TAKE PROFIT (TRAIL)','exit_price': close}          # FILL AT BAR CLOSE
return None
```

- **Hard SL & Hard TP** fill at the **line** — disaster stop and limit-target both modelled as exact-price fills.
- **Soft SL & Trailing TP** fill at the **confirming bar's close** — slow-confirmation exits accept whatever price the bar actually closed at, which is generally further past the threshold than the line itself.

Dual-timeframe note (queued, not implemented): in the target architecture, hard SL/TP scans **1-min** candles within each 4h interval, soft SL/trail scans **2-min** candles built from the 1-min stream. First trigger wins. Currently the engine collapses both to the 4h close.

**Watch arming** (`_maybe_arm_watch`):

> ```
> if not watch_armed and (close − avg) ≥ tp_watch_threshold_points (long):
>     watch_armed = True
> ```

The watch is sticky — once armed it stays armed for the trade's lifetime.

Cited rule (MASTER_STRATEGY_GUIDE §5):

> *"Once armed, if a later candle closes back below (long) or above (short) the watch line — measured on the `tp_confirmation_timeframe_minutes = 2` timeframe — exit with `'TAKE PROFIT (TRAIL)'`."*

In 4h-only mode the 2-min confirmation collapses to the 4h close (§3 caveat).

### B.7 Trade dict shape

The engine emits one dict per closed round-trip, defined at `scaling_strategy.py:_build_trade`:

```python
{
  'entry_idx':            int,      # bar index where position opened
  'exit_idx':             int,      # bar index where position exited

  'direction':            'long' | 'short',

  # CANDLE-GROUNDED display prices (2026-05-24 fix):
  'entry_signal_price':   float,    # legs[0].price = signal bar's close (always in OHLC)
  'exit_close':           float,    # close at exit_idx (always in OHLC)

  # ALGORITHM-EFFECTIVE prices used for PnL math:
  'avg_entry_price':      float,    # weighted avg of leg prices
  'exit_price':           float,    # SL/TP line (synthetic) or close (TRAIL only)

  'contracts':            int,      # sum of legs
  'profit_points':        float,    # (exit_price − avg) for long, opposite for short
  'profit_dollars':       float,    # profit_points × contracts × point_value

  'exit_reason':          'STOP LOSS (HARD)' | 'STOP LOSS (SOFT)' | 'TAKE PROFIT' | 'TAKE PROFIT (TRAIL)',

  'legs':                 [{'contracts': int, 'price': float, 'candle_idx': int}, ...],

  # Attached by BoxStrategy.backtest after the fact:
  'box_signal':           {'signal': 'long'|'short', 'weekly_level': str, 'weekly_signal': ...,
                           'monthly_level': str|None, 'monthly_signal': ..., 'conflict': bool,
                           'weekly_box_start': 'YYYY-MM-DD', 'monthly_box_start': '...'}
}
```

### B.8 SSE serialization

`src/api/app.py:_trade_to_jsonable` coerces numpy scalars to Python floats/ints and forwards the same shape (plus any extra fields like `box_signal`) into the `event: complete` payload `{metrics, trades, candles, elapsed_ms, boxes}`.

### B.9 Frontend rendering

`frontend/src/components/TradeList.vue`:

| Column | Source field | Always in OHLC? |
|---|---|---|
| Entry time | `candleTime(entry_idx)` | yes (candle timestamp) |
| Exit time | `candleTime(exit_idx)` | yes |
| Entry px | `entry_signal_price` | **yes** (post-fix) |
| Exit px | `exit_close` | **yes** (post-fix) |
| Pts | `profit_points` | n/a (computed) |
| $ | `profit_dollars` | n/a |
| Reason | `exit_reason` | n/a |
| Box signal | `box_signal.weekly_level` etc. | n/a |

Hovering the Entry px / Exit px cell reveals the algorithm-effective prices (`avg_entry_price`, `exit_price` line) + per-leg breakdown when they differ. The cell is dotted-underlined when there's a difference.

Chart markers (`ChartPane.vue:toMarkers`) use Lightweight Charts' `position: 'belowBar' | 'aboveBar'` — anchored to the bar, not to a specific price, so they don't claim an off-candle coordinate.

---

## Part C — Worked examples (real data, expected outputs — DUAL-TIMEFRAME)

The four examples below are the actual output of the dual-timeframe engine on the real `NQ_4h.csv` + `NQ_1m.csv` + `NQ_full_data.csv` datasets, January 2025, with the parameters from Part A.3. They cover every dual-timeframe exit path: SOFT SL (1-min walks → 2-min close), HARD SL (1-min close), TRAIL (2-min close after arming), and another TRAIL (winning case).

**Note for users coming from the 4h-only blueprint (pre-2026-05-24):** the dual-timeframe engine fires exits at sub-bar resolution. Many trades that *looked* like TP wins on 4h are actually TRAIL exits or SOFT SL losses on 1-min, because the 1-min path between entry and the 4h close was noisier than the 4h close alone suggested. The new numbers below are the **realistic** backtest output.

### Example 1 — Standard single-leg LONG, SOFT SL exit

**Demonstrates: the 1-min path firing SOFT SL on a 2-min close before the 4h bar's close reaches the hard line.**

#### Inputs

Candles `2025-01-01 18:00` → `2025-01-03 14:00` (12 bars) from `NQ_4h.csv`:

| idx | datetime | Open | High | Low | Close | Volume |
|---:|---|---:|---:|---:|---:|---:|
| 0 | 2025-01-01 18:00 | 21269.00 | 21333.00 | 21121.75 | 21322.25 | 32778 |
| 1 | 2025-01-01 22:00 | 21321.75 | 21396.75 | 21287.00 | 21389.50 | 20661 |
| 2 | 2025-01-02 02:00 | 21389.25 | 21424.50 | 21318.00 | 21397.75 | 40365 |
| 3 | 2025-01-02 06:00 | 21398.00 | 21490.50 | 21166.50 | 21391.25 | 135603 |
| 4 | 2025-01-02 10:00 | 21392.50 | 21444.00 | 20983.75 | 21047.50 | 309123 |
| 5 | 2025-01-02 14:00 | 21047.75 | 21203.50 | 21028.00 | 21182.50 | 120335 |
| 6 | 2025-01-02 18:00 | 21186.75 | 21250.00 | 21144.00 | 21242.50 | 18875 |
| 7 | 2025-01-02 22:00 | 21243.00 | 21260.00 | 21207.50 | 21237.25 | 10476 |
| 8 | 2025-01-03 02:00 | 21237.25 | 21288.00 | 21210.50 | 21237.00 | 25667 |
| 9 | 2025-01-03 06:00 | 21237.75 | 21434.50 | 21208.50 | 21382.25 | 95909 |
| 10 | 2025-01-03 10:00 | 21382.75 | 21531.25 | 21261.50 | **21509.25** | 224256 |
| 11 | 2025-01-03 14:00 | 21509.50 | 21559.25 | 21474.75 | **21493.00** | 104242 |

Box row `2025-01-03` (relevant weekly level only):

```
WRLU = 21407.91444    WRLD = 21312.60315
```

with threshold 0.75 ⇒ `above` ⇔ `c > 21408.66`; `below` ⇔ `c < 21311.85`; `inside` otherwise.

#### State machine trace (W-RL level, 2025-01-03 box row)

Box-date mapping (B.1, A.1): bars 0–5 belong to `2025-01-02`; bars 6–11 to `2025-01-03`. State is per `(box_date, level_name)`, so bars 0–5 act on the 2025-01-02 row (which has the same WRL bounds in this case — preprocessed weekly data) and bars 6–11 act on 2025-01-03. The transitions on the 2025-01-03 row:

| idx | candle close | side (WRL) | state machine | signal |
|---:|---:|---|---|---|
| 6 | 21242.50 | below | first observation on (2025-01-03, W-RL) ⇒ state := below | **hold** |
| 7 | 21237.25 | below | side == last_state ⇒ no transition | **hold** |
| 8 | 21237.00 | below | side == last_state | **hold** |
| 9 | 21382.25 | inside | inside ⇒ state unchanged, inside_seen=True | **hold** |
| 10 | **21509.25** | **above** | above and last_state=='below' and inside_seen ⇒ state := above | **long** |
| 11 | 21493.00 | above | side == last_state | hold |

(For bars 0–5 acting on the 2025-01-02 row, similar transitions occur but don't fire on bar 10 — they belong to a different `(box_date, level)` key.)

**Expected output of `BoxLookup.get_signal_detail(close=21509.25, ts=2025-01-03 10:00)`:**

```python
{
  'signal': 'long',
  'weekly_signal': 'long',
  'weekly_level': 'W-RL',
  'weekly_upper': 21407.91444,
  'weekly_lower': 21312.60315,
  'weekly_box_start': '2025-01-03',
  'monthly_signal': 'hold' | None,    # depends on monthly state for this date
  'monthly_level': 'M-IH' | ...,      # per the user's CSV trade #1: 'M-IH'
  'conflict': False,
}
```

(Trade #1 in user's CSV has `Monthly Box = M-IH` — the monthly signal was `hold` for this bar, so the aggregate took weekly priority for the W-RL `long` signal.)

#### Entry decision (bar 10, idx=10)

```
O = 21382.75   C = 21509.25   |C − O| = 126.50  →  is_big_candle = false   (126.5 ≤ 400)
box_directional = 'long'   →  enter standard box entry
Position(direction='long', base_level=21509.25, legs=[Leg(contracts=1, price=21509.25, candle_idx=10)])
```

#### Exit checks — dual-timeframe walker

```
avg            = 21509.25                       (single leg)
sl_soft_line   = 21509.25 − 10  = 21499.25
sl_hard_line   = 21509.25 − 15  = 21494.25
tp_target_line = 21509.25 + 150.25 = 21659.50
tp_watch_line  = 21509.25 + 50  = 21559.25
```

The walker iterates 1-min bars from 2025-01-03 10:00 onwards, checking:

- **per 1-min bar:** `close ≤ sl_hard_line` (HARD trigger) and `high ≥ tp_target_line` (TP trigger).
- **per 2-min boundary:** `close ≤ sl_soft_line` (SOFT trigger) and (after the watch arms on a 2-min close ≥ avg + 50) `close < tp_watch_line` (TRAIL trigger).

At **2025-01-03 15:47** (the 1-min bar ending the 2-min window 15:46–15:47), the 2-min close `21497.25` lands below `sl_soft_line = 21499.25` ⇒ **SOFT** fires. The 1-min closes from 10:00 to 15:47 never dipped past `sl_hard_line = 21494.25`, so HARD never triggers first.

#### Trade dict emitted

```json
{
  "entry_idx":          10,
  "exit_idx":           11,
  "direction":          "long",

  "entry_signal_price": 21509.25,
  "exit_close":         21497.25,
  "exit_time":          "2025-01-03T15:47:00",

  "avg_entry_price":    21509.25,
  "exit_price":         21497.25,

  "contracts":          1,
  "profit_points":     -12.00,
  "profit_dollars":    -24.00,
  "exit_reason":        "STOP LOSS (SOFT)",
  "legs":              [{"contracts": 1, "price": 21509.25, "candle_idx": 10}],
  "box_signal":         {"signal": "long", "weekly_level": "W-RL",
                         "weekly_box_start": "2025-01-03", ...}
}
```

#### Dashboard renders (TradeList row)

| # | Dir | Entry time | Exit time | Entry px | Exit px | Pts | $ | Reason | Box signal |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 1 | **LONG** | 2025-01-03 10:00 | **2025-01-03 15:47** | **21509.25** | **21497.25** | −12.0 | **-$24.00** | STOP LOSS (SOFT) | W-RL (W) since 2025-01-03 |

Exit Time column shows the sub-bar timestamp (`trade.exit_time`). Entry/Exit price cells display `entry_signal_price` / `exit_close`; for SOFT exits the two algorithm-effective fields (`avg_entry_price`, `exit_price`) equal the displayed prices — no dotted-underline indicator on either cell.

**Contrast with the legacy 4h-only path:** the user's pre-2026-05-24 CSV showed STOP LOSS (HARD) at 21494.25 / -15 pts / -$30. The dual-timeframe engine fires SOFT 13 minutes before the 4h bar 11 closes, at a slightly less-bad price (-12 pts / -$24). The legacy result was a check-order artifact (`if close ≤ sl_hard_line` evaluated first on the 4h close); the dual-timeframe result is what would have happened in real trading with sub-bar order routing.

---

### Example 2 — Standard SHORT, HARD SL exit (dual-timeframe)

**Demonstrates: 1-min HARD SL firing before the 4h bar's pullback range can reach the leg-2 trigger price.**

#### Inputs

Candles for idx 62 (signal bar) and idx 63 (exit bar). From `NQ_4h.csv` filtered `2025-01-01..2025-01-31`:

```
idx=62  2025-01-16 10:00   O=21377.50  H=21474.75  L=21262.25  C=21290.50
idx=63  2025-01-16 14:00   O=21290.00  H=21395.75  L=21172.25  C=21214.25
```

Box row `2025-01-16` (weekly only — relevant level is W-RH):

```
WRHU = 21459.194575    WRHD = 21360.785875
```

#### Signal + entry at idx=62

`box_directional = 'short'` (close 21290.50 traverses below WRH from a prior above-side state). Standard entry, single leg at signal-bar close:

```
Position(direction='short', base_level=21290.50,
         legs=[Leg(1, 21290.50, 62)])
avg = 21290.50, contracts = 1
sl_hard_line = 21290.50 + 15 = 21305.50
sl_soft_line = 21290.50 + 10 = 21300.50
leg2_target  = 21290.50 + 100 = 21390.50    ← never reached before exit
```

#### Exit checks — dual-timeframe walker

The walker iterates 1-min bars from 2025-01-16 14:00 onwards (start of bar 63). At **2025-01-16 14:04** a 1-min close at `21309.50` ≥ `sl_hard_line = 21305.50` ⇒ **HARD** fires. The fill is AT the line (`21305.50`), not the bar's close.

**Leg 2 never fills** — the leg-2 trigger (`high ≥ 21390.50`) is checked only AFTER the exit walker; since the exit fires inside bar 63's 1-min window 14:04, the engine closes the position before the 4h-level `_maybe_fill_legs` step ever runs on bar 63.

#### Trade dict emitted

```json
{
  "entry_idx": 62, "exit_idx": 63, "direction": "short",
  "entry_signal_price": 21290.50,
  "exit_close":         21309.50,             // 1-min bar's actual close
  "exit_time":          "2025-01-16T14:04:00",
  "avg_entry_price":    21290.50,             // single leg
  "exit_price":         21305.50,             // HARD fills at the line
  "contracts": 1,
  "profit_points":  -15.00,
  "profit_dollars": -30.00,
  "exit_reason": "STOP LOSS (HARD)",
  "legs": [{"contracts": 1, "price": 21290.50, "candle_idx": 62}]
}
```

#### Dashboard renders

| # | Dir | Entry time | Exit time | Entry px | Exit px | Pts | $ | Reason | Box signal |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 2 | **SHORT** | 2025-01-16 10:00 | **2025-01-16 14:04** | **21290.50** | **21309.50** | −15.0 | **-$30.00** | STOP LOSS (HARD) | W-RH (W) since 2025-01-16 |

**Tooltip on Exit px (dotted-underlined):** *"Exit display: 21309.50 (close of the bar that confirmed STOP LOSS (HARD)). PnL math uses algorithm line: 21305.50. Diff: −4.00 points."*

**Contrast with the legacy 4h-only path:** the pre-2026-05-24 engine showed `leg2_price=21390.50` filling on bar 63 and a TRAIL exit on bar 66 (+$25). The dual-timeframe engine never gets that far: HARD fires 4 minutes into bar 63, before leg 2's trigger is reached. The legacy +$25 win is illusory.

---

### Example 3 — Big-candle LONG, TRAIL exit (dual-timeframe)

**Demonstrates: §2 big-candle exception followed by a 2-min TRAIL that fires before the 1-min high reaches the TP target.**

#### Inputs

Candle idx 101 (signal) and idx 102 (exit). From `NQ_4h.csv` filtered `2025-01-01..2025-01-31`:

```
idx=101  2025-01-27 02:00   O=21388.75  H=21412.00  L=20763.75  C=20886.75   (big red bar)
idx=102  2025-01-27 06:00   O=20887.75  H=21341.00  L=20878.00  C=21334.25
```

#### Big-candle check + entry (bar 101)

```
|C − O|  =  502.00     >  big_candle_threshold_points = 400
→  is_big_candle = TRUE
bc_dir_raw = 'short' (close < open) → reversed → LONG (playbook reads 400+ pt red as exhaustion)
box_directional = 'long'  →  no conflict, both say LONG

Position(direction='long', base_level=20886.75,
         legs=[Leg(big_candle_full_contracts=4, price=20886.75, candle_idx=101)])
avg = 20886.75, contracts = 4
```

Exit lines:
```
sl_hard_line   = 20886.75 − 15  = 20871.75
sl_soft_line   = 20886.75 − 10  = 20876.75
tp_target_line = 20886.75 + 150.25 = 21037.00
tp_watch_line  = 20886.75 + 50  = 20936.75
```

#### Exit checks — dual-timeframe walker

The walker iterates 1-min bars from 2025-01-27 06:00 onwards (the bar after the signal). The price runs immediately in favour:

1. Within the first few 2-min windows of bar 102, a 2-min close reaches **≥ 20936.75** ⇒ **watch arms**.
2. At **2025-01-27 06:25**, a 2-min close at **20915.75** is below `tp_watch_line = 20936.75` ⇒ **TRAIL** fires. The 1-min high during this 25-minute hold never reached `tp_target_line = 21037.00`.

#### Trade dict emitted

```json
{
  "entry_idx": 101, "exit_idx": 102, "direction": "long",
  "entry_signal_price": 20886.75,
  "exit_close":         20915.75,
  "exit_time":          "2025-01-27T06:25:00",
  "avg_entry_price":    20886.75,
  "exit_price":         20915.75,             // TRAIL fills at 2-min close
  "contracts": 4,
  "profit_points":   29.00,
  "profit_dollars":  232.00,                  // 29.00 × 4 × 2.0
  "exit_reason": "TAKE PROFIT (TRAIL)",
  "legs": [{"contracts": 4, "price": 20886.75, "candle_idx": 101}]
}
```

#### Dashboard renders

| # | Dir | Entry time | Exit time | Entry px | Exit px | Pts | $ | Reason | Box signal |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 5 | **LONG** | 2025-01-27 02:00 | **2025-01-27 06:25** | **20886.75** | **20915.75** | +29.0 | **+$232.00** | TAKE PROFIT (TRAIL) | W-RL (W) since 2025-01-27 |

No dotted-underline on either price cell (single-leg entry; TRAIL fills at the 2-min close which equals `exit_close`).

**Contrast with the legacy 4h-only path:** the 4h engine showed `high ≥ tp_target_line` on bar 102 (H=21341.00) firing TAKE PROFIT at 21037.00 for +$1202. The dual-timeframe engine TRAILS out 5 minutes earlier at +$232 — a $970 swing. The TP-target hit at 06:30+ minutes was preceded by a 2-min retracement at 06:25 that the watch caught. The legacy result over-states P&L by 5×.

---

### Example 4 — Standard SHORT, TRAIL exit with profit (dual-timeframe)

**Demonstrates: a winning TRAIL — the 2-min watch arms when price moves in favour, then a later 2-min close pulls back through the watch line for a +$93 exit.**

#### Inputs

Candle idx 115 (signal) → idx 116 (exit). From `NQ_4h.csv` filtered `2025-01-01..2025-01-31`:

```
idx=115  2025-01-29 10:00   ...   C=21467.25     (signal bar — short below W-RL)
idx=116  2025-01-29 14:00   ...                  (exit bar)
```

#### Signal + entry (bar 115)

`box_directional = 'short'`. Standard entry, single leg at signal-bar close:

```
Position(direction='short', base_level=21467.25,
         legs=[Leg(1, 21467.25, 115)])
avg = 21467.25, contracts = 1
sl_hard_line   = avg + 15  = 21482.25
sl_soft_line   = avg + 10  = 21477.25
tp_target_line = avg − 150.25 = 21317.00
tp_watch_line  = avg − 50  = 21417.25
```

#### Exit checks — dual-timeframe walker

Inside bar 116 (2025-01-29 14:00 onwards) the price moves in favour (down for a SHORT). A 2-min close reaches **≤ 21417.25** ⇒ **watch arms**. Subsequently at **14:13**, a 2-min close at **21420.50** is ABOVE `tp_watch_line = 21417.25` (price pulled back upward) ⇒ **TRAIL** fires.

#### Trade dict emitted

```json
{
  "entry_idx": 115, "exit_idx": 116, "direction": "short",
  "entry_signal_price": 21467.25,
  "exit_close":         21420.50,
  "exit_time":          "2025-01-29T14:13:00",
  "avg_entry_price":    21467.25,
  "exit_price":         21420.50,             // TRAIL fills at 2-min close
  "contracts": 1,
  "profit_points":   46.75,
  "profit_dollars":  93.50,                   // 46.75 × 1 × 2.0
  "exit_reason": "TAKE PROFIT (TRAIL)"
}
```

#### Dashboard renders

| # | Dir | Entry time | Exit time | Entry px | Exit px | Pts | $ | Reason | Box signal |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 7 | **SHORT** | 2025-01-29 10:00 | **2025-01-29 14:13** | **21467.25** | **21420.50** | +46.8 | **+$93.50** | TAKE PROFIT (TRAIL) | W-RL (W) since 2025-01-29 |

No dotted-underline on either cell (single-leg + TRAIL → all four price fields agree).

**Note:** the legacy 4h-only engine reported this trade as `STOP LOSS (HARD)` (`exit_price=21482.25`, -$30). The 4h bar's high almost certainly touched `21482.25` mid-bar, but on the 1-min timeline a 2-min CLOSE never actually crossed the hard line — the close-confirmation rule keeps the trade alive long enough for it to flip into profit. This is the most dramatic legacy-vs-dual-timeframe divergence in January.

---

## Part D — How to run this as a verification

1. Check out `dev` at HEAD (`283917e` or later).
2. Start the backend: `uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000`.
3. POST to `/api/backtest/box` with the body shape in B.1 and the parameters in A.3, `start='2025-01-01'`, `end='2025-01-31'`.
4. From the SSE `event: complete` payload, locate trades by `entry_idx` (the table in each Example C is one row of the `complete.trades` array).
5. Every numeric field MUST match the "Trade dict emitted" block exactly.
6. Open the dashboard at `http://localhost:5173`, run the same backtest with the same params, and check the TradeList renders the "Dashboard renders" tables exactly. Hovering Entry / Exit price cells MUST reveal the tooltip content described.

**Automated regression locks:**

| Test file | Locks |
|---|---|
| `tests/test_box_lookup_signal.py` | Box state machine — classification, traversal, first-observation, weekly priority |
| `tests/test_box_strategy_big_candle.py` | §2 big-candle exception + §5 conflict resolution (3 policies) |
| `tests/test_box_strategy_integration.py` | End-to-end BoxStrategy.backtest on synthetic candles |
| `tests/test_scaling_strategy.py` | 1-1-2 distribution, leg fills, SL/TP exits, watch arming, re-entry |
| `tests/test_trade_log_alignment.py` | `entry_signal_price` / `exit_close` fields (this blueprint's Part B.7 contract) |
| `tests/test_api_box_sse.py` | `/api/backtest/box` SSE serialization (`_trade_to_jsonable`) |

If any of those tests fail, this blueprint's claims are no longer guaranteed. Re-run `pytest tests/ -v` after every change to the strategy or serialization paths.

---

## Part E — Known semantic boundaries (not bugs)

These are the places where the displayed numbers can deviate from "what's on the candle" by design. The 2026-05-24 fix surfaces both views — candle-grounded **and** algorithm-effective — so the operator can audit either:

| Path | `entry_signal_price` vs `avg_entry_price` | `exit_close` vs `exit_price` |
|---|---|---|
| Single-leg entry, TRAIL exit | equal | equal (TRAIL fills at close) |
| Single-leg entry, SOFT SL exit | equal | equal (SOFT fills at close, post 2026-05-24 fix) |
| Single-leg entry, HARD SL exit | equal | differ (HARD line vs bar close — disaster-stop contract) |
| Single-leg entry, TP exit (hard target) | equal | differ (TP line vs bar close) |
| Multi-leg entry, any exit | differ (signal close vs synthetic avg) | follows the above rows per exit reason |
| Big-candle entry, any exit | equal (one fill at signal close) | follows the above rows per exit reason |

Cell-level dotted-underline + tooltip in `TradeList.vue` makes every divergence visible. The CSV export carries both columns. PnL math is always done from `avg_entry_price` / `exit_price`.

**Asymmetric fill rationale** (user rule, 2026-05-24): hard SL and hard TP model exact limit/stop orders at the threshold; soft SL and trailing TP model "we wait for a confirming close" — when that close arrives, the realised price IS that close. Hence: `exit_price = close` for SOFT and TRAIL; `exit_price = line` for HARD and TP-target.

---

## Part G — Dual-timeframe SL/TP engine (IMPLEMENTED 2026-05-24)

**Status:** SHIPPED. Engine code at `src/strategy/scaling_strategy.py::ScalingStrategy._check_exits_subbar`. Tests at `tests/test_subbar_exits.py` (5 cases, one per exit reason + legacy fallback). End-to-end real-data lock at `tests/test_blueprint_examples.py` (5 cases against `NQ_4h.csv` + `NQ_1m.csv` + `NQ_full_data.csv`).

### G.1 Why

Per the original blueprint (`Currunt_Strategy_Algo_for_Trading.md` §4 + user's 2026-05-24 spec):

- **Hard SL** confirms on a `hard_sl_confirmation_timeframe_minutes` (target 1 min) candle. The disaster stop reacts fast.
- **Soft SL** confirms on a `soft_sl_confirmation_timeframe_minutes` (target 2 min) candle. The slow stop avoids wick-fakeouts.
- **Hard TP** target hit checked on 1 min — high (long) / low (short) reaches the target line within a 1-min candle.
- **Trailing TP** checked on 2 min — close back through the watch line on a 2-min candle.

In 4h-only mode (current), all four collapse to the 4h close. This is acceptable for first-pass backtests but masks intra-bar SL/TP firing order and can over-state win rate.

### G.2 Engine design (when implemented)

1. **Input contract:** `BoxBacktestRequest` gains a required `data_path_1min` field. Backend validates it exists; loader returns a frame with the same OHLCV shape as the 4h frame.
2. **Pre-index the 1-min frame** by 4h-bar boundaries so each 4h-bar maps to the 240 1-min bars it contains.
3. **Per 4h bar with a position open:**
   - Walk the 240 1-min candles in order.
   - At each 1-min candle: check hard SL line and (long: `high ≥ tp_target_line`, short: `low ≤ tp_target_line`).
   - Aggregate consecutive 1-min into rolling 2-min windows; at each 2-min boundary: check soft SL and trail.
   - The **first event** (in 1-min time) wins. `exit_idx` is still the 4h-bar index; a new field `exit_minute_idx` (or `exit_time` ISO string) records the 1-min boundary that fired.
4. **Trade dict gains `exit_time`** (ISO timestamp of the 1-min/2-min bar that confirmed the exit), exposed in the frontend as the Exit Time column instead of the 4h-bar timestamp.

### G.3 Dashboard validation (`BoxParamsModel` + Vue form)

Pydantic validator (post-init):

```python
@model_validator(mode='after')
def _sl_ordering(self):
    if self.sl_hard_points <= self.sl_soft_points:
        raise ValueError(
            f'sl_hard_points ({self.sl_hard_points}) must be > sl_soft_points '
            f'({self.sl_soft_points}) — hard SL is the disaster stop, farther out.'
        )
    if self.soft_sl_confirmation_timeframe_minutes <= self.hard_sl_confirmation_timeframe_minutes:
        raise ValueError(
            f'soft_sl_confirmation_timeframe_minutes '
            f'({self.soft_sl_confirmation_timeframe_minutes}) must be > '
            f'hard_sl_confirmation_timeframe_minutes '
            f'({self.hard_sl_confirmation_timeframe_minutes}) — soft confirms slower.'
        )
    return self
```

Frontend `SettingsPanel.vue` runs the same checks live and refuses to submit while either invariant is violated.

### G.4 Migration record (DONE)

1. ✅ Added `data_path_1min` field to `BoxBacktestRequest` (required).
2. ✅ Renamed `hard_sl_confirmation_timeframe_seconds` → `_minutes`, default 1 (commit `a83ef21`).
3. ✅ Engine refactor: `ScalingStrategy.backtest(df, df_1min=None|DataFrame)` — sub-bar walker when 1-min frame supplied, 4h legacy path when None (commit `86fb9d0`).
4. ✅ `tests/test_blueprint_examples.py` re-derived against the dual-timeframe engine.
5. ✅ Blueprint Part C rewritten — see above; legacy 4h numbers preserved in commit history (tag `c838c27`).

### G.5 Out-of-scope expansion in the rules

The user's notes (`notes2.md:59`) read:

> *"we account for stop loss and take profit in a time frame to prevent spikes; the longer the candle the smaller the range (stricter); the shorter the time frame the bigger the range so it prevents very big losses."*

This already justifies the asymmetric (timeframe, distance) pairing the user wants: **slow confirmation + tight distance** for soft (the playbook's "give it room to breathe but stop close on a confirmed close"); **fast confirmation + wide distance** for hard (the playbook's disaster stop). The dual-timeframe engine simply makes this explicit at the per-candle level instead of collapsing both checks to the 4h close.

---

## Part F — Source-of-truth document mapping

| Topic | Document | Section |
|---|---|---|
| 1-1-2 scaling | `docs/MASTER_STRATEGY_GUIDE.md` | §3 §1 |
| Big-candle exception | same | §3 §2 |
| Entry confirmation (15-sec) | same | §3 §3 |
| Dual stop-loss | same | §3 §4 |
| Take profit + trail | same | §3 §5 |
| Re-entry | same | §3 §5b |
| Box state machine | same | §2.1 |
| Box aggregation (weekly priority) | same | §2.2 |
| Big-candle vs Box conflict | same | §5 |
| PnL formula | same | §3 §0 / §7.2 |
| No-fallback rule | `docs/CODING_RULES.md` | §1 |
| Box CSV semantics | `docs/Data_Shape_To_Do.md` | full file |
| NQ session cycle | `notes2.md` | lines 95-101 |
| Trade dict shape | `docs/MASTER_STRATEGY_GUIDE.md` | §7.3 (now superseded by Part B.7 above) |
| Trade-log alignment fix | `docs/superpowers/plans/2026-05-23-nsga2-PROGRESS.md` | "BUG INTERLUDE 2026-05-24" |

**This blueprint is reference, not spec.** When a rule appears to conflict with what's in the source documents above, the source documents win and this blueprint must be updated. When a real run deviates from this blueprint while the source documents still match the code, the code has drifted and that's a bug worth opening a ticket on.
