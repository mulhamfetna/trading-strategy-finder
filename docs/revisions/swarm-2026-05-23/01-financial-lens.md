# Financial Lens Audit Findings

Generated: 2026-05-23
Lens: Expert Financial Consultant (metric correctness, accounting consistency, fee/slippage/PnL math, point-value handling, capital reconciliation, EV/Sharpe/profit-factor)

## Section: Header
- **FIN-H-1** | Medium | frontend/src/App.vue:5 — Title hard-codes "NQ 1-1-2 Scaling Strategy Dashboard" but the SettingsPanel now lets users select the TradingView Box strategy mode.
  - Impact: Misleading branding — a Box backtest run is reported under a Scaling banner, undermining attribution/auditability of metrics shown below it.
  - Fix: Bind the heading text to `settings.strategyMode` (e.g. "NQ Box Strategy Dashboard" when `box`).
- **FIN-H-2** | Low | frontend/src/App.vue:6 — Subtitle says "phase D" but no capital/period/dataset summary appears in the header.
  - Impact: Header KPI quick-check item ("no stale period labels, final capital reconciles") cannot be satisfied — there is no header reconciliation surface.
  - Fix: Add a small header strip showing run dates and net P/L pulled from `backtest.metrics` once a run is complete.

## Section: SettingsPanel
- **FIN-S-1** | High | frontend/src/components/SettingsPanel.vue:57 — `point_value` is a user-editable NumField with no min lock at `2.0` for NQ and no contract-symbol hint.
  - Impact: Direct violation surface for BUG-001 — a user can silently set `point_value=1` or `0.5` and every dollar metric downstream is wrong while still appearing valid. The canonical lock `test_run_backtest_15min_uses_nq_point_value_for_pnl` only guards the legacy 15-min path, not this UI input.
  - Fix: Treat `point_value` as a per-instrument constant (lookup from a symbol dropdown) or at minimum warn when ≠ 2.0 for NQ; persist it in a read-only "Instrument" group.
- **FIN-S-2** | High | frontend/src/components/SettingsPanel.vue:55-65 — No fee / commission / slippage inputs anywhere in the panel, even though `Trade.fees_paid` and `Metrics.total_fees` exist in the schema.
  - Impact: Scaling/Box backtests run with zero fees regardless of contract count — net vs gross are identical, profit_factor and EV are pre-fee under a "Net Profit" label (BUG-006, BUG-009).
  - Fix: Add `fee_per_contract` and `slippage_points` inputs wired into `ScalingParamsModel` and applied in `_build_trade`.
- **FIN-S-3** | Medium | frontend/src/components/SettingsPanel.vue:56-60 — `total_contracts` and `leg1+leg2+leg3` are independent fields; nothing enforces `leg1+leg2+leg3 == total_contracts`.
  - Impact: User can ship `total_contracts=4` but `1+1+3=5` legs; `big_candle_full_contracts` can also drift from `total_contracts`, breaking position-sizing accounting.
  - Fix: Validate sum on change; derive `total_contracts` instead of accepting it.
- **FIN-S-4** | Medium | frontend/src/components/SettingsPanel.vue:84-95 — TP/SL are entered in points but not validated against pullback distances; e.g. `sl_soft_points < leg3_pullback_points` will stop out before leg-3 fills.
  - Impact: Risk model becomes internally inconsistent (related to BUG-013).
  - Fix: Cross-field validation warning when SL points ≤ deepest pullback.
- **FIN-S-5** | Low | frontend/src/components/SettingsPanel.vue: whole file — No "initial_capital" field, yet `Metrics.final_capital` ships in the schema.
  - Impact: Capital reconciliation is unanchored — `final_capital` is never computed by `_scaling_metrics`. Frontend cannot reconcile return % to initial capital.
  - Fix: Add capital input and compute return % in `_scaling_metrics`.

## Section: ProgressBar
- **FIN-P-1** | High | frontend/src/components/ProgressBar.vue:31 — `pnl_so_far` is displayed as "+$X" but is computed in `scaling_strategy.py:288` as `sum(profit_dollars)` with no fee deduction.
  - Impact: Net/gross conflation in a live counter the user trusts (BUG-006/BUG-009). The label "PnL" implies net, the math is pre-fee.
  - Fix: Once fees are introduced (FIN-S-2), subtract them in `pnl_so_far`; otherwise rename to "Gross PnL".
