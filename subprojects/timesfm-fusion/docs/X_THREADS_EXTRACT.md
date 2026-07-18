# X-thread extract → experiment: Hidden Markov Model regime detection

**Source:** `x.md` (user-provided, 2026-07-15). Two threads, one theme.

## What the threads actually say
- **@antpalkin (cvxv666)** — teaser: Markov chains as the "real" quant edge; "markets have moods —
  trend, chop, panic; every strategy only works inside one; when the mood flips no bell rings." Promotional
  (points to an app). **Idea, not method:** regime detection via Markov chains.
- **@RuujSs (Ruuj)** — a full, rigorous **Hidden Markov Model (HMM) regime-detection framework** with working
  `hmmlearn` code. Third in a trilogy: cointegration → **Kalman filter** → HMM. The substance:
  - Hidden regimes (calm / transitional / crisis) generate observed returns/vol/volume; Baum-Welch (EM)
    learns transition matrix + per-regime emission distributions.
  - **Two questions:** *decoding* (Viterbi, historical) vs *filtering* (forward algo, live).
  - **Central discipline — matches ours exactly:** *filtered* probabilities (past-only) for live decisions;
    *smoothed* (whole-sample) only for research — using smoothed in a backtest is **lookahead bias**.
  - Choosing #states: BIC **plus** interpretability/stability (2–4 typical); check regime persistence/duration.
  - Failure modes: Baum-Welch local maxima → **10 random restarts**; geometric-duration assumption; **feature
    choice matters** (returns + realized-vol + volume + cross-asset corr beats returns-only).

## Why this is worth an experiment (and how it connects)
- It's the **principled version of the regime idea** that our TimesFM vol-band was a crude proxy for — and it
  directly targets the failure that killed TimesFM (**regime-specificity**): instead of one always-on vol
  veto, *detect the regime* and adapt.
- **Zero external data** — needs only our own price/returns (2010–2026 available). Fully doable now, no API.
- Connects to the parked **exogenous-signals-fusion** (regime state → policy) and the **Kalman** workstream
  (Ruuj's trilogy is literally cointegration → Kalman → HMM). The article's filtered-vs-smoothed rule *is* our
  causality standard, so it slots into the reporting system cleanly.

## The experiment (via [REPORTING_TEMPLATE.md](REPORTING_TEMPLATE.md))
1. **PRIOR_ART** — HMM/jump-model regime filters for intraday index futures: does regime-gating improve
   *risk-adjusted* return **out-of-sample** (not just in-sample)? (Our TimesFM prior-art already found
   "regime-gated participation robustly improved Sharpe/DD" and flagged the backfire condition — extend it.)
   Confirm `hmmlearn` license/fit for commercial research.
2. **REPRO/BASELINE** — fit a Gaussian HMM (2–4 states) on NQ features (returns, realized-vol, volume) on
   2010–2026; produce **filtered** (causal) regime probabilities; label our fusion trades by live regime.
3. **DUMB CONTROL** — does the HMM regime beat a trivial regime proxy (e.g. a realized-vol tercile, or a
   simple trend/vol quadrant)? If a 2-line vol-tercile matches a full HMM, we don't need the HMM.
4. **ROBUSTNESS** — the same battery: does conditioning on regime help the *majority* of years/CPCV folds;
   filtered-only (no smoothed leakage); regime-stability check; random-regime control. **Break the n=1.**
5. **VERDICT** — GO/NO-GO; if GO, feed the live regime state into the L1/L2 policy (size / sit-out), NOT
   entry direction.

## ⚠️ Scope / branch note
This is a **substantial new method-workstream** (regime detection), tightly coupled to the Kalman study and
exogenous-signals-fusion. Per the one-workstream-one-branch convention it should get **its own branch/worktree**
— I will **not** auto-create it; say the word. Task **#110**.
