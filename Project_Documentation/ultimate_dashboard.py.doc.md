File: src/main/ultimate_dashboard.py
Relative path: src/main/ultimate_dashboard.py
High-level overview:
- Generator for the 15-minute ML-filtered scalping dashboard. Resamples
  1min -> 15min, runs the scalping pipeline with RSI(5), EMA(5/15),
  volume spike + RandomForest filter, backtests with NQ point-value
  PnL, and renders an HTML dashboard with candlestick chart, OHLC
  summary, metric grid, trade log, and analysis tabs.
Purpose:
- Standalone "proof of concept" dashboard used as the headline artifact.
Run:
- From repo root: `python3 -m src.main.ultimate_dashboard`
- Writes:
    output/dashboards/ultimate_trading_dashboard.html  (iter 3)
    output/dashboards/dashboard_data.json              (iter 3)
Key functions/sections:
- create_ultimate_dashboard(): main orchestrator.
- resample_15min(df), prepare_data(df), train_ml(df), apply_ml_filter(...),
  apply_rsi_entry_filters(signals, rsi_values, ...)
- run_backtest_15min(signals, closes, df, ...): backtest variant tailored
  for the 15min pipeline. Uses NQ point value (=2.0) for PnL. Note: this
  has not yet been migrated to the intra-candle TP/SL resolution that
  src/backtest/engine.py uses (iter 4 follow-up).
- analyze_trade(df, trade, n), prepare_chart_data(...), generate_logs(...),
  generate_insights(...): build the dashboard payload.
- generate_html(data): renders the HTML by composing Python fragments
  and calling src/dashboard/template_renderer.render_template against
  templates/ultimate_dashboard.html.tpl (iter 2 - 19 named slots).
Inputs/outputs:
- Inputs: 1min.csv at repo root.
- Outputs: docs/dashboard_data.json -> output/dashboards/dashboard_data.json,
  output/dashboards/ultimate_trading_dashboard.html.
Related files:
- src/data/loader.py, src/data/splitter.py
- src/signals/ml_filter.py (Random Forest)
- src/backtest/engine.py (separate from run_backtest_15min defined here)
- src/dashboard/template_renderer.py (iter 2)
- templates/ultimate_dashboard.html.tpl (iter 2)
- run_dashboard_on_train.py at repo root invokes this module against the
  train split.
Tests referencing this file:
- tests/test_ultimate_dashboard.py:
    apply_rsi_entry_filters, generate_html (candlestick, total fees,
    template separation, output path), run_backtest_15min (NQ point
    value), fast_optimizer & run_dashboard_on_train path assertions.
Notes / Gotchas:
- 1min data is descending; the pre-resample step reverses it
  ([::-1]) - keep this if you add a new pipeline.
- run_backtest_15min only checks Close for TP/SL. src/backtest/engine.py
  was upgraded to High/Low + resolution modes in iter 4; this function
  has NOT been migrated yet.
- apply_rsi_entry_filters zeros out signals where RSI is on the wrong
  side of the band (longs require RSI <= oversold). Tested behavior -
  don't relax without updating the test.
Academic notes:
- See docs/Tutorials/Random_Forest_Filter.md, RSI.md,
  PL_TP_SL.md, Sharpe_Ratio.md.
