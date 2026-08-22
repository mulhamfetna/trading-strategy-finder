---
name: all-stocks-signals-data-map
description: WS-AS exhaustive data map — every input candle CSV + box CSV in ALL_STOCKS, the exact (candles → boxes) pairing per instrument, schemas, date/hour coverage, and the full output tree that each instrument's delivery bundle must contain.
type: data-map
status: draft — awaiting verification
created: 2026-06-08
workstream: WS-AS (all-stocks-signals)
---

# WS-AS — Input → Output Data Map

> ⚠️ **Data location changed 2026-08-22:** market data lives ONLY on the server (`~/Mulham/wsg-i`, `~/Mulham/data_2010_1s`); the local checkout has NO data trees. Authoritative map: `docs/DATA-AND-KNOWLEDGE-MAP.md`.

## 1. Source tree (`ALL_STOCKS/` — server path `/home/dev/Mulham/wsg-i/ALL_STOCKS/`, the ONLY copy since 2026-08-22)
```
ALL_STOCKS/
├── CANDLES/
│   ├── CME/
│   │   ├── NQ_Continuous_Data/NQ_{1m,2m,5m,15m,1h,2h,4h}.csv
│   │   └── ES_Continuous_Data/ES_{1m,2m,5m,15m,1h,2h,4h}.csv
│   └── ETF/
│       ├── QQQ_Data/RTH/QQQ_RTH_{…7 TFs}.csv     QQQ_Data/ETH/QQQ_ETH_{…7 TFs}.csv
│       └── SQQQ_Data/RTH/SQQQ_RTH_{…7 TFs}.csv   SQQQ_Data/ETH/SQQQ_ETH_{…7 TFs}.csv
└── BOXS/
    ├── CME/NQ/NQ_{day,week,month,full}_data.csv     CME/ES/ES_{…}.csv
    └── ETF/RTH/QQQ/QQQ_{…}.csv  ETF/ETH/QQQ/QQQ_{…}.csv
        ETF/RTH/SQQQ/SQQQ_{…}.csv ETF/ETH/SQQQ/SQQQ_{…}.csv
```

## 2. The instrument pairing table (NO mixing — this is the contract)
Each row is one delivery bundle. `<TF>` ∈ {1m,2m,5m,15m,1h,2h,4h}.

| Token | Candle glob | Box file (`_full_data.csv`) | Roll rule (D1) |
|---|---|---|---|
| `NQ` | `CANDLES/CME/NQ_Continuous_Data/NQ_<TF>.csv` | `BOXS/CME/NQ/NQ_full_data.csv` | futures hour≥18 |
| `ES` | `CANDLES/CME/ES_Continuous_Data/ES_<TF>.csv` | `BOXS/CME/ES/ES_full_data.csv` | futures hour≥18 |
| `QQQ-RTH` | `CANDLES/ETF/QQQ_Data/RTH/QQQ_RTH_<TF>.csv` | `BOXS/ETF/RTH/QQQ/QQQ_full_data.csv` | calendar-day |
| `QQQ-ETH` | `CANDLES/ETF/QQQ_Data/ETH/QQQ_ETH_<TF>.csv` | `BOXS/ETF/ETH/QQQ/QQQ_full_data.csv` | calendar-day* |
| `SQQQ-RTH` | `CANDLES/ETF/SQQQ_Data/RTH/SQQQ_RTH_<TF>.csv` | `BOXS/ETF/RTH/SQQQ/SQQQ_full_data.csv` | calendar-day |
| `SQQQ-ETH` | `CANDLES/ETF/SQQQ_Data/ETH/SQQQ_ETH_<TF>.csv` | `BOXS/ETF/ETH/SQQQ/SQQQ_full_data.csv` | calendar-day* |

\* = the decision point (D1). For RTH the roll is moot (no bars ≥18); for ETH it changes the 18:00/
19:00 after-hours bars only.

## 3. Schemas
### Candle CSV (all instruments, all TFs) — identical to NQ
`datetime, open, high, low, close, volume` (lowercase). `src.data.loader.load_data` normalises
headers and parses `datetime`. Verified byte-compatible with the existing loader.

