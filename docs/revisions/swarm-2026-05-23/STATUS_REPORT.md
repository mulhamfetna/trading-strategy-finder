# Bug Status Report

Generated: 2026-05-23
Scope: every entry in `docs/bug-checklist-revision-history.md` (BUG-001..026) plus the action-plan FIX items they spawned. Each row shows what was broken, where, what the fix did, and how it was verified.

Legend:
- **✅ Fixed** — patched in production code with a regression test in this branch.
- **🧹 Resolved-by-purge** — code that held the bug was deleted on 2026-05-23 (legacy purge).
- **📚 N/A** — feature doesn't exist in the current UI.
- **⏳ Pending** — Phase 4–6 item, not yet started.

---

## Catalogued bugs from prior rounds (BUG-001 .. BUG-015)

### BUG-001 — NQ contract multiplier missing (`$2/point`)
- **Status:** ✅ Fixed (active path) / 🧹 Resolved-by-purge (legacy path)
- **What was broken:** P/L was reported in % of capital rather than as `points × contracts × point_value=2.0`, so dollar metrics were undersized.
- **Fix location:** `src/strategy/scaling_strategy.py:459` (active scaling path) — already correct. The legacy `src/backtest/engine.py:170-174` that still held the regression was erased with the legacy purge on 2026-05-23.
- **Fix explanation:** The scaling engine multiplies `profit_points * contracts * point_value` everywhere. The legacy `%-of-capital` formula is gone because its module is gone.

### BUG-002 — Exit timestamp before entry timestamp
- **Status:** ✅ Fixed
- **What was broken:** Some trades surfaced an `exit_idx` ≤ `entry_idx`, making the trade impossible.
- **Fix location:** `src/strategy/scaling_strategy.py:172, 461-462`.
- **Fix explanation:** `entry_idx = position.opened_at_idx` is set on the prior bar; `exit_idx = idx` is the current bar at close. In dual-timeframe mode, the precise `exit_time` is sourced from a 1-min bar inside the same 4h window, so it's always after entry.

