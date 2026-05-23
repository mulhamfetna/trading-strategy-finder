# Action Plan — swarm-2026-05-23

Generated: 2026-05-23
Source: 8-agent parallel swarm audit (see [00-SUMMARY.md](00-SUMMARY.md)).
Updates appended to: `docs/bug-checklist-revision-history.md` (Master Bug Register + Fixes Needed Report Log).

This plan groups fixes by phase. **Each phase ends with a verification gate.** Higher-numbered phases assume earlier phases are merged and CI is green.

---

## Phase 0 — Regression Sealing (block release)

One catalogued bug from prior revisions remains regressed. Until it's sealed, **no other fix should be merged**.

> BUG-015 (bare `except: pass`) was resolved automatically by the 2026-05-23 legacy purge — `src/signals/ml_filter.py` and `src/main/ultimate_dashboard.py` no longer exist. Add a CI guard that fails on `^\s*except:\s*pass$` and `^\s*except Exception:\s*pass$` outside whitelisted lines to prevent re-introduction.

### FIX-2026-05-23-02 — BUG-011 regression: PF/Sharpe shown as `0.00`
- **Files:** `frontend/src/components/MetricsCards.vue:14-15`, `src/api/app.py:399-414`, `src/api/schemas.py` (Metrics)
- **Backend:** `_scaling_metrics` must return `profit_factor: Optional[float]` — `None` when `gross_loss == 0`; same for `sharpe_ratio` when `len(trades) < 2` or `std == 0`.
- **Frontend:** if `metrics.profit_factor === null` render `"N/A"`; if `metrics.sharpe_ratio === null` render `"N/A"`.
- **Regression test:** `frontend/tests/MetricsCards.test.ts` — fixture with `total_trades: 1` asserts `N/A` for Sharpe; fixture with all-wins asserts `N/A` (or `∞`) for PF.

---

## Phase 1 — Critical UI / data integrity

### FIX-2026-05-23-03 — Max DD sign/format (BUG-026 — downgraded)
- **Files:** `frontend/src/components/MetricsCards.vue:12`
- **Change:** Replace `formatDollar(-metrics.max_drawdown)` with a magnitude-only formatter that doesn't add a `+` sign on zero. Backend already returns a non-negative magnitude; the frontend just needs to stop fighting the sign.
- **Verification:** zero-DD run renders `$0.00` (no `+`, no `-`); positive DD renders `-$N.NN` red.
- **Note:** The unit-collision aspect of the original finding is resolved — `src/backtest/metrics.py` (the percent-emitting path) was deleted in the legacy purge.

### FIX-2026-05-23-04 — Replay desync on Run Backtest (BUG-020)
- **Files:** `frontend/src/stores/replay.ts`, `frontend/src/stores/backtest.ts:45`, `frontend/src/App.vue:21`
- **Change:** in `useReplayStore`, add `watch(() => useBacktestStore().candles.length, (n) => { if (n === 0 && isActive.value) deactivate(); })`. Also disable the "Run Backtest" button while replay is active OR call `replay.deactivate()` at the start of `backtest.run()`.
- **Verification:** integration test — activate replay → run backtest → assert `replay.isActive === false` and `currentIdx === 0`.

### FIX-2026-05-23-11 — EMA chart title stale after period change (BUG-023)
- **Files:** `frontend/src/components/ChartPane.vue:264-275, 326-337`
- **Change:** in the period watcher (currently only calls `applyData`), also call `emaFastSeries?.applyOptions({title: 'EMA' + settings.indicators.emaFast})` and same for slow.
- **Verification:** manual — change emaFast in SettingsPanel; pane label updates.

### FIX-2026-05-23-13 — BOX_STRATEGY.md describes abandoned rule
- **Files:** `docs/BOX_STRATEGY.md:69-71`
- **Change:** Replace "both weekly AND monthly must agree" wording with: "Signal fires as soon as price crosses ONE box level (weekly takes priority over monthly when both are active)." Match `box_lookup.py:154-157` behaviour.
- **Verification:** doc match; cross-reference `Currunt_Strategy_Algo_for_Trading.md` if it mentions the rule too.

---

## Phase 2 — Critical test infrastructure (BUG-024, BUG-025)

These three Critical findings mean the regression risk is **structurally invisible** to CI today. Without them, every fix below is unguarded.

### FIX-2026-05-23-08 — Tests verify themselves (BUG-025)
- **Files:** `frontend/src/services/sse.ts`, `frontend/src/components/ChartPane.vue`, `frontend/tests/sse_parser.test.ts:9-24`, `frontend/tests/chart_data.test.ts:9`
- **Change:**
  - Export `parseSseFrame` from `services/sse.ts`.
  - Extract `toUTCTimestamp`, `computeEMA`, `computeRSI` from `ChartPane.vue` into `services/chart_helpers.ts` and re-import inside ChartPane.
  - Tests import from production code; remove the inlined copies.
