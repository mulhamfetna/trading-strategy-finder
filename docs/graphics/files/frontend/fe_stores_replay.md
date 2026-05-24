---
name: fe_stores_replay
mirrors: frontend/src/stores/replay.ts
purpose: Pinia store that drives the partial-reveal scrubber for ChartPane. When replay is active, ChartPane slices the candles array up to `currentIdx` and only draws bars + markers that have "happened" by that point.
related: [[fe_components_chartpane]], [[fe_stores_backtest]]
---

# `frontend/src/stores/replay.ts`

Owns the playback state machine. The chart reads `isActive` and `currentIdx` from this store; everything else (PnL panels, ReplayBar) reads the computed properties.

## State (graphics-relevant)

| Field | Type | Meaning |
|---|---|---|
| `isActive` | `boolean` | Replay mode on/off. ChartPane checks this to decide whether to slice the candles array. |
| `currentIdx` | `number` | The frontier — bars `[0..currentIdx]` are visible. |
| `isPlaying` | `boolean` | Drives the play/pause button state; not directly read by ChartPane. |
| `speed` | `number` | Candles advanced per 200 ms tick. |
| `total` | `computed<number>` | Length of `useBacktestStore.candles`. |

## Computed (informational; not used by the chart itself)

`percent`, `currentCandle`, `realisedPnl`, `unrealisedPnl`, `runningPnl`, `activeTrade` — these feed the PnL panels and the replay HUD. ChartPane only reads `isActive` and `currentIdx`.

## Actions

| Action | Effect on the chart |
|---|---|
| `activate()` | Stops timer, sets `isActive=true`, rewinds `currentIdx=0`. ChartPane's watcher fires; chart redraws empty. |
| `deactivate()` | Stops timer, sets `isActive=false`. ChartPane redraws with the full dataset. |
| `play()` | Starts a 200 ms interval that advances `currentIdx` by `speed`. ChartPane re-renders on each step via the watcher. |
| `pause()` | Stops the interval. Chart freezes at the current frontier. |
| `stepForward()` / `stepBack()` | Single-bar nudge with pause. |
| `seekTo(idx)` | Jump to an index (used by the scrubber). |
| `jumpToTrade(entryIdx)` | Used from the trade list — activates replay and seeks to the entry bar. |

## BUG-020 safety net

The store watches `total` and forces `deactivate()` + `currentIdx = 0` whenever the backtest store clears its candle array. Without that, a running playback timer would continue against an empty array, the scrubber's `:max` would go negative, and `currentCandle` would be undefined. The watcher uses `flush: 'sync'` so cleanup happens in the same tick as the candles reassignment, before any setInterval callback can observe `total = 0`.

## What this file does NOT do

It does not contain any drawing code. The visual "partial reveal" effect is implemented inside [[chartpane_applyData]] — this store only publishes the frontier index that drawing code observes.