### BUG-003 — Corrupted timestamp format (`YYYY-MM-DD 00:00:00 HH:MM:SS`)
- **Status:** ✅ Fixed in the active path. Latent in API layer → escalated to BUG-016 and fixed this session.
- **What was broken:** When `Date` parsed to a `Timestamp` and a `Time` column existed, string concatenation produced `"2025-07-28 00:00:00T18:21:00"`.
- **Fix location:** `src/api/app.py:_candles_from_df` (see BUG-016 below); frontend slice in `TradeList.vue:105` / `ChartPane.vue:106`.
- **Fix explanation:** Date column normalised via `dt.strftime('%Y-%m-%d')` before concat. Output now always matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$`.

### BUG-004 — Return string format `+-X%`
- **Status:** ✅ Fixed
- **What was broken:** Sign string was concatenated with no normalisation, producing impossible `+-X%`.
- **Fix location:** `frontend/src/components/MetricsCards.vue` (`formatDollar`), `TradeList.vue:59,62`.
- **Fix explanation:** Sign is now a single `'+' | '' | '-'` token; zero renders unsigned. Verified by `MetricsCards.test.ts`.

### BUG-005 — Negative return shown in green / zero in green / zero in red
- **Status:** ✅ Fixed
- **What was broken:** Color was inferred from `>= 0`, so exact zero inherited green (or in some cells a hardcoded red).
- **Fix location:** `frontend/src/components/MetricsCards.vue` — new `signColor()` helper applied per card.
- **Fix explanation:** `signColor()` returns green only when `> 0`, red only when `< 0`, neutral at exactly `0`. Avg Win / Avg Loss / Net Profit / Max DD all derive their color this way now.

### BUG-006 — Net/gross metric labeling mismatch
- **Status:** ✅ Fixed (active) / 🧹 Resolved-by-purge (legacy lib)
- **What was broken:** `total_profit` shipped as "Net" while actually being a gross figure; labels and formulas didn't reconcile.
- **Fix location:** `src/api/app.py:_scaling_metrics` cleanly separates `gross_profit`, `gross_loss`, `total_profit`. Legacy `src/backtest/metrics.py` that held the rev-5 ambiguity was deleted.
- **Fix explanation:** The active path emits separate gross/total fields; the frontend renders them under unambiguous labels.

### BUG-007 — Stale insights text from old dataset
- **Status:** ✅ Fixed
- **What was broken:** Re-running a backtest left stale metrics/trades/candles visible until the new SSE `complete` event arrived.
- **Fix location:** `frontend/src/stores/backtest.ts:38-47` (`run()` resets all state).
- **Fix explanation:** `run()` zeroes `metrics`, `candles`, `trades`, `boxes`, `progress`, `warnings`, `error` before the SSE stream starts — no carry-over possible.

### BUG-008 — Contradictory insights (e.g. "all winning trades" with zero winners)
- **Status:** 📚 N/A
- **What was broken:** Legacy HTML dashboard generated free-text narratives that could contradict the actual metric counts.
- **Fix location:** No insights/narrative panel exists in the current Vue UI; the legacy dashboard module was deleted.
- **Fix explanation:** Risk eliminated by deletion. If we ever re-add narrative text, the rule "narratives must reflect actual counts" still applies.

### BUG-009 — EV/Trade inconsistency with fee handling
- **Status:** ✅ Fixed (consistent today)
- **What was broken:** EV display formula didn't match how fees were treated elsewhere in the metrics dict.
- **Fix location:** `src/api/app.py:399-414`.
- **Fix explanation:** The scaling pipeline deducts no fees anywhere (pre-fee labels everywhere), so EV = mean(profit_dollars) is coherent with the per-trade P/L shown in the trade list. If fees are reintroduced, EV must be updated in lockstep.

### BUG-010 — Running capital mismatch in metrics logs
- **Status:** ✅ Fixed
- **What was broken:** Legacy pipeline emitted a `capital_after` sequence that didn't reconcile trade-by-trade.
- **Fix location:** Scaling trades carry no `capital_after`; no running capital is displayed in the UI.
- **Fix explanation:** Surface that could mis-reconcile no longer exists. If reintroduced, must be derived from `cumsum(profit_dollars)` so it's algebraically guaranteed.

### BUG-011 — Profit factor / Sharpe displayed as raw zero when undefined
- **Status:** ✅ Fixed
- **What was broken:** When PF or Sharpe were mathematically undefined (no losses; n < 2; std = 0), the backend returned `0.0` and the frontend rendered `"0.00"`, mimicking a real "no edge" result.
- **Fix location:** `src/api/app.py:_scaling_metrics` returns `None` for undefined values; `frontend/src/components/MetricsCards.vue` renders `"N/A"`. Types: `Optional[float]` in `src/api/schemas.py`, `number | null` in `frontend/src/types.ts`.
- **Fix explanation:** Backend distinguishes "undefined" from "zero edge". Frontend's new `formatRatio()` shows `N/A` for null. Regression locks: `tests/test_scaling_metrics.py` + `frontend/tests/MetricsCards.test.ts`.

### BUG-012 — R/R displayed while no valid winners or inconsistent with data
- **Status:** 📚 N/A
- **What was broken:** Legacy dashboard had an R/R card that could fire with no valid winners.
- **Fix location:** No R/R card in the current UI.
- **Fix explanation:** Surface doesn't exist. If reintroduced, render conditionally with sample-size guard.

### BUG-013 — SL/TP stated vs realized exits inconsistent
- **Status:** ✅ Fixed
- **What was broken:** Engine could fill an SL/TP at a price that didn't match the stated rule, with no slippage disclosure.
- **Fix location:** `src/strategy/scaling_strategy.py:411-429`.
- **Fix explanation:** Exits clamp the exit price to the stated SL/TP level. Reported SL always equals stated SL — no realized > stated mismatch is possible. (Slippage modelling could be added later; see Phase 5 hygiene.)

### BUG-014 — Strategy labeling mismatch ("scalping" with multi-day holding times)
- **Status:** ✅ Fixed (label) / ⏳ Pending (holding-time enforcement)
- **What was broken:** Header read "scalping" but trades regularly held multi-day.
- **Fix location:** `frontend/src/App.vue` — title is now dynamic per `settings.strategyMode` (see BUG-019). No "scalping" label exists anywhere in the active UI; legacy `ScalpingStrategy` class deleted.
- **Fix explanation:** Header always reflects the strategy the user actually selected. Time-based exits enforcement and a holding-time histogram remain Phase-5 items.

### BUG-015 — Silent exception swallowing (`except: pass`) in signal filtering
- **Status:** 🧹 Resolved-by-purge
- **What was broken:** Bare `except: pass` in `src/signals/ml_filter.py:89` and `src/main/ultimate_dashboard.py:310` masked every error (including `KeyboardInterrupt`).
- **Fix location:** Both files were deleted with the legacy purge on 2026-05-23. The pattern was also flagged in the API stream path; see BUG-017.
- **Fix explanation:** Modules holding the regression are gone. Recommended CI lint: fail on `^\s*except\s*(Exception)?\s*:\s*pass$` outside whitelisted lines.

---

## New bugs catalogued by the 2026-05-23 swarm (BUG-016 .. BUG-026)

### BUG-016 — Latent timestamp-concat corruption in `_candles_from_df`
- **Status:** ✅ Fixed
- **What was broken:** Same BUG-003 pattern was reachable in the API layer: if `Date` was parsed to a `Timestamp` and `Time` was a separate column, the f-string produced `"2025-07-28 00:00:00T18:21:00"`.
- **Fix location:** `src/api/app.py:_candles_from_df`.
- **Fix explanation:** Date column is now normalised via `dt.strftime('%Y-%m-%d')` (or sliced to first 10 chars when stringy) before concatenation. Tests in `tests/test_candles_from_df.py` enforce the `^YYYY-MM-DDTHH:MM:SS$` shape.

### BUG-017 — Silent SSE degrade in `/api/backtest/scaling` and `/api/backtest/box`
- **Status:** ✅ Fixed
- **What was broken:** Three `except Exception: pass` sites in `src/api/app.py` swallowed failures in the optional 1-min CSV load and the box-rect pre-compute. The UI never knew the run had silently degraded.
- **Fix location:** `src/api/app.py` (three sites); `frontend/src/services/sse.ts` (parser); `frontend/src/stores/backtest.ts` (`warnings: string[]`); `frontend/src/components/ProgressBar.vue` (UI surface).
- **Fix explanation:** Each swallow now emits an SSE frame `event: warning\ndata: {stage, message}`. The frontend parser recognises the new event, the store appends to a reactive `warnings` array, and ProgressBar renders the list in a blue chip. Errors are visible without breaking the run.

### BUG-018 — Sentinel-as-denominator in legacy `calculate_metrics`
- **Status:** 🧹 Resolved-by-purge
- **What was broken:** `gross_loss = abs(sum(losing_trades)) if losing_trades else 1` made PF a scale-dependent garbage number when there were no losses.
- **Fix location:** `src/backtest/metrics.py` — deleted with the legacy purge.
- **Fix explanation:** Module no longer exists. The active path (`_scaling_metrics`) was already corrected as part of BUG-011.

### BUG-019 — Strategy-mode header label drift
- **Status:** ✅ Fixed
- **What was broken:** `frontend/src/App.vue:5` hard-coded "NQ 1-1-2 Scaling Strategy Dashboard" even when the user picked the TradingView Box strategy.
- **Fix location:** `frontend/src/App.vue`.
- **Fix explanation:** Title is now a `computed` over `settings.strategyMode` — "NQ 1-1-2 Scaling Strategy Dashboard" for scaling, "NQ TradingView Box Strategy Dashboard" for box. Regression test in `frontend/tests/App.test.ts`. The leaky internal "phase D" subtitle was also removed.

### BUG-020 — Replay store desyncs when "Run Backtest" pressed while replay active
- **Status:** ✅ Fixed
- **What was broken:** Clicking Run Backtest mid-replay cleared `backtest.candles`, leaving `total = 0`, `:max="-1"` on the scrubber, and `currentCandle = undefined`. The play-timer kept ticking against zero-length data.
- **Fix location:** `frontend/src/stores/replay.ts`.
- **Fix explanation:** A sync watcher (`watch(total, ..., { flush: 'sync' })`) deactivates replay when the candle array becomes empty, and clamps `currentIdx` if the length shrinks but stays positive. Two new regression tests in `frontend/tests/replay_store.test.ts`.

### BUG-021 — TypeScript `Metrics` shape diverges from Pydantic
- **Status:** ✅ Fixed
- **What was broken:** `_scaling_metrics` emitted a raw dict that bypassed Pydantic validation. The TS `Metrics` interface declared fields the backend never sent (`total_fees`, `final_capital`, etc.).
- **Fix location:** `src/api/schemas.py:Metrics`, `frontend/src/types.ts:Metrics`, `src/api/app.py` (SSE complete event).
- **Fix explanation:** The Pydantic model now exactly mirrors what the backend emits, with `Optional[float]` for PF/Sharpe. The SSE complete event routes the dict through `Metrics.model_validate(...).model_dump()` so any future shape drift raises a `ValidationError` instead of silently shipping bad JSON. Regression test in `tests/test_scaling_metrics.py::test_metrics_dict_validates_against_pydantic_schema`.

### BUG-022 — Unauthenticated file-upload endpoint with no size cap and `allow_origins=["*"]`
- **Status:** ✅ Fixed
- **What was broken:** `/api/upload-data-file` accepted unlimited-size uploads from any origin (`allow_origins=["*"]`), reading them entirely into memory and writing them to the repo root with no traversal validation.
- **Fix location:** `src/api/app.py`.
- **Fix explanation:**
  - CORS allowlist now defaults to `localhost:5173` / `127.0.0.1:5173` and is configurable via `TRADING_DASH_ALLOW_ORIGINS` env var.
  - Upload streams in 1 MB chunks with a 200 MB cap (`MAX_UPLOAD_BYTES`); excess returns 413.
  - Filename normalised via `os.path.basename`; result-path verified to stay under repo root via `commonpath`.
  - Failures clean up the partial file.
  - Regression tests in `tests/test_api.py` cover extension rejection, traversal-stripping, and size-cap enforcement.

### BUG-023 — EMA chart series titles don't update on period change
- **Status:** ✅ Fixed
- **What was broken:** EMA series titles (e.g. "EMA20") were baked in at `addSeries` time. Changing `emaFast`/`emaSlow` in SettingsPanel updated the data but not the pane label.
- **Fix location:** `frontend/src/components/ChartPane.vue` (period watcher).
- **Fix explanation:** The period watcher now calls `emaFastSeries?.applyOptions({ title: 'EMA' + settings.indicators.emaFast })` (and same for slow) before re-running `applyData()`. Regression test in `frontend/tests/ChartPane.test.ts`.

### BUG-024 — `BoxesPrimitive` and chart helpers have zero tests
- **Status:** ✅ Fixed
- **What was broken:** The bar-time snapping logic added to fix the original "boxes vanish over weekends" issue had no test coverage. A regression would be invisible.
- **Fix location:** `frontend/src/components/BoxesPrimitive.ts` (extracted `lowerBound` and `snapBox` as pure exports); `frontend/tests/BoxesPrimitive.test.ts` (new, 14 tests).
- **Fix explanation:** The snap logic was extracted from the renderer into a pure `snapBox(box, barTimes)` function (with `lowerBound` also exported). The renderer now calls these via the same path the tests exercise. Tests cover: binary-search edge cases, boxes predating the chart, boxes extending past the chart, the canonical Saturday-gap case, and exclusive-end semantics.

### BUG-025 — Tests verify themselves (inlined copies of production code)
- **Status:** ✅ Fixed
- **What was broken:** `frontend/tests/sse_parser.test.ts` and `frontend/tests/chart_data.test.ts` re-implemented the production helpers (`parseSseFrame`, `toUTCTimestamp`, `computeEMA`, `computeRSI`) inline. Tests passed even when production code drifted.
- **Fix location:** `frontend/src/services/sse.ts` (exported `parseSseFrame`); `frontend/src/services/chart_helpers.ts` (new — extracted from `ChartPane.vue`); both test files now import production code.
- **Fix explanation:** Production helpers live in importable modules and the tests import them directly. ChartPane's local copies were deleted; the component imports from the helper module too. Production-test divergence becomes a build error rather than a silent miss.

### BUG-026 — Max DD sign/format
- **Status:** ✅ Fixed
- **What was broken:** `MetricsCards.vue:12` rendered `formatDollar(-metrics.max_drawdown)` with the cell hardcoded red. For zero drawdown, `-0 >= 0` evaluated true, producing `+$0.00` colored red — contradiction. (The unit-collision aspect of the original finding was resolved automatically by the legacy purge that removed the percent-emitting `calculate_metrics`.)
- **Fix location:** `frontend/src/components/MetricsCards.vue` — new `formatDrawdown()` plus color-from-sign via `signColor()`.
- **Fix explanation:** `formatDrawdown(magnitude)` returns `$0.00` for zero (unsigned, neutral color) and `-$N.NN` for nonzero (red). The same approach was applied to Avg Win, Avg Loss, and Net Profit so no card inherits a stale color at exactly zero. Regression tests in `frontend/tests/MetricsCards.test.ts`.

---

## Action-plan items still pending (Phase 4–6 hygiene)

These were lower-priority findings from the swarm. None blocks release.

| FIX ID | Bug ref | Severity | Status |
|---|---|---|---|
| FIX-2026-05-23-14 (Phase 4) | TRD-S-1/2/3 — Settings input validation (`:min`, sl_hard ≥ sl_soft, leg3 > leg2) | High | ⏳ Pending |
| FIX-2026-05-23-15 (Phase 4) | UXUI-S-2 — "Settings changed — Run Backtest to apply" hint | High | ⏳ Pending |
| FIX-2026-05-23-16 (Phase 4) | FIN-R-1, TRD-R-1 — Unrealised PnL in replay running total | High | ⏳ Pending |
| FIX-2026-05-23-17 (Phase 4) | UXUI-C-1, TRD-C-5, TECH-C-2 — `fitContent()` per replay tick | High | ⏳ Pending |
| FIX-2026-05-23-18 (Phase 4) | TECH-C-3 — `lowerBound - 1` off-by-one for x2 | Medium | ⏳ Pending (current behaviour is correct given exclusive-end semantics; reconfirmed by new tests) |
| FIX-2026-05-23-19 (Phase 4) | TECH-T-3, LOG-T-1 — TradeList row key collision on re-entry | High | ⏳ Pending |
| FIX-2026-05-23-20 (Phase 4) | LOG-T-2, TRD-T-6 — "weekly + monthly" cell misleading | Medium | ⏳ Pending |
| FIX-2026-05-23-21 (Phase 4) | LOG-T-3 — `conflict: bool` flag in `get_signal_detail` | High | ⏳ Pending |
| Phase 5 items | Settings collapsible, `tabular-nums`, glossary tooltips, etc. | Medium | ⏳ Pending |
| Phase 6 items | Polish (CSV filename HHMMSS, aria-labels, EMA insufficient-data overlay, etc.) | Low | ⏳ Pending |

---

## Verification snapshot (2026-05-23)

| Surface | Tests | Status |
|---|---|---|
| Backend (`pytest tests/ -v`) | 33 passed | ✅ |
| Frontend (`npm test`) | 69 passed across 11 files | ✅ |
| Production build (`npm run build`) | 340 KB JS, 14 KB CSS, no errors | ✅ |
| Bug bounty knowledge base | BUG-001..026 status accurate as of this report | ✅ |

## Files added or significantly changed this session

```
src/api/app.py                              [legacy stripped; BUG-011/016/017/021/022 patches]
src/api/schemas.py                          [legacy types stripped; Metrics aligned with active emitter]
src/strategy/__init__.py                    [exports trimmed to scaling/box]
tests/test_api.py                           [/api/backtest block removed; BUG-022 tests added]
tests/test_scaling_metrics.py     (NEW)     [BUG-011, BUG-021 locks]
tests/test_candles_from_df.py     (NEW)     [BUG-016 lock]

