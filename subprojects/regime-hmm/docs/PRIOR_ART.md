# Prior-art — market-regime detection (HMM / Jump Model) for our strategy

**Date 2026-07-15.** Web sweep (July 2026) + the user's `x.md` framework. Verdict up front: **GO to test —
this direction has real out-of-sample support** (unlike the TimesFM band), but the X-thread's HMM is likely
**not** the best tool — the statistical **Jump Model** beats it in the literature.

## 1. Does regime-switching actually help out-of-sample? — YES (real evidence)
- **Nystrup et al., "Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model
  Approach"** (arXiv **2402.05272**): out-of-sample on major US/Germany/Japan equity indices **1990–2023**,
  *with transaction costs and trading delays* — regime-switching **reduces volatility & max-drawdown and
  raises Sharpe**. This is the strongest, most rigorous support and directly relevant (index-level, OOS, costs).
- **Regime-Switching Factor Investing with HMMs** (MDPI, JRFM): HMM-based regime predictions achieve higher
  absolute and risk-adjusted returns vs static allocation.
- Practitioner corroboration (QuantifiedStrategies, QuantStart/QSTrader, a 2005–2026 regime strategy at
  Sharpe ~1.22 / maxDD ~19.5%). Weaker evidence class, but consistent direction.
- **Contrast with TimesFM:** the vol-band gate had *no* published precedent; regime-switching does. This is a
  materially more promising direction — which is *also* a reason to hold it to the same robustness bar.

## 2. ⚠️ Jump Model > HMM (the key steer)
The **statistical Jump Model (JM)** consistently **outperforms the HMM** in the Nystrup study: annualized
return **9.82% → 12.55%**, Sharpe **0.51 → 0.78**, with lower drawdown. JM regimes are **more persistent and
interpretable** (HMMs flicker; the geometric-duration assumption is unrealistic for crises). Implication for
us: **implement both**, and treat the JM as the strong contender, not the HMM as the default.

## 3. Causality — the X-thread's own central rule (and ours)
Ruuj's framework is emphatic and correct: **filtered** probabilities (forward algorithm, past-data-only) for
any live/backtest decision; **smoothed** probabilities and the **Viterbi** decoded path are for *diagnostics
only*. Using smoothed regime labels in a backtest is **lookahead bias** — "a strategy that looks excellent
with smoothed labels can perform completely differently live." This *is* our causality standard; we enforce
filtered-only in the backtest and reserve smoothed/Viterbi for the shaded-region charts.

## 4. Model-design cautions (from the framework + literature)
- **Local maxima:** Baum-Welch/EM finds a local optimum → **≥10 random restarts**, keep best log-likelihood.
  (JM has an analogous fit-stability concern.)
- **#states:** not learned — chosen. **2–4 states** in practice; use **BIC + interpretability + a
  persistence/stability check** (reject flickering regimes), not BIC alone.
- **Features matter more than the algorithm:** returns + realized-vol + volume (+ cross-asset corr) >
  returns-only. This is where our own data (and later, exogenous feeds) plug in.
- **A regime is a statistical summary, not a physical fact** — depends on features/#states/validation. Keep
  the humility; validate OOS.

## 5. Frequency caveat — regime is a SLOW state
Nearly all the OOS evidence is on **daily** data; a regime is a slow macro state (persists weeks–months).
Our fusion trades **intraday (1h)**. Plan: fit the regime on **daily** returns+vol and map it onto intraday
trades (the regime as a daily backdrop); test intraday-native fitting only as a variant (less validated; more
prone to flicker). QuantConnect has an intraday-HMM example but it's not a strong evidence base.

## 6. Tooling / license
`hmmlearn` (GaussianHMM) — BSD-licensed, actively maintained, standard for HMMs (fine for commercial
research). Jump Models: reference implementations exist (e.g. `jumpmodels`-style code / the paper's method);
confirm license before vendoring, else implement the (simple) coordinate-descent JM ourselves.

## Go / No-Go
**GO to test — this is the most promising signal direction we've found**, with genuine OOS precedent and a
clear best-in-class method (Jump Model). Do NOT skip robustness just because the prior is favorable — the
TimesFM lesson is that a favorable-looking single window means nothing. **Use it for policy (size/sit-out),
not entry direction.**

## Validation plan to run on OUR data
1. Fit HMM **and** Jump Model (2–4 states) on **daily** NQ features (returns, realized-vol, volume),
   **filtered** regime probabilities, ≥10 restarts, BIC+stability for #states.
2. Label the 2024–26 fusion trades (and the longer 2010–26 book where box data allows) by their **live**
   (filtered) regime; measure P/L, DD, Return/DD **conditioned on regime**.
3. **Dumb control:** does the HMM/JM regime beat a plain **realized-vol tercile** or a trend-vol quadrant?
4. **Robustness:** per-year, CPCV, filtered-only (no smoothed leakage), regime-persistence check, and a
   **random-regime control** (shuffle regime labels — does the real regime beat random?). Break the n=1.
5. If it survives: wire regime → **policy** (reduce size / sit out in the crisis regime), re-measure.

Sources: arXiv 2402.05272 (Nystrup, Jump Model); MDPI JRFM 13(12):311 (HMM factor investing);
QuantifiedStrategies / QuantStart / QuantConnect (practitioner); `x.md` (@RuujSs HMM framework).
