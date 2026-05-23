# Logic Lens Audit Findings

Generated: 2026-05-23
Lens: Logic Expert (contradictions, stale values, impossible states, rule-vs-outcome consistency, off-by-one, state-machine integrity, reactive dependencies)

## Section: Header
- **LOG-H-1** | High | frontend/src/App.vue:10 — Replay visibility hinges on `candles.length` only. SSE error path leaves replay active over zero-length candles → divide-by-zero on `total - 1`.
  - Fix: Call `replay.deactivate()` at the start of `backtest.run()`.
- **LOG-H-2** | Medium | frontend/src/App.vue:19-24 — Run Backtest button doesn't clear prior error; contradictory state Idle + stale error.
  - Fix: Clear `error` on next click or surface explicit "Retry".

## Section: SettingsPanel
- **LOG-S-1** | High | frontend/src/stores/settings.ts:34-44 — `reset()` does `Object.assign(params, DEFAULTS)` — if a new field is added to `params` without updating DEFAULTS, stale value persists silently.
  - Fix: `for (const k of Object.keys(params)) delete params[k]; Object.assign(params, DEFAULTS)`.
- **LOG-S-2** | Medium | frontend/src/components/SettingsPanel.vue:56-63 — Missing constraint between `total_contracts` and `leg1+leg2+leg3`; ProgressBar `maxLegs` ignores `total_contracts`.
- **LOG-S-3** | Medium | frontend/src/components/SettingsPanel.vue:124 — `rsiPeriod` `:min="2"` but no NaN guard on `v-model.number`.

## Section: ProgressBar
- **LOG-P-1** | High | frontend/src/components/ProgressBar.vue:27 — After completion, `progress.current_idx` remains the last partial; bar shows "990/1000" while metrics reflect full 1000.
  - Fix: On `complete`, set `progress = { ..., current_idx: total-1, percent: 100 }`.
- **LOG-P-2** | Medium | frontend/src/components/ProgressBar.vue:51 — `Legs filled` flickers `0/4` between trades.
- **LOG-P-3** | Medium | frontend/src/components/ProgressBar.vue:8-12 — Error precedence chain: catch-block may overwrite SSE error.

## Section: ReplayBar
- **LOG-R-1** | Critical | frontend/src/stores/replay.ts:50-61, 79 — Clicking "Run Backtest" while replay is active: `candles` cleared → `total=0` → `seekTo` clamps to `-1` → `currentCandle = candles[-1]` undefined; scrubber `max=-1`.
  - Fix: Watch `backtest.candles.length` in replay store; on change, `deactivate()` or reset `currentIdx=0`.
- **LOG-R-2** | High | frontend/src/stores/replay.ts:24-28 — `runningPnl` filters by `exit_idx <= currentIdx`; for `entry_idx == exit_idx` trades PnL credit appears at entry candle.
- **LOG-R-3** | Medium | frontend/src/components/ReplayBar.vue:70 — Combined with LOG-R-1: `:max=-1` invalid HTML.

## Section: MetricsCards
- **LOG-M-1** | High | frontend/src/components/MetricsCards.vue:12 — `formatDollar(-metrics.max_drawdown)` negates backend's positive magnitude; `$0.00` becomes `+$0.00` in red.
- **LOG-M-2** | High | frontend/src/components/MetricsCards.vue:7-15 — With `total_trades===0`, all cards show "0.00"/"+$0.00" — BUG-011/008.
- **LOG-M-3** | Medium | frontend/src/components/MetricsCards.vue:13-14 — Avg Loss zero+red contradiction.
- **LOG-M-4** | Medium | src/api/app.py:381,409 — `losses` includes breakeven; `profit_factor=0` when all wins — BUG-012 contradiction.

## Section: ChartPane + BoxesPrimitive
- **LOG-C-1** | Critical | frontend/src/components/ChartPane.vue:326 — EMA period change doesn't update chart title strings ("EMA20" stays after period changed to 5).
  - Fix: Call `applyOptions({title: ...})` in period watcher.
- **LOG-C-2** | High | frontend/src/components/ChartPane.vue:129-138 — No `entry_idx <= exit_idx` assertion at render boundary; BUG-002 surface.
  - Fix: Assertion + console.warn.
- **LOG-C-3** | High | frontend/src/components/ChartPane.vue:159-218 — `applyData` recomputes markers/indicators on every replay tick — O(N) every 200ms.
  - Fix: Memoize indicator results or recompute only on data change.
- **LOG-C-4** | High | frontend/src/components/BoxesPrimitive.ts:74-101 — `_barTimes` shrinks during replay (set from `rows = candles.slice(0, viewTo+1)`); boxes can vanish during replay.
  - Fix: Pass FULL `candles` times to `setBarTimes`, only slice the candle series data.
- **LOG-C-5** | Medium | frontend/src/components/BoxesPrimitive.ts:103 — `x1 >= x2` silently drops degenerate boxes; verified that line 92 already catches the all-negative case.

## Section: TradeList
- **LOG-T-1** | High | frontend/src/components/TradeList.vue:102-106 — `:key="${t.entry_idx}-${t.exit_idx}"` may collide on dual-mode re-entries.
  - Fix: Include `i` or `direction` in the key.
- **LOG-T-2** | Medium | frontend/src/components/TradeList.vue:68-75 — Cell shows `weekly_level + monthly_level`, but only one fires (weekly priority); "W-RH + —" implies both contributed.
  - Fix: Show only firing level or label `(priority: weekly)`.
- **LOG-T-3** | High | src/strategy/box_lookup.py:160-184 — `get_signal_detail` returns both weekly and monthly signals independently; weekly fires long + monthly fires short → silently drop conflict; trade enters long while tooltip claims both contributed.
  - Impact: BUG-008 canonical — contradictory narrative.
  - Fix: Add `conflict: True/False` flag; or refuse to fire on conflicting signals.
- **LOG-T-4** | Medium | frontend/src/components/TradeList.vue:99 — `displayed = computed(() => props.trades)` no-op alias.

## Summary
- Total: 22 | Critical: 2 | High: 11 | Medium: 9 | Low: 0