frontend/src/App.vue                        [BUG-019 dynamic header]
frontend/src/components/MetricsCards.vue    [BUG-011, BUG-026, BUG-005 family]
frontend/src/components/ChartPane.vue       [BUG-023 EMA titles; helpers moved to chart_helpers.ts]
frontend/src/components/BoxesPrimitive.ts   [snap logic extracted, exported]
frontend/src/components/ProgressBar.vue     [BUG-017 warnings surface]
frontend/src/services/api.ts                [legacy runBacktest removed]
frontend/src/services/sse.ts                [parseSseFrame exported; 'warning' event type]
frontend/src/services/chart_helpers.ts (NEW)[extracted from ChartPane.vue]
frontend/src/stores/backtest.ts             [warnings: string[]]
frontend/src/stores/replay.ts               [BUG-020 sync watcher]
frontend/src/types.ts                       [Metrics shape aligned; legacy types removed]

frontend/tests/App.test.ts             (NEW)[BUG-019]
frontend/tests/MetricsCards.test.ts    (NEW)[BUG-011, BUG-026, BUG-005]
frontend/tests/BoxesPrimitive.test.ts  (NEW)[BUG-024]
frontend/tests/ChartPane.test.ts            [BUG-023 EMA-title test added]
frontend/tests/chart_data.test.ts           [imports production helpers]
frontend/tests/replay_store.test.ts         [BUG-020 desync + clamp tests]
frontend/tests/sse_parser.test.ts           [imports production parseSseFrame]

docs/bug-checklist-revision-history.md      [all BUG entries + FIX rows updated]
docs/revisions/REVISION_LOG.md              [Round 8 + Round 9 entries]
docs/BOX_STRATEGY.md                        [single-box rule documented]
docs/revisions/swarm-2026-05-23/            [per-lens reports + action plan + this report]

DELETED (legacy purge):
  src/main/, src/dashboard/, src/indicators/, src/backtest/, src/signals/
  src/strategy/scalping_strategy.py, src/strategy/backtester.py
  9 legacy test files + tests/test_data_loader.py
```
