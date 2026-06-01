# Phase 3 — ARIMA

> Script: `scripts/03_arima.py`. Output: `outputs/03_arima.csv` (585 rows).

`auto_arima(p∈[0,5], q∈[0,5], d=0, AIC)` on log-returns, walk-forward retrain_every=20 on 2026.

## Headline numbers

| metric | naive | ARIMA | lift vs naive |
|---|---:|---:|---:|
| RMSE  | $133.59 | $133.95 | **−0.26%** |
| MAE   | $96.40 | $96.70 | −0.31% |
| MAPE  | 0.377% | 0.378% | −0.25% |
| hit_rate | 0.00% (degenerate) | **53.50%** | — |

## Honest read

ARIMA's RMSE is **statistically indistinguishable from naive** (lift = −0.26%, well within noise on 585 bars). Its yhat is essentially a tiny bias around zero log-return per bar — which is the AR-AIC-selected stationary process's best linear forecast under the assumption that returns are white noise. Note the result is *very slightly worse* than naive, meaning AIC-selected ARIMA terms add tiny noise that costs ~$0.36/bar in RMSE on a $133.59 baseline.

The interesting number is **hit_rate = 53.5%**. ARIMA is right on direction ~53% of the time vs naive's 0% (naive predicts yhat_return = 0 which doesn't have a sign). So ARIMA *does* extract a small directional signal — but it's small enough that it doesn't show up in RMSE because the magnitude of its predicted moves is also small relative to actual moves. This is the textbook "Slutsky-effect" result: any stationary linear model fit to log-returns will produce point forecasts close to zero, and beating the naive forecast requires either (a) modelling something other than the mean (volatility, regime), or (b) a model with explicit autoregression at the *right* lag (which ARIMA tries, but on this data the AIC criterion doesn't find a strong enough lag to materially exceed the mean estimate).

## Implication for the tournament

If Prophet (with all the levers from the research report: log-returns target, regressors, walk-forward, CV-tuned changepoints) still cannot beat naive after this, that's strong evidence that **the structural problem isn't Prophet's specific assumptions — it's that 4h NQ log-returns are close to white noise**, and no point-forecast model can extract enough edge to register in RMSE. That would be the dominant verdict of the study.
