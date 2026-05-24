---
title: Graphics Pipeline — Master Index
purpose: End-to-end orchestration of how candles and TradingView-style boxes flow from CSV on disk to pixels on the Lightweight Charts canvas.
scope: Candle rendering, box overlay rendering, EMA / Volume / RSI overlays, trade markers, replay scrubbing. Does not cover strategy execution math.
status: Authoritative. Reflects the system as it actually runs on 2026-05-24.
---

# Graphics Pipeline — Master Index

This is the single source of truth for everything the chart draws: OHLC candles, the box rectangles overlaid behind them, EMA/Volume/RSI overlays, and the trade markers. Every file and function involved in producing those pixels is documented under this tree.

The chart on screen is correct. Where any older project doc disagrees with what's documented here, this tree wins.

---

## 1. Data sources (on disk)

| File | Role | Shape |
|---|---|---|
| `NQ_4h.csv` | OHLCV bars for the chart, entry-signal timeframe | `Date,Open,High,Low,Close,Volume` ascending |
| `NQ_1m.csv` | 1-minute bars (used by SL/TP exit search; not drawn) | same column shape |
| `NQ_full_data.csv` | Unified weekly + monthly box levels (v4 schema) | `Date, W*U/W*D, M*U/M*D` per session day |

All three live in the project root and are gitignored. The frontend never reads them directly — it pulls everything through the FastAPI backend.

---

## 2. End-to-end data flow

### 2a. Candles flow (initial dashboard load)

```
NQ_4h.csv on disk
    │
    │  (src/data/loader.py)  load_data()           ← outside graphics scope; just produces a DataFrame
    ▼
GET /api/candles  ──────────► [[get_candles]]           (FastAPI endpoint)
    │
    │  helpers:                [[load_and_filter]]      (date filter)
    │                          [[candles_from_df]]      (DataFrame → Candle[])
    ▼
HTTP JSON: CandlesResponse { candles: Candle[], count, range }
    │
    ▼  axios call:             [[fetchCandles]]         (frontend/src/services/api.ts)
    ▼  Pinia action:           [[candlesStore_load]]    (frontend/src/stores/candles.ts)
    ▼
useCandlesStore.candles  (reactive ref<Candle[]>)
    │
    ▼  prop drilling
ChartPane.vue                                         ← consumes via the candles prop
```

### 2b. Candles + boxes flow (after a backtest)

A backtest run is the channel that delivers BOTH the candles drawn on the chart AND the box rectangles overlaid on them. The candles store path above is bypassed in this case — the backtest response carries the candles directly.

```
POST /api/backtest/box  ──► SSE stream  (see src/api/app.py: _box_event_stream)
    │
    │  helpers:                 [[load_and_filter]]
    │                           [[candles_from_df]]            (candles into 'complete' payload)
    │                           [[boxlookup_get_box_rects]]    (BoxLookup builds rect list)
    ▼
event: complete  { metrics, trades, candles, boxes, elapsed_ms }
    │
    ▼  SSE client:              frontend/src/services/sse.ts → streamBoxBacktest()
    ▼  Pinia action:            [[backtestStore_run]]          (frontend/src/stores/backtest.ts)
    ▼
useBacktestStore.candles  (reactive)
useBacktestStore.boxes    (reactive)
useBacktestStore.trades   (reactive)
    │
    ▼  prop binding
ChartPane.vue
```

### 2c. Pixels (inside ChartPane.vue)

Once the chart has candles, boxes, and trades, the render path is:

```
ChartPane.vue
    │
    ├── [[chartpane_initChart]]  — creates chart, candle series, primitives, EMA/Vol/RSI series
    │
    └── [[chartpane_applyData]]  — runs on every data change & every replay tick
            │
            ├── candleSeries.setData(  [[toLwcData]]( rows ) )
            │       └── per row: [[toUTCTimestamp]]( candle.t )       ← string → UTCTimestamp
            │
            ├── emaFastSeries.setData( [[computeEMA]]( closes, period ) )
            ├── emaSlowSeries.setData( [[computeEMA]]( closes, period ) )
            ├── rsiSeries.setData(     [[computeRSI]]( closes, period ) )
            ├── volSeries.setData( built-in-place from rows )
            │
            ├── markersApi.setMarkers( [[chartpane_toMarkers]]( rows, trades, viewTo ) )
            │
            └── boxesPrimitive.setBarTimes(...) + .setBoxes(boxes)
                    └── on next frame, the renderer's [[boxes_renderer_draw]] paints rectangles
                            └── for each box: [[boxes_snapBox]] picks bar-snapped x1/x2 timestamps
                                      └── [[boxes_lowerBound]] (binary search inside snapBox)
```

