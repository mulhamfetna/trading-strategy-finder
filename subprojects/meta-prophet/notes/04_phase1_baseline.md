# Phase 1 — Naive baseline + harness

> Scripts: `scripts/01_baseline_naive.py`, `scripts/common/{data,features,metrics,walkforward}.py`
> Tests: 19 green (`tests/test_{data_load,metrics,features,walkforward}.py`)
> Output: `outputs/01_naive.csv` (585 rows)

## Headline numbers

| metric | value |
|---|---:|
| RMSE  | **$133.59** |
| MAE   | $96.40 |
| MAPE  | **0.38%** per bar |
| hit_rate | 0.00 (degenerate — see note) |
| lift_vs_naive | 0.00 (by definition) |

## What the harness does

Walk-forward, rolling-origin, retrain every 20 bars. At each eval bar t:
- `model.fit(history)` — history = train_pool + realised eval bars 0..t-1
- `yhat_return = model.predict_one(target_row)` — target_row has datetime + bar-open-known regressors
- `yhat_price = realised_close[t-1] * exp(yhat_return)`

The naive model always returns yhat_return = 0, so yhat_price = realised previous close.

## What this number means

This is **the floor every other model has to beat**. The original `prophet_test.py` reported
$5,625 RMSE because of a row-index misalignment bug (forecast.csv had 1534 in-sample fits +
100 forward rows, compared row-by-row to 585 rows of 2026 data — most of the diff was
2025 vs 2026 level, not forecast error). The honest naive RMSE on 2026 walk-forward is
**~42× smaller** than the legacy number.

## Caveats

- `hit_rate = 0.00` is mechanically correct but uninformative: naive predicts
  `yhat_return = 0`, so `sign(yhat_return) = 0`, which never matches the realised `sign(y_true_return) = ±1`.
  Naive has no directional view; the metric is meaningful only for the other three models.
- All other models will be scored using this RMSE ($133.59) as the denominator of
  `lift_vs_naive`. A positive lift means the model genuinely beat "tomorrow ≈ today".