- **Verification:** edit `parseSseFrame` to break it (e.g., return null always); existing sse_parser tests must fail.

### FIX-2026-05-23-09 — BoxesPrimitive uncovered (BUG-024)
- **Files:** new `frontend/tests/BoxesPrimitive.test.ts`
- **Cases (minimum 5):**
  1. `lowerBound` returns 0 for value below all elements.
  2. `lowerBound` returns `arr.length` for value above all elements.
  3. `lowerBound` returns exact index when value equals an element.
  4. Box whose `start_time` falls on a Saturday (no bar) snaps to next Monday's bar.
  5. Box whose `end_time` exactly matches a bar — confirm right edge isn't dropped (catches TECH-C-3 off-by-one).
- **Verification:** all 5 tests pass.

### FIX-2026-05-23-09b — Coverage for the rest of the dashboard
- **Files:** new `frontend/tests/App.test.ts`, `MetricsCards.test.ts`, `TradeList.test.ts`, `ProgressBar.test.ts`, `ReplayBar.test.ts`
- **Scope:** smoke render + one critical behaviour per component (button click triggers store action, etc.).
- **Verification:** vitest runs >= 60 tests (currently 40).

---

## Phase 3 — Contract and security hardening

### FIX-2026-05-23-06 — Pydantic/TS contract drift (BUG-021)
- **Files:** `src/api/schemas.py`, `src/api/app.py:399-414`, `frontend/src/types.ts:60-79`
- **Change:** Add `class ScalingMetrics(BaseModel)` mirroring everything `_scaling_metrics` actually emits (`wins`, `losses`, `expected_value`, `gross_loss`, ...). Drop fields the scaling endpoint doesn't produce from the TS `Metrics` type, or split into `Metrics` + `ScalingMetrics`.
- **Verification:** Python test that `ScalingMetrics(**_scaling_metrics(...))` round-trips without warnings.

### FIX-2026-05-23-07 — Unauth file upload (BUG-022)
- **Files:** `src/api/app.py:55-63, 235-245, 269` and the request models in `schemas.py`
- **Change:**
  - Restrict `allow_origins` to `["http://localhost:5173"]` in dev; configurable.
  - Enforce `MAX_UPLOAD_BYTES = 200 * 1024 * 1024` (200 MB); stream the upload via `shutil.copyfileobj(file.file, fh)` rather than `await file.read()`.
  - `data_path = os.path.basename(req.data_path)` in `_validate_request`; reject if it escapes a configured `DATA_ROOT`.
- **Verification:** integration tests — large upload rejected with 413; path traversal returns 400.

### FIX-2026-05-23-10 — Silent SSE degrade (BUG-017)
- **Files:** `src/api/app.py:307, 512, 541`
- **Change:** Replace each `except Exception: pass` with:
  ```python
  except Exception as exc:
      queue.put({"event": "warning", "data": {"stage": "1min_load", "message": str(exc)}})
  ```
  Frontend `sse.ts` consumes the `warning` frame and surfaces in `progress.warnings: string[]`.
- **Verification:** integration test — request scaling backtest with missing 1-min CSV → SSE warning event received.

### FIX-2026-05-23-12 — Latent BUG-003 timestamp concat (BUG-016)
- **Files:** `src/api/app.py:120`
- **Change:** add a guard:
  ```python
  if pd.api.types.is_datetime64_any_dtype(df['Date']):
      dates = df['Date'].dt.strftime('%Y-%m-%d')
  else:
      dates = df['Date'].astype(str)
  timestamps = [f"{d}T{t}" for d, t in zip(dates, df['Time'].astype(str))]
  ```
