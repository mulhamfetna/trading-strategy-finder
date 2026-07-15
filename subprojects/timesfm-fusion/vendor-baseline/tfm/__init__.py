"""TimesFM-driven futures strategy harness (NQ / ES).

A clean, self-contained backtest stack that uses a *time-series foundation model*
(Google TimesFM) as a STANDALONE directional signal generator, wrapped in a
distribution-aware edge filter and volatility-adaptive risk sizing.

Design goals:
  - honest out-of-sample (walk-forward) evaluation, never in-sample curve-fit only
  - realistic costs (commission + slippage), 1 contract, single position
  - the forecaster is an interface: swap MockForecaster <-> TimesFMForecaster freely
"""
