---
name: backtestStore_run
file: frontend/src/stores/backtest.ts
signature: run() → Promise<void>
responsibility: Drives the master-strategy backtest end-to-end. Opens the SSE stream, drains progress events, and writes the `complete` payload (metrics + trades + candles + boxes) into the store's reactive refs — populating everything ChartPane needs to render the result.
related: [[fe_stores_backtest]], [[chartpane_applyData]], [[boxlookup_get_box_rects]]
---

# `useBacktestStore.run`

The only entry point that produces a chart-renderable backtest result. Called from the "Run" button. Re-entrant guard at the top prevents a second click from racing with an in-flight stream.

## Lifecycle

```
   isRunning = true
   error / warnings / progress / metrics / elapsedMs ← null
   candles / trades / boxes ← []                    ← blank the chart immediately
   lastRunSettings ← JSON.stringify(runPayload)     ← snapshot for isDirty diff

   for await (ev of streamBoxBacktest(runPayload)):
      progress  → store ev.data
      complete  → write metrics + trades + candles + boxes + elapsedMs
      warning   → append "<stage>: <message>" to warnings[]
      error     → store ev.data.detail ?? ev.data.message

   isRunning = false
```

## Wire shape sent to the backend

```ts
{
  params: settings.params,
  data_path: settings.dataPath,
  data_path_1min: settings.dataPath1min,
  box_data_path: settings.boxDataPath,
  start: settings.startDate || undefined,
  end: settings.endDate || undefined,
}
```

This is forwarded to `streamBoxBacktest` in `frontend/src/services/sse.ts`. Every key here is REQUIRED by the backend's `BoxBacktestRequest` — drift produces a 422 from the validation handler. A regression test (`frontend/tests/sse_request_shape.test.ts`) asserts the exact key set the SSE client puts on the wire.

`start` / `end` are converted from empty string to `undefined` so the SSE client can send them as `null` (the backend requires the key but accepts null).

## Why candles / boxes are zeroed up-front

Mirrors the candles store's "blank on error" rationale: do not let stale on-screen results outlive a new run. The user clicks "Run", the chart goes blank, and the moment the `complete` event lands the chart fills back in.

## What `isDirty` watches

`isDirty` is a computed boolean. It JSON-stringifies the CURRENT settings the same way `runPayload` was stringified and compares to `lastRunSettings`. When they differ, the UI can mark the displayed results as out-of-date.

## What this action does NOT do

- It does not deactivate replay — the replay store's own `total` watcher handles that on the candles-cleared transition.
- It does not draw anything itself. The reactive refs it writes are what trigger ChartPane's watcher.
