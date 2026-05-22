# Copilot Instructions — Trading Strategy Finder

## Run from the repo root

- Use `python3 -m src.main.main` for the multi-strategy comparison.
- Use `python3 -m src.main.ultimate_dashboard` for the 15-min dashboard.
- Use `python3 -m src.main.fast_optimizer` for the parameter sweep.
- Use `python3 -m src.main.live_dashboard` for the live simulation dashboard.
- Use `python3 -m src.main.run_strategy --data 1min.csv --start 2025-09-01 --end 2025-12-31 --strategy scalping` for a custom date range.
- Use `python3 run_dashboard_on_train.py` for the train-split dashboard variant.
- Use `uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000` for the FastAPI backend.

## Tests

- Run the suite with `pytest tests/ -v`.
- Run a single test with pytest nodeid syntax, for example:
  `pytest tests/test_api.py::test_backtest_runs_pipeline_and_returns_metrics -v`
- There is no repo-defined build, lint, or typecheck command.

## Architecture

`src/data/loader.py` loads and normalizes OHLCV CSVs, `src/data/splitter.py` handles the 2025/date-range splits, and `src/data/resampler.py` builds higher timeframes. Indicator modules in `src/indicators/` add timeframe-specific features, `src/signals/base_signals.py` turns them into `signal` values, `src/signals/ml_filter.py` adds the ML gate, `src/backtest/engine.py` simulates trades, `src/backtest/metrics.py` summarizes them, and `src/dashboard/` renders reports and charts. Entry points in `src/main/` wire those pieces together, while `src/api/app.py` exposes the same strategy/backtest pipeline over FastAPI.

`src/strategy/scalping_strategy.py` and `src/strategy/backtester.py` are the OOP wrapper used by the newer entry points and the API. The API is currently the live-dashboard migration surface; the tests cover its REST and SSE endpoints directly.

## Conventions that matter here

- Prefer `load_data()` over `pd.read_csv()`; it strips headers, normalizes column names to Title Case, and maps `datetime` to `Date`.
- Most indicator/signal helpers copy the DataFrame before mutating it and return a new frame.
- Signal values are `-1` short, `0` hold, `1` long.
- `generate_*_signals()` writes the rule-based `signal` column; `apply_ml_filter()` adds `ml_signal` and leaves `signal` in place.
- `run_backtest()` reads `signal` first and only falls back to `ml_signal` when `signal` is missing.
- The 1-minute CSV is loaded newest-first; reverse it to ascending order before backtesting.
- The common split point is `2025-06-30`, with most flows limited to 2025 data.
- Backtest trade dicts are consumed by metrics and dashboards; keep `entry_idx`, `exit_idx`, `direction`, `entry_price`, `exit_price`, `profit_pct`, `profit_dollars`, `capital_after`, `exit_reason`, and `fees_paid` intact.
- `tp_sl_resolution` is a real input with three accepted values: `conservative`, `optimistic`, and `direction-proxy`.
- Generated artifacts go under `output/dashboards/` and `output/configs/`; do not commit generated HTML/JSON/config files.
- If docs and code disagree, trust the executable code.

## Data and file layout reminders

- Restore the root-level CSVs before running anything that needs market data.
- Keep changes aligned with the `src/` package layout; the old root-level script paths in some docs are stale.
