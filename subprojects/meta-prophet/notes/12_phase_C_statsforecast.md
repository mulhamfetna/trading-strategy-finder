# Phase C — Nixtla StatsForecast AutoARIMA

> Script: `scripts/08_statsforecast_autoarima.py`. Output: `outputs/08_statsforecast_autoarima.csv`.
> Library: `statsforecast==1.7.6` (Nixtla), `AutoARIMA(max_p=5, max_q=5, d=0)`.

## Headline numbers

| Library | RMSE ($) | MAE ($) | MAPE (%) | Hit-rate (%) | Lift vs naive (%) |
|---|---:|---:|---:|---:|---:|
| **pmdarima** auto_arima (Phase 3) | 133.95 | 96.70 | 0.378 | 53.50 | −0.26 |
| **statsmodels** SARIMAX(1,0,1) (Phase B.1) | 134.05 | 96.72 | 0.378 | 53.50 | −0.34 |
| **nixtla** StatsForecast AutoARIMA (this phase) | 134.92 | 97.14 | 0.380 | 51.79 | **−0.99** |

## Honest read

**Three ARIMA implementations, three slightly different results.** The spread is ~0.97% RMSE between the best (pmdarima 133.95) and the worst (Nixtla 134.92), with statsmodels SARIMAX landing in between. All three lose to naive — but the *magnitude* of the loss differs by 4× (Phase 3's −0.26% vs this phase's −0.99%).

**This is an instructive finding about ARIMA-library variance:** with identical data, identical (d=0, no-seasonality, AIC) selection criterion, identical walk-forward protocol, **three implementations land 0.97% apart in RMSE**. The most likely reasons:

1. **Different (p,q) choices.** AIC selection is stepwise/heuristic; small numerical differences in likelihood computation can flip which model wins. We don't log per-retrain order selections, so can't confirm directly without a deeper trace.
2. **Different optimizers.** pmdarima uses statsmodels under the hood but with custom step heuristics; raw statsmodels uses MLE; Nixtla uses a Fortran-port (originally R's auto.arima) reimplemented in Python.
3. **Different initialization defaults.** SARIMAX `enforce_stationarity=False` vs Nixtla's default constraints could affect early-walk-forward fits where data is thin.

## Cross-phase summary so far (6 entries)

| Rank | Model | RMSE | Lift vs naive |
|---:|---|---:|---:|
| 1 | naive | 133.59 | 0.00 |
| 2 | prophet (tuned) | 133.89 | −0.22 |
| 3 | arima (pmdarima) | 133.95 | −0.26 |
| 4 | sarimax-plain | 134.05 | −0.34 |
| 5 | sarimax-regressors | 134.20 | −0.45 |
| 6 | statsforecast | 134.92 | **−0.99** |

**The naive baseline is increasingly dominant.** Phases 2-C add 5 entries spanning Prophet (Bayesian piecewise trend), pmdarima ARIMA (stepwise AIC), statsmodels SARIMAX (fixed order ± regressors), and Nixtla AutoARIMA (Fortran-port stepwise) — none beats predicting "tomorrow ≈ today". Phase D's Darts (LSTM / NBEATS / TFT) is the last chance to find a model that does.

## Caveats

- We did not log per-retrain (p,q) order selections — that would require modifying the driver. If the Darts results are also negative, a follow-up audit of the Nixtla order selections vs pmdarima's would be worth doing.
- Nixtla's library specialises in *batched* multi-series forecasting; running it one-series-at-a-time in our harness doesn't exploit its primary speedup. Wall-clock comparison would be unfair as set up.
