"""WS-H — multi-timeframe entry-frame parameter search (self-contained in this subproject).

Everything for the per-timeframe profit-vs-drawdown optimisation lives here:
  timeframes.py  — the 7 decision-timeframe registry (bar duration + raw CSV) [H.3]
  core.py        — timeframe-parametric, metrics-only backtest (engine + gate + breaker) [H.1]
  ...            — cooldown caps [H.4], SL/TP bounds [H.5], folds [H.6], NSGA-II driver [H.7]

See TASK.md for the full spec. Nothing here writes outside subprojects/wsg-strategy/.
"""