- **Verification:** new `tests/test_candles_from_df_date_time_timestamps.py` — Date as `Timestamp`, Time as string; assert output matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$`.

---

## Phase 4 — High-severity UX and trading realism

### FIX-2026-05-23-05 — Strategy-mode header drift (BUG-019)
- **Files:** `frontend/src/App.vue:5`
- **Change:** `<h1>{{ settings.strategyMode === 'box' ? 'NQ TradingView Box Strategy' : 'NQ 1-1-2 Scaling Strategy' }}</h1>`

### Other Phase-4 items (lift directly from individual lens reports)

| Item | Lens(es) | File:line | Severity |
|---|---|---|---|
| Settings: add `:min="0.25"` to all point/SL/TP fields; validate `sl_hard >= sl_soft`; validate `leg3 > leg2` | Trading TRD-S-1/2/3 | SettingsPanel.vue:62-94 | High |
| Settings: surface "Settings changed — Run Backtest to apply" hint | UX/UI UXUI-S-2 | SettingsPanel.vue:128 | High |
| Replay: while open trade, compute unrealized PnL = `(close − avg_entry) × contracts × point_value × dir` and add to runningPnl | Financial FIN-R-1, Trading TRD-R-1 | replay.ts:25-28 | High |
| ChartPane: `fitContent()` only on initial mount, not on every replay tick | UX/UI UXUI-C-1, Trading TRD-C-5, Technical TECH-C-2 | ChartPane.vue:217 | High |
| ChartPane: shallow-watch correctness — drop unused `{deep:false}` annotation or replace with `series.update()` per tick | Technical TECH-C-1/2 | ChartPane.vue:326 | High |
| BoxesPrimitive: replace `lowerBound - 1` with `upperBound` for x2 path (off-by-one when end matches bar) | Technical TECH-C-3 | BoxesPrimitive.ts:95 | Medium |
| MetricsCards: render Avg Win/Avg Loss color from sign at call-site, not as a fixed prop | UX/UI UXUI-M-2, Logic LOG-M-3 | MetricsCards.vue:13-14 | High |
| TradeList: `:key="${i}-${entry_idx}-${exit_idx}"` to avoid collisions on re-entry | Technical TECH-T-3, Logic LOG-T-1 | TradeList.vue:42 | High |
| TradeList: drop or fix "weekly + monthly" cell — only one fires; show priority label | Logic LOG-T-2, Trading TRD-T-6 | TradeList.vue:68-75 | Medium |
| `get_signal_detail`: add `conflict: bool` flag when weekly & monthly disagree | Logic LOG-T-3 | box_lookup.py:160-184 | High |

---

## Phase 5 — Medium severity hygiene

(Apply as time permits. None block release.)

- Settings: collapsible sections, group `point_value` under "Instrument", add unit chips to NumField (UXUI-S-1, S-4, S-6).
- MetricsCards: `tabular-nums`, `Intl.NumberFormat`, centralise `formatDollar` in `services/format.ts` (UXUI-M-6, M-7, QC-MC-5).
- TradeList: add filter chips, sortable columns, glossary tooltips, `truncate` on max-w cells (UXUI-T-1, T-5, T-7).
- ChartPane: conditional pane creation for Volume/RSI when toggled off; legend overlay for B/S markers (UXUI-C-5, C-8, QC-CP-3).
- Replay: speed 100×/500×/"skip to next trade"; trade tick-marks on scrubber; `tabindex` + keydown on rows (TRD-R-4, UXUI-R-3, UXUI-T-4).
- Documentation parity: add `Total Fees`, `Final Capital`, `Expected Value` cards even before fees are computed (FIN-M-7).
- Backend: add `pytest.ini` with `rootdir = .` (QA-X-6); use `pytest.skip(...)` instead of silent `return` in `test_loader_4h.py:46` (QA-X-7).

---

## Phase 6 — Low severity polish

(Cosmetics; ship in batches.)

- Sign formatter: treat exact zero as unsigned (FIN, UXUI, QC echoes).
- CSV export filename includes HHMMSS (QC-TL-8).
- Header subtitle: replace "phase D" with build version (UXUI-H-2, QC-H-1).
- Default browser radio styling on dark theme (UXUI-S-8).
- `aria-label` on icon buttons (UXUI-R-2, R-5).
- Locale-format elapsed-ms (QC-PB-3).
- ChartPane EMA disappear notice when insufficient candles (QC-CP-4).

---

## Verification Gates Between Phases

After each phase, BEFORE moving to the next:
1. Run `pytest tests/ -v` from repo root.
2. Run `cd frontend && npm test`.
3. Manual: hard-reload browser, run a backtest in **both** Scaling and Box modes, verify the metrics cards, chart, and trade list render the expected data (no `0.00` where `N/A` should appear, no `-$0.00` red).
4. Append a fresh row to `docs/bug-checklist-revision-history.md` Master Bug Register if any new bug is discovered.

Release gate (per `docs/reviewer-playbook-segmented.md §9`):
- Phases 0, 1, 2, 3 all merged.
- Stage A (Known Bugs Pass against checklist) returns no FAIL.
- No new Critical or High items added without an accompanying FIX-2026-05-23-* entry.

---

## Ownership Suggestion

| Phase | Suggested owner |
|---|---|
| 0 | Core Engineering (regression seal) |
| 1 | Quant/Strategy Engineering (financial correctness) |
| 2 | QA + Core Engineering (test infrastructure) |
| 3 | Backend Engineering (contract + security) |
| 4 | Frontend Engineering + UX |
| 5 | Frontend Engineering |
| 6 | Anyone (polish PRs) |

---

## Estimated Effort (rough)

- Phase 0: 0.5 day each fix → 1 day total.
- Phase 1: 1 day per fix → 4 days.
- Phase 2: 2 days (test scaffolding + 5 component tests + BoxesPrimitive tests).
- Phase 3: 2-3 days (Pydantic + security + warning frames + property test).
- Phase 4: 3-4 days.
- Phase 5: 2-3 days (mostly UI polish).
- Phase 6: 1 day batch.

Critical path (Phases 0-3): ~10 days for one engineer; ~4 days with 2 engineers in parallel.
