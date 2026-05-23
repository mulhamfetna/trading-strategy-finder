# Revision Mistakes Log

This log captures concrete mistakes discovered across revisions and what changed to fix them.

## Round 1: RSI entry filter asymmetry

- **Mistake:** RSI filtering logic treated long and short entries inconsistently.
- **Impact:** Signals were accepted/rejected unevenly, skewing strategy behavior.
- **Fix applied:** Unified RSI entry rules for long/short conditions and covered by regression tests.

## Round 2: Duplicate "Total Fees" label in dashboard

- **Mistake:** HTML generation duplicated the `Total Fees` metric label.
- **Impact:** Misleading UI and reduced confidence in dashboard metrics.
- **Fix applied:** Removed duplicate label and added a test asserting a single `Total Fees` label.

## Round 3: Incorrect PnL scaling for NQ contracts

- **Mistake:** Backtest PnL did not correctly apply NQ point-value scaling.
- **Impact:** Reported profit/loss was numerically wrong.
- **Fix applied:** Corrected backtest PnL point-value handling and added regression test coverage.

## Round 4: Hardcoded dashboard HTML became brittle

- **Mistake:** Dashboard HTML was hardcoded in Python string blocks.
- **Impact:** Hard to maintain, difficult to evolve UI safely.
- **Fix applied:** Extracted template into `templates/ultimate_dashboard.html.tpl` and added strict renderer behavior.

## Round 5: Line chart hid OHLC candle behavior

- **Mistake:** Visualization used close-line chart only.
- **Impact:** Open/high/low dynamics and candle context were invisible.
- **Fix applied:** Switched to candlestick visualization and added OHLC summary section.

## Round 6: Entry scripts scattered at repository root

- **Mistake:** Main runnable scripts were outside `src/main/`.
- **Impact:** Poor structure and fragile import paths.
- **Fix applied:** Moved entry scripts under `src/main/` and updated imports/tests accordingly.

## Round 7: No live dashboard runtime

- **Mistake:** Workflow relied only on generated static HTML.
- **Impact:** No live app endpoint for consolidated viewing.
- **Fix applied:** Added Dash app at `src/dashboard/dash_app.py` with embedded live/equity previews.

## Round 8 (swarm-2026-05-23): Two catalogued bugs regressed; 11 new patterns catalogued

- **Mistake (BUG-015 regression):** Bare `except: pass` re-introduced at `src/signals/ml_filter.py:89-90` and `src/main/ultimate_dashboard.py:310-311` after being marked Resolved in round 5.
- **Mistake (BUG-011 regression):** Profit Factor / Sharpe rendered as raw `"0.00"` in `frontend/src/components/MetricsCards.vue:14-15` instead of `N/A` when undefined.
- **Impact:** Silent ML-filter failures invalidate signal output; "0.00" PF/Sharpe misleads users about strategy quality on sparse data.
- **Action:** Eight-agent parallel swarm dispatched (Financial, Trading, UX/UI, Logic, QA, QC, Technical, Regression). 200 findings catalogued; 11 new BUG-### entries (BUG-016..026) appended to the Master Bug Register. Action plan at `docs/revisions/swarm-2026-05-23/ACTION_PLAN.md`.

## Round 13 (no-fallback-rule-2026-05-23): Strict mode for strategy + data pipeline