- **FIN-P-2** | Medium | frontend/src/components/ProgressBar.vue:36 — `win_rate_so_far.toFixed(1)` is rendered even when `trades_so_far == 0`; backend returns `0.0` for that case.
  - Impact: Violates BUG-011 — undefined statistic displayed as a hard zero.
  - Fix: Render "—" when `progress.trades_so_far === 0`.
- **FIN-P-3** | Medium | frontend/src/components/ProgressBar.vue:76-78 — `maxLegs` is computed from the live settings store, not from the in-flight run's params snapshot.
  - Impact: If the user edits leg counts mid-run, "Legs filled X / Y" shows mismatched Y vs the actual run's denominator.
  - Fix: Snapshot params at run start and read denominator from the SSE-payload.

## Section: ReplayBar
- **FIN-R-1** | High | frontend/src/stores/replay.ts:25-28 — `runningPnl` sums `t.profit_dollars` only for trades whose `exit_idx <= currentIdx`; it ignores unrealized P/L of the currently open position.
  - Impact: At any replay frame where a trade is open, the displayed running P/L is stale by the size of the open MTM exposure. With 1-4 contracts × 100-300 pt moves × $2/pt this is hundreds-to-thousands of dollars hidden during the most critical replay moments.
  - Fix: Add unrealized = `(currentClose − avg_entry_price) × contracts × point_value × directionSign` for the active trade and add to `runningPnl`.
- **FIN-R-2** | Medium | frontend/src/components/ReplayBar.vue:46 — `runningPnl` is labeled by formatting alone (no "Net"/"Gross" caption) and uses the same `profit_dollars` that omits fees.
  - Impact: Net/gross conflation in the replay overlay (BUG-006).
  - Fix: Caption the chip "Gross PnL" until fees are implemented.
- **FIN-R-3** | Low | frontend/src/stores/replay.ts:31-35 — `activeTrade` uses `findIndex` so it only returns the FIRST trade matching the window.
  - Impact: Fragile under future scaling-out variants.
  - Fix: Document the single-position invariant or return all matches.

## Section: MetricsCards
- **FIN-M-1** | High | frontend/src/components/MetricsCards.vue:12 — `Max DD` is rendered as `formatDollar(-metrics.max_drawdown)` while `_scaling_metrics` (src/api/app.py:387-398) returns a NON-NEGATIVE magnitude in dollars. Negating it produces `-$N` for a real drawdown and `+$0.00` for zero (because `-0 >= 0`).
  - Impact: Sign/format contradiction; zero drawdown shows `+$0.00` in red.
  - Fix: Use `Math.abs` or render the magnitude without negation; handle `0` as unsigned.
- **FIN-M-2** | High | frontend/src/components/MetricsCards.vue:7 — Label says "Net Profit" but `total_profit` from `_scaling_metrics` (src/api/app.py:384, 406) equals `gross_profit + gross_loss` with no fee deduction.
  - Impact: Directly violates BUG-006 / FIX-2026-05-21-01. The headline KPI is gross, not net.
  - Fix: Rename to "Gross P/L" until fees are wired, or compute `net = total_profit − total_fees`.
- **FIN-M-3** | High | frontend/src/components/MetricsCards.vue:10 — `profit_factor.toFixed(2)` is rendered even when backend returns hard `0.0` for "undefined" cases.
  - Impact: BUG-011 — PF=0 displayed where PF is mathematically undefined.
  - Fix: Backend should return `None`/`"N/A"` when `gross_loss == 0`; frontend should render `'∞'` or `'N/A'`.
- **FIN-M-4** | High | frontend/src/components/MetricsCards.vue:11 — `sharpe_ratio.toFixed(2)` similarly shows hard `0.00` when `std == 0`.
  - Impact: BUG-011 again.
  - Fix: Return `None` from backend when `std == 0` or `n < 2`; render `N/A`.
- **FIN-M-5** | High | src/api/app.py:381,383,409 — `losses` includes break-even trades (`profit_dollars <= 0`) AND `gross_loss` is summed (negative). When all trades are wins, `gross_loss == 0` → `profit_factor = 0`.
  - Impact: Profit factor inverting a perfect strategy into a "no edge" report.
  - Fix: Use `profit_dollars < 0` for losses, return `float('inf')` or `None` when no losers.
