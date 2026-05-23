# QC Lens Audit Findings

Generated: 2026-05-23
Lens: QC / Quality Control (output sampling, acceptance criteria, value ranges, formatting consistency, edge-case rendering, what the user actually sees)

## Section: Header
- **QC-H-1** | Low | frontend/src/App.vue:6 — Static literal "phase D" subtitle.
- **QC-H-2** | Low | frontend/src/App.vue:5 — Title contradicts active strategy mode.
- **QC-H-3** | Medium | frontend/src/App.vue:9-16 — No global replay-mode indicator in header.

## Section: SettingsPanel
- **QC-SP-1** | Medium | frontend/src/components/SettingsPanel.vue:56-64 — No client-side validation `leg1+leg2+leg3 == total_contracts`.
- **QC-SP-2** | Medium | frontend/src/components/SettingsPanel.vue:62-63 — Pullback fields allow negative.
- **QC-SP-3** | Low | frontend/src/components/SettingsPanel.vue:93-94 — SL/TP fields allow negative.
- **QC-SP-4** | Low | frontend/src/components/SettingsPanel.vue:114-124 — RSI period stays editable when RSI hidden; no opacity cue.
- **QC-SP-5** | Low | frontend/src/components/SettingsPanel.vue:43-48 — Start/End placeholders don't adapt to filled-state.

## Section: ProgressBar
- **QC-PB-1** | Medium | frontend/src/components/ProgressBar.vue:36 — `win_rate.toFixed(1)` shows "0.0%" — indistinguishable from "no trades".
- **QC-PB-2** | Medium | frontend/src/components/ProgressBar.vue:51 — `maxLegs=0` if user blanks leg fields → "X / 0".
- **QC-PB-3** | Low | frontend/src/components/ProgressBar.vue:10 — Elapsed always "ms".
- **QC-PB-4** | Low | frontend/src/components/ProgressBar.vue:80-81 — Percent contract not asserted; future 0..1 emit would saturate at <1%.
- **QC-PB-5** | Low | frontend/src/components/ProgressBar.vue:84-86 — `+$0.00` when 0.

## Section: ReplayBar
- **QC-RB-1** | Low | frontend/src/components/ReplayBar.vue:46 — `+$0.00` at 0.
- **QC-RB-2** | Low | frontend/src/components/ReplayBar.vue:93-95 — `formatTime` truncates seconds via naive `.slice(0,16)`; if upstream emits BUG-003 pattern (Timestamp + Time concat), display becomes `"2025-01-03 00:00:0"`.
- **QC-RB-3** | Low | frontend/src/components/ReplayBar.vue:67-74 — `:max=-1` when total=0.

## Section: MetricsCards
- **QC-MC-1** | High | frontend/src/components/MetricsCards.vue:10-11 — PF/Sharpe `"0.00"` instead of N/A (BUG-011 regression).
- **QC-MC-2** | Medium | frontend/src/components/MetricsCards.vue:9 — `win_rate.toFixed(1)` shows "0.0%" with 0 trades.
- **QC-MC-3** | High | frontend/src/components/MetricsCards.vue:12 — `formatDollar(-max_drawdown)`: `-$500.00` red for $500 DD; `-0 >= 0` evaluates true so `+$0.00` shown for zero DD.
- **QC-MC-4** | Medium | frontend/src/components/MetricsCards.vue:13-14 — Avg Loss force-red; if backend ever sends positive, +red contradiction.
- **QC-MC-5** | Medium | frontend/src/components/MetricsCards.vue: all — No thousands separator.
- **QC-MC-6** | Low | frontend/src/components/MetricsCards.vue:7 — "Net Profit" label, server value is gross.

## Section: ChartPane
- **QC-CP-1** | Medium | frontend/src/components/ChartPane.vue:104-109 — `toUTCTimestamp` adds `Z`; NQ CSV is CT/ET.
- **QC-CP-2** | Medium | frontend/src/components/ChartPane.vue:148 — Exit-marker label sign derived from dollars, value shown in points; for fractional positive dollars rounding to 0 points → "+0".
- **QC-CP-3** | Medium | frontend/src/components/ChartPane.vue:192-197 — Volume/RSI panes always created; empty axis range visible when toggled off.
- **QC-CP-4** | High | frontend/src/components/ChartPane.vue:177-178 — EMA period unbounded; if period >= candles count, indicator silently disappears.
  - Fix: Show "EMA-200 unavailable, only 47 candles" overlay.
- **QC-CP-5** | Medium | frontend/src/components/BoxesPrimitive.ts:150-156 — Overlapping labels stack illegibly.
- **QC-CP-6** | Low | frontend/src/components/BoxesPrimitive.ts:155 — `labelY` clamps to visTop only, not visBottom.
- **QC-CP-7** | Medium | frontend/src/components/BoxesPrimitive.ts:127 — Border drawn across full x1..x2; visual ambiguity at overlapping weekly/monthly edges.

## Section: TradeList
- **QC-TL-1** | High | frontend/src/components/TradeList.vue:102-106 — `c.t.replace('T',' ').slice(0,16)` on upstream BUG-003 pattern → `"2025-01-03 00:00:0"` truncation.
- **QC-TL-2** | Medium | frontend/src/components/TradeList.vue:59 — `-0.04.toFixed(1)='-0.0'` displayed red.
- **QC-TL-3** | Medium | frontend/src/components/TradeList.vue:61-62 — Independent sign derivation for pts vs $; flat trade can show `-0.0 (red)` + `+$0.00 (green)`.
- **QC-TL-4** | Medium | frontend/src/components/TradeList.vue:99 — No defensive sort by entry time.
- **QC-TL-5** | Medium | frontend/src/components/TradeList.vue:65-78 — `max-w-[200px]` without `truncate`; multi-line wrap breaks row height.
- **QC-TL-6** | Low | frontend/src/components/TradeList.vue:73-74 — `.slice(5)` on short box-start strings yields empty.
- **QC-TL-7** | Low | frontend/src/components/TradeList.vue:64 — `exit_reason` plain text, unbounded cell.
- **QC-TL-8** | Low | frontend/src/components/TradeList.vue:165 — CSV filename only includes date; same-day backtests overwrite.
- **QC-TL-9** | Medium | frontend/src/components/TradeList.vue:7 — Header count lacks W/L breakdown.

## Summary
- Total: 36 | Critical: 0 | High: 4 | Medium: 18 | Low: 14
