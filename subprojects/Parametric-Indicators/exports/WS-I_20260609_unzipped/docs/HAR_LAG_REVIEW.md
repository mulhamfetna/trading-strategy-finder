---
name: har-lag-review
description: WS-I review (notes #1) — empirical study of the HAR-RV lookback lags (1/5/22 classic vs 1/6/30 current) on the real NQ 4h data. Conclusion: KEEP 1/6/30 — it is the empirical best fit; no code change.
type: review
status: complete — recommendation: keep 1/6/30 (no change)
created: 2026-06-08
workstream: WS-I
---

# HAR-RV lag review — 1/5/22 vs 1/6/30 (is the current choice the best fit?)

## Question
The HAR-RV volatility gate forecasts each bar's vol from past realized vol over three lookbacks:
`vf[i] = 0.5·rv[i−1] + 0.3·mean(rv[i−W:i]) + 0.2·mean(rv[i−M:i])`. Two things were asked:
1. Is it **candle-based, not day-based?** → **Yes.** RV is computed per decision bar (candle) from
   the 1-min squared log-returns inside that bar; the lookbacks W/M are in **bars (candles)**, not
   calendar days. No change needed there.
2. Is **(W,M) = (6,30)** (current) the best fit, or should it be the textbook **(5,22)**? → studied
   below.

## Method
Real NQ data via `strategy.load_inputs()`: **2,119** 4h decision bars, split 2025 (train, 1,534) /
2026 (out-of-sample, 585). RV per bar = `volatility.compute_rv_pts(bar_minutes=240)`. For each lag
set, the same fixed-weight HAR (0.5/0.3/0.2) forecast `vf[i]` was scored against the realized `rv[i]`
by Pearson correlation, RMSE, MAE. Also an **OLS-fitted** HAR (fit on 2025, scored on both splits) to
measure the explanatory power of the lag *structure* itself.

## Results

### Fixed-weight HAR (the actual gate formula): vf vs realized rv
| lags (1/W/M) | split | corr | RMSE | MAE |
|---|---|--:|--:|--:|
| 1/5/22 (classic) | 2025 | 0.6004 | 63.72 | 39.87 |
| 1/5/22 (classic) | **2026 (OOS)** | 0.3827 | 62.45 | 45.74 |
| **1/6/30 (current)** | 2025 | **0.6180** | **62.32** | **38.29** |
| **1/6/30 (current)** | **2026 (OOS)** | **0.4123** | **60.97** | **44.03** |

1/6/30 wins on **every** metric, **every** split.

### OLS-fitted HAR (explanatory power of the lag structure; target rv[i])
| lags | R² in-sample (2025) | R² OOS (2026) |
|---|--:|--:|
| 1/5/22 | 0.3676 | 0.1370 |
| **1/6/30** | **0.3892** | **0.1652** |

Again 1/6/30 has the higher R², in-sample and out-of-sample.

### Grid search (OOS-2026 correlation), W∈{4..8} × M∈{18,22,26,30,34}
```
w\m       18      22      26      30      34
4     0.3665  0.3617  0.3636  0.3674  0.3628
5     0.3871  0.3827  0.3846  0.3886  0.3840
6     0.4104  0.4063  0.4082  0.4123  0.4079   ← row max at M=30
7     0.4103  0.4062  0.4080  0.4122  0.4079
8     0.4034  0.3992  0.4010  0.4053  0.4009
```
**Grid optimum = (W,M) = (6,30), OOS corr 0.4123** — exactly the current setting. (W=7 is a virtual
tie; M=30 best across the board.) Classic (5,22) = 0.3827, clearly worse.

## Why 6/30 fits better here
On 4h bars the NQ session is ~6 bars/day, so **W=6 ≈ one trading day** and **M=30 ≈ one week** — a
natural day/week decomposition for this instrument and timeframe, whereas the textbook 5/22 is
calibrated to *daily* bars (5 = a trading week, 22 = a trading month). At 4h resolution 5/22 simply
spans a shorter, worse-matched horizon.

## Conclusion & recommendation
**Keep 1/6/30 — no change.** It is the empirical best fit (best forecast skill and explanatory power,
in-sample and OOS, and the grid optimum), and keeping it also preserves byte-parity with the approved
WS-G winner. Changing to 1/5/22 would *reduce* gate quality **and** break that parity — not justified.

(If we later want a marginal gain, a per-timeframe lag scaling — keep "≈1 day / ≈1 week" in bar units
as the TF changes — is the direction to explore, not a fixed 5/22.)
