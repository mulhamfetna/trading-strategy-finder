# Meta-Prophet — Interim Report (Phases 1-3 complete; Expansion in progress)

> **Status (2026-06-01):** This report covers the 3-model leaderboard (naive / Prophet / ARIMA). A 4-phase expansion is in progress (`10_expansion_plan.md`) that will add 9 more entries via SARIMAX, Nixtla StatsForecast, and Darts (LSTM/NBEATS/TFT — each plain and with regressors). Final leaderboard will have 12 entries. This file will be rewritten when the expansion completes.
>
> Companion docs: `00_research_report.md`, `01_data_jump_investigation.md`,
> `02_mape_and_relative_error_explained.md`, `03_design.md`, `04_phase1_baseline.md`,
> `05_phase2_prophet_tuned.md`, `06_phase3_arima.md`, `07_phase4_neuralprophet_BLOCKED.md`,
> `09_neuralprophet_root_cause_report.md`, `10_expansion_plan.md`.
>
> Outputs: `outputs/leaderboard.csv`, `outputs/{01_naive,02_prophet,03_arima}.csv`.
> Plots: `plots/{leaderboard,error_distribution,<model>_trajectory}.png`.

---

## Leaderboard (sorted by RMSE, 2026 walk-forward, retrain every 20 bars)

| Rank | Model | RMSE ($) | MAE ($) | MAPE (%) | Hit-rate (%) | Lift vs naive (%) |
|---:|---|---:|---:|---:|---:|---:|
| 1 | **naive** (previous-close) | **133.59** | 96.40 | 0.377 | — | 0.00 |
| 2 | prophet (tuned, 14 regressors) | 133.89 | 97.22 | 0.380 | 51.62 | **−0.22** |
| 3 | arima (auto, d=0) | 133.95 | 96.70 | 0.378 | 53.50 | **−0.26** |

> NeuralProphet was dropped — four distinct dependency-stack incompatibilities — see `07_phase4_neuralprophet_BLOCKED.md`.

---

## Verdict

**The naive previous-close baseline wins.** Neither a fully-tuned Prophet (log-return target, 14 bar-open-known regressors, CV-tuned `changepoint_prior_scale`, walk-forward retraining every 3 days, custom intraday/weekly Fourier seasonalities) nor auto-ARIMA(p,0,q) on log-returns can beat naive on RMSE. Both lose by a margin of −0.22% / −0.26% — within noise, but the *sign* is consistently negative.

**This was not a Prophet tuning problem.** It is a **structural property of the data**: 4h NQ log-returns are close to white noise, and no point-forecast model can extract enough mean-edge to register in RMSE. The original `prophet_test.py`'s reported $5,625 RMSE was a measurement artifact (row-index misalignment + no walk-forward); the honest naive baseline is **$133.59**, and the gap above that is ~$200 per bar of pure noise that no model in this study moves.

The 53.50% directional hit-rate from ARIMA shows there *is* a tiny extractable signal in *which way* the next bar moves — but its magnitude is too small relative to bar volatility to translate into RMSE improvement.

---

## What the data showed (numbers, not narrative)

- **Phase 1 (naive):** RMSE $133.59. This is the floor. Original legacy eval reported $5,625 = 42× inflated by a row-alignment bug.
- **Phase 2 (Prophet):** RMSE $133.89, **lift = −0.22%**. CV picked `cps=0.001` (the tightest setting) — Prophet's own CV told us "the smoother the trend, the better the score", which is Prophet saying "I don't have anything to fit here".
- **Phase 3 (ARIMA):** RMSE $133.95, **lift = −0.26%**, hit-rate 53.50%. Auto-ARIMA on log-returns finds (effectively) a near-zero point forecast — same outcome as naive in RMSE, with a tiny directional bias that doesn't pay off in magnitude.
- **Phase 4 (NeuralProphet):** Blocked — would have tested whether AR-Net's autoregression closes the gap that vanilla Prophet structurally cannot.

---

## Why the +8.21% Apr-9-2025 bar matters

