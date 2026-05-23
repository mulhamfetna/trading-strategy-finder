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

## Signal Logic

### For each 4h candle close:

1. **Find active weekly box** — the weekly row where `date_shifted ≤ candle_date < date_shifted + 7 days`
2. **Find active monthly box** — the monthly row where `date_shifted ≤ candle_date < date_shifted + 30 days`
3. **For each box level** (checking individual boxes, not intersections):
   - `close > upper_edge + 0.75` → **LONG** signal for that box
   - `close < lower_edge − 0.75` → **SHORT** signal for that box
   - Otherwise → HOLD for that box

### Validation rule (current — single-box, weekly priority):
- Signal fires as soon as **one** box level produces a direction signal — we do **not** require weekly and monthly to agree.
- Weekly takes priority: if the weekly side fires `long`/`short`, we trade that direction; only if the weekly side is silent does the monthly side fire.
- If one box is null (TH/TL not present) → that side simply abstains.
- Intersected boxes are **not** counted in this iteration.

> **History:** The legacy rule (≤ 2026-05-23) required weekly AND monthly to agree before firing. That rule was abandoned in favour of single-box firing so the strategy reacts as soon as price crosses any tracked level. The active implementation in `src/strategy/box_lookup.py:get_signal` matches the single-box rule above.

### Entry:
- Signal confirmed at close of 4h candle
- Enter at **open of next 4h candle**
- Same 1-1-2 scaling mechanics as current ScalingStrategy

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
