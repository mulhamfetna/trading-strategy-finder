# Trading Lens Audit Findings

Generated: 2026-05-23
Lens: Expert Trader (signal realism, execution realism, risk asymmetry, scaling logic, stop/TP placement, strategy plausibility, NQ-specific behavior)

## Section: Header
- **TRD-H-1** | Low | frontend/src/App.vue:5 — Header text "NQ 1-1-2 Scaling Strategy Dashboard" is hard-coded even when the user picks "TradingView Box" mode. Pattern matches BUG-014.
  - Fix: Bind the title to `settings.strategyMode`.
- **TRD-H-2** | Medium | frontend/src/App.vue:9-15,17-25 — "Replay" and "Run Backtest" buttons are not mutually disabled. Starting a new backtest mid-replay leaves the replay store pointing at stale candles.
  - Fix: Force `replay.deactivate()` inside `backtest.run()` before clearing arrays.

## Section: SettingsPanel
- **TRD-S-1** | High | frontend/src/components/SettingsPanel.vue:62-63,84,93-94 — Point-distance fields have no `min`. Negative or zero values are accepted; engine then fires legs above the base on a long.
  - Fix: Add `:min="0.25"` (one tick) on all point-distance NumFields; clamp in `_check_exits`.
- **TRD-S-2** | High | frontend/src/components/SettingsPanel.vue:93-94 — No ordering constraint between `sl_soft_points` and `sl_hard_points`. If `sl_soft > sl_hard`, dual-SL semantics silently inverted.
  - Fix: Validate `sl_hard >= sl_soft`; show inline error.
- **TRD-S-3** | High | frontend/src/components/SettingsPanel.vue:62-63 — No constraint that leg3 > leg2 pullback.
  - Fix: Add validation `leg3 > leg2`.
- **TRD-S-4** | Medium | frontend/src/components/SettingsPanel.vue:56 — `total_contracts` is exposed but never used in engine math; engine uses `leg1+leg2+leg3` or `big_candle_full_contracts`.
  - Fix: Drive sizing from `total_contracts` or remove field.
- **TRD-S-5** | Medium | frontend/src/components/SettingsPanel.vue:62-63,71,84,93-94 — No NQ tick-size snap (0.25 pts).
  - Fix: Round to 0.25 on blur, or use `:step="0.25"`.
- **TRD-S-6** | Medium | frontend/src/components/SettingsPanel.vue:1-146 — No session/RTH filter; strategy executes on weekend gap candles.
  - Fix: Add RTH-only / ETH / 24h selector wired to backend.
- **TRD-S-7** | Low | frontend/src/components/SettingsPanel.vue:71 — `big_candle_threshold_points` has no `min=0`; setting to 0 makes every candle "big".
  - Fix: `:min="50"` or similar.

## Section: ProgressBar
- **TRD-P-1** | Low | frontend/src/components/ProgressBar.vue:76-78 — `maxLegs = leg1+leg2+leg3` (4) but engine can use `big_candle_full_contracts` (4 default) — for non-default params, ratio is wrong.
  - Fix: `maxLegs = max(legs_sum, big_candle_full_contracts)`.
- **TRD-P-2** | Low | frontend/src/components/ProgressBar.vue:27 — Counter references 4h candles only; no minute-timeframe indication.
  - Fix: Display secondary "minute X/Y within window".

## Section: ReplayBar
- **TRD-R-1** | High | frontend/src/components/ReplayBar.vue:50-55 + replay.ts:25-29 — `runningPnl` sums only completed trades; entries that JUST closed snap from 0 to final P&L in a single tick (no incremental unrealized).
  - Impact: Replay scrub shows future info — trader can't observe drawdown/MFE during the hold.
  - Fix: While `entry_idx ≤ currentIdx < exit_idx`, compute unrealized PnL from current bar close vs avg_entry_price.
- **TRD-R-2** | High | frontend/src/stores/replay.ts:34 — `activeTrade` finds only the first matching trade; scaling trades have multi-bar leg-fills which are never visualized.
  - Fix: Render per-leg markers from `trade.legs[].candle_idx`.
- **TRD-R-3** | Medium | frontend/src/components/ReplayBar.vue:67-74 — Scrubber lets user scrub backward and still see entry markers, leaking foresight of future trades.
  - Fix: Hide entry markers unless `exit_idx <= currentIdx`.
