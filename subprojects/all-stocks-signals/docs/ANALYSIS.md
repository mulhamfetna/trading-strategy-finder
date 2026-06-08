---
name: all-stocks-signals-analysis
description: WS-AS deep analysis — replicating the NQ_SIGNALS_DELIVERY signal-export pipeline across all 6 instruments in ALL_STOCKS (NQ, ES, QQQ-RTH, QQQ-ETH, SQQQ-RTH, SQQQ-ETH). Documents the existing frozen pipeline, the per-instrument divergences (session-roll, level families), and the exact decisions that gate implementation.
type: analysis
status: draft — awaiting verification
created: 2026-06-08
workstream: WS-AS (all-stocks-signals)
---

# WS-AS — All-Stocks Signal Export: Deep Analysis

## 0. The goal (restated)
Produce, for **each of the 6 instruments** in `ALL_STOCKS/`, a delivery bundle that is a
**byte-faithful mirror** of `NQ_SIGNALS_DELIVERY.zip` — the 4-stage signal product
(all-signals → holds-dropped → reverse-signals → reverse-by-direction) across **7 timeframes**
(1m, 2m, 5m, 15m, 1h, 2h, 4h) × **3 presets** (full, 2025, 2026). Each instrument's candles must be
matched to **its own** boxes — no cross-instrument mixing.

The 6 instruments:
| Token | Class | Source candles | Source boxes | Session hours (1h sample) |
|---|---|---|---|---|
| `NQ` | CME future | `CANDLES/CME/NQ_Continuous_Data/NQ_<TF>.csv` | `BOXS/CME/NQ/NQ_full_data.csv` | 18→16 (overnight) |
| `ES` | CME future | `CANDLES/CME/ES_Continuous_Data/ES_<TF>.csv` | `BOXS/CME/ES/ES_full_data.csv` | 18→16 (overnight) |
| `QQQ-RTH` | ETF regular | `CANDLES/ETF/QQQ_Data/RTH/QQQ_RTH_<TF>.csv` | `BOXS/ETF/RTH/QQQ/QQQ_full_data.csv` | 09:30→15:30 |
| `QQQ-ETH` | ETF extended | `CANDLES/ETF/QQQ_Data/ETH/QQQ_ETH_<TF>.csv` | `BOXS/ETF/ETH/QQQ/QQQ_full_data.csv` | 04:00→19:00 |
| `SQQQ-RTH` | ETF regular | `CANDLES/ETF/SQQQ_Data/RTH/SQQQ_RTH_<TF>.csv` | `BOXS/ETF/RTH/SQQQ/SQQQ_full_data.csv` | 09:30→15:30 |
| `SQQQ-ETH` | ETF extended | `CANDLES/ETF/SQQQ_Data/ETH/SQQQ_ETH_<TF>.csv` | `BOXS/ETF/ETH/SQQQ/SQQQ_full_data.csv` | 04:00→19:00 |

