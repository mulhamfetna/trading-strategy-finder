# Dashboard Template + Candlestick View Design

## Problem Statement

The current dashboard HTML is built as a large hardcoded string inside `ultimate_dashboard.py`. The chart also emphasizes the close series more than the candle structure, even though the underlying data already contains `Open`, `High`, `Low`, and `Close`.

This phase will:

1. Extract the HTML shell into a template file.
2. Add a reusable renderer for filling the template from Python.
3. Upgrade the chart to a candlestick view.
4. Make opening and closing prices explicit in the dashboard UI.

Scope excludes the live-dashboard migration and larger codebase restructuring.

## Architecture

- `templates/ultimate_dashboard.html.tpl`
  - Holds the dashboard shell, layout, styles, and script placeholders.
  - No Python logic lives in the template.
- `src/dashboard/template_renderer.py`
  - Loads the template file from disk.
  - Performs strict placeholder replacement using standard-library string handling.
  - Raises explicit errors when the template file or required placeholders are missing.
- `ultimate_dashboard.py`
  - Continues to assemble dashboard data.
  - Delegates final HTML composition to the renderer.

This separation keeps data preparation in Python and presentation in the template.

## Data Flow

1. `create_ultimate_dashboard()` or the existing dashboard generator builds the final dashboard payload.
2. The renderer injects prebuilt metric blocks, trade sections, logs, insights, and chart JSON into the template.
3. The chart uses Plotly candlesticks built from `Open`, `High`, `Low`, and `Close`.
4. A compact OHLC summary panel shows the latest candle open and close values for quick inspection.
5. The final HTML is written to `output/dashboard/ultimate_trading_dashboard_test.html`.

## UI Behavior

- The main chart should show candlesticks instead of only a close-price line.
- Open and close prices must be visible in the dashboard UI without requiring code inspection.
- The close line may remain as a lighter overlay if it improves readability, but the candle structure is the primary view.

## Error Handling

- Missing template file raises a clear `FileNotFoundError`.
- Missing required placeholders or context keys raises an explicit error.
- The renderer does not silently emit partial HTML if a required value is missing.

## Testing

Add tests that verify:

1. The renderer can load the template and emit HTML to the expected output path.
2. The dashboard template is externalized from `ultimate_dashboard.py`.
3. The chart payload includes OHLC arrays and the generated HTML references candlestick rendering.
4. Existing dashboard and backtest tests still pass after the refactor.

## Deliverables

1. `templates/ultimate_dashboard.html.tpl`
2. `src/dashboard/template_renderer.py`
3. Updated dashboard generation flow using the template
4. Candlestick chart with explicit open/close visibility
5. Passing tests and regenerated dashboard artifact

