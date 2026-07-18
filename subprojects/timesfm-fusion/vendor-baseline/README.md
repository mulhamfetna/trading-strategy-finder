# TimesFM Futures Strategy Harness (NQ / ES)

An honest, out-of-sample backtest stack that uses Google's **TimesFM** time-series foundation
model as a **standalone directional signal** — wrapped in a distribution-aware edge filter and
volatility-adaptive risk sizing. Built to be compared, fairly, against the reference
`mtf_layer_fusion_backtester`.

## Why this design

TimesFM forecasts a *distribution* over the future path (median + 10th/90th deciles). We never
trade a raw point forecast; a trade fires only when the expected move **exceeds the forecast's own
uncertainty** by a margin *and* clears a cost/noise floor. SL/TP are sized off the forecast
distribution, so risk adapts to the current price regime and timeframe automatically.

Critically, everything is measured **out-of-sample**: params are tuned on the first ~70% of the
data (TRAIN) and reported on the held-out ~30% (TEST). The reference numbers are full-period,
in-sample, n=1 — so the TEST return/DD here is the honest yardstick.

## Layout

| file | role |
|---|---|
| `tfm/data.py` | load NQ/ES OHLCV, per-contract economics + costs, walk-forward split |
| `tfm/forecaster.py` | `Forecaster` interface, `MockForecaster` (causal null), `TimesFMForecaster` |
| `tfm/strategy.py` | forecast → (direction, edge filter, vol-adaptive SL/TP) |
| `tfm/engine.py` | causal single-contract backtest (intrabar SL/TP, horizon force-exit, costs) |
| `tfm/metrics.py` | stats matching the reference `run_stats.py` (PnL, PF, maxDD, return/DD) |
| `tfm/walkforward.py` | tune a small robust grid on TRAIN, report on TEST |
| `run.py` | CLI entry point |

## Run

```bash
pip install numpy pandas                      # harness only
python run.py --instrument ES --tf 1h         # mock forecaster (null baseline)
python run.py --instrument NQ --tf 1h

pip install "timesfm[torch]"                  # the real model (weights pulled on first use)
python run.py --instrument ES --forecaster timesfm --tf 1h
```

Data path defaults to the reference bundle; override with `FUTURES_DATA_DIR`.

## Status

- [x] Causal harness + walk-forward validated end-to-end on the mock (null) forecaster.
- [x] Real TimesFM 2.5 (200M, PyTorch, CPU) wired in: `compile(ForecastConfig)` then batched
      `forecast`; full-series forecasts are disk-cached (`.cache/`) so threshold sweeps are free.
- [x] Any-timeframe support: native 1m/1h/4h + resampled 2m/5m/15m/30m/2h from 1m.
- [~] Diagnostic (`diagnose.py` / `run_diag.py`): does the median carry directional edge, and is
      the quantile band calibrated? Drives the strategy choice below.
- [ ] Standalone directional walk-forward on ES/NQ, OOS vs benchmark.
- [ ] If no directional edge (expected): pivot to TimesFM's calibrated volatility — either a
      band-reversion standalone strategy, or a defensive overlay on the box-breakout edge.

## Compute notes (CPU)

Model load+compile ≈ 445 s (once per process); inference ≈ 60 ms/context. So one full-series pass:
1h ≈ 8 min, 15m ≈ 32 min, 5m ≈ 90 min, 1m ≈ 8 h. Forecasts are cached to disk, so re-runs and
threshold sweeps are instant. Precompute the big timeframes first; lower TFs are batched jobs.
