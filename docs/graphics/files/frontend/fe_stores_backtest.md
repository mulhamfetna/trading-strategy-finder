---
name: fe_stores_backtest
mirrors: frontend/src/stores/backtest.ts
purpose: Pinia store that drives the master-strategy backtest and — after the SSE stream's `complete` event — holds the candles, boxes, and trades that ChartPane renders. This is the primary candle/box source for the chart whenever a backtest has been run.
related: [[fe_components_chartpane]], [[fe_stores_replay]], [[src_api_app]]
---

# `frontend/src/stores/backtest.ts`

Owns the entire master-strategy run lifecycle: kicks off the SSE stream, accumulates progress, lands the final payload. The chart reads three reactive arrays from this store: `candles`, `boxes`, `trades`.

## State (graphics-relevant)

| Field | Type | Meaning |
|---|---|---|
| `isRunning` | `boolean` | True while the SSE stream is open. |
| `progress` | `ScalingProgress \| null` | Latest `event: progress` payload — not drawn on the chart itself. |
| `error` / `warnings` | `string \| null`, `string[]` | Stream-error surfacing for the UI. |
| `candles` | `Candle[]` | Bars to draw — filled from `complete.candles`. |
| `boxes` | `BoxRect[]` | Overlay rectangles — filled from `complete.boxes ?? []`. |
| `trades` | `ScalingTrade[]` | Drives the trade markers via [[chartpane_toMarkers]]. |
| `metrics` | `Metrics \| null` | Out of graphics scope; the cards consume this. |
| `elapsedMs` | `number \| null` | Diagnostic, not drawn. |

## Computed (graphics-relevant)

| Field | Meaning |
|---|---|
| `percent` | Progress percentage forwarded to the ProgressBar. |
| `hasResults` | True after the `complete` event has landed — the chart treats this as "render the result". |
| `isDirty` | True when the current settings no longer match the run that produced the on-screen results. Useful for fading the chart / showing a "stale" badge. |

## Actions

| Action | Doc |
|---|---|
| `run()` | [[backtestStore_run]] |

`run()` is the only entry point. It resets all the drawn arrays to empty BEFORE opening the stream, so the chart blanks while the backtest is in flight rather than showing a mix of old and new data. The SSE wire shape it sends is asserted by `frontend/tests/sse_request_shape.test.ts` — every key the backend's `BoxBacktestRequest` requires must appear.

## Why two stores feed the chart

Before a backtest is run the chart is fed by [[fe_stores_candles]] (raw OHLCV). After a backtest has completed it is fed by THIS store (candles + boxes + trades). ChartPane itself doesn't know which one — it just takes a `candles` / `trades` / `boxes` prop and re-renders. The parent component decides which store to bind to.
