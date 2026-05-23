# Technical Lens Audit Findings

Generated: 2026-05-23
Lens: Technical Expert (code quality, data pipeline integrity, exception handling, deterministic behavior, race conditions, type-safety, security)

## Section: Header
- **TECH-H-1** | Medium | frontend/src/App.vue:76-89 — `onKey` doesn't skip `<textarea>` or contenteditable.
- **TECH-H-2** | High | frontend/src/App.vue:21 — Run Backtest enabled while `replay.isActive` → race condition (clears candles while replay timer runs).
  - Fix: Disable button while replay active or call `replay.deactivate()` at top of `backtest.run()`.

## Section: SettingsPanel
- **TECH-S-1** | Low | frontend/src/components/SettingsPanel.vue:56-77 — No `:min` on point fields; no leg-sum invariant.
- **TECH-S-2** | Medium | frontend/src/components/SettingsPanel.vue:24-39 — `data_path`/`min_data_path` unvalidated → `os.path.exists("/etc/passwd.csv")` accepted; error messages leak FS info.
  - Fix: Normalize via `os.path.basename` and require under repo root.

## Section: ProgressBar
- **TECH-P-1** | Low | frontend/src/components/ProgressBar.vue:75-78 — `maxLegs` from `leg1+leg2+leg3` ignores big-candle exception.
- **TECH-P-2** | Medium | frontend/src/components/ProgressBar.vue:27 — `current_idx + 1` can show `total/total` mid-stream.

## Section: ReplayBar
- **TECH-R-1** | High | frontend/src/stores/replay.ts:54-61 — `setInterval` timer has no scope-dispose hook; HMR leaves ghost timers.
  - Fix: `onScopeDispose(_stopTimer)` or App `onBeforeUnmount` hook.
- **TECH-R-2** | Medium | frontend/src/components/ReplayBar.vue:30 — `.number` modifier fragile pattern.
- **TECH-R-3** | Medium | frontend/src/stores/replay.ts:31-35 — `activeTrade` O(N) on every reactive read at 200ms.

## Section: MetricsCards
- **TECH-M-1** | High | frontend/src/types.ts:60-79 vs src/api/schemas.py:81-97 — TypeScript declares fields the scaling backend never sends (`total_fees`, `final_capital`, `max_consecutive_losses`). Pydantic `Metrics` shape bypassed by `_scaling_metrics` raw dict.
  - Fix: Dedicated `ScalingMetrics` Pydantic model + mirror in TS.
- **TECH-M-2** | Low | frontend/src/components/MetricsCards.vue:12 — Sign-flip on `max_drawdown`.

## Section: ChartPane / BoxesPrimitive
- **TECH-C-1** | High | frontend/src/components/ChartPane.vue:326 — `watch([candles, trades, boxes], applyData, { deep: false })` shallow watch; future in-place mutation (live streaming) won't trigger redraw.
- **TECH-C-2** | High | frontend/src/components/ChartPane.vue:159-218 — Full `setData(toLwcData(rows))` re-sent every tick; O(N) every 200ms.
  - Fix: Use `series.update()` for incremental data; skip `fitContent` during replay.
- **TECH-C-3** | Medium | frontend/src/components/BoxesPrimitive.ts:40-47 — `lowerBound` off-by-one when `box.end_time` exactly matches a bar time (box right edge dropped).
  - Fix: Use `upperBound` then subtract 1.
- **TECH-C-4** | Medium | frontend/src/components/BoxesPrimitive.ts:75,90 — Excess overdraw when both x out-of-range.
- **TECH-C-5** | High | frontend/src/components/BoxesPrimitive.ts:26-35 vs frontend/src/types.ts:159-168 — `BoxRect` declared twice; drift risk.
  - Fix: Re-export from `BoxesPrimitive.ts` via `import type { BoxRect } from '../types'`.
- **TECH-C-6** | Medium | frontend/src/components/ChartPane.vue:104-109 — `Z` suffix on local timestamps; systematic 5-6h drift.
- **TECH-C-7** | Low | frontend/src/components/ChartPane.vue:222-233 — Primitives not detached before `chart.remove()`.

## Section: TradeList
- **TECH-T-1** | Medium | frontend/src/components/TradeList.vue:99 — Vestigial `displayed` computed.
- **TECH-T-2** | Medium | frontend/src/components/TradeList.vue:138-168 — Synchronous CSV export blocks UI for 10k+ trades.
- **TECH-T-3** | High | frontend/src/components/TradeList.vue:42 — `:key="${entry_idx}-${exit_idx}"` collides on re-entry same-candle trades.
  - Fix: Add index to key.
- **TECH-T-4** | Low | frontend/src/components/TradeList.vue:138 — CSV headers include `Contracts` but table doesn't show it.

## Cross-cutting Backend
- **TECH-X-2** | High | src/api/app.py:55-63 — `allow_origins=["*"]`; `/api/upload-data-file` accepts uploads from any web page.
  - Fix: `MAX_UPLOAD_BYTES`, restrict origins, or require `X-Local-Token`.
- **TECH-X-3** | High | src/api/app.py:235-245 — `await file.read()` with no size cap.
  - Fix: Stream + max-bytes limit.
- **TECH-X-4** | Medium | src/api/app.py:269-308 — Daemon worker holds resources on client disconnect.
- **TECH-X-5** | Medium | src/strategy/box_strategy.py:172 — Bare `except Exception → None`.
- **TECH-X-6** | Medium | src/api/app.py — 1-min load failure silently degrades; no UI signal.

## Summary
- Total: 23 | Critical: 0 | High: 8 | Medium: 11 | Low: 4
- **Post-cleanup note (2026-05-23):** TECH-X-1 dropped — referenced `src/signals/ml_filter.py:89` which was erased with the legacy purge.