- **FIN-M-6** | High | src/api/app.py:414 — `expected_value` is `mean(profit_dollars)` — no fee adjustment.
  - Impact: BUG-009 — EV labeled net is actually gross.
  - Fix: Subtract per-trade fee in mean once fees exist.
- **FIN-M-7** | Medium | frontend/src/components/MetricsCards.vue: full file — No display for `total_fees`, `gross_profit`, `net_profit`, `final_capital`, `expected_value`, `max_consecutive_losses`.
  - Impact: Capital reconciliation and fee transparency invisible to the user.
  - Fix: Add cards for at least `total_fees`, `final_capital`, `expected_value`.
- **FIN-M-8** | Medium | frontend/src/components/MetricsCards.vue:13-14 — `avg_profit` and `avg_loss` rendered with `formatDollar` which prefixes `+` for non-negative values; `avg_loss=0` yields `"+$0.00"` colored red.
  - Impact: BUG-005 family.
  - Fix: Handle zero-loser case explicitly (`N/A`).

## Section: ChartPane
- **FIN-C-1** | Medium | frontend/src/components/ChartPane.vue:146-148 — Exit marker color uses `t.profit_dollars >= 0` but the marker text shows `profit_points.toFixed(0)`.
  - Impact: Coupling fragile.
  - Fix: Drive both from `profit_dollars` sign.
- **FIN-C-2** | Medium | frontend/src/components/ChartPane.vue:104-109 — `toUTCTimestamp` forces a `Z` suffix on naive timestamps. NQ futures CSV is exchange-time (CT/ET).
  - Impact: Session-attribution bug (BUG-003 family).
  - Fix: Document the TZ convention; convert explicitly rather than tagging.
- **FIN-C-3** | Low | frontend/src/components/ChartPane.vue:59-93 — Frontend EMA/RSI may not match backend indicator math.
  - Impact: Chart overlays could disagree with engine signals.
  - Fix: Ship indicator values from the backend payload.

## Section: TradeList
- **FIN-T-1** | High | frontend/src/components/TradeList.vue:58-63 — Points and Dollars cells labeled by header alone (`Pts`, `$`) with no "gross/net" qualifier.
  - Impact: BUG-006 — gross figures read as net.
  - Fix: Compute net per row or rename header to "Gross $".
- **FIN-T-2** | High | frontend/src/components/TradeList.vue: file — No "Contracts" column despite the `ScalingTrade.contracts` field.
  - Impact: Auditor cannot reconstruct `profit_dollars = profit_points × contracts × $2`.
  - Fix: Add a "Qty" column.
- **FIN-T-3** | Medium | frontend/src/components/TradeList.vue:148 — CSV export emits `Points`/`Dollars` but no fees, no contracts × point_value reconciliation, no "values are gross" header.
  - Impact: Exported audit artifact ambiguous.
  - Fix: Add `Contracts`, `PointValue`, `Fees`, `NetDollars` columns.
- **FIN-T-4** | Medium | frontend/src/components/TradeList.vue: file — No `Holding Time` column. BUG-014 undiagnosable.
  - Fix: Render `exit_time − entry_time`.
- **FIN-T-5** | Medium | frontend/src/components/TradeList.vue:55,109-111 — `exitTime(t)` falls back to candle time at `t.exit_idx` (4h bar containing exit) when no `exit_time`.
  - Impact: BUG-002 surface — exit timestamp not strictly later than entry.
  - Fix: Append `+4h` to exit time when only bar index is known.
- **FIN-T-6** | Low — No financial finding.
- **FIN-T-7** | Low | frontend/src/components/TradeList.vue:64 — No realized-slippage column — BUG-013 surface.
  - Fix: Add a `Slippage` column.

## Summary
- Total: 31 | Critical: 0 | High: 13 | Medium: 13 | Low: 5
- **Post-cleanup note (2026-05-23):** All legacy-only findings dropped. The Max DD unit-collision finding (FIN-M-1) was originally Critical because the legacy `calculate_metrics` path emitted DD in percent while scaling emitted dollars; with the legacy path deleted in this same cleanup, the issue downgrades to a High (sign/format only).