It doesn't, for this study. Walk-forward on **2026 only** never tests against the April-2025 tariff-pause shock. That bar lives in the training pool. **What it does** is set the variance Prophet's CV scorer uses to choose `changepoint_prior_scale` — and Prophet correctly identifies that one giant outlier should not drive a trend flex (hence `cps=0.001`).

The bar matters mostly as **a cautionary example** of why this asset class is structurally hard: any model trained on 2025 has seen a 14σ Gaussian event that no Gaussian-residual model can faithfully predict, so its 2026 confidence intervals are blown out even if its point estimates are reasonable. We did not report confidence-interval coverage in this study; that would be a follow-up.

---

## What to do if no model beat naive

(Per design §9, this is one of the locked deliverables — answering "what next?".)

Three orthogonal directions, ranked by likely value:

1. **Switch the target.** Log-returns are too noisy at 4h cadence for point forecasting. Try:
   - **Realised volatility** (`std` of next-N-bar returns) — predictable, autocorrelated, useful for sizing.
   - **Direction-only** (binary `sign(return)`) — classification metrics (AUC, hit-rate), not RMSE. This is what the existing `simple_strategy` Stage-1 already does, so it's also the closest tie-in to the live system.
   - **Range or `close - open`** — has more structure than point returns.

2. **Add external information.** Every regressor in this study was bar-open-known from price/time alone. Adding **VIX prior close**, **options skew**, **news sentiment**, or **macro/Fed-rate-decision indicators** would test whether off-asset features close the gap. (Easier to source: VIX. Hardest: real-time sentiment.) This is also where the `trends_agenitic_analysis` strategy-based indicator could feed back in.

3. **Revive NeuralProphet** (see `07_phase4_neuralprophet_BLOCKED.md` for revival recipe). A separate Python 3.11 + torch 2.5 venv would unblock AR-Net. The remaining question is whether AR-Net at `n_lags=10-20` finds an autocorrelation that ARIMA(p,0,q) missed. ARIMA's 53.5% hit-rate suggests there *is* a small AR signal — NeuralProphet's deeper AR is the natural next test.

**What NOT to do:** more Prophet tuning. The 40-config CV grid already found that the tightest possible setting wins on CV, meaning Prophet's hypothesis space is *too smooth* for this data. Adding more configs would not help. Adding holidays, manual changepoints, MCMC, logistic growth — all on the research report's "dead-end" list.

---

## Honest caveats specific to this study

1. **n = 1 regime change observed** (2025 V-shape → 2026 continuation rally). Conclusions about lift signs hold for this regime; can't generalise to "Prophet always loses to naive on NQ".
2. **Hit-rates near 50% are noisy.** ARIMA's 53.50% on 585 bars is suggestive but not statistically significant. Would need ~5,000+ bars to claim ARIMA has a real directional edge.
3. **Eval window is only 5 months of 2026.** A full-year out-of-sample would strengthen every conclusion here.
4. **Retrain cadence held fixed at 20 bars (~3 days).** The plan included sensitivity to 1 and 100 bars but wasn't run as part of this study (out of scope after dependency-stack issues consumed the time budget). Worth a follow-up if Prophet is to be deployed live — daily retrain may help, but evidence here is that the structural problem dominates the cadence question.

---

## Reproducibility

All scripts are deterministic given the input CSVs (auto_arima may have minor variation if the underlying solver does — pmdarima's stepwise search is mostly deterministic). To re-run from scratch:

```bash
cd subprojects/meta-prophet
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/01_baseline_naive.py        # ~30 s
.venv/bin/python scripts/03_arima.py                 # ~5-10 min
.venv/bin/python scripts/02_prophet_tuned.py         # ~10-20 min (tier-1 search dominates)
.venv/bin/python scripts/05_compile_leaderboard.py   # ~10 s
```

Total: ~30 min wall-clock on a modern laptop.

Tests (~1 s):

```bash
.venv/bin/pytest tests/ -v
```

19 tests, all green, including the no-lookahead invariant.