- **New project-wide rule** documented in `docs/CODING_RULES.md`: silent fallback to default values is forbidden across the strategy + data pipeline. Every missing value raises a typed exception with structured `code` / `message` / `system_status` payload.
- **`src/exceptions.py`** added with `ConfigurationError` (base), `MissingParameterError`, `MissingDataFileError`. `to_payload()` produces the SSE-friendly dict.
- **Pydantic models stripped of defaults** — `ScalingParamsModel`, `BoxParamsModel`, `BoxBacktestRequest`. Every field required via `Field(...)` or implicit required. Optional date range still `Optional[str]` but the field itself is required (caller must send `null`).
- **Python dataclasses stripped of defaults** — `ScalingParams`, `BoxStrategyParams`. Every field required.
- **Function arg defaults stripped** — `ScalingStrategy(params)`, `BoxStrategy(params, box_lookup)`, `BoxLookup(week_path, month_path, tick_threshold, weekly_window_days, monthly_window_days)`. Caller must supply everything.
- **Fallback expressions removed** — `getattr(p, 'big_candle_resolution', 'big_candle_wins')` → `p.big_candle_resolution` with explicit Literal check raising `MissingParameterError` on unknown values.
- **FastAPI exception handlers** for `ConfigurationError` and `RequestValidationError` wrap missing-field / missing-file errors into structured 422 JSON.
- **SSE workers** catch `ConfigurationError` and emit `event: error` frames with the full `system_status` payload.
- **Test fixture module** `tests/_fixtures.py` exports `scaling_params()`, `box_strategy_params()`, `box_params_dict()` — playbook defaults live there (test-only) so production code never imports them by accident.
- **Cleanup:** the legacy `/api/strategy/config` endpoint + `StrategyConfig` Pydantic + frontend `fetchStrategyConfig` were all dead code (V2 hardcoded-values report finding); deleted.
- **Cleanup:** `_DEFAULT_SPLIT = '2025-06-30'` and the train/test dataset branch in `_load_and_filter` were dead post-legacy-purge; deleted.
- **Cleanup:** `/api/candles` `Query('1min.csv', ...)` legacy default removed; `data_path` now required.
- **Cleanup:** `/api/boxes` Query defaults for box CSVs removed; all five box-lookup args now required.
- **Verification:** 35 backend tests + 77 frontend tests + production build all green.

## Round 12 (master-strategy-only-2026-05-23): Retire the Scaling/Box mode toggle

- **Question that triggered the round:** "If both layers are integrated, why is there still a radio toggle asking me to choose between them?"
- **Decision:** Box is the master strategy's only directional oracle. The toggle was a holdover from when the two playbooks were treated as alternatives. The `close > prev_close` rule in `ScalingStrategy._maybe_open_position` predated the Box and is retired from the production code path.
- **Removed:**
  - `SettingsPanel.vue` Strategy radio section.
  - `useSettingsStore.strategyMode` field.
  - `streamScalingBacktest` from `frontend/src/services/sse.ts`.
  - `/api/backtest/scaling` endpoint + `_scaling_event_stream` from `src/api/app.py`.
  - `ScalingBacktestRequest` from `src/api/schemas.py`.
  - `tests/test_api_scaling_sse.py` (endpoint is gone).
- **Kept:**
  - `ScalingStrategy` as the **test-only base class** — `tests/test_scaling_strategy.py` still drives it directly to verify the leg-fill / SL / TP mechanics in isolation.
- **Header now reads:** "NQ Master Strategy Dashboard" — no more strategy-name drift (BUG-019 family permanently resolved).
- **Docs:** `docs/MASTER_STRATEGY_GUIDE.md` §1–§2 rewritten to describe one strategy with one oracle; §5 conflict policy now describes a shipped parameter rather than a planned one.
- **Verification:** 35 backend tests + 77 frontend tests + production build all green.

## Round 11 (master-strategy-guide-2026-05-23): Consolidate playbooks + ship conflict policy

- **Consolidation:** `docs/MASTER_STRATEGY_GUIDE.md` written as the new single source of truth for strategy behaviour. Merges `Currunt_Strategy_Algo_for_Trading.md` (1-1-2 execution framework) + `BOXES_Strategy.md` (Box directional oracle) + `docs/BOX_STRATEGY.md` + `docs/STRATEGY_INTEGRATION_ANALYSIS.md`. The four source documents are now frozen historical reference; future strategy edits land in the master guide.
- **Big-Candle vs Box conflict policy shipped:** new `big_candle_resolution: Literal['big_candle_wins', 'box_wins', 'skip']` field on `BoxStrategyParams` (default `'big_candle_wins'` preserves prior behaviour). `BoxStrategy._maybe_open_position` now evaluates the box signal even on big-candle bars and resolves disagreement per the user-selected policy. Pydantic schema + TypeScript types + SettingsPanel dropdown updated. Regression test `tests/test_box_strategy_big_candle.py` locks all three policies including a sanity test for the "no conflict when both agree" case.
- **CLAUDE.md updated** to point at the master guide as the canonical reference.
- **Verification:** 38 backend tests + 78 frontend tests + production build all green.