### 2d. Replay scrubbing path

```
Replay UI → [[fe_stores_replay]] actions (play/pause/step/seek)
    │
    ▼  currentIdx changes
ChartPane.vue watcher → [[chartpane_applyData]] again
    │
    ▼
candleSeries shows rows.slice(0, viewTo+1)        ← partial reveal of historical candles
boxesPrimitive.setBarTimes(barTimes for that slice) ← box x-snap respects the visible bars
markers are filtered to trades whose entry_idx ≤ viewTo
```

---

## 3. Files in this pipeline

### Backend
- [[src_api_app]] — FastAPI endpoints for candles + boxes, SSE stream for backtest (carries candles+boxes to chart)
- [[src_api_schemas]] — Pydantic models for the Candle, CandlesResponse, BoxRect wire shapes
- [[src_strategy_box_lookup]] — Produces `BoxRect[]` from `NQ_full_data.csv` for the chart overlay

### Frontend
- [[fe_types]] — TypeScript mirrors of the backend wire shapes (`Candle`, `BoxRect`, `CandlesResponse`)
- [[fe_services_api]] — Axios REST client for `/api/candles`
- [[fe_services_chart_helpers]] — Pure helpers used by ChartPane: timestamp conversion, EMA, RSI
- [[fe_services_chart_theme]] — Canvas-side colour palette (mirrors Tailwind tokens)
- [[fe_stores_candles]] — Pinia store wrapping the `/api/candles` REST call
- [[fe_stores_backtest]] — Pinia store driven by the SSE stream; holds candles + boxes + trades for the chart after a backtest
- [[fe_stores_replay]] — Pinia store that drives the partial-reveal scrubber for ChartPane
- [[fe_components_chartpane]] — The Vue component that owns the Lightweight Charts instance
- [[fe_components_boxesprimitive]] — Custom LWC v5 series primitive that paints the box rectangles

---

## 4. Coordinate / colour contracts

These contracts must remain consistent across backend and frontend; the chart depends on them.

### 4a. Timestamps
- Backend emits `Candle.t` as `YYYY-MM-DDTHH:MM:SS` (no timezone suffix). `_candles_from_df` normalises any combination of `Date` / `Date+Time` columns into this exact shape.
- `BoxRect.start_time` / `end_time` are integer Unix seconds (UTC).
- Frontend converts the candle string to a Lightweight-Charts `UTCTimestamp` (seconds since epoch) via `toUTCTimestamp`. A naive string parse fails silently in LWC; the helper appends `Z` so the date is interpreted as UTC.
- Box rects are matched to candle x-coordinates by snapping to the nearest real bar timestamp; bars that don't exist (weekend / session-close gaps) are skipped.

### 4b. NQ session and box date mapping
- NQ session runs 18:00 (day D-1) → 17:00 (day D) NY time.
- `BoxLookup._candle_to_box_date`: candles with `hour ≥ 18` map to the NEXT calendar day's box row.
- `BoxLookup.get_box_rects` produces rectangles whose start_time = 18:00 of the day before the row's `Date`, end_time = 17:00 of that `Date`.

### 4c. Colour palette
- Single source of truth: `frontend/src/services/chart_theme.ts → CHART_THEME`.
- Box per-level fill + border colours: `src/strategy/box_lookup.py → _LEVEL_COLORS`. The backend emits the colour strings directly inside each BoxRect so the frontend never has to look them up.
- Bull (`#00c853`) / Bear (`#ff5252`) are mirrored in `tailwind.config.js` (`tv-green` / `tv-red`); when adding a colour both must be updated.

### 4d. Z-ordering on the canvas
- Box rectangles draw at `zOrder = 'bottom'` (under the candles) — see `BoxesPaneView.zOrder()`.
- Trade markers draw via Lightweight-Charts' built-in markers plugin (above the candles).
- EMA, RSI lines and Volume bars are LWC series; they obey the platform's own pane ordering.

---

## 5. Why this tree exists

Every other piece of project documentation has been deleted. This tree is the only place the system is described. If anything here disagrees with the code, the code is right and this file should be edited — not abandoned in favour of a second, drifting source.

Recovery of older docs (if ever needed): `git show docs-pre-wipe -- <path>`.
