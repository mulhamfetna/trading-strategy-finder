---
name: fe_stores_candles
mirrors: frontend/src/stores/candles.ts
purpose: Pinia store wrapping `GET /api/candles`. Owns the candle array, loading flag, and error state for the standalone "explore raw candles" path. After a backtest runs, the chart reads candles from [[fe_stores_backtest]] instead — this store is the pre-backtest path.
related: [[fe_services_api]], [[fe_components_chartpane]]
---

# `frontend/src/stores/candles.ts`

Tiny store. Holds an array of `Candle` plus async-state booleans.

## State

| Field | Type | Meaning |
|---|---|---|
| `candles` | `Candle[]` | What ChartPane draws (when bound to this store rather than the backtest store). |
| `loading` | `boolean` | True from action invocation until response or error. |
| `error` | `string \| null` | Caller-displayable message, null on success. |
| `range` | `{ start, end } \| null` | Echo of the requested date window (from `CandlesResponse.range`). |

## Actions

| Action | Doc |
|---|---|
| `load(start, end, dataset)` | [[candlesStore_load]] |

`dataset` is `'train' | 'test'` and is forwarded to the backend, but at this point the backend treats both the same way for `/api/candles` — the split happens downstream. The action calls [[fetchCandles]] with the user's currently-selected `dataPath` from the settings store and writes the response into the store's reactive refs.

On any thrown error the store sets `error.value` and clears `candles.value` so the UI can show an empty state plus the message — it does NOT keep stale candles around. This is intentional: a partial dataset on screen would mislead the trader.