### Box CSV (`_full_data.csv`, all instruments) — superset of what NQ used
`Date, Scraped_At, dOpen, wOpen, mOpen, D*(daily 24), W*(weekly), M*(monthly)`. Column **order**
varies between instruments but the pipeline reads **by name** via `box_lookup` triples, so order is
irrelevant. Level families consumed:
- Weekly (`_WEEKLY_LEVELS`, 8 pairs) — **used by NQ mirror**
- Monthly (`_MONTHLY_LEVELS`, 8 pairs) — **used by NQ mirror**
- Daily (`D*`, 8 pairs) — present & populated, **ignored unless D2=(b)**

The separate `*_day_data.csv` / `*_week_data.csv` / `*_month_data.csv` are split views of the same
data; `_full_data.csv` is the single unified source (drop-in for the original `NQ_full_data.csv`).

## 4. Coverage (verified)
| Instrument | Candle datetime range | Candle hours | Box Date range |
|---|---|---|---|
| NQ | 2025-01-01 18:00 → 2026-05-19 19:00 | 0–16, 18–23 | 2025-01-01 → 2026-05-22 |
| ES | 2025-01-01 18:00 → 2026-05-19 19:00 | 0–16, 18–23 | 2025-01-01 → 2026-05-22 |
| QQQ-RTH | 2025-01-02 09:30 → 2026-05-19 15:30 | 9–15 | 2025-01-01 → 2026-05-22 |
| QQQ-ETH | 2025-01-02 04:00 → 2026-05-19 19:00 | 4–19 | 2025-01-01 → 2026-05-22 |
| SQQQ-RTH | 2025-01-02 09:30 → 2026-05-19 15:30 | 9–15 | 2025-01-01 → 2026-05-22 |
| SQQQ-ETH | 2025-01-02 04:00 → 2026-05-19 19:00 | 4–19 | 2025-01-01 → 2026-05-22 |
Every box range fully covers its instrument's candle range. Presets: `full` (all rows), `2025`,
`2026` (calendar-year filter on the candle's own data).

## 5. Output tree (per instrument — mirror of `NQ_SIGNALS_DELIVERY/`)
For `<INSTR>` ∈ the 6 tokens:
```
<INSTR>_SIGNALS_DELIVERY/
├── 1_all_signals/        <INSTR>_<TF>_<preset>.csv          (10 cols, incl. holds)
├── 2_holds_dropped/      <INSTR>_<TF>_<preset>.csv          (10 cols, long/short only)
├── 3_reverse_signals/    <INSTR>_<TF>_<preset>.csv          (21 cols)
├── 4_reverse_by_direction/
│   ├── long_to_short/    <INSTR>_<TF>_<preset>.csv
│   └── short_to_long/    <INSTR>_<TF>_<preset>.csv
├── README.md
└── SUMMARY.csv           (rows/long/short/hold/no_hold/reverse per TF×preset)
```
Counts per bundle: 7 TF × 3 preset = 21 files in each of folders 1–3, 42 in folder 4 ⇒ **105 CSVs +
README + SUMMARY** per instrument; **6 bundles** total (+ optional 6 zips). Reference magnitude
(NQ, from the committed `SUMMARY.csv`): 1m-full = 4,669,738 signal rows / 2,174 reverse windows;
4h-full = 20,322 / 372. ETF-RTH bundles are ~25–30× smaller (RTH = ~2,400 1h candles vs ~8,100).

## 6. Validation hooks
- **NQ parity:** regenerated `NQ_SIGNALS_DELIVERY` must diff-clean against the committed one
  (anchors the generalization).
- **No-mix assertion:** every emitted `box_id`'s date must resolve within the instrument's own box
  `Date` index; cross-instrument paths are impossible by construction (config record per instrument).
- **Coverage assertion:** box range ⊇ candle range (already verified above) — fail loudly otherwise.
- **Per-bundle SUMMARY.csv:** the row/window counts are written on every run for eyeballing.
