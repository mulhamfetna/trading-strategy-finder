---
name: candlesStore_load
file: frontend/src/stores/candles.ts
signature: load(start: string, end: string, dataset: 'train' | 'test') → Promise<void>
responsibility: Pinia action — fetches candles for the requested window and writes them into the reactive store so ChartPane redraws. Handles the loading flag and error surfacing.
related: [[fetchCandles]], [[fe_stores_candles]], [[chartpane_applyData]]
---

# `useCandlesStore.load`

The only action on the candles store. Reads `dataPath` from the settings store (so the user's CSV pick is honoured) and writes the result into `candles`, `range`, and the async-state refs.

## Implementation

```ts
async function load(start, end, dataset) {
  loading.value = true;
  error.value = null;
  const settings = useSettingsStore();
  try {
    const resp = await fetchCandles(start, end, dataset, settings.dataPath);
    candles.value = resp.candles;
    range.value = resp.range;
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err);
    candles.value = [];                    // ← intentional: blank chart on error
  } finally {
    loading.value = false;
  }
}
```

## Why it blanks `candles` on error

`candles.value = []` in the catch block is deliberate. If the previous successful response left bars on the chart and a new request fails, leaving the old bars up gives the trader a false sense that they're looking at the requested range. Better to show empty + an error than show stale-but-wrong.

## What this action does NOT do

- It does NOT change the replay store. Replay deactivation on candles-cleared is handled by [[fe_stores_replay]]'s `total` watcher, not by this action.
- It does NOT fetch boxes. Box overlays come from the backtest path ([[backtestStore_run]]), not this one.
- It does NOT call `dataset` differently — it just forwards.

## Pre-conditions

- `settings.dataPath` must be populated. The settings store defaults to `DEFAULT_DATA_PATH = 'NQ_4h.csv'`, so the only way this can be empty in practice is if a test or buggy mutation cleared it.
