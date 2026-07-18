# Prior-art — Chronos-2 as a vol/uncertainty signal

**Date 2026-07-18.** Web sweep (July 2026) + HF model card. Verdict: **GO to test**, with tempered
expectations (our strategy is vol-seeking, so any vol-veto likely fails — the value is the *covariate* angle
and a fair A/B vs TimesFM).

## What Chronos-2 is
- Amazon; **120M**, encoder-only (T5-style); zero-shot. **Apache-2.0** (both `amazon/chronos-2` and
  `autogluon/chronos-2` on HF) → commercial use fine.
- **Probabilistic:** up to **21 quantiles** (q0.01–0.99) — richer than TimesFM's 10 deciles; we use
  `quantile_levels=[0.1,0.5,0.9]` so the band `(q0.9−q0.1)/price` is directly comparable to the TimesFM test.
- **Covariates:** univariate / multivariate / covariate-informed in one model; past + future covariates via a
  `future_df`. This is the differentiator — lets us condition on VIX / breadth / **our HMM regime**.
- SOTA zero-shot on fev-bench, GIFT-Eval, Chronos Benchmark II (July-2026); ~300 forecasts/s on one GPU.
- API: `Chronos2Pipeline.from_pretrained("amazon/chronos-2")` → `predict_df(df, prediction_length, quantile_levels, id_column, timestamp_column, target)`.

## Evidence on foundation models for financial volatility
- The realized-vol-vs-GARCH literature (e.g. arXiv 2607.05291) tests Chronos/Moirai/TimesFM against HAR-RV /
  GARCH — foundation models are competitive-to-modest, not clearly dominant, for realized-vol forecasting.
- No published precedent for "FM forecast band as a tradeable vol *gate*" (same gap found in the TimesFM
  prior-art). So this remains an original test — the burden of proof is ours.

## Our own strongest prior (from this program)
- **TimesFM vol-band gate: NO-GO** (regime-specific; failed OOS). [../../timesfm-fusion/docs/ROBUSTNESS.md]
- **The box-fusion strategy is VOL-SEEKING** — best Ret/DD in the most turbulent regime; a high-vol veto
  backfires. [../../regime-hmm/docs/ROBUSTNESS.md]
- **Therefore the *default expectation* is that Chronos-2's vol-veto also fails.** The experiment earns its
  keep by testing (a) whether a *forward* 21-quantile band behaves differently than TimesFM's, and (b) the
  **covariate framing** (feed the HMM regime) — the genuinely novel, unique-to-Chronos-2 angle.

## Go / No-Go
**GO to test** — cheap (Apache-2.0, ~one forecast pass) and it closes the "did we try the best successor?"
question + opens the covariate angle. **Hold to the full battery**; do not deploy on a single-window win.

## Validation plan
1. Chronos-2 band over 2024–26 NQ 1h → `nq_2426_relband_chronos.csv`.
2. Reuse the TimesFM battery (dumb-control + per-year + block-bootstrap + random-veto + gated-DD) → **A/B vs
   TimesFM to the same numbers**.
3. Covariate variant: add the HMM regime as a covariate; re-measure.
4. Verdict. Expect NO-GO for the veto; the covariate result is the real question.
