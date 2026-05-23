# UX/UI Lens Audit Findings

Generated: 2026-05-23
Lens: UX/UI Expert (semantic color, readability, hierarchy, terminology, cognitive load, affordances, button states, empty states, a11y)

## Section: Header
- **UXUI-H-1** | Medium | frontend/src/App.vue:5 — Hardcoded title contradicts active strategy mode.
- **UXUI-H-2** | Medium | frontend/src/App.vue:6 — Subtitle "phase D" leaks internal dev jargon.
- **UXUI-H-3** | High | frontend/src/App.vue:10 — Replay button uses `v-if` (vanishes) vs Run Backtest uses `:disabled`. Inconsistent state pattern.
  - Fix: Use `:disabled` rather than `v-if`.
- **UXUI-H-4** | Medium | frontend/src/App.vue:9-25 — No `focus-visible` ring on header buttons.
  - Fix: `focus:ring-2 focus:ring-tv-blue focus:outline-none`.
- **UXUI-H-5** | Low | frontend/src/App.vue:23 — "Running..." ellipsis with no spinner.

## Section: SettingsPanel
- **UXUI-S-1** | High | frontend/src/components/SettingsPanel.vue:1-136 — 8 sections in 384px-wide aside with no collapse.
  - Fix: Collapsible sections with persisted open-state.
- **UXUI-S-2** | High | frontend/src/components/SettingsPanel.vue:128-135 — No "Apply" indication; user can't tell when settings take effect.
  - Fix: Show "Settings changed — Run Backtest to apply" hint.
- **UXUI-S-3** | Medium | frontend/src/components/SettingsPanel.vue:31-40 — Box file pickers appear/vanish on mode switch with no transition.
- **UXUI-S-4** | Medium | frontend/src/components/SettingsPanel.vue:54-65 — `point_value` placed in "Entry distribution" section — terminology mismatch.
- **UXUI-S-5** | Medium | frontend/src/components/SettingsPanel.vue:124 — RSI period not visually nested under the gating checkbox.
- **UXUI-S-6** | Medium | frontend/src/components/NumField.vue:1-15 — No unit suffix in number inputs; 7+ different point-value fields.
  - Fix: Add unit chip (e.g., "pts", "$", "contracts").
- **UXUI-S-7** | Low | frontend/src/components/SettingsPanel.vue:23 — Inline help-text styled like links but aren't.
- **UXUI-S-8** | Low | frontend/src/components/SettingsPanel.vue:7-15 — Default browser radios on dark theme.

## Section: ProgressBar
- **UXUI-P-1** | High | frontend/src/components/ProgressBar.vue:10 — `percentText` shows "0.0%" before first progress event arrives.
  - Fix: Show indeterminate animation until first event.
- **UXUI-P-2** | Medium | frontend/src/components/ProgressBar.vue:55-57 — `text-tv-red` on `bg-tv-red/10` may fail WCAG AA.
- **UXUI-P-3** | Medium | frontend/src/components/ProgressBar.vue:30-33 — `+$0.00` in green when pnl=0 (BUG-005 family).
- **UXUI-P-4** | Low | frontend/src/components/ProgressBar.vue:51 — Label "Legs" but denominator is contracts (max 3 vs 4).
- **UXUI-P-5** | Low | frontend/src/components/ProgressBar.vue:84-86 — No thousands separator.

## Section: ReplayBar
- **UXUI-R-1** | Medium | frontend/src/components/ReplayBar.vue:42-47 — `runningPnl >= 0` triggers green including exactly 0 (BUG-005 family).
- **UXUI-R-2** | Medium | frontend/src/components/ReplayBar.vue:10-24 — Tooltip inconsistency; Play/Pause missing.
- **UXUI-R-3** | Medium | frontend/src/components/ReplayBar.vue:67-74 — Scrubber missing current-position label, min/max time labels, trade-tick marks.
- **UXUI-R-4** | Medium | frontend/src/App.vue:76-89 — Key handler ignores textarea/contenteditable.
- **UXUI-R-5** | Low | frontend/src/components/ReplayBar.vue:62 — "✕" button has no `aria-label`.
- **UXUI-R-6** | Low | frontend/src/components/ReplayBar.vue:33-38 — Speed select lacks focus ring on dark theme.

