# MAPE and relative error — what they mean for NQ 4h

> Companion to `01_data_jump_investigation.md`. Explains why the current eval's RMSE = $5,625 is misleading, why we need a relative metric (MAPE) alongside RMSE, and what MAPE specifically tells us about a non-stationary price series that grew ~20% across the eval window.

---

## 1. The three error families

Given a forecast `y_hat[t]` and the realised value `y[t]`, with `n` bars:

| Family | Formula | Units | What it measures |
|---|---|---|---|
| **RMSE** | `√( mean( (y − y_hat)² ) )` | same as `y` (dollars on price) | Average miss size in *absolute* terms; penalises large misses quadratically (sensitive to outliers like the +8.21% bar). |
| **MAE**  | `mean( |y − y_hat| )` | same as `y` | Average miss size in *absolute* terms; equal weight on all misses (robust to outliers). |
| **MAPE** | `mean( |y − y_hat| / |y| ) × 100%` | percent | Average miss size as a *fraction of the realised value*; scale-invariant. |

RMSE and MAE both answer **"how many dollars are we off, on average?"** MAPE answers **"how many percent are we off, on average?"** On a series whose level changes a lot, these are very different questions.

---

## 2. Why this distinction is critical *for this specific dataset*

Our eval window (2026 — 585 bars) opens at **$25,604** and closes at **$28,950**. Across the window the price level changes by **+13.1%**. That means a "$500 miss" is a different fractional error at the start of the window than at the end:

```
$500 miss when price is $25,604  →   1.95% error
$500 miss when price is $28,950  →   1.73% error
```

RMSE / MAE treat both as identical errors. MAPE treats them as different. **MAPE is the right metric when you want to know if the model is consistently good as a fraction of price**; RMSE/MAE are right when you want to know the dollar cost of being wrong.

Worse, **if we compared models across the 2025 + 2026 span**, RMSE would systematically over-weight errors in late 2026 (where price is ~$28k) vs. the April 2025 lows (~$16.8k) — a model that is 1% off at both will look ~70% "worse" at the high end purely because of the price level. MAPE corrects that.

---

## 3. Where the current `$5,625` RMSE actually came from

The original `prophet_test.py` computed:

```python
evaluation_df["Error"] = real_data_df["close"] - forecasted_results_df["yhat"]
```

This is row-by-row, **by position in the file**, not by date. Look at the file lengths:

- `forecast.csv` has **1,634 rows** = 1,534 in-sample fits over the 2025 training period + 100 forward predictions
- `NQ_4h_2026.csv` has **585 rows**

So pandas aligned by **integer index**: row 0 of 2026 (Jan 1, 2026, close = $25,604) was being compared to row 0 of forecast.csv (Jan 1, **2025**, in-sample fit ≈ $21,322). That's why the very first row of `evaluation_results.csv` has Error = +$4,294 — it's the *level difference between 2025 and 2026*, not a forecast error.

**The headline "RMSE = $5,625" is essentially measuring "how much higher is NQ in 2026 than in 2025 on average"**, not "how accurate is the Prophet forecast." Once we align by date and use only the genuine 100-step forecast, the honest RMSE will be substantially smaller (still bad — vanilla Prophet on raw price is structurally poor — but smaller).

---

## 4. What MAPE / RMSE / MAE will look like in the new tournament

In the corrected harness, each metric will be reported per model. Here are realistic ranges to expect on this data, based on the research-report findings (Prophet on raw price gets MAPE in the high single digits; on log-returns + walk-forward, well-behaved models get MAPE around 0.3–0.6% per 4h bar):

| Model | Expected MAPE | Expected RMSE | Expected lift vs naive |
|---|---:|---:|---:|
| Naive (yhat = previous close)            | ~0.4% per bar  | ~$140  | — (this *is* the baseline) |
| Prophet vanilla on raw close (current)   | ~5–10% per bar | ~$1,000–$3,000 if aligned by date | **worse** than naive |
| Prophet on log-returns + walk-forward + regressors | ~0.4–0.5% per bar | ~$130–$170 | break-even to mildly better |
| ARIMA(1,0,1) on log-returns              | ~0.4% per bar | ~$140 | break-even |
| NeuralProphet with AR-Net                | ~0.35–0.45% per bar | ~$120–$160 | possibly +5–15% lift |

**Key insight:** the naive predictor "tomorrow ≈ today" gets ~0.4% MAPE on this data because **the 4h bar autocorrelation is high and the per-bar volatility (0.58% std in 2025, 0.53% std in 2026) is small relative to the level**. Any model that can't beat ~0.4% MAPE is contributing zero. This is exactly the "beat-the-naive" benchmark the research report flagged as decisive.

---

## 5. The "vs-naive lift" metric — the only honest scoreboard

Lift over naive is computed:

```
lift = (RMSE_naive − RMSE_model) / RMSE_naive
```

- Positive → model beats naive (good).
- Zero → model exactly equals naive (no edge).
- Negative → model is worse than predicting "same as previous close" (bad — model is contributing noise).

This is the headline number in the final leaderboard. RMSE and MAPE are absolute scales; lift is the *relative* scale that answers "is this model adding value?" The Manokhin / Hyndman / Prophet-maintainer critique of Prophet-for-stocks all reduces to this: most Prophet-on-stocks studies don't compute this lift, and the few that do find it ≤ 0.

---

## 6. A note on MAPE's known weaknesses

MAPE has two well-known issues, both of which I'll handle in the harness:

1. **Asymmetric**: a 10% over-forecast is penalised differently than a 10% under-forecast (because `|y − y_hat| / |y|` has `|y|` in the denominator, not `|y_hat|`). For NQ at $25k this is a third-decimal effect — fine to ignore.
2. **Blows up when `y → 0`**: not a concern for index futures (price never near zero), but if we later forecast log-returns directly, MAPE on the *return series* will be wildly noisy because returns hover near zero. **For that case we'll report RMSE/MAE on returns and MAPE on the reconstructed price.** This is the standard pattern in financial forecasting.

---

## 7. Recommendation for the tournament

Report **four metrics per model** on the reconstructed price (so all four models are scored on the same target, even if they internally forecast different things):

1. **RMSE** ($) — primary dollar-scale metric (matches existing eval intent).
2. **MAE** ($) — outlier-robust dollar metric (less skewed by the +8.21% bar and similar shocks).
3. **MAPE** (%) — relative metric, fair across years with level shifts.
4. **Lift over naive** (% relative RMSE improvement) — the headline.

Plus one diagnostic: **directional hit-rate** (sign of forecast return vs sign of realised return). Not the optimisation target, but a useful "does this model know anything?" sanity check — a competent model should be >50%.

Together these four numbers give a complete picture: how big are the misses in dollars, in percent, and is the model contributing any skill at all over the trivial baseline. They are all already in the design (Section 1, "Metrics" subsection).