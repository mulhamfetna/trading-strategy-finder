---
name: phase-C2-volatility-results
description: Workstream C2 result — deep learning (NBEATS/LSTM/Transformer) on the 1-min volatility (range) target. Unlike direction (C1), all three BEAT the naive baseline and edge EWMA on RMSE (LSTM best, +8% vs EWMA), confirming volatility is the learnable signal. Honest caveat on QLIKE (variance-risk loss) cheap EWMA still wins.
type: explainer
---

# Workstream C2 — deep learning on 1-min VOLATILITY (the mirror image of C1)

> C1 proved 1-min *direction* is noise (nothing beat naive). C2 points the same GPU models at
> the 1-min *range* (volatility, ACF ≈ 0.75) and asks the honest question: do they beat not
> just naive persistence but a cheap **EWMA**? Answer: **yes on RMSE (first time anything beats
> baselines in this whole study), but EWMA still wins on the risk-calibration metric (QLIKE).**

---

## 1. Results (GPU, 467k train / 20k test, target = log range, 1-step walk)

| Model | RMSE | lift vs naive | lift vs EWMA | QLIKE (↓ better) | train |
|---|---:|---:|---:|---:|---:|
| naive (persistence) | 0.000270 | — | — | — | — |
| EWMA(span 60) | 0.000245 | +9.3% | — | **0.594** | — |
| **LSTM** | **0.000226** | **+16.5%** | **+8.0%** | 0.654 | 222 s |
| NBEATS | 0.000231 | +14.7% | +6.0% | 0.709 | 36 s |
| Transformer | 0.000233 | +13.9% | +5.1% | 0.767 | 575 s |

Outputs: `server_runs/c2/c2_{lstm,nbeats,transformer}/result.json` + `preds.csv`.

## 2. The headline: volatility IS learnable (C1 vs C2, side by side)

| | C1 — direction (return) | C2 — volatility (range) |
|---|---|---|
| Target ACF(1) | −0.006 (noise) | +0.75 (persistent) |
| Best model vs naive | tie (−0.005%) | **+16.5%** |
| Best model vs EWMA | n/a | **+8.0% (RMSE)** |
| Conclusion | unpredictable | **predictable** |

This is the first time in the entire meta-prophet study that learned models **beat the
baselines**. It confirms the central thesis: **don't predict price, predict volatility.** The
same 487k bars that taught the models nothing about direction let them genuinely improve a
volatility forecast.

## 3. The honest caveat: it depends which ruler you use

- On **RMSE** (point accuracy of the range level) the DL models win, LSTM best (+8% over EWMA).
- On **QLIKE** (the standard volatility loss, which heavily penalises *under*-predicting
  variance — what a risk manager cares about) the **cheap EWMA actually wins** (0.594 vs
  0.65–0.77). The DL models are better at the average level but less well-calibrated in the
  tails/variance sense.
- **Takeaway:** the simple EWMA is already ~90% of the way there; deep learning adds a *modest,
  real, but metric-dependent* edge. This is the opposite of "DL magic" — it's "DL is a few
  percent better on one metric, worse on another, at 10–600× the cost." Use the cheap model as
  the workhorse; reserve DL for where its RMSE edge matters.

## 4. Model notes
- **LSTM is the best** volatility model here (best RMSE, best QLIKE among the DL three) — and
  cheap (222 s). NBEATS is fastest (36 s) and close. The **Transformer is the weakest DL** here
  (worst RMSE and QLIKE of the three) and 16× slower than NBEATS — consistent with transformers
  being overkill/over-parameterised for this signal.
- No scaling drama this time: log-range is well-conditioned (the notes/38 lesson applied), so
  even NBEATS behaved (no −500% blow-up like C1).

## 5. Where this points next
1. **Workstream A (GARCH/HAR family) is now the benchmark to beat.** EWMA already rivals DL on
   QLIKE; HAR-RV / realized-GARCH / HEAVY (the proper volatility models) likely beat *both* and
   are cheap CPU. The real volatility tournament is DL **vs** HAR-family — run A and compare on
   the same 1-min range with RMSE **and** QLIKE.
2. **Use the volatility forecast where it pays:** position-sizing / SL-TP gating in the cloned
   backtest engine (Workstream G), and as a confirmation signal for the flip detector
   (Workstream D) — that's where a +8% RMSE vol edge turns into risk reduction.

## 6. Status
- **C1 (direction) + C2 (volatility): DONE.** Together they nail the thesis: price-direction
  unpredictable at 1-min; volatility predictable and learnable, with DL giving a modest edge
  over EWMA on RMSE (EWMA still best on QLIKE). **Workstream C complete.**
- Next per the plan: **Workstream A** (advanced GARCH/HAR family) as the volatility benchmark,
  then the combination tournament (G).

## 7. One-paragraph summary (baby)
We pointed the same big models that *failed* on price at the thing that actually has a pattern:
volatility (how big each minute's move is). This time they worked — all three beat the dumb
"same as last minute" guess by ~15%, and even beat a simple smoothing baseline (EWMA) by ~5–8%
on average error, with the LSTM best. The honest fine print: judged by the volatility-specific
risk metric (QLIKE), the cheap EWMA is still a touch better, so deep learning's win is real but
modest and metric-dependent — the simple model is already most of the way there. Bottom line:
volatility is genuinely forecastable (unlike price), the cheap models are surprisingly strong,
and the next step is to pit deep learning against the proper volatility models (GARCH/HAR family)
and then use the best forecast for risk-sizing in the backtest.
