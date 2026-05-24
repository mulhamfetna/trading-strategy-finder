---
name: chartpane_initChart
file: frontend/src/components/ChartPane.vue
signature: initChart() → void
responsibility: Instantiates the Lightweight Charts instance, every series the chart owns, the BoxesPrimitive overlay, and the crosshair-move handler. Tears down any prior chart first. Called on mount and on any pane add/remove (toggling volume or RSI).
related: [[chartpane_applyData]], [[chartpane_rebuildChart]], [[boxes_primitive_attached]], [[fe_components_chartpane]]
---

# `initChart`

The factory function for the chart instance. Heavy, but only runs at mount or when the user flips a pane visibility toggle.

## Teardown (when re-entering)

```ts
if (chart) {
  markersApi = null;
  boxesPrimitive = null;
  chart.remove();         // also fires boxesPrimitive.detached() internally
  chart = null;
  candleSeries = null;
  emaFastSeries = null;
  emaSlowSeries = null;
  volSeries = null;
  rsiSeries = null;
}
lastCandlesRef = null;    // force the next applyData() to call fitContent()
```

The order matters: drop the JS refs before calling `chart.remove()` so any teardown side-effects can't see stale references.

## Chart creation

```ts
chart = createChart(containerRef.value, {
  layout:           { background: { color: CHART_THEME.bg }, textColor: CHART_THEME.text },
  grid:             { vertLines: { color: CHART_THEME.border }, horzLines: { color: CHART_THEME.border } },
  timeScale:        { borderColor: CHART_THEME.border },
  rightPriceScale:  { borderColor: CHART_THEME.border },
  autoSize:         true,
});
```

`autoSize: true` is what lets the chart shrink/grow with its container (LWC v5 feature — the container itself is sized by the scoped CSS at the bottom of the SFC).

## Series + primitives, in order

1. **Candle series** (pane 0) — `addSeries(CandlestickSeries, {...})` with bull/bear colours from `CHART_THEME`.
2. **BoxesPrimitive** — `new BoxesPrimitive()` then `candleSeries.attachPrimitive(boxesPrimitive)`. The primitive's `zOrder = 'bottom'` means boxes draw under candles. See [[boxes_primitive_attached]].
3. **EMA fast + slow** (pane 0) — `addSeries(LineSeries, { title: 'EMAxx', priceLineVisible: false, lastValueVisible: false }, 0)`. `priceLineVisible: false` keeps the right-edge price label off the EMA so it doesn't crowd the candle's own.
4. **Volume histogram** (pane 1) — only when `settings.indicators.showVolume`. Bound to its own price scale `'vol'` so it doesn't share the candle pane's price axis.
5. **RSI line** (pane 1 or 2) — only when `settings.indicators.showRSI`. Pane index is `2` when volume is enabled, else `1`. Two `createPriceLine` calls add dashed horizontal threshold lines at 30 and 70 with the bull/bear-threshold colours.

## Crosshair handler

```ts
chart.subscribeCrosshairMove((param) => {
  if (!param.time || !candles.value.length) {
    hoveredCandle.value = null;
    return;
  }
  const ts = param.time as number;
  hoveredCandle.value = candles.value.find((c) => (toUTCTimestamp(c.t) as number) === ts) ?? null;
});
```

Linear search. Acceptable at current dataset sizes; would warrant a `Map<UTCTimestamp, Candle>` if the bar count ever exceeded ~50k.

## Final step

`applyData()` is called at the end so the freshly-instantiated chart populates immediately rather than waiting for the next reactive change.
