# Box Strategy — TradingView Box System

## Confirmed Facts

| # | Fact | Value |
|---|------|-------|
| 1 | Date shift (one-time preprocessing) | −2 calendar days |
| 2 | NQ tick size | 0.25 points → 3 ticks = **0.75 points** |
| 3 | Box validation | **Both** weekly AND monthly must confirm same direction |
| 4 | TH1/TH2, TL1/TL2 | Sub-edges within TH/TL box → generate their own signals |
| 5 | wOpen / mOpen | Opening price reference only — no signal role |
| 6 | Primary timeframe | 4h candles (same as current ScalingStrategy) |
| 7 | Entry execution | Open of next 4h candle after signal closes |

---

## Box Data Files

| File | Rows | Window | Columns |
|------|------|--------|---------|
| `NQ_week_data.csv` | 73 | 7 days | WRHU/D, WIHU/D, WILU/D, WRLU/D, WTHU/D, WTH1/2, WTLU/D, WTL1/2, wOpen |
| `NQ_month_data.csv` | 17 | 30 days | MRHU/D, MIHU/D, MILU/D, MRLU/D, MTHU/D, MTH1/2, MTLU/D, MTL1/2, mOpen |

---

## Column Naming System

```
[W/M]  [BoxType]  [U/D or 1/2]
  │       │            │
  │       │            └─ U = upper edge, D = lower edge
  │       │               1/2 = internal sub-levels of TH/TL
  │       └── RH = Reversal High
  │           IH = Intermediate High
  │           IL = Intermediate Low
  │           RL = Reversal Low
  │           TH = Trending High (extreme, ~42% present)
  │           TL = Trending Low  (extreme, ~42% present)
  └── W = Weekly, M = Monthly
```

---

## Box Price Hierarchy (high → low)

```
    [ WTHU / WTH1 / WTH2 / WTHD ]   ← Trending High (null when price never extreme)
         WRHU ────────── WRHD        ← Reversal High
         WIHU ────────── WIHD        ← Intermediate High
         ─────── wOpen ──────        ← Reference only (no signal)
         WILU ────────── WILD        ← Intermediate Low
         WRLU ────────── WRLD        ← Reversal Low
    [ WTLU / WTL1 / WTL2 / WTLD ]   ← Trending Low  (null when price never extreme)
```

---

## Signal Logic — Traversal (v3.1+, 2026-05-23 onward)

### For each 4h candle close:

1. **Find active weekly box** — the weekly row where `date_shifted ≤ candle_date < date_shifted + 7 days`
2. **Find active monthly box** — the monthly row where `date_shifted ≤ candle_date < date_shifted + 30 days`
3. **For each box level**, classify the close relative to the box edges:
   - `close > upper_edge + 0.75` → **above**
   - `close < lower_edge − 0.75` → **below**
   - otherwise                   → **inside**
4. **Per-level state machine** keyed by `(box_row_id, level_name)` tracks the last `above`/`below` observation. A signal fires only when the classification **transitions** from one side to the opposite side. Same-side repeats and inside-box bars return `hold`.

```text
states: { 'above', 'below', None }   # None = haven't observed this (row, level) yet

on each bar t with close c:
  c_side = classify(c, upper(row, level), lower(row, level))

  if c_side == 'inside':
    signal := 'hold'                 # transient — do not change state
  elif state is None:
    state := c_side                  # first observation — record only
    signal := 'hold'
  elif state == c_side:
    signal := 'hold'                 # same side, no transition
  else:                              # opposite-side transition
    signal := 'short' if state == 'above' else 'long'
    state := c_side
```

Going **down through the box** (`above → below`) → **SHORT**.
Going **up through the box** (`below → above`) → **LONG**.
Entering the box and exiting back the same side → **HOLD** (state never changed).

### Aggregating weekly + monthly:

- Per box (weekly / monthly) we evaluate every level and pick the closest one to the close as the **active level** for that side.
- The aggregate signal uses **weekly priority**: if the weekly side fires `long`/`short`, use it; otherwise use the monthly side.
- `conflict = True` when weekly and monthly fire opposite directions on the same bar.
- If one side has no active box row → that side reports `None` (distinct from `'hold'`).
- The aggregate signal is `'long'`, `'short'`, or `'hold'` when at least one side has an active row — never `None` unless both sides have no box.

### Three states (the headline change):

| Aggregate signal | Meaning | Action taken |
|---|---|---|
| `'long'`  | Close traversed the box bottom-to-top this bar | Open a long position |
| `'short'` | Close traversed the box top-to-bottom this bar | Open a short position |
| `'hold'`  | At least one side has an active box but no traversal fired | Do nothing |
| `None`    | Neither weekly nor monthly has an active row | Do nothing (data gap) |

### Entry:
- Signal confirmed at close of 4h candle
- Enter at **open of next 4h candle**
- Same 1-1-2 scaling mechanics as current ScalingStrategy

---

## Signal Logic — Legacy (pre-v3.1, ≤ 2026-05-23) — FROZEN

> The rule below was the active behaviour before the traversal rewrite. Kept for historical context; do not use as a reference for current implementation.

For each 4h candle close:
- `close > upper_edge + 0.75` → **LONG** signal for that box
- `close < lower_edge − 0.75` → **SHORT** signal for that box
- Otherwise → HOLD

Validation rule (single-box, weekly priority): signal fires as soon as **one** box level produces a direction signal. Weekly takes priority over monthly. No state machine; every bar past the edge re-fires.

Earlier still (pre-2026-05-23): the rule required weekly AND monthly to agree before firing. That was abandoned in favour of single-box firing.

---

## Pre-processing (One-Time)

Script: `scripts/preprocess_boxes.py`

- Load `NQ_week_data.csv` and `NQ_month_data.csv`
- Subtract 2 calendar days from `Date` column
- Save as `NQ_week_data_shifted.csv` and `NQ_month_data_shifted.csv`
- **Run once; commit results; never re-run**

---

## Box Level Priority for Entry

When multiple box levels fire simultaneously, use the **closest box** to the current price (the one the price just broke through). Ties broken by the more conservative level (lower box for longs, higher box for shorts).

---

## Implementation Plan

See task list. Components:

1. `scripts/preprocess_boxes.py` — one-time date shift
2. `src/strategy/box_lookup.py` — BoxLookup class (date → active box levels)
3. `src/strategy/box_strategy.py` — BoxStrategy (extends ScalingStrategy, replaces signal detection)
4. `src/api/schemas.py` — BoxBacktestRequest schema
5. `src/api/app.py` — `/api/backtest/box` SSE endpoint
6. `frontend/src/types.ts` — TypeScript types
7. `frontend/src/stores/` — settings + backtest stores for box mode
8. `frontend/src/components/SettingsPanel.vue` — box file pickers + strategy selector

---

## Out of Scope (Later Iterations)

- Intersected box signals
- Daily (D-prefix) boxes — no daily CSV provided yet
- Average retracement / breakeven stop management
- Multi-timeframe tick confirmation (1-min tick check for 15-min candles)
