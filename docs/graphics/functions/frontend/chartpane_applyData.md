---
name: chartpane_applyData
file: frontend/src/components/ChartPane.vue
signature: applyData() → void
responsibility: Push the current props + replay state into every series. Runs on every data prop change, every settings change, and every replay scrub tick. The most-frequently-called function in the chart.
related: [[chartpane_initChart]], [[chartpane_toMarkers]], [[toLwcData]], [[computeEMA]], [[computeRSI]], [[boxes_primitive_setBoxes]]
---

# `applyData`

The render workhorse. Watched by every reactive source that affects what's drawn — props, indicator periods, replay state.

## Step 1: pick the visible slice

```ts
const viewTo = replay.isActive ? replay.currentIdx : candles.value.length - 1;
const rows = candles.value.slice(0, viewTo + 1);
const closes = rows.map((r) => r.c);
const times  = rows.map((r) => toUTCTimestamp(r.t));
```

In replay mode the candle array is sliced to `[0..currentIdx]`. Outside replay it's the full array. `closes` and `times` are computed once because they're used by all the overlays.

## Step 2: dataset-change detection (FIX-17)

```ts
const candlesChanged = candles.value !== lastCandlesRef;
lastCandlesRef = candles.value;
```

Identity comparison. The candles array reference changes only when a new backtest writes a fresh array — a replay tick uses the SAME reference. `candlesChanged` gates the `fitContent()` call at the end so that scrubbing during replay does NOT zoom the chart back out.

## Step 3: apply each series

```ts
candleSeries.setData(toLwcData(rows));                                       // candles
emaFastSeries?.setData(buildLineData(computeEMA(closes, indicators.emaFast)));
emaSlowSeries?.setData(buildLineData(computeEMA(closes, indicators.emaSlow)));

if (showVolume) volSeries?.setData(rows.map(...));   // histogram, bull/bearTinted per close direction
else            volSeries?.setData([]);

if (showRSI) rsiSeries?.setData(buildLineData(computeRSI(closes, indicators.rsiPeriod)));
else         rsiSeries?.setData([]);
```

`buildLineData` is the inline reducer that strips out the `null`s from `computeEMA` / `computeRSI` output and pairs the survivors with their `times[i]`. Volume gets its colour decision inline (`r.c >= r.o ? bullTinted : bearTinted`) because it needs both the row and the index.

When a pane is off, `setData([])` is called to clear it — important if the user had it on, then toggled it off without changing the candles.

## Step 4: trade markers

```ts
const visibleTrades = replay.isActive
  ? trades.value.filter((t) => t.entry_idx <= viewTo)
  : trades.value;
const m = toMarkers(rows, visibleTrades, viewTo);
markersApi
  ? markersApi.setMarkers(m)
  : (markersApi = createSeriesMarkers(candleSeries, m));
```

Lazy-creates the markers plugin instance the first time it's needed (it can't exist before `candleSeries` exists). Subsequent calls reuse the same instance. See [[chartpane_toMarkers]] for how the marker list is built.

## Step 5: boxes

```ts
if (boxesPrimitive) {
  const barTimes = rows.map((r) => (toUTCTimestamp(r.t) as unknown as number));
  boxesPrimitive.setBarTimes(barTimes);
  boxesPrimitive.setBoxes(boxes.value);
}
```

Both the bar-time array AND the box list are refreshed every call. The bar-time array changes whenever the visible slice changes (replay) — without that refresh, box x-coordinates would snap to the WRONG bars during a scrub.

## Step 6: conditional fitContent

```ts
if (candlesChanged) {
  chart?.timeScale().fitContent();
}
```

Only runs on a real dataset reload. Without this gate, every replay tick would auto-fit and obliterate the user's manual pan / zoom.