All 6 × 7 timeframe candle files exist; all 6 box `_full_data.csv` files carry weekly **and**
monthly **and** daily levels, fully populated (363/363 dated rows, 2025-01-01 → 2026-05-22, which
fully covers every instrument's candle range).

---

## 1. The existing pipeline (what we are mirroring)
The NQ delivery was produced by the **frozen** pipeline in `subprojects/signals/`:

- **Stage 1** — `generate_stage1.py::_emit_rows(candles, box_df)`: for each candle, map it to a
  box-date row, then for each **active** level-pair emit `long`/`short`/`hold` by the rule
  `color + inclusive-touch + strict-close-vs-edge` (full spec in `full_candles/docs/PIPELINE.md` §3).
- **Stage 2** — `stage1_0_reverse_signals/generate_stage2.py::generate(stage1_df)`: collapse to one
  state per candle, scan reverse windows (long→…→short / short→…→long), emit `window_high`,
  `window_low`, direction-aware `tp`/`sl`, `holds_between` (PIPELINE.md §5).
- **Driver** — `full_candles/generate_full_candles.py`: runs Stage 1 + Stage 2 for all 7 TFs × 3
  presets, writes all-signals / holds-dropped / reverse / by_direction, plus `SUMMARY.csv`.
- **Packager** — `full_candles/package_delivery.py`: re-lays the outputs into the 4 numbered
  folders + README + SUMMARY that make up `NQ_SIGNALS_DELIVERY/`.

Output schemas (identical for every instrument we add):
- all-signals & holds-dropped — **10 cols**: `datetime, open, high, low, close, volume, signal,
  box_id, box_upper, box_lower`.
- reverse & by_direction — **21 cols**: anchor(8) + reverse(8) + `window_high, window_low, tp, sl,
  holds_between`.

---

## 2. The divergences from NQ (what must change)
The pipeline is **timeframe-agnostic** but **NOT instrument-agnostic** today. Two things are
hardwired to NQ:

### 2.1 Candle → box-date mapping (the session roll) — **MATERIAL**
`generate_stage1._emit_rows` line 83 calls `BoxLookup._candle_to_box_date(ts)`, which applies the
**futures** rule:
```
candle.hour >= 18  →  box_date = candle.date + 1 day      # 18:00 belongs to next session
candle.hour <  18  →  box_date = candle.date
```
Effect per class (verified against the real hour histograms):
- **NQ, ES (CME futures):** hours span 18–23 and 0–16. The 18:00–23:59 bars genuinely belong to the
  next session day → **the rule is correct, keep it.**
- **QQQ-RTH, SQQQ-RTH (ETF regular):** hours are 9–15 only. No bar is ≥18, so the roll **never
  fires** → `box_date = candle.date` for every bar. The futures rule is a harmless no-op here, but
  it is cleaner to state the intent: ETF = calendar-day mapping.
- **QQQ-ETH, SQQQ-ETH (ETF extended):** hours span **4–19**. Bars at **18:00 and 19:00 DO exist**,
  so the futures rule would **roll those after-hours bars onto the *next* calendar day's box** —
  almost certainly wrong for an ETF, whose extended session is still the *same* calendar trading
  day. This is the single decision that changes real output rows. **→ DECISION D1.**

### 2.2 Level families: weekly + monthly vs + daily — **MATERIAL**
`generate_stage1` line 31 sets `_LEVEL_PAIRS = _WEEKLY_LEVELS + _MONTHLY_LEVELS` — i.e. the NQ
delivery used **weekly + monthly only** and **ignored the daily (`D*`) columns**, even though
`NQ_full_data.csv` already contained them. The `ALL_STOCKS` boxes additionally ship explicit
`*_day_data.csv` files and fully-populated `D*` columns. So: mirror NQ exactly (weekly+monthly), or
add the **daily** family as a third level group (more boxes ⇒ more signals)? **→ DECISION D2.**

### 2.3 Instrument identity (paths + filename token) — mechanical
The driver hardwires `_DATA_DIR`, `_BOX_CSV`, the `NQ_` filename token, and the `Full_Canldes_Data`
layout. Generalizing these is mechanical (a per-instrument config record). No decision needed beyond
the **output token** for the two-variant ETFs — proposed `QQQ-RTH` / `QQQ-ETH` / `SQQQ-RTH` /
`SQQQ-ETH` so RTH and ETH never collide.

### 2.4 Reuse-without-drift (implementation choice, not a domain decision)
`_emit_rows` calls the static `BoxLookup._candle_to_box_date` directly, so it can't be reused as-is
for the ETF rule. Planned approach (stated for transparency, default chosen): **parameterize**
`_emit_rows`/the driver with a `candle_to_box_date` callable (default = the exact `BoxLookup` rule)
and a `level_pairs` list, then lock NQ output **byte-identical** to the committed
`NQ_SIGNALS_DELIVERY` via a regression test. Futures pass the `BoxLookup` rule (parity); ETFs pass a
calendar-day rule. This keeps Stage 1/Stage 2 math frozen and shared.

---

## 3. What is NOT changing (invariants)
- Stage 1 rule (color/touch/edge), Stage 2 reverse-window scan, tp/sl formulas, ordering, and both
  output schemas — **frozen and shared verbatim**.
- Preset semantics: `full` = all rows for that instrument; `2025`/`2026` = calendar-year filter;
  Stage 2 runs independently per preset (a year-straddling window appears only in `full`).
- Determinism: same inputs + same code → byte-identical outputs (stable mergesort, no timestamps).
- **No mixing:** each instrument uses only its own candles and its own boxes.
- **NQ parity:** the regenerated `NQ` bundle must match the committed `NQ_SIGNALS_DELIVERY` exactly
  (this is the correctness anchor for the whole generalization).

---

## 4. Scale & the parallelism question
Per instrument: 7 TF × 3 presets = 21 Stage-1 runs → ~5 artifacts each. 6 instruments ⇒ **~630
output CSVs** + 6 SUMMARY.csv + 6 bundles. The 1-minute presets dominate cost (NQ 1m `full` ≈ 4.67 M
signal rows; ETF-RTH are ~30× smaller). Each **instrument is fully independent** (own candles, own
boxes, own outputs) ⇒ the workload is embarrassingly parallel at the instrument grain (6 workers),
or finer at the (instrument × TF) grain (42 workers). Options — local multiprocessing vs the AMD GPU
server (CPU-bound, so GPU irrelevant; the server just offers more cores/RAM) — are weighed in
`PLAN.md §Parallelism`. **→ DECISION D3 (where/how to run).**

---

## 5. Decisions — RESOLVED (user, 2026-06-08)
| # | Decision | **Resolution** |
|---|---|---|
| **D1** | ETF / ETH session roll | **Follow NQ logic uniformly** — every instrument uses `BoxLookup._candle_to_box_date` (futures hour≥18 → +1 day). ETH 18:00/19:00 bars roll to the next day's box, same as NQ. No per-instrument roll seam. |
| **D2** | Level families | **Follow NQ logic** — weekly + monthly only (`_WEEKLY_LEVELS + _MONTHLY_LEVELS`); daily `D*` columns ignored, exactly as NQ. |
| **D3** | Where to run | **Evaluate inside this workstream (AS.6)** — benchmark local-parallel vs the training server, then choose. No effect on outputs. |

**Consequence:** every instrument runs the **identical frozen code path** (same roll, same levels,
same Stage 1/Stage 2). The only generalization is instrument **identity** (candle paths + box CSV +
output token). This makes NQ regeneration **byte-identical by construction** and removes the roll/
level seams the draft plan anticipated — see `PLAN.md` (AS.2 collapses to a thin reuse wrapper).
