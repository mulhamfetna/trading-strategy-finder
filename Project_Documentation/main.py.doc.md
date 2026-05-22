File: src/main/main.py
Relative path: src/main/main.py
High-level overview:
- Multi-strategy comparison entrypoint. Loads data, prepares the scalping,
  day-trading, and intraday strategies, and compares their metrics
  side-by-side.
Purpose:
- Provide a single command that runs all three strategies on the same data
  and prints a summary so the user can pick a winner.
Run:
- From repo root: `python3 -m src.main.main`
  (the file is a module under src/main/ since commit cf904c9 - do not run
  `python3 src/main/main.py` directly, the imports won't resolve.)
Key functions/sections:
- main(): orchestrates the three strategy runs.
- run_scalping_strategy(train, test, capital): scalping path on 1min data
  (reverses the descending CSV to ascending - see src/main/main.py:42).
- run_day_trading_strategy(train, test, capital): 15min day-trading path.
- run_intraday_strategy(train, test, capital): 15min intraday path.
Inputs/outputs:
- Inputs: 1min.csv and NQ_15min_processed.csv at repo root.
- Outputs: console-only comparison report.
Related files:
- src/data/loader.py, src/data/splitter.py (filter_by_date_range, split_train_test)
- src/indicators/{scalping,day_trading,intraday}.py
- src/signals/{base_signals,ml_filter}.py
- src/backtest/{engine,metrics}.py
- src/dashboard/report.py (generate_comparison_report)
Tests referencing this file:
- No direct tests; the pieces are covered by tests/test_signals.py,
  tests/test_backtest.py, tests/test_indicators.py.
Notes / Gotchas:
- The 1min CSV loads newest-first; main.py:42 reverses it to ascending
  before the scalping backtest. Do the same in any new pipeline that
  consumes 1min data directly.
- Strategy scope is hardcoded to 2025 with split at 2025-06-30; for
  arbitrary date ranges use src/main/run_strategy.py (iter 5).
Academic notes:
- Demonstrates the train/test split discipline; ML filter trained on
  pre-2025-06-30 candles and applied to the test window.
