# Data Format v4 — Unified Box CSV (2026-05-24)

## Summary

Replaced two separate preprocessed CSVs (`NQ_week_data_shifted.csv`, `NQ_month_data_shifted.csv`)
with a single unified file: **`NQ_full_data.csv`**.

---

## File: NQ_full_data.csv

| Property | Value |
|----------|-------|
| Rows | ~363 trading days (2025-01-01 → present) |
| Columns | 53 raw; 36 loaded (D* and Scraped_At dropped at parse time) |
| Key | `Date` — the closing day of each NQ market session |

### Columns loaded (36 total)

**Metadata:** `Date`

**Weekly box levels (16):**

| Column | Meaning |
|--------|---------|
| `WIHD`, `WIHU` | Weekly Inside HIGH zone — lower / upper edge |
| `WILD`, `WILU` | Weekly Inside LOW zone — lower / upper edge |
| `WRHD`, `WRHU` | Weekly Range HIGH zone — lower / upper edge |
| `WRLD`, `WRLU` | Weekly Range LOW zone — lower / upper edge |
| `WTHD`, `WTHU` | Weekly Target HIGH band — lower / upper edge *(sparse)* |
| `WTH1`, `WTH2` | Weekly Target HIGH — individual levels 1 & 2 *(sparse)* |
| `WTLD`, `WTLU` | Weekly Target LOW band — lower / upper edge *(sparse)* |
| `WTL1`, `WTL2` | Weekly Target LOW — individual levels 1 & 2 *(sparse)* |

**Monthly box levels (16):** same pattern with M prefix (`MIHD`, `MIHU`, …, `MTL1`, `MTL2`).

**Dropped at load time (not used):** `Scraped_At`, `dOpen`, `wOpen`, `mOpen`,
and all D* columns (`DIHD`, `DIHU`, `DILD`, `DILU`, `DRHD`, `DRHU`, `DRLD`, `DRLU`,
`DTH1`, `DTH2`, `DTHD`, `DTHU`, `DTL1`, `DTL2`, `DTLD`, `DTLU`).

### Null semantics

- Inside (I) and Range (R) zones: always populated (363/363).
- Target (TH/TL) zones: sparse — null means no target zone active that day.
  The system already handles this via `pd.isna()` checks in `_best_level`.

---

## Market session cycle (New York time)

```
Calendar day D:
  18:00 (day D-1)  ──▶  SESSION OPENS
  17:00 (day D)    ──▶  SESSION CLOSES
  17:00–18:00      ──▶  CLOSED (no trade — no candles exist in this window)

CSV Date tag = day D (the CLOSING day)
```

---

## Candle → box date mapping rule

Implemented in `BoxLookup._candle_to_box_date()`:

```python
if candle_ts.hour >= 18:
    box_date = candle_date + 1 day   # started next session
else:
    box_date = candle_date           # still in current session
```

**Empirical verification:** NQ_4h.csv contains bars only at hours
`[2, 3, 6, 7, 10, 11, 14, 15, 18, 19, 22, 23]`. Hours 16 and 17 are
absent. The paired hours (e.g. 2 and 3) reflect DST — bars shift +1 hour
in summer (EDT). The closed period (17:00–18:00) has zero bars.

**Examples:**
- Candle `2025-05-05 22:00` → hour=22 ≥ 18 → box_date = `2025-05-06`
- Candle `2025-05-05 12:00` → hour=12 < 18 → box_date = `2025-05-05`

---

## Active row lookup

Old (pre-v4): sliding window — `Date ≤ ts < Date + window_days`  
**New (v4):** direct date index — `df.loc[candle_to_box_date(ts)]`

Because every trading day already has its own row in the unified CSV, no
window parameters are needed. The `BoxLookup` constructor now takes only
`unified_path` and `tick_threshold`.

---

## API / schema changes (v4)

| Layer | Old | New |
|-------|-----|-----|
| `BoxLookup.__init__` | `week_path, month_path, tick_threshold, weekly_window_days, monthly_window_days` | `unified_path, tick_threshold` |
| `BoxStrategyParams` dataclass | `week_data_path, month_data_path, weekly_window_days, monthly_window_days` | `box_data_path` |
| `BoxParamsModel` (Pydantic) | `weekly_window_days, monthly_window_days` | *(removed)* |
| `BoxBacktestRequest` | `week_data_path, month_data_path` | `box_data_path` |
| `/api/boxes` query params | `week_path, month_path, weekly_window_days, monthly_window_days` | `box_data_path` |
| Frontend `settings.ts` | `weekDataPath, monthDataPath` | `boxDataPath` |
| Frontend `sse.ts` | `week_data_path, month_data_path` | `box_data_path` |

---

## Box rect rendering

`get_box_rects()` now groups consecutive rows with identical price values
into a single rectangle. Session boundaries:

```
rect start_time = 18:00 on (first_date_in_group - 1 day)
rect end_time   = 17:00 on last_date_in_group
```

Groups are reset when values change OR when the date gap exceeds 4 calendar
days (handles multi-week coincidences correctly).

---

## Test fixture changes

All test fixtures that previously created two separate CSV files
(`w.csv` + `m.csv`) now create a single `u.csv` with `_unified_csv()`.
Default test date changed from `2025-01-01` (with window_days=7) to
`2025-01-03` (direct lookup — all canonical test candles at hours < 18
on 2025-01-03 map directly to box_date=2025-01-03).

Tests with candles at hour ≥ 18 (e.g. `'2025-01-03 20:00'` → box_date=2025-01-04)
include explicit rows for both affected dates.
