File: src/main/fast_optimizer.py
Relative path: src/main/fast_optimizer.py
High-level overview:
- Brute-force / grid parameter sweep for the scalping strategy. Runs many
  RSI period x oversold/overbought x EMA x volume threshold x SL/TP x ML
  combinations and writes the winner to output/configs/best_config.txt.
Purpose:
- Find the highest-Sharpe / highest-profit-factor config for the scalping
  strategy on the 2025 data slice.
Run:
- From repo root: `python3 -m src.main.fast_optimizer`
- Writes: output/configs/best_config.txt (iter 3)
Key functions/sections:
- save_best_config(config): persists the winning param set.
- analyze_parameter_impact(results): aggregates which params moved the
  needle most.
- The sweep loops and ML feature engineering are inline (could be
  extracted in iter 7 hybrid refactor).
Inputs/outputs:
- Inputs: 1min.csv at repo root.
- Outputs: output/configs/best_config.txt
- Side effect (existing in repo, not iter 6 work): the sweep historically
  mutated src/signals/base_signals.py to overwrite thresholds. Avoid this
  by treating the output config as the source of truth.
Related files:
- src/data/loader.py, src/data/splitter.py
- src/indicators/scalping.py, src/signals/base_signals.py
- src/backtest/engine.py, src/backtest/metrics.py
Tests referencing this file:
- tests/test_ultimate_dashboard.py::test_fast_optimizer_writes_best_config_to_output_configs
Notes / Gotchas:
- Run time scales with the size of the sweep grid; expect minutes-to-hours
  on the full 1min dataset.
- One source-mutation side-effect noted above is preserved for v1.x
  compatibility but flagged as a code smell in the refactor backlog.
Academic notes:
- See docs/Tutorials/Parameter_Rationale.md for what each threshold means.
