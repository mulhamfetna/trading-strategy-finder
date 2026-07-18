# Workstream: market-regime detection (research-regime-hmm)

**Branch:** `research-regime-hmm` (off `dev`). **Opened 2026-07-15.**
**Origin:** user-provided X threads (`x.md` on the timesfm branch) — @antpalkin (Markov-chain regime teaser)
and @RuujSs (a rigorous Hidden Markov Model framework). **Goal:** detect the market's *regime*
(calm / transitional / crisis, or trend / chop / panic) and use it to adapt our L1/L2 policy — **position
size / sit-out, NOT entry direction** — the way our exogenous-signals-fusion design intends.

**Why now:** our TimesFM investigation failed *because* of regime-specificity — one always-on vol veto
doesn't generalize. Regime *detection* is the principled response: instead of vetoing high-vol trades
blindly, identify the regime and change risk posture. And unlike the TimesFM band, regime-switching has
**real out-of-sample evidence** (see PRIOR_ART).

## Run through the standard reporting system
(Template lives on the timesfm branch: `subprojects/timesfm-fusion/docs/REPORTING_TEMPLATE.md`.)
1. **PRIOR_ART** ✅ ([docs/PRIOR_ART.md](docs/PRIOR_ART.md)) — regime-switching *works* OOS; **Jump Models
   beat HMMs**; use *filtered* (causal) not smoothed probabilities; regime is a *slow* state.
2. **REPRO/BASELINE** — fit on our NQ data (2010–2026), filtered regime probs, label fusion trades.
3. **DUMB CONTROL** — vol-tercile / trend-vol quadrant. **Plus the strong alternative: Jump Model vs HMM.**
4. **ROBUSTNESS** — per-year / CPCV / filtered-only / regime-stability / random-regime control. Break n=1.
5. **VERDICT** — GO/NO-GO; if GO, feed the live regime into the L1/L2 **policy head** (size/sit-out).

## Design decisions seeded by the prior-art
- **Test HMM *and* the statistical Jump Model** (JM); literature says JM wins (more persistent/interpretable,
  higher Sharpe, lower DD). Don't just implement the X-thread's HMM.
- **Regime = a slow, likely DAILY state.** Fit on daily returns+realized-vol (+volume/cross-asset) and map
  the regime onto intraday (1h) trades. Intraday-native regime fitting is less validated — treat as a variant.
- **Policy, not direction.** Regime → size / sit-out (matches exogenous-signals-fusion; the parked project).
- **Causality is non-negotiable:** filtered forward-algorithm probabilities only; smoothed/Viterbi for
  diagnostics only (smoothed in a backtest = lookahead — the X-thread's own central warning).

## Links / coupling
Trilogy from the source (cointegration → Kalman → HMM) ties this to the Kalman study. Survivors feed the
parked **exogenous-signals-fusion** workstream. Constraint: server compute only; no local box.
