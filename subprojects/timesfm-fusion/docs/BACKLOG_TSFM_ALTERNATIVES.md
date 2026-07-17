# Backlog — recent time-series foundation models to experiment with

**Created 2026-07-15** from a live web sweep (July 2026). Goal: test *more recent / stronger* successors
to TimesFM as **uncertainty/volatility-regime signals** for our L1 fusion — running each through the
[REPORTING_TEMPLATE.md](REPORTING_TEMPLATE.md) five-stage system. **Carry the TimesFM lesson in from the
start:** don't get seduced by a single-window win — go straight to dumb-control + multi-regime robustness,
and check the gated-DD-vs-ungated-DD tell.

2026 leaderboard picture (fev-bench / GIFT-Eval / Chronos-ZS): **Chronos-2, TimesFM-2.5, TiRex** lead;
**Moirai-2, Toto** follow. TimesFM-2.5 already tested here → **NO-GO** (regime-specific).

## Priority order (by fit for a probabilistic vol/uncertainty signal + recency + license)

| # | Model | Org | Why it's promising for us | Fit | License |
|---|-------|-----|---------------------------|-----|---------|
| A | **Chronos-2** | Amazon | 120M encoder (T5-style); **21 quantiles** (q0.01–0.99) — *richer* uncertainty than TimesFM's 10 deciles → a finer vol band; **native covariates/multivariate** (could ingest VIX/breadth as inputs); SOTA zero-shot; 300+/s | ★★★ | check HF (Bolt=Apache-2.0) |
| B | **TiRex** | NX-AI | 35M **xLSTM** (not a transformer → a genuinely *different* failure mode, good for diversity); tops GiftEval/Chronos-ZS; tiny/fast; quantile output | ★★★ | check HF (open weights) |
| C | **Moirai-2** | Salesforce | universal multivariate + **covariates**, any frequency; quantile forecasts; strong on messy real data | ★★☆ | check HF |
| D | **Toto-2** | Datadog | open-weights, trained on **high-frequency observability** telemetry (closer to intraday spikiness than pageviews); SOTA on BOOM | ★★☆ | open weights |
| E | **Lag-Llama** | open/academic | probabilistic, explicit uncertainty quantification; a lighter baseline | ★☆☆ | Apache-2.0 |
| — | Time-MoE · Sundial · IBM Granite TTM · TabPFN-TS · Moment · Chronos-Bolt | various | secondary; test only if A–D show signal | ★ | mostly open |

## The experiment for EACH model (same protocol, TimesFM-informed)
1. **PRIOR_ART** — confirm license/commercial-use; how it emits quantiles; any *financial/volatility* eval
   published (esp. the realized-vol-vs-GARCH literature, arXiv 2607.05291 and similar).
2. **REPRO/BASELINE** — install (isolated venv), run over 2024–26 NQ 1h (reuse `forecast_2426.py`, swap the
   forecaster), cache the `(q_hi−q_lo)/price` band. No new baseline claim to hit — establish ours.
3. **DUMB CONTROL** — band-gate vs ATR/realized-vol/range (reuse `dumb_control.py`). Must beat cheap proxies.
4. **ROBUSTNESS** — reuse `robustness_2426.py`: per-year, threshold sweep, block-bootstrap, random-veto,
   gated-DD tell. **This is the gate that killed TimesFM — run it before believing anything.**
5. **VERDICT** — GO/NO-GO; log in [EXPERIMENTS_LOG.md](EXPERIMENTS_LOG.md).

## Two framings to test (not just the veto-gate)
- **(i) Vol veto-gate** — the TimesFM framing (fragile; test but expect the same failure unless a model's
  band tracks *forward* risk better).
- **(ii) Covariate-aware forecasting** — Chronos-2 / Moirai-2 accept exogenous covariates, so they *bridge*
  to the data-source program ([BACKLOG_DATA_SOURCES.md](BACKLOG_DATA_SOURCES.md)): feed VIX / breadth /
  rates as covariates and test whether the model's *conditional* uncertainty is a better regime signal than
  the univariate band. This is the more novel angle and is unique to the covariate-capable models (A, C).

## Cheap efficiency note
The harness caches forecasts to `.npz`, so once a model's band is computed over 2024–26 the whole
dumb-control + robustness battery is instant. Budget ≈ one CPU forecast pass (~15 min) per model.

## Tasks created: see #102 (Chronos-2), #103 (TiRex), #104 (Moirai-2), #105 (Toto-2). Do in that order.