## Section: MetricsCards
- **UXUI-M-1** | Critical | frontend/src/components/MetricsCards.vue:12 — `Max DD` always red, `-` prefix on positive backend value; "-$0.00" shown red when no DD.
- **UXUI-M-2** | High | frontend/src/components/MetricsCards.vue:13-14 — Empty-state zero gets wrong color (Avg Win green at 0, Avg Loss red at 0).
- **UXUI-M-3** | High | frontend/src/components/MetricsCards.vue:10-11 — PF/Sharpe `"0.00"` instead of N/A (BUG-011).
- **UXUI-M-4** | Medium | frontend/src/components/MetricsCards.vue:7 — Label "Net Profit" maps to `total_profit` (gross).
- **UXUI-M-5** | Medium — **FIXED THIS SESSION**: Empty-state placeholder added.
- **UXUI-M-6** | Medium | frontend/src/components/MetricCard.vue:3 — Values lack `tabular-nums`; column alignment broken.
- **UXUI-M-7** | Low | frontend/src/components/MetricsCards.vue:26-29 — `formatDollar` duplicated across 4 components.

## Section: ChartPane
- **UXUI-C-1** | High | frontend/src/components/ChartPane.vue:217 — `fitContent()` on every replay tick destroys user pan/zoom.
- **UXUI-C-2** | High | frontend/src/components/BoxesPrimitive.ts:74-101 — Boxes with off-screen prices still draw tinted full-height bands.
- **UXUI-C-3** | Medium | frontend/src/components/ChartPane.vue:233-243 — Chart bg `#131722` hardcoded; Tailwind drift risk.
- **UXUI-C-4** | Medium | frontend/src/components/ChartPane.vue:4-6 — Empty state lacks CTA.
- **UXUI-C-5** | Medium | frontend/src/components/ChartPane.vue:131-138 — No chart legend for B/S/squares.
- **UXUI-C-6** | Medium | frontend/src/components/ChartPane.vue:359, 366 — Fixed 520px chart height.
- **UXUI-C-7** | Low | frontend/src/components/BoxesPrimitive.ts:150-156 — Label color uses semi-transparent border_color.
- **UXUI-C-8** | Low | frontend/src/components/ChartPane.vue:283-303 — Volume + RSI panes always added; vertical space wasted.

## Section: TradeList
- **UXUI-T-1** | High | frontend/src/components/TradeList.vue:7 — No glossary/tooltip for exit reason jargon.
- **UXUI-T-2** | High | frontend/src/components/TradeList.vue:23 — Nested 384px scroll inside page scroll.
- **UXUI-T-3** | Medium | frontend/src/components/TradeList.vue:58-63 — "+$0.00" in green at exact zero.
- **UXUI-T-4** | Medium | frontend/src/components/TradeList.vue:131-136 — Replay rows not keyboard-focusable.
- **UXUI-T-5** | Medium | frontend/src/components/TradeList.vue:65-78 — No `truncate` on max-w cells.
- **UXUI-T-6** | Medium | frontend/src/components/TradeList.vue:139 — CSV header casing differs from UI labels.
- **UXUI-T-7** | Medium | frontend/src/components/TradeList.vue:7-19 — No filter/sort/search.
- **UXUI-T-8** | Low | frontend/src/components/TradeList.vue:31-37 — Inconsistent column header abbreviations.
- **UXUI-T-9** | Low | frontend/src/components/TradeList.vue:56-57 — No thousands separator on prices.
- **UXUI-T-10** | Low | frontend/src/components/TradeList.vue:113-126 — HTML `title` attr tooltip renders inconsistently.

## Summary
- Total: 41 | Critical: 1 | High: 8 | Medium: 23 | Low: 9
