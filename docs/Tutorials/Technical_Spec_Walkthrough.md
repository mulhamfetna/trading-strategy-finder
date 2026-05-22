# Technical Spec Walkthrough — Ultimate Dashboard

This document is the **module-by-module explanation** of the project. Use it when someone asks, “What exactly did you build?”

## 1. Problem statement

The project evaluates whether a trading strategy can be built from:
- historical market data,
- technical indicators,
- rule-based trade signals,
- an ML filter to remove weak entries,
- a backtest engine that computes realistic futures P/L,
- and a dashboard that explains the results.

The candidate role is data scientist, so the main contribution is:
- choosing the features,
- designing the signal logic,
- testing the strategy,
- and packaging the result into a reproducible report.

## 2. High-level architecture

1. `load_data()` reads raw CSV.
2. `filter_2025()` and `split_train_test()` create a time-based train/test split.
3. `resample_15min()` converts 1-minute data into 15-minute candles.
4. `prepare_data()` computes RSI, EMA, volume spike, and rule-based signals.
5. `train_ml()` trains a RandomForest filter on historical signal rows.
6. `apply_ml_filter()` removes weak candidate entries.
7. `apply_rsi_entry_filters()` enforces symmetric long/short RSI logic.
8. `run_backtest_15min()` simulates trades and computes contract P/L.
9. `calculate_metrics()` summarizes performance.
10. `generate_html()` builds the final dashboard.

## 3. Entry-point and orchestration files

### `ultimate_dashboard.py`
- Main proof-of-concept pipeline for the submitted technical task.
- Owns end-to-end flow: load/split/resample, indicators, rule signals, ML filtering, backtest, metrics, JSON output, and HTML dashboard generation.
- This is the file to present first in interview code walkthroughs because it connects all core modules into one reproducible run.

How to run:
- `python3 ultimate_dashboard.py`

Expected outcome:
- Console prints pipeline progress (load, resample, train, backtest, metrics).
- Creates/updates:
  - `docs/dashboard_data.json`
  - `docs/ultimate_trading_dashboard.html`
- Final console line indicates dashboard generation complete.

### `main.py`
- General multi-strategy execution entrypoint for broader project runs.
- Useful to explain that the project supports strategy comparison beyond the dashboard-focused pipeline.
- In interview language: this demonstrates extensibility and experiment orchestration across strategy variants.

How to run:
- `python3 main.py`

Expected outcome:
- Runs 3 strategy paths (scalping/day-trading/intraday) if enough data is available.
- Prints per-strategy metrics and comparison summary in terminal.
- Shows best strategy recommendation from comparison report logic.
- Produces analysis output in console (not a dedicated new HTML artifact).

### `fast_optimizer.py`
- Faster optimization path used to iterate parameter candidates quickly.
- Tradeoff: speed and iteration throughput vs deeper exhaustive search.
- In interview language: this supports practical research loops when you need many experiments quickly.

How to run:
- `python3 fast_optimizer.py`

Expected outcome:
- Runs random-search optimization (default 200 tests in `__main__`).
- Prints progress and “new best” configurations during search.
- Writes:
  - `best_config.txt` (best parameter set)
- Also updates RSI thresholds in `src/signals/base_signals.py` when a best config is saved (important side effect).

### `live_dashboard.py`
- Live/demo-oriented dashboard script for runtime-style visualization workflows.
- Shows how analysis artifacts can move from pure backtest reporting to operational monitoring views.
- In interview language: this bridges research outputs and real-time team usage.

How to run:
- `python3 live_dashboard.py`

Expected outcome:
- Runs a console-based “live” simulation and a 3-strategy comparison.
- Generates/updates:
  - `docs/live_trading_dashboard.html`
  - `docs/equity_curve_dashboard.html`
- Prints summary and output file paths at the end.

## 4. Data layer

### `src/data/loader.py`
- Normalizes CSV input into the expected OHLCV schema.
- This matters because the rest of the pipeline assumes consistent column names.

### `src/data/splitter.py`
- Keeps the experiment time-ordered.
- The split date `2025-06-30` prevents future data from leaking into training.

### `resample_15min()`
- Converts 1-minute bars into 15-minute bars.
- 15-minute bars reduce noise and match the scalping use case better than raw 1-minute bars for the demo.

## 5. Indicator layer

### `src/indicators/scalping.py`
- RSI(5): short momentum/exhaustion detector.
- EMA(5) and EMA(15): fast/slow trend confirmation.
- Volume spike: relative volume confirmation.

Why these values:
- short horizon,
- fast reaction,
- enough smoothing to avoid pure noise,
- and easy explanation in interview form.

## 6. Signal layer

### Rule-based signals
- `generate_scalping_signals()` turns indicator states into `-1, 0, 1`.
- That gives a deterministic baseline before ML filtering.

### RSI filter
- `apply_rsi_entry_filters()` makes long and short logic symmetric.
- Long entries are only kept if RSI is sufficiently low.
- Short entries are only kept if RSI is sufficiently high.

This is important because the earlier bug made the logic one-sided.

## 7. ML filter layer

### `src/signals/ml_filter.py`
- Adds features such as price changes, volume ratios, RSI, EMA spread, and volatility.
- Trains a RandomForest baseline classifier.
- Uses time-based historical data, not shuffled data.

Why RandomForest:
- robust baseline,
- handles nonlinear combinations,
- fast enough for interview/demo scale,
- easy to explain.

Why `n_estimators=100` and `max_depth=10`:
- 100 trees gives stable results.
- depth 10 keeps it from overfitting a small dataset.

## 8. Backtest layer

### `run_backtest_15min()`
- Enters a position when a signal appears.
- Exits on stop-loss or take-profit.
- Uses `point_value=2.0` for NQ E-mini futures.
- Computes `profit_dollars = points_moved * point_value - fee_per_trade`.

Why this matters:
- futures are not naturally measured as percent-of-capital,
- point-based P/L matches how the contract really pays,
- and it makes the dashboard economically correct.

### `src/backtest/metrics.py`
- Converts trade results into net profit, win rate, profit factor, drawdown, Sharpe, and expected value.
- These are the numbers the dashboard and interview talk track rely on.

## 9. Dashboard layer

### `generate_html()`
- Creates the visual report.
- Shows metrics, trade list, analysis, playbook rules, logs, and insights.

Why the dashboard exists:
- the final interview is not just “did it work?” but “can you explain it?”
- the dashboard turns strategy mechanics into a story.

## 10. What to say in the interview

1. “I started with raw 1-minute data and reshaped it into 15-minute candles to reduce noise.”
2. “I used RSI, EMA, and volume because they capture momentum, trend, and participation.”
3. “I trained a RandomForest as a signal filter, not as the main signal generator.”
4. “I corrected the P/L model to contract economics, which is the right framing for futures.”
5. “I built the dashboard so the team lead can integrate the playbook into the live system.”

## 11. Hidden assumptions and caveats

- No advanced slippage model beyond fixed fees.
- No multi-contract sizing.
- No walk-forward optimization in this proof-of-concept.
- The ML filter is a baseline, not a final production model.

These are good points to mention because they show engineering honesty.
