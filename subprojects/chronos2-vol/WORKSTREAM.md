# Workstream: Chronos-2 as a vol/uncertainty signal (research-chronos2)

**Branch:** `research-chronos2` (off dev). **Opened 2026-07-18.** Backlog item #102 (TSFM alternatives).
**Question:** does Amazon **Chronos-2** — the current leading TimesFM successor — succeed as a vol/regime
signal for our L1 fusion where **TimesFM failed** (regime-specific NO-GO)? And does its **covariate** support
let us feed the HMM regime as an input (the regime salvage path)?

## Why Chronos-2 specifically
- **Apache-2.0** (commercial OK). `Chronos2Pipeline.from_pretrained("amazon/chronos-2")`.
- **Richer uncertainty:** up to 21 quantiles (vs TimesFM's 10 deciles) → a finer forward vol band.
- **Native covariates** (past + future) → unique ability to condition uncertainty on VIX/breadth/**our HMM regime**.
- Tops fev-bench / GIFT-Eval / Chronos Benchmark II in the July-2026 sweep.

## Plan (standard reporting system)
1. **PRIOR_ART** ✅ ([docs/PRIOR_ART.md](docs/PRIOR_ART.md)).
2. **BASELINE** — Chronos-2 forecast over 2024–26 NQ 1h → band `(q0.9−q0.1)/price` → `nq_2426_relband_chronos.csv`.
3. **DUMB CONTROL + ROBUSTNESS** — **reuse the TimesFM battery verbatim** (`dumb_control.py`,
   `robustness_2426.py` point at the Chronos band + the same fusion book): per-year, threshold sweep,
   block-bootstrap, random-veto, gated-DD tell. Direct A/B vs TimesFM.
4. **Covariate variant** — feed the HMM regime (from research-regime-hmm) as a covariate; does *conditional*
   uncertainty beat the univariate band?
5. **VERDICT** — GO/NO-GO.

## Prior expectation (be honest)
Given the [regime discovery](../../regime-hmm/docs/ROBUSTNESS.md) — our strategy is **vol-seeking** — a
vol-veto from ANY model is expected to fail the same way. Chronos-2's fair test is: (a) does its *forward*
band behave differently, and (b) does the *covariate* framing (novel) add anything. Run the full battery
regardless; a favorable single window means nothing (the TimesFM lesson).

Reuses: server `~/Mulham/tfm-repro/` band→gate→battery scripts + fusion book; NQ 1h data 2024–26.
