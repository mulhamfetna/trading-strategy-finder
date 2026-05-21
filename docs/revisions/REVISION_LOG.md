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
