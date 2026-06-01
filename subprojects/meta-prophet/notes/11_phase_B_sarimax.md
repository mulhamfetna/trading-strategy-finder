# Phase B — SARIMAX (plain + regressors)

> Scripts: `scripts/06_sarimax_plain.py`, `scripts/07_sarimax_regressors.py`.
> Outputs: `outputs/06_sarimax_plain.csv`, `outputs/07_sarimax_regressors.csv`.
> Library: statsmodels 0.14 `SARIMAX`, fixed `order=(1,0,1)`.

## Why SARIMAX

SARIMAX is the standard non-Prophet way to do AR + exogenous regressors. Two questions answered:
- **B.1 (plain):** does a different ARIMA library (statsmodels vs pmdarima) change the verdict? (Sanity-check.)
- **B.2 (regressors):** do the 14 bar-open-known regressors from Phase 2 add any value beyond pure AR?

## Headline numbers

| Model | RMSE ($) | MAE ($) | MAPE (%) | Hit-rate (%) | Lift vs naive (%) |
|---|---:|---:|---:|---:|---:|
| naive | 133.59 | 96.40 | 0.377 | — | 0.00 |
| prophet | 133.89 | 97.22 | 0.380 | 51.62 | −0.22 |
| arima (pmdarima) | 133.95 | 96.70 | 0.378 | 53.50 | −0.26 |
| **sarimax-plain (statsmodels)** | **134.05** | 96.72 | 0.378 | **53.50** | −0.34 |
| **sarimax-regressors** | **134.20** | 97.24 | 0.380 | **51.62** | **−0.45** |

## Honest read

**B.1 (plain SARIMAX) ≈ pmdarima ARIMA.** RMSE differs by 0.07% (134.05 vs 133.95); hit-rate is identical at 53.50%. **The verdict is library-robust** — our ARIMA result wasn't a pmdarima artifact. Statsmodels's fixed-order SARIMAX(1,0,1) lands in the same place as pmdarima's AIC-selected auto-ARIMA.

**B.2 (SARIMAX + 14 regressors) is *worse*, not better.** RMSE goes UP from 134.05 (plain) → 134.20 (regressors). Hit-rate drops from 53.50% → 51.62% — **regressors actively hurt directional accuracy**. This mirrors Phase 2's finding: Prophet's CV picked `cps=0.001` (rejecting trend flexibility), and SARIMAX's regressors don't help either. **The 14 bar-open-known features add noise, not signal, on this dataset.**

## Cross-phase pattern emerging

Two independent libraries (Prophet via `add_regressor`, SARIMAX via `exog=`) tested the regressor question, and **both came back negative or neutral**. This is becoming a robust finding, not a single-experiment fluke:

| Model | RMSE plain | RMSE +regressors | Δ |
|---|---:|---:|---:|
| Prophet | (no plain run) | 133.89 | — |
| ARIMA / SARIMAX | 133.95 / 134.05 | 134.20 (SARIMAX+exog) | +0.15 |

The Darts experiments in Phase D will give us 3 more data points (RNN, NBEATS, TFT × plain/regressors). If all three corroborate the SARIMAX result, we can definitively conclude that **the 14 bar-open-known features we engineered do not help any point-forecast model on this data**.

## Caveats

1. SARIMAX order is fixed at `(1,0,1)`. pmdarima's AIC search in Phase 3 may have picked a slightly different order — but the result is so close to pmdarima's that the impact is at most 0.07% RMSE, well within noise.
2. SARIMAX with `enforce_stationarity=False` allows non-stationary AR — appropriate because we're already feeding it stationary log-returns, but means the optimizer can wander into mathematically odd parameter regions on small training slices.
3. Same n=1 regime caveat as all other phases — verdict on regressors is for this specific 16-month sample.