- **TRD-R-4** | Low | frontend/src/components/ReplayBar.vue:30-39 — Max speed 25× insufficient for 1-min CSV.
  - Fix: Add 100× / 500× / "skip to next trade".

## Section: MetricsCards
- **TRD-M-1** | High | frontend/src/components/MetricsCards.vue:12 — Sign of Max DD ambiguous between negation and color, BUG-005 pattern.
  - Fix: `Math.abs(metrics.max_drawdown)` with explicit sign prefix.
- **TRD-M-2** | Medium | frontend/src/components/MetricsCards.vue:11 — Sharpe shown without sample-size guard.
  - Fix: Show "N/A" when total_trades < 20.
- **TRD-M-3** | Medium | frontend/src/components/MetricsCards.vue:10 — Profit Factor shown unconditionally; if gross_loss=0, "Infinity"/"NaN" possible.
  - Fix: Conditional rendering, fallback to "N/A".
- **TRD-M-4** | Medium | frontend/src/components/MetricsCards.vue:13-14 — No "Holding Time"/"Avg Trade Duration" metric. BUG-014 echo.
  - Fix: Add Avg Holding Bars card.

## Section: ChartPane
- **TRD-C-1** | High | frontend/src/components/ChartPane.vue:128-152 — Entry marker placed at `rows[t.entry_idx]`. In 4h-only Box mode it points one bar earlier than physical possibility (close already happened).
  - Fix: Normalize `entry_idx` to "bar where order actually filled" in both code paths.
- **TRD-C-2** | High | frontend/src/components/ChartPane.vue:140-151 — Exit marker uses `rows[t.exit_idx]` for the 4h bar, but actual exit happened at 1-min `exit_time`.
  - Fix: Use `exit_time` for ChartPane marker tooltip.
- **TRD-C-3** | Medium | frontend/src/components/ChartPane.vue:122-138 — Trade markers ignore per-leg fills.
  - Fix: Render `t.legs[]` with smaller markers / dotted price lines.
- **TRD-C-4** | Medium | frontend/src/components/ChartPane.vue:104-109 — `toUTCTimestamp` forces Z on naive timestamps; NQ futures CSV is CT/ET.
  - Fix: Surface source timezone of the CSV and convert explicitly.
- **TRD-C-5** | Medium | frontend/src/components/ChartPane.vue:217 — `fitContent()` runs on every `applyData()` including every replay tick.
  - Fix: Only `fitContent()` on initial load.

## Section: TradeList
- **TRD-T-1** | High | frontend/src/components/TradeList.vue:55,108-111 — `exitTime` falls back to `candleTime(exit_idx)` (4h bar open) when no `exit_time` set — exit time can appear up to 4h before actual exit.
  - Fix: Engine must always write `exit_time`.
- **TRD-T-2** | High | frontend/src/components/TradeList.vue:54,102-106 — `candleTime(entry_idx)` returns the 4h candle's open. In 4h-only entries this is up to 4h before actual fill.
  - Fix: Store explicit `entry_time` on the trade.
- **TRD-T-3** | Medium | frontend/src/components/TradeList.vue:56-57 — No leg-by-leg breakdown, no MFE, no hold duration.
  - Fix: Expandable row with legs[] / pullback levels / hold bars.
- **TRD-T-4** | Medium | frontend/src/components/TradeList.vue:64 — `exit_reason` "TAKE PROFIT (TRAIL)" inner-loop uses 1-min closes not 2-min as documented.
  - Fix: Re-sample to 2-min or update docs.
- **TRD-T-5** | Medium | frontend/src/components/TradeList.vue:99 — No direction/exit_reason/date filtering.
  - Fix: Add filter chips.
- **TRD-T-6** | Low — **NOTE: this finding is outdated**. BOX_STRATEGY.md still describes the legacy "both must agree" rule; the user explicitly abandoned that rule in this conversation. `box_lookup.py:154-157` correctly fires on EITHER (weekly priority). The DOCUMENTATION (BOX_STRATEGY.md:69-71) needs updating, not the code.
  - Fix: Update BOX_STRATEGY.md to describe single-box (weekly-priority) rule.

## Summary
- Total: 27 | Critical: 0 | High: 9 | Medium: 13 | Low: 5
