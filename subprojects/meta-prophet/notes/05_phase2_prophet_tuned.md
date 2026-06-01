# Phase 2 — Prophet tuned

> Script: `scripts/02_prophet_tuned.py`. Outputs: `outputs/02_prophet.csv` (585 rows), `outputs/02_prophet_search.json` (full 40-config search log).

## Tier 1 — hyperparam search on 2025

Grid: `changepoint_prior_scale × seasonality_prior_scale × seasonality_mode` (5 × 4 × 2 = 40 configs). Each scored via Prophet's `cross_validation(initial='180 days', period='14 days', horizon='4 hours')` + `performance_metrics(rolling_window=1)`.

**Locked config: `cps=0.001, sps=0.1, mode=multiplicative` → CV-rmse = 0.004802 (on log-returns).**

Notable: CV picked the **tightest changepoint flexibility** (`cps=0.001`, smallest in grid). That tells us Prophet's CV evaluator found *no useful trend signal* — the more rigid the trend, the better the CV score. The grid showed `cps=0.001, 0.1, 0.5` tied on the same rmse_cv at multiple `(sps, mode)` combinations, meaning the regularisation regime doesn't matter much — log-returns are near-stationary noise and Prophet has very little to fit beyond zero.

**Regressors dropped:** `dow_sat` (NQ futures closed Saturdays — constant zero). Other 14 of 15 regressors retained.

## Tier 2 — walk-forward on 2026

Retrain every 20 bars (~3 days) over 585 eval bars. Each retrain refits Prophet on `(all of 2025) + (2026 bars realised so far)`.

## Headline numbers

| metric | naive | Prophet (tuned) | lift vs naive |
|---|---:|---:|---:|
| RMSE  | $133.59 | $133.89 | **−0.22%** |
| MAE   | $96.40  | $97.22  | −0.85% |
| MAPE  | 0.377%  | 0.380%  | −0.85% |
| hit_rate | 0.00% (degenerate) | **51.62%** | — |

## Honest read

A **fully-tuned, log-return-target, CV-optimised, walk-forward-retrained Prophet with 14 bar-open-known regressors cannot beat the naive previous-close baseline on RMSE.** Lift is −0.22% — Prophet is marginally *worse* than predicting "tomorrow ≈ today". This is exactly the result the research report (`00_research_report.md`) and Prophet's own maintainer (@bletham, [Issue #1502](https://github.com/facebook/prophet/issues/1502)) predicted for stock/futures price series.

The 51.62% hit-rate shows Prophet does extract a tiny directional signal — but smaller than ARIMA's 53.5% on the same data, and not large enough to translate into RMSE improvement.

**What this rules out:**
- Prophet's structural assumption (smooth piecewise-linear trend + Fourier seasonality + standardised regressors) is not the right shape for 4h NQ log-returns.
- Tier-1 CV did its job and chose the most-rigid trend possible — confirming there's no time-structure for Prophet to extract beyond the mean.
- Adding more regressors (we have 14 active) does not move the needle in any tried combination.

**What this does NOT rule out:**
- A model with explicit autoregression at the *right* lag (e.g., NeuralProphet's AR-Net, or LSTMs). NeuralProphet was Phase 4 but was blocked by dependency-stack issues — see `07_phase4_neuralprophet_BLOCKED.md`.
- A model that forecasts a *different* target (volatility, regime, directional class) instead of point price. That's a different study.
- A model that uses *external* information (VIX, options skew, news sentiment, macro data). Adding regressors known only at bar-close was not in this study's scope.

## Caveats

1. Tier-1 search ran on 2025 only — there's no guarantee the locked config is optimal for the 2026 regime (which is a continuation rally vs 2025's V-shape).
2. 40-config grid is small (the design intentionally kept it so — research said only `changepoint_prior_scale` matters strongly).
3. Hit-rate 51.62% is barely above 50% noise floor — would need ~5,000+ bars to call it statistically significant.