## Round 10 (action-plan-execution-2026-05-23): Phases 0-6 complete

- **Phase 0 (regression sealing):** BUG-011 (PF/Sharpe = `0.00` regressed) fixed via backend `None` + frontend `N/A`. BUG-015 was resolved-by-purge in round 9.
- **Phase 1 (critical UI/data):** BUG-026 (Max DD sign/format) + BUG-005 family rebuilt around `formatDollar`/`formatDrawdown`/`signColor`. BUG-020 (replay desync) fixed by sync-flush watcher on candles length. BUG-023 (EMA chart titles stale) fixed via `applyOptions` in the period watcher. `BOX_STRATEGY.md` updated to describe single-box rule.
- **Phase 2 (test infra):** BUG-025 (self-verifying tests) fixed by extracting `services/chart_helpers.ts` and exporting `parseSseFrame`. BUG-024 (BoxesPrimitive uncovered) fixed by extracting pure `snapBox` + 14 unit tests. New `App.test.ts` and `MetricsCards.test.ts` files.
- **Phase 3 (contract + security):** BUG-021 (TS/Pydantic drift) — `schemas.Metrics` aligned, SSE complete payload validates through Pydantic. BUG-022 (unauth upload) — CORS allowlist, 200 MB cap, chunked stream, basename + commonpath guard. BUG-017 (silent SSE degrade) — three `except: pass` sites now emit `warning` SSE frames; ProgressBar surfaces them. BUG-016 (latent timestamp concat) — `_candles_from_df` normalises Date via `dt.strftime`.
- **Phase 4 (UI realism):** FIX-14 settings validation, FIX-15 dirty-state hint, FIX-16 unrealised PnL in replay, FIX-17 `fitContent` only on data change, FIX-19 TradeList key collision, FIX-20 box cell display, FIX-21 `conflict` flag in `get_signal_detail`.
- **Phase 5 (hygiene):** `services/format.ts` centralised formatters, `tabular-nums` everywhere, `pytest.ini` at repo root, `test_loader_4h.py` uses explicit `pytest.skip`.
- **Phase 6 (polish):** aria-labels on icon buttons, focus rings on header buttons, EMA insufficient-data overlay, CSV filename includes HHMMSS.
- **Verification:** 36 backend tests + 77 frontend tests + production build all green.
- **Outstanding:** none in the action plan. Remaining Master Bug Register items are all PASS or DONE.

## Round 9 (legacy-purge-2026-05-23): Erase the legacy Python pipeline

- **Decision:** Project focus has fully shifted to the FastAPI + Vue 3 stack (scaling and box strategies via SSE). The legacy HTML-dashboard Python pipeline was no longer used by the Vue UI but kept BUG-015 reachable and resurrected BUG-001 in the legacy `/api/backtest` path. Dev-branch-only cleanup.
- **Erased modules:** `src/main/`, `src/dashboard/`, `src/indicators/`, `src/backtest/`, `src/signals/`, `src/strategy/scalping_strategy.py`, `src/strategy/backtester.py`.
- **API surface trimmed:** `/api/backtest` endpoint removed from `src/api/app.py`; corresponding Pydantic models (`BacktestRequest`, `BacktestResponse`, `Trade`) removed from `src/api/schemas.py`. `runBacktest` removed from `frontend/src/services/api.ts`; `Trade`/`BacktestRequest`/`BacktestResponse` removed from `frontend/src/types.ts`.
- **Tests pruned:** 9 legacy test files erased plus the `/api/backtest` block in `tests/test_api.py` and `tests/test_data_loader.py` (depended on missing `1min.csv`).
- **Bug-bounty consequences:** BUG-015 marked "resolved-by-purge"; BUG-001 partial-FAIL closed; BUG-018 dropped; BUG-026 downgraded High; legacy-only findings stripped from the per-lens swarm reports.
- **Verification:** `pytest tests/ -v` → 19 passed; `cd frontend && npm test` → 40 passed; `npm run build` → built clean (340 KB JS, 14 KB CSS).
- **Outstanding work:** only the active-stack fixes in `docs/revisions/swarm-2026-05-23/ACTION_PLAN.md` remain.
