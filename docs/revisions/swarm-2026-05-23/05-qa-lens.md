# QA Lens Audit Findings

Generated: 2026-05-23
Lens: QA / Quality Assurance (test coverage, reproducibility, traceability, regression-suite quality, test-isolation, mocking integrity)

## Section: Header
- **QA-H-1** | High | frontend/tests/ (no file) — Zero tests cover `App.vue`. Run-Backtest, Replay, keybindings, layout order have no assertion.
  - Fix: Add `App.test.ts` with testid assertions and a layout-order snapshot.
- **QA-H-2** | Medium | frontend/src/App.vue:76-91 — Spacebar/arrow keybindings have no unit test.
  - Fix: Dispatch synthetic `KeyboardEvent` in a mounted test.

## Section: SettingsPanel
- **QA-SP-1** | High | frontend/tests/SettingsPanel.test.ts:17-26 — Only label text asserted; no schema-shape check against Pydantic `StrategyConfig`.
  - Fix: Contract test against the real Pydantic model.
- **QA-SP-2** | Medium | frontend/src/components/FilePicker.vue, DatePicker.vue — Zero tests despite non-trivial logic.
- **QA-SP-3** | Medium | frontend/tests/SettingsPanel.test.ts:40-51 — Reset test only checks `total_contracts`.

## Section: ProgressBar
- **QA-PB-1** | High | frontend/tests/ — Zero tests for `ProgressBar.vue`. `data-testid="progress-panel"` unused.

## Section: ReplayBar
- **QA-RB-1** | High | frontend/tests/ — Zero tests for `ReplayBar.vue`. Only store logic is covered, not UI binding.

## Section: MetricsCards
- **QA-MC-1** | Medium | frontend/tests/ — Zero tests for `MetricsCards.vue` or `MetricCard.vue`. Critical "$2/point" lock isn't reflected here.

## Section: ChartPane
- **QA-CP-1** | Critical | frontend/tests/ChartPane.test.ts:49-54 — `mountChart` never passes `boxes` or `trades`. The new BoxesPrimitive bar-time snapping is uncovered.
  - Fix: Add `BoxesPrimitive.test.ts` with unit tests for `lowerBound` and the snap behavior.
- **QA-CP-2** | High | frontend/tests/ChartPane.test.ts:31-38 — `lightweight-charts` fully mocked; `attachPrimitive`/`setData` are spied but payload shape never asserted.
- **QA-CP-3** | High | frontend/src/components/BoxesPrimitive.ts — No `.test.ts` peer.
- **QA-CP-4** | Medium | frontend/tests/chart_data.test.ts:9 — Helpers duplicated, not imported from production code.

## Section: TradeList
- **QA-TL-1** | High | frontend/tests/ — Zero tests for `TradeList.vue` despite recent activity (Save CSV button, reactivity fix, remove 200-row cap).
- **QA-TL-2** | High | frontend/src/types.ts:120 — `box_signal?: BoxSignal` has no counterpart in Pydantic schemas.py; no contract test.

## Cross-cutting findings
- **QA-X-2** | High | src/api/app.py — Multiple `except Exception: pass` in 1-min load and box overlay paths.
- **QA-X-3** | Critical | frontend/tests/sse_parser.test.ts:9-24 — Test re-implements `parseSseFrame` instead of importing.
  - Fix: Export `parseSseFrame` and import.
- **QA-X-4** | High | tests/ — No tests for `src/strategy/box_strategy.py`, `src/strategy/box_lookup.py`, `scripts/preprocess_boxes.py`.
- **QA-X-5** | High | repo root — No Playwright/Cypress; no E2E for Run Backtest → SSE → Chart → click flow.
- **QA-X-6** | Medium | repo root — No `pytest.ini` / `pyproject.toml`.
- **QA-X-7** | Medium | tests/test_loader_4h.py:46 — Silent `return` on missing data file instead of `pytest.skip`.

## Summary
- Total: 18 | Critical: 2 | High: 10 | Medium: 6 | Low: 0
- Components with zero frontend tests: App.vue, ProgressBar.vue, ReplayBar.vue, MetricsCards.vue, MetricCard.vue, TradeList.vue, StatusItem.vue, NumField.vue, FilePicker.vue, DatePicker.vue, BoxesPrimitive.ts (11 of 12).
- Backend modules with zero tests: box_strategy.py, box_lookup.py, scripts/preprocess_boxes.py.
- **Post-cleanup note (2026-05-23):** QA-X-1 dropped — bare `except: pass` (BUG-015 regression) lived in `src/signals/ml_filter.py:89` and `src/main/ultimate_dashboard.py:310`, both of which were erased with the legacy purge. BUG-015 is no longer reachable from the active codebase.
