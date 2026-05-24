---
name: fe_components_chartpane
mirrors: frontend/src/components/ChartPane.vue
purpose: The Vue component that owns the Lightweight Charts instance. Wires candles, EMA / Volume / RSI overlays, trade markers, and the box-rectangle primitive together; reacts to settings, backtest, and replay store changes.
related: [[fe_components_boxesprimitive]], [[fe_services_chart_helpers]], [[fe_services_chart_theme]], [[fe_stores_backtest]], [[fe_stores_replay]]
---

# `frontend/src/components/ChartPane.vue`

The component takes three props — `candles`, `trades`, `boxes` — and draws everything. Whoever instantiates it picks which store to bind the props to (raw-candles store before a run, backtest store after).

## Module-level state (inside `<script setup>`)

| Variable | Type | Purpose |
|---|---|---|
| `chart` | `IChartApi \| null` | The LWC chart instance. Lives across rebuilds but is nulled on unmount. |
| `candleSeries` | `ISeriesApi<'Candlestick'>` | Pane 0, primary series. |
| `markersApi` | `ISeriesMarkersPluginApi<Time>` | LWC v5 markers plugin instance, attached to the candle series. |
| `emaFastSeries`, `emaSlowSeries` | `ISeriesApi<'Line'>` | Pane 0 overlay lines. |
| `volSeries` | `ISeriesApi<'Histogram'>` | Pane 1 when `showVolume`. |
| `rsiSeries` | `ISeriesApi<'Line'>` | Pane 1 or 2 when `showRSI`; with two horizontal price lines at 30 and 70. |
| `boxesPrimitive` | `BoxesPrimitive \| null` | Custom series primitive — paints box rectangles behind the candles. |
| `lastCandlesRef` | array reference | FIX-17: identity-compared to skip `fitContent()` when the data array hasn't actually changed. Prevents replay scrubbing from destroying the user's manual zoom. |
| `hoveredCandle` | `Ref<Candle \| null>` | Backs the OHLC tooltip in the top-left corner. |

## Functions in this file

| Function | Doc | One-line role |
|---|---|---|
| `toMarkers(rows, tradeRows, viewTo)` | [[chartpane_toMarkers]] | Builds the entry-arrow + exit-square marker list. |
| `applyData()` | [[chartpane_applyData]] | Reapplies every series' data and the markers + boxes. Runs on every data or replay change. |
| `rebuildChart()` | [[chartpane_rebuildChart]] | Tears down + reinstantiates the chart while preserving the visible range. Used when a pane is added or removed. |
| `initChart()` | [[chartpane_initChart]] | Creates the chart and all its series + primitives. |

The `emaWarning` computed and the crosshair-move subscriber are inline; they're trivial enough to not warrant their own function docs. The warning surfaces when an EMA period exceeds the number of loaded candles (QC-CP-4). The crosshair handler updates `hoveredCandle` to drive the tooltip — it does a linear search through `candles.value` because the array is short enough that a Map cache isn't worth the bookkeeping.

## Watchers (graphics-relevant)

| Watch source | Reaction |
|---|---|
| `[candles, trades, boxes]` (shallow) | `applyData()` — the primary redraw trigger. |
| `[settings.indicators.showVolume, showRSI]` | `rebuildChart()` — toggling a pane on/off forces a teardown + rebuild because LWC's pane index changes. |
| `[settings.indicators.emaFast, emaSlow, rsiPeriod]` | Update overlay titles via `applyOptions` (BUG-023 — titles are baked at addSeries time) and call `applyData()` to recompute. NO rebuild. |
| `replay.currentIdx`, `replay.isActive` | `applyData()` — re-slice the candles. |

## Lifecycle

`onMounted(initChart)` → chart appears once the container has a size (LWC needs a non-zero parent).

`onBeforeUnmount` → clears every ref to its null state and calls `chart.remove()`. The primitive's `detached()` runs as part of `chart.remove()`.

## CSS

Scoped block at the bottom. Floors the chart at 360 px tall, uses 55% of viewport, ceilings at 720 px (so it doesn't dominate ultrawide displays). The tooltip + warning chip use CSS variables sourced from `CHART_THEME` via inline style on the chart shell, so no hex literals are duplicated in the stylesheet.
