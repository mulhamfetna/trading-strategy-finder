# Bug Checklist (All Previous Revisions)

Generated: 2026-05-21  
Scope: Consolidated known bugs and quality risks extracted from prior exported reviews and bug reports.

---

## How To Use

1. Run this checklist at the start of every revision/QA cycle (**Stage A: Known Bugs Pass**).
2. Mark each item as: `PASS`, `FAIL`, or `N/A`.
3. If a failed item is new or regressed, append it to the **Master Bug Register** section.

---

## A) Master Regression Checklist

| ID | Bug Pattern | Category | Severity | First Seen | Last Seen | Current Expectation |
|---|---|---|---|---|---|---|
| BUG-001 | NQ contract multiplier missing (`$2/point`) causing under-sized P/L | Financial logic | Critical | report-revision4 | report-revision4 | Must remain fixed in all future outputs |
| BUG-002 | Exit timestamp before entry timestamp | Data integrity | Critical | CRITICAL_TIMESTAMP_BUG | CRITICAL_TIMESTAMP_BUG | Must never occur |
| BUG-003 | Corrupted timestamp format (`YYYY-MM-DD 00:00:00 HH:MM:SS`) | Formatting/data | High | re_review/v3 | fixed in final review | Must remain clean |
| BUG-004 | Return string format `+-X%` | UI logic | High | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Must show valid signed format only |
| BUG-005 | Negative return shown in green | UX/UI | Medium | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Negative must be red |
| BUG-006 | Net/gross metric labeling mismatch | Financial semantics | High | re_review/v3 | revision5 (semantic concern) | Labels must be unambiguous (`gross_wins`, `net_profit`, etc.) |
| BUG-007 | Stale insights text from old dataset | Data freshness | Critical | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Insights must match current run only |
| BUG-008 | Contradictory insights (e.g., "all winning trades" with zero winners) | Logic/content | High | COMPREHENSIVE_BUG_REPORT | COMPREHENSIVE_BUG_REPORT | Narratives must reflect actual counts |
| BUG-009 | EV/Trade inconsistency with fee handling | Financial logic | Medium | COMPREHENSIVE_BUG_REPORT | re_review | EV formula and display must match |
| BUG-010 | Running capital mismatch in metrics logs | Financial/data | High | re_review | re_review | Capital path must reconcile per trade |
| BUG-011 | Profit factor / Sharpe displayed as raw zero when undefined | Statistical clarity | Medium | COMPREHENSIVE_BUG_REPORT | **FIXED 2026-05-23** in `_scaling_metrics` + `MetricsCards.vue:14-15` (backend emits `None`; frontend renders `N/A`). Regression tests: `tests/test_scaling_metrics.py`, `frontend/tests/MetricsCards.test.ts`. | Show `N/A` with reason when insufficient data |
| BUG-012 | R/R displayed while no valid winners or inconsistent with data | Financial logic | High | COMPREHENSIVE_BUG_REPORT | re_review | R/R must be data-driven and conditionally shown |
| BUG-013 | SL/TP stated vs realized exits inconsistent without explanation | Risk model | High | re_review | revision5 (still relevant) | Show slippage/gap note and realized stats |
| BUG-014 | Strategy labeling mismatch ("scalping" with multi-day holding times) | Strategy framing | Medium | revision5 | revision5 | Label and holding profile must be consistent |
| BUG-015 | Silent exception swallowing (`except: pass`) in signal filtering path | Technical reliability | High | revision5 | **resolved-by-purge 2026-05-23** (src/signals/ml_filter.py and src/main/ultimate_dashboard.py erased with the legacy stack) | Add CI lint to prevent re-introduction |
| BUG-016 | Latent timestamp-concat corruption in `_candles_from_df` (BUG-003 family in API layer) | Data formatting | High | swarm-2026-05-23 | **FIXED 2026-05-23** in `src/api/app.py:_candles_from_df` — Date column normalised via `dt.strftime` before concat; output always matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$`. Regression test in `tests/test_candles_from_df.py`. | Property test on Date+Time CSV |
| BUG-017 | Silent SSE degrade in `/api/backtest/scaling` 1-min fallback and box-rect compute (BUG-015 family in API stream path) | Technical reliability | Medium | swarm-2026-05-23 | **FIXED 2026-05-23** — three swallowed `except Exception: pass` sites in `src/api/app.py` (scaling 1-min load, box 1-min load, box-rect pre-compute) replaced with `yield _sse_format('warning', ...)`. Frontend SSE parser + backtest store + ProgressBar now surface `warnings: string[]` to the user. | Emit `event: warning` SSE frame instead of `pass` |
| BUG-018 | ~~Sentinel-as-denominator in legacy `calculate_metrics`~~ | ~~Statistical clarity~~ | ~~Medium~~ | swarm-2026-05-23 | **dropped-by-purge 2026-05-23** (src/backtest/metrics.py erased) | n/a |
| BUG-019 | Strategy-mode header label drift — App header hardcodes "1-1-2 Scaling" while Box mode runs underneath | UI freshness | Medium | swarm-2026-05-23 | **FIXED 2026-05-23** in `frontend/src/App.vue` — title now derived from `settings.strategyMode` via a computed; subtitle dev-jargon "phase D" removed. Test in new `frontend/tests/App.test.ts`. | Bind heading to `settings.strategyMode`; echo of BUG-014 |
| BUG-020 | Replay store desyncs when "Run Backtest" pressed while replay active (`candles=[]` → `total=0` → `:max=-1` HTML) | State machine | High | swarm-2026-05-23 | **FIXED 2026-05-23** in `frontend/src/stores/replay.ts` — `watch(total, ...)` with `flush: 'sync'` deactivates replay when candles clear and clamps `currentIdx` if length shrinks. Regression tests in `frontend/tests/replay_store.test.ts`. | Watch `backtest.candles.length`; call `deactivate()` on change |
| BUG-021 | TypeScript `Metrics` shape diverges from Pydantic; `_scaling_metrics` raw dict bypasses validation | Technical contract | High | swarm-2026-05-23 | **FIXED 2026-05-23** — `schemas.Metrics` aligned with `_scaling_metrics` output (legacy fields dropped, PF/Sharpe now `Optional[float]`). SSE complete payload now routes the metrics dict through `Metrics.model_validate(...).model_dump()` so shape drift fails fast. Regression test `tests/test_scaling_metrics.py::test_metrics_dict_validates_against_pydantic_schema`. | Define dedicated `ScalingMetrics` Pydantic model + TS mirror |
| BUG-022 | Unauthenticated file-upload endpoint with no size cap and `allow_origins=["*"]` | Security | High | swarm-2026-05-23 | **FIXED 2026-05-23** in `src/api/app.py` — CORS narrowed to localhost (override via `TRADING_DASH_ALLOW_ORIGINS` env), upload streams in 1 MB chunks with a 200 MB cap (`MAX_UPLOAD_BYTES`), filename basenamed + commonpath-checked against repo root. Regression tests in `tests/test_api.py` cover extension reject, traversal-stripping, and size cap. | Restrict origins, require local-token, enforce `MAX_UPLOAD_BYTES` |
| BUG-023 | EMA chart series titles do not update on period change (LOG-C-1) | UI freshness | Medium | swarm-2026-05-23 | **FIXED 2026-05-23** in `ChartPane.vue` period-change watcher — calls `emaFastSeries.applyOptions({title})` and same for slow before re-running `applyData()`. Regression test in `frontend/tests/ChartPane.test.ts`. | `applyOptions({title})` in period watcher |
| BUG-024 | `BoxesPrimitive` and chart helpers have zero tests; new bar-time snapping uncovered | QA / regression risk | High | swarm-2026-05-23 | **FIXED 2026-05-23** — extracted pure `snapBox` + exported `lowerBound`; renderer now calls them. Added `frontend/tests/BoxesPrimitive.test.ts` (14 tests) covering: edge cases of binary search; box predates/extends chart; canonical Saturday-gap scenario; end_time exclusivity. | Add `BoxesPrimitive.test.ts` covering `lowerBound` + snap |
| BUG-025 | `sse_parser.test.ts` and `chart_data.test.ts` re-implement production code instead of importing — tests verify themselves | QA / divergence | Critical | swarm-2026-05-23 | **FIXED 2026-05-23** — `parseSseFrame` exported from `services/sse.ts`; `toUTCTimestamp`/`toLwcData`/`computeEMA`/`computeRSI` extracted to `services/chart_helpers.ts`; both test files now import production code. | Export the helpers from production modules and import in tests |
| BUG-026 | Max DD sign/format — UI force-negates the backend's positive magnitude, producing `-$0.00` red when DD is zero | UI | High | swarm-2026-05-23 | **FIXED 2026-05-23** in `MetricsCards.vue` — new `formatDrawdown` returns `$0.00` for zero magnitude and `-$N.NN` for nonzero; red applied only when nonzero. Also fixes BUG-005-family zero sign-color drift in Net Profit / Avg Win / Avg Loss via new `formatDollar` + `signColor` helpers. Regression tests in `frontend/tests/MetricsCards.test.ts`. | Drop the negation in `MetricsCards.vue:12`; treat zero as unsigned |

---

## B) Panel/Section Quick Checks

### Header / KPI
- [ ] Return sign and color are correct for gain/loss.
- [ ] Final capital, return %, and net P/L reconcile to initial capital.
- [ ] No stale period labels or static values after data refresh.

### Metrics Panel
- [ ] `net_profit`, `gross_*`, `fees`, and `final_capital` naming is unambiguous.
- [ ] EV/Trade formula includes fee treatment consistently.
- [ ] Undefined metrics (Sharpe/PF) are shown as `N/A` when sample is insufficient.

### Trades Panel
- [ ] Every entry meets documented rules at entry timestamp.
- [ ] Every exit reason matches actual trigger path.
- [ ] Direction badge, P/L sign, and class coloring are consistent.

### Analysis Panel
- [ ] Winner/loser narratives match counts and actual outcomes.
- [ ] Terminology is consistent with other tabs.

### Playbook Panel
- [ ] Rules reflect actual engine behavior (including slippage/gap behavior).
- [ ] Strategy label matches holding-time reality.
- [ ] R/R statement matches realized data context.

### Logs Panel
- [ ] For every trade: `ENTRY -> EXIT -> METRICS`.
- [ ] Exit timestamp is always later than entry timestamp.
- [ ] Running capital sequence reconciles exactly.

### Insights Panel
- [ ] No stale text from previous run.
- [ ] Findings/recommendations match current metrics and counts.
- [ ] Narrative claims are statistically valid for sample size.

### Chart Panel
- [ ] Time axis formatting is clean and monotonic.
- [ ] Marker indices map to valid trade rows.
- [ ] Indicator lengths align with candle arrays.

---

## C) Master Bug Register (Append Each Iteration)

Add newly discovered bugs here with unique IDs.

| New ID | Revision | Segment | Lens That Found It | Severity | Evidence | Added By |
|---|---|---|---|---|---|---|
| BUG-016 | swarm-2026-05-23 | API / data ingest | Regression auditor | High | src/api/app.py:120 — `f"{d}T{t}"` with parsed-Timestamp `d` | swarm Regression |
| BUG-017 | swarm-2026-05-23 | API stream path | QA + Technical + Regression | Medium | src/api/app.py:307,512,541 — bare `except Exception: pass` | swarm QA-X-2, TECH-X-6 |
| BUG-018 | swarm-2026-05-23 | Metrics | Regression auditor | Medium | src/backtest/metrics.py:45 — `gross_loss = 1 if no losers` | swarm Regression |
| BUG-019 | swarm-2026-05-23 | Header | Financial + Trading + UX/UI + QC | Medium | frontend/src/App.vue:5 | FIN-H-1, TRD-H-1, UXUI-H-1, QC-H-2 |
| BUG-020 | swarm-2026-05-23 | Replay | Logic + Technical | High | frontend/src/stores/replay.ts:50-61, App.vue:21 | LOG-R-1, LOG-H-1, TECH-H-2 |
| BUG-021 | swarm-2026-05-23 | Metrics contract | Technical | High | frontend/src/types.ts:60-79 vs src/api/schemas.py:81-97 | TECH-M-1 |
| BUG-022 | swarm-2026-05-23 | API / upload | Technical | High | src/api/app.py:55-63, 235-245 | TECH-X-2, TECH-X-3 |
| BUG-023 | swarm-2026-05-23 | Chart | Logic | Medium | frontend/src/components/ChartPane.vue:264-275, 326 | LOG-C-1 |
| BUG-024 | swarm-2026-05-23 | Tests | QA | High | frontend/src/components/BoxesPrimitive.ts (no peer test) | QA-CP-1, QA-CP-3 |
| BUG-025 | swarm-2026-05-23 | Tests | QA | Critical | frontend/tests/sse_parser.test.ts:9-24; chart_data.test.ts:9 | QA-X-3, QA-CP-4 |
| BUG-026 | swarm-2026-05-23 | Metrics | Financial + UX/UI + Logic + QC | Critical | frontend/src/components/MetricsCards.vue:12 vs app.py:387 vs metrics.py:97 | FIN-M-1, UXUI-M-1, LOG-M-1, QC-MC-3 |

---

## D) Fixes Needed Report Log (For Development Team)

Append one report summary per revision cycle.

### Revision 2026-05-21 (from latest deep re-review)

| Fix ID | Severity | Segment | Fix Needed | Validation |
|---|---|---|---|---|
| FIX-2026-05-21-01 | High | Metrics | Clarify/rename gross metric semantics (`gross_wins` vs pre-fee net) to remove financial ambiguity | Metrics labels reconcile with formulas and trade aggregates |
| FIX-2026-05-21-02 | High | Playbook/Strategy Framing | Reclassify strategy label from "scalping" or enforce time-based exits to match observed holding profile | Holding-time stats align with declared strategy type |
| FIX-2026-05-21-03 | High | System Pipeline | Remove silent exception swallowing (`except: pass`) in signal/ML filtering path; surface explicit errors | Error path test confirms failures are observable and traceable |
| FIX-2026-05-21-04 | Medium | Validation/QA | Add robustness evidence: walk-forward/out-of-sample splits, benchmark comparison, sensitivity checks | Report includes reproducible robustness section each revision |

### Revision 2026-05-23 (swarm-2026-05-23 — 7-lens audit + regression auditor)

See `docs/revisions/swarm-2026-05-23/` for per-lens detail.
Action plan: `docs/revisions/swarm-2026-05-23/ACTION_PLAN.md`.

| Fix ID | Severity | Segment | Fix Needed | Validation |
|---|---|---|---|---|
| FIX-2026-05-23-01 | ~~Critical~~ Resolved-by-purge | System Pipeline | ~~BUG-015 regressed~~ — both file locations erased with the legacy stack on 2026-05-23. Add CI lint to prevent re-introduction. | `grep -E '^\s*except\s*(Exception)?\s*:\s*pass$' src/` returns nothing. |
| FIX-2026-05-23-02 | ~~Critical~~ **DONE** | Metrics | ~~BUG-011 regressed~~ — fixed in commit on 2026-05-23. `_scaling_metrics` returns `None` for PF/Sharpe when undefined; `MetricsCards.vue` renders `N/A`. Tests in `tests/test_scaling_metrics.py` and `frontend/tests/MetricsCards.test.ts`. | ✅ Tests pass. |
| FIX-2026-05-23-03 | ~~High~~ **DONE** | Metrics / Risk | ~~BUG-026~~ — fixed in commit on 2026-05-23. New `formatDrawdown`/`signColor` helpers in `MetricsCards.vue`. Tests at `frontend/tests/MetricsCards.test.ts`. | ✅ Tests pass. Zero DD renders `$0.00`; positive DD renders red `-$N.NN`. |
| FIX-2026-05-23-04 | ~~High~~ **DONE** | Replay / State | ~~BUG-020~~ — fixed in commit on 2026-05-23. Sync watcher on `total` deactivates replay and clamps `currentIdx`. Tests in `frontend/tests/replay_store.test.ts`. | ✅ Two new tests pass; full sweep 53/53 green. |
| FIX-2026-05-23-05 | ~~High~~ **DONE** | Header | ~~BUG-019~~ — fixed in commit on 2026-05-23. `App.vue` title derived from `settings.strategyMode`. Test in `frontend/tests/App.test.ts`. | ✅ Selecting "TradingView Box" updates header text; test passes. |
| FIX-2026-05-23-06 | ~~High~~ **DONE** | API contract | ~~BUG-021~~ — fixed in commit on 2026-05-23. `schemas.Metrics` aligned with `_scaling_metrics`; SSE complete payload validated through it; TS mirror updated. Regression test in `tests/test_scaling_metrics.py`. | ✅ Tests pass. |
| FIX-2026-05-23-07 | ~~High~~ **DONE** | Security | ~~BUG-022~~ — fixed in commit on 2026-05-23. CORS now limited to localhost via env-configurable allowlist; upload streamed + capped + basenamed. Tests in `tests/test_api.py`. | ✅ Tests pass. |
| FIX-2026-05-23-08 | ~~Critical~~ **DONE** | Tests | ~~BUG-025~~ — fixed in commit on 2026-05-23. `parseSseFrame` exported; chart helpers moved to `services/chart_helpers.ts`; both test files import them. | ✅ Build passes; 67/67 frontend tests green. |
| FIX-2026-05-23-09 | ~~Critical~~ **DONE** | Tests | ~~BUG-024~~ — fixed in commit on 2026-05-23. Pure `snapBox` extracted from the renderer; 14 unit tests added at `frontend/tests/BoxesPrimitive.test.ts`. | ✅ All 14 tests pass; full sweep 67/67 green. |
| FIX-2026-05-23-10 | ~~High~~ **DONE** | API stream | ~~BUG-017~~ — fixed in commit on 2026-05-23. SSE `warning` frames emitted from app.py; frontend parser + store + UI surface them. | ✅ Build green; 69/69 frontend tests pass; 28/28 backend tests pass. |
| FIX-2026-05-23-11 | ~~Critical~~ **DONE** | Chart | ~~BUG-023~~ — fixed in commit on 2026-05-23. `applyOptions({title})` called from the period watcher. Test in `frontend/tests/ChartPane.test.ts`. | ✅ Changing EMA period updates pane title; test passes. |
| FIX-2026-05-23-12 | ~~High~~ **DONE** | API / latent | ~~BUG-016~~ — fixed in commit on 2026-05-23. `_candles_from_df` normalises Date via `dt.strftime`. Tests in `tests/test_candles_from_df.py`. | ✅ 5/5 timestamp tests pass; 33/33 backend tests pass. |
| FIX-2026-05-23-13 | ~~Medium~~ **DONE** | Docs | ~~`docs/BOX_STRATEGY.md` describes abandoned rule~~ — updated in commit on 2026-05-23 to describe single-box (weekly priority), with a history note pointing at the legacy rule. | ✅ Doc matches `box_lookup.py:get_signal`. |
| FIX-2026-05-23-14 | ~~High~~ **DONE** | Settings | TRD-S-1/2/3 — added `:min="0.25"` to all point/SL/TP/threshold fields in `SettingsPanel.vue`; cross-field validation messages for `sl_hard >= sl_soft` and `leg3 > leg2`. Tests in `frontend/tests/SettingsPanel.test.ts`. | ✅ 5/5 SettingsPanel tests pass. |
| FIX-2026-05-23-15 | ~~High~~ **DONE** | UX | UXUI-S-2 — backtest store now snapshots run settings; `isDirty` computed exposes a "Settings changed — Run Backtest to apply" hint + ring around the Run button. Tests in `frontend/tests/backtest_store.test.ts`. | ✅ Hint appears after edit, clears on re-run. |
| FIX-2026-05-23-16 | ~~High~~ **DONE** | Replay / Financial | FIN-R-1 / TRD-R-1 — replay store exposes `realisedPnl`, `unrealisedPnl`, `runningPnl` (sum). MTM uses `(close − avg_entry) × contracts × point_value × dirSign`. ReplayBar tooltip shows the split. Three new tests in `frontend/tests/replay_store.test.ts`. | ✅ Open-long, open-short, post-exit cases verified. |
| FIX-2026-05-23-17 | ~~High~~ **DONE** | Chart | UXUI-C-1 / TRD-C-5 / TECH-C-2 — `fitContent()` now only fires when `candles.value` identity changes, not on replay scrub or indicator edits. Regression test in `frontend/tests/ChartPane.test.ts`. | ✅ Indicator edits no longer reset zoom. |
| FIX-2026-05-23-18 | Medium | Chart / latent | TECH-C-3 — verified by tests: current `lowerBound - 1` behaviour for x2 is correct given exclusive-end semantics (`box.end_time` is the first bar AFTER the box). No code change required. | ✅ `BoxesPrimitive.test.ts` covers the exact-bar-match case. |
| FIX-2026-05-23-19 | ~~High~~ **DONE** | TradeList | TECH-T-3 / LOG-T-1 — Vue `:key` changed to `${i}-${entry_idx}-${exit_idx}` so same-candle re-entries can't collide. | ✅ Build clean; sweep green. |
| FIX-2026-05-23-20 | ~~Medium~~ **DONE** | TradeList | LOG-T-2 / TRD-T-6 — Box-signal cell now shows only the firing side (weekly priority) plus a "conflict" badge when weekly and monthly disagree. Tooltip + CSV unchanged. | ✅ Cell no longer implies dual contribution. |
| FIX-2026-05-23-21 | ~~High~~ **DONE** | Strategy | LOG-T-3 — `box_lookup.get_signal_detail` now returns `conflict: bool`; `frontend/src/types.ts` mirrors. Tests in `tests/test_box_lookup_signal.py`. | ✅ Backend test asserts conflict True/False; UI badge wired. |
| FIX-2026-05-23-22 | Hygiene (Phase 5) **DONE** | Frontend | `services/format.ts` centralises `formatDollar`, `formatDrawdown`, `formatRatio`, `signColor`, `formatInt`, `formatElapsed`. MetricsCards, ProgressBar, ReplayBar, TradeList all use it. MetricCard now has `tabular-nums`. TradeList uses `Intl.NumberFormat` for prices + `truncate` on box/exit-reason cells. | ✅ Build clean; all panels consistent. |
| FIX-2026-05-23-23 | Hygiene (Phase 5) **DONE** | Tests | `pytest.ini` added at repo root; `test_loader_4h.py` uses `pytest.skip(...)` instead of silent `return`. | ✅ pytest discovers tests; missing-CSV path reports SKIP. |
| FIX-2026-05-23-24 | Polish (Phase 6) **DONE** | A11y | aria-labels on icon buttons (replay step/play/exit, CSV export). Focus rings on header buttons. EMA-insufficient-data overlay on ChartPane (orange chip top-right when period > candle count). CSV filename now includes HHMMSS. | ✅ Build clean; 77 frontend tests, 36 backend tests still green. |

---

## Source Reports Consolidated

- `docs/legacy/COMPREHENSIVE_BUG_REPORT.md`
- `docs/legacy/CRITICAL_TIMESTAMP_BUG.md`
- `docs/legacy/report-revision4.md`
- `docs/legacy/report-revision5.md`
- `docs/ultimate_trading_dashboard_review_v3.md`
- `docs/legacy/ultimate_trading_dashboard_re_review.md`
- `docs/legacy/ultimate_trading_dashboard_final_review.md`
- `docs/revisions/swarm-2026-05-23/` — full per-lens reports + summary
- `docs/revisions/swarm-2026-05-23/ACTION_PLAN.md` — prioritized fix sequence
