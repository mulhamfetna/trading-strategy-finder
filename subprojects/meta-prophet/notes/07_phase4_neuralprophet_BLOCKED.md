# Phase 4 — NeuralProphet — PERMANENTLY EXCLUDED

> **Status update (2026-06-01):** This note documents the *initial* dependency-chain failures (4 of them). After the user requested deeper investigation, a follow-up root-cause analysis in **`09_neuralprophet_root_cause_report.md`** revealed three *additional* failures, the dominant of which is **structural**: NeuralProphet 0.8 requires uniform-cadence time series and treats CME weekend closures (52h, every Friday-Sunday) as missing data. This is a published, maintainer-confirmed bug (NP Discussion #1521) for which there is no workaround that preserves the apples-to-apples comparison.
>
> **NeuralProphet is now permanently excluded from this tournament.** Read `09_neuralprophet_root_cause_report.md` for the full evidence (cited GitHub issues, Snyk inactive-maintenance flag, lookback-survivability quantification per `n_lags`).
>
> **What runs instead** (per the expansion plan in `10_expansion_plan.md`): SARIMAX (statsmodels), Nixtla StatsForecast AutoARIMA, and Darts (LSTM/NBEATS/TFT). These libraries support irregular timestamps natively and answer the same "does autoregression beat naive?" research question NeuralProphet was supposed to answer.

---

> Originally planned as the 4th tournament entry (AR-Net on log-returns + lagged regressors).
> **Dropped** after hitting four distinct, unrelated NeuralProphet 0.8 + torch 2.12 + Python 3.14 compatibility issues in succession. The driver script `scripts/04_neuralprophet.py` exists in the repo as a record of what we tried but is not part of the leaderboard.

## What broke (in order of discovery)

1. **`add_lagged_regressor(name=...)` API mismatch.** NeuralProphet 0.8.0 renamed the kwarg from `name` (singular) to `names` (plural, list). Pre-existing tutorial code crashes. Fixed in our driver (line 52).

2. **`auto_normalization_setting` mis-flags log-returns as singular.** With `normalize='auto'` (default), NeuralProphet's auto-detect calls `len(np.unique(array)) < 2` on `y` and on each lagged regressor. For 4h log-returns (tiny values ~10⁻³) this can mis-fire when the array has limited unique values per the float-level uniqueness check. Setting `normalize='standardize'` explicitly on the constructor was supposed to bypass the auto-detect, but it doesn't propagate to lagged-regressor normalization downstream.

3. **`torch.load` weights_only default change.** torch 2.6+ changed `weights_only` default from `False` → `True`, which blocks NeuralProphet's checkpoint reload after fit (it pickles its own config dataclasses). Worked around by monkey-patching `torch.load` to default `weights_only=False`.

4. **Lagged-regressor singularity at certain `n_lags` depths.** Even after fixes 1–3, with `n_lags=10` and our 14 bar-open-known regressors (including one-hot tod_/dow_ columns), one of the lagged copies becomes singular on a sub-slice (a one-hot column lagged by N looks all-zero inside any window not containing the active session). NeuralProphet rejects this at validation rather than down-weighting. To fix, we would have to drop all categorical regressors and only use the 3 continuous ones (`prior_log_return`, `prior_range`, `rolling_20bar_vol`) — but that's no longer the same model as the Phase-2 Prophet entry, breaking the apples-to-apples comparison.

## Why we stopped

The user's primary research question (per the design doc §1) is **"can Prophet beat naive on this data, and if not, what does?"**. NeuralProphet was the *third* alternative entry, intended to test whether autoregression closes a gap that vanilla Prophet structurally cannot. The remaining 3 entries (naive / Prophet / ARIMA) still answer the primary question because:

- **Naive vs Prophet** answers "does any Prophet tuning beat the trivial baseline?"
- **Prophet vs ARIMA** answers "is the *kind* of model right? Does a model with explicit AR structure (ARIMA) beat one without (Prophet)?" That's the same question NeuralProphet was supposed to answer with AR-Net.

If ARIMA materially beats Prophet, we have evidence that adding AR structure helps — and the actionable recommendation is to revisit NeuralProphet *with a pinned older dependency stack* (Python 3.11, torch 2.5, neuralprophet 0.7) in a follow-up study.

## How to revive

To run NeuralProphet later:
1. Create a separate venv at `subprojects/meta-prophet/.venv-np/` with Python 3.11.
2. `pip install 'neuralprophet==0.7.0' 'torch<2.6' 'pandas<2.2'`.
3. Drop the categorical regressors from `_REGRESSORS` (keep only `prior_log_return`, `prior_range`, `rolling_20bar_vol`).
4. Re-run `scripts/04_neuralprophet.py` using that venv.
5. The walk-forward harness, metrics, and naive baseline are all already in place — just need a working NP and the output CSV will plug into `05_compile_leaderboard.py` automatically (the MODELS list already includes the entry, just uncommented).

Estimated revival cost: ~half a day for the env setup + a couple of hours of compute. Not worth the priority for this study.
