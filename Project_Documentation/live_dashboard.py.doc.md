File: src/main/live_dashboard.py
Relative path: src/main/live_dashboard.py
High-level overview:
- Live trading simulation. Walks through the test split candle-by-candle,
  prints actions to the console, and produces two HTML dashboards:
  a live-feed view and an equity curve. Designed as a demo of how the
  scalping algorithm would behave on a streaming feed.
Purpose:
- Bridge between the offline backtest and a future live-data adapter.
Run:
- From repo root: `python3 -m src.main.live_dashboard`
- Writes (iter 3):
    output/dashboards/live_trading_dashboard.html
    output/dashboards/equity_curve_dashboard.html
Key functions/sections:
- get_output_paths() -> (live_path, equity_path): the path constants
  pinned by tests/test_live_dashboard.py.
- create_live_simulation(): main loop that prints each candle and
  triggers entries/exits.
- HTML emission helpers for the live + equity views.
Inputs/outputs:
- Inputs: 1min.csv at repo root.
- Outputs: HTML files under output/dashboards/.
Related files:
- src/data/loader.py, src/data/splitter.py
- src/indicators/scalping.py
- src/signals/{base_signals,ml_filter}.py
- src/backtest/engine.py, src/backtest/metrics.py
- src/dashboard/dash_app.py (reads the HTML files this writes, with
  docs/ fallback for legacy)
Tests referencing this file:
- tests/test_live_dashboard.py::test_get_output_paths_uses_output_dashboards_directory
Notes / Gotchas:
- Output paths use plural 'dashboards/' after iter 3 (previously was
  singular 'dashboard/' on phase3-live-dashboard branch).
- This module also uses the simple close-only TP/SL check inline,
  not the intra-candle resolution from src/backtest/engine.py
  (would benefit from the iter 4 treatment in a follow-up).
Academic notes:
- See docs/Tutorials/PL_TP_SL.md for how stop loss and take profit are
  evaluated during the simulation.
