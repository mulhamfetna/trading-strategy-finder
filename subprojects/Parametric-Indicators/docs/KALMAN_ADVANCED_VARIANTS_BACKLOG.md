# WS-KALMAN — Advanced Variants & Fusion Backlog (further-push catalogue)

> ⬜ **BACKLOG / FURTHER PUSH — visit later, only if higher-priority workstreams don't pan out.**
> The closed Kalman/fusion study (`RESEARCH_KALMAN_FUSION_STUDY.md`, `KALMAN_FUSION_TRIALS_DEEPDIVE.md`) tested
> **only the vanilla linear Kalman filter**. This document mines the **full landscape** of advanced Kalman-family
> filters and advanced signal-fusion algorithms — with **finance/stock-designed filters emphasized** — and records
> each with its **current status** (all untested here) and its **fit for our specific problem**, so a future
> re-open has a ready-ranked menu. Registered in `WORKSTREAMS.md` under `WS-KALMAN` (further push).
>
> *Synthesized from the estimation-theory + quantitative-finance literature (Kalman 1960 → modern deep state-space
> models). Not yet citation-backed; a `deep-research` pass can add sources on request.*

---

## 0. How to read this — the bar every candidate must clear

Our closed study established the constraints any new method must respect. A candidate is only worth building if it
plausibly beats one of these two problems **under walk-forward** (single-split wins are not accepted — that lesson
is why M2 was rejected):

| Target sub-problem | The bar | Where it plugs in |
|---|---|---|
| **D — Direction** of the dropped signals | win-rate **> 57.5%** out-of-sample (payoff pinned at 0.74) | admit/redirect policy on dropped box signals |
| **R — Regime / risk state** from diverse inputs | improves **risk-adjusted** return via **sizing / SL-TP / sit-out** | the policy head π(state) — *not* entry direction |
| **X — Exits** conditioned on state | moves payoff **above 0.74** durably | per-trade exit scaling |

**Governing principle carried forward:** *"sophistication ≠ information."* A fancier filter on the **same**
near-random price input (problem D) cannot manufacture directional signal — so most Kalman *variants* are **low
priority for D** and only interesting for **R** (fusing genuinely diverse inputs) or **X**. This ranking reflects
that throughout.

**Status legend:** ⬜ untested (candidate) · 🔶 partially relevant (a cousin was tried) · ⭐ priority pick for a
re-open.

---

## 1. Category A — Nonlinear Kalman filters (Gaussian, deterministic)

Handle nonlinear dynamics/observation while keeping a Gaussian posterior. **For us:** only useful if we introduce a
**nonlinear** state model (e.g. a nonlinear regime→return map); on the linear trend problem they reduce to the
vanilla KF, so **low value for D**.

| Method | One-line mechanism | Finance relevance | Fit | Status |
|---|---|---|---|---|
| **Extended KF (EKF)** | Linearize f/h via Jacobians at the current estimate | Time-varying beta, nonlinear term-structure | D-low, R-med | ⬜ |
| **Iterated EKF (IEKF)** | Re-linearize the update iteratively → better fixed point | Strong-nonlinearity measurement models | R-med | ⬜ |
| **Second-order EKF** | Adds Hessian (bias-correction) terms | Rarely used in fin | Low | ⬜ |
| **Unscented KF (UKF)** | Sigma-point (unscented) propagation — no Jacobians, 3rd-order accurate | Stochastic-vol, nonlinear factor models | R-med ⭐ | ⬜ |
| **Cubature KF (CKF)** | Spherical-radial cubature points; stable in high-dim | Multi-asset/factor state | R-med | ⬜ |
| **Gauss–Hermite / Quadrature KF** | Quadrature integration of the moments | Accurate low-dim nonlinear | R-low | ⬜ |
| **Central-Difference / Divided-Difference (CDKF/DD1-DD2)** | Stirling-interpolation derivatives | Alt to UKF | R-low | ⬜ |
| **Ensemble KF (EnKF)** | Monte-Carlo ensemble approximates covariance; high-dim | Large cross-sectional state (many names) | R-med | ⬜ |

> **Pick of the category: UKF** — if a re-open uses a nonlinear regime/vol state, UKF is the standard, derivative-
> free upgrade over EKF and cheap to try.

---

## 2. Category B — Non-Gaussian / Monte-Carlo filters

Drop the Gaussian assumption — essential for **heavy-tailed, jumpy** financial returns and multi-modal regime
posteriors. **Higher relevance than Category A** because returns are demonstrably non-Gaussian.

| Method | One-line mechanism | Finance relevance | Fit | Status |
|---|---|---|---|---|
| **Particle Filter (SIR / bootstrap, SMC)** | Weighted samples approximate any posterior | **Stochastic-volatility filtering**, jump models — a finance staple | R-high ⭐ | ⬜ |
| **Auxiliary Particle Filter (APF)** | Look-ahead resampling → lower variance | SV with informative obs | R-med | ⬜ |
| **Rao-Blackwellized PF (RBPF)** | Analytic (KF) for linear substate + particles for the rest | Linear-Gaussian + regime switch | R-high ⭐ | ⬜ |
| **Gaussian-Sum Filter** | Posterior = mixture of Gaussians | Multi-modal regime belief | R-med | ⬜ |
| **Grid / point-mass filter** | Discretize the state space | Low-dim, rarely fin | Low | ⬜ |

> **Pick: Particle / Rao-Blackwellized PF** — the natural tool for a **stochastic-volatility / jump regime state**
> feeding the policy head (problem R/X). This is where non-Gaussian filtering genuinely earns its keep in markets.

---

## 3. Category C — Adaptive & robust filters

Tune noise online or resist outliers — directly targets two real market pathologies: **regime-shifting noise** and
**fat-tailed shocks**. **Medium-high relevance for R and X.**

| Method | One-line mechanism | Finance relevance | Fit | Status |
|---|---|---|---|---|
| **Adaptive KF (IAE — innovation-based)** | Estimate Q/R online from the innovation sequence | Vol-regime shifts (our M3 target, done via terciles) | R-med, X-med 🔶 | ⬜ |
| **Sage–Husa adaptive filter** | Recursive Q/R estimation | Nonstationary series | X-med | ⬜ |
| **Multiple-Model Adaptive Estimation (MMAE)** | Bank of KFs at different Q/R; Bayesian weight | Uncertain vol level | R-med | ⬜ |
| **Variational-Bayes adaptive KF** | VB jointly infers state + noise | Modern adaptive SV | R-med ⭐ | ⬜ |
| **H-∞ (minimax) filter** | Minimizes worst-case error; no noise-Gaussianity needed | Robust to model misspecification | R-med, X-med | ⬜ |
| **Robust / Huber KF** | Huber loss on innovations → outlier-resistant | **Fat-tailed returns, jumps** | R-high ⭐, X-med | ⬜ |
| **Masreliez filter** | Nonlinear score-function update for non-Gaussian obs | Heavy-tailed obs noise | X-low | ⬜ |
| **Fading-memory / covariance-inflation KF** | Down-weights old data (forgetting factor) | Faster regime adaptation | R-med, X-med 🔶 | ⬜ |

> **Pick: Robust (Huber) KF + adaptive Q/R** — cheap, directly matched to fat tails and vol regimes; the closest
> "unbuilt M2b" the original study named (*adaptive-Q/R relatives*).

---

## 4. Category D — Multi-model & regime-switching filters ⭐ (finance-central)

Explicitly model **discrete regimes** (bull/bear, calm/stormy) with switching dynamics — the single most
finance-native branch, and the most aligned with our **regime/policy-head** goal.

| Method | One-line mechanism | Finance relevance | Fit | Status |
|---|---|---|---|---|
| **Interacting Multiple Model (IMM)** | Bank of filters + Markov switch, mixed each step; near-optimal, cheap | Regime-aware tracking | R-high ⭐ | ⬜ |
| **Generalized Pseudo-Bayes (GPB1/GPB2)** | Merge/branch switching hypotheses | Precursor to IMM | R-med | ⬜ |
| **Kim filter (Kim & Nelson)** | KF + Hamilton filter + collapsing → **regime-switching state space** | **Canonical fin regime model** (Markov-switching w/ state) | R-high ⭐ | ⬜ |
| **Switching Linear Dynamical System (SLDS)** | Latent discrete + continuous state; approx inference | Regime + trend jointly | R-med | ⬜ |
| **Hamilton / Markov-switching (HMM regime)** | Discrete-only regime posterior (no continuous state) | **Bull/bear regime detection** — very common | R-high ⭐ | ⬜ |
| **Markov-switching GARCH / MS-SV** | Regime-dependent volatility dynamics | Vol-regime sizing/sit-out | R-high ⭐, X-high | ⬜ |

> **Picks: HMM / Kim filter / IMM** — these are *the* finance regime tools and map **exactly** onto our
> policy-head goal (size/sit-out by regime). If WS-SIG-FUSION's diverse inputs arrive, an **HMM or Kim-filter
> regime state** is the highest-value fusion target — strictly more principled than M3's tercile buckets.

---

## 5. Category E — Numerical, structural & smoothing forms

Not new information, but better **numerics, causality control, or a modeling frame**. Useful engineering, low
alpha.

| Method | One-line mechanism | Relevance | Fit | Status |
|---|---|---|---|---|
| **Square-root / UD-factorized KF (Potter, Bierman)** | Propagate √P for numerical stability | Long/ill-conditioned runs | infra | ⬜ |
| **Information filter / SRIF** | Track P⁻¹ (information form); easy fusion of many sensors | **Multi-source fusion math** | R-infra ⭐ | ⬜ |
| **Kalman–Bucy filter** | Continuous-time KF | Tick/HFT-scale modeling | Low | ⬜ |
| **RTS / fixed-lag smoothers** | Backward pass uses future data | **Research/labeling only — look-ahead, never live** | analysis | ⬜ |
| **Steady-state KF (α-β, α-β-γ)** | Constant-gain simplification | Cheap trackers | Low | ⬜ |
| **Dynamic Linear Models (DLM) / BSTS** | Bayesian structural time series (trend+seasonal+reg) | **Structural decomposition of price/vol** | R-med ⭐ | ⬜ |

> **Pick: DLM/BSTS + information-form fusion** — a clean Bayesian frame for a multi-component state and for fusing
> many exogenous series (Category-F/G territory).

---

## 6. Category F — Finance & trading-specific filters ⭐⭐ (the emphasis)

Filters actually **designed for or popularized in markets**. This is the category the user specifically asked to
mine.

| Method | What it does in markets | Fit for us | Status |
|---|---|---|---|
| **Kalman dynamic hedge-ratio / pairs-trading filter** | State = time-varying hedge ratio/spread; OU mean-reversion on the spread | Not entry-dir for us, but the template for a **dynamic-relationship state** (e.g. NQ↔VIX beta) | R-med ⭐ | ⬜ |
| **State-space time-varying beta (dynamic CAPM)** | KF tracks rolling β of an asset to a factor | **NQ's β to VIX/breadth/rates** = a fusion feature | R-high ⭐ | ⬜ |
| **Stochastic-volatility particle filter (SV / SVJ)** | Filters latent vol (+ jumps) from returns | **Vol state for sizing/sit-out** | R-high, X-high ⭐ | ⬜ |
| **Markov-switching regime models (Hamilton)** | Bull/bear/crisis regime probabilities | **Policy-head regime gate** | R-high ⭐ | ⬜ |
| **John Ehlers' DSP filters** (MAMA/FAMA, "Kalman-ish" adaptive MA, Super Smoother, Hilbert cycle) | Low-lag adaptive smoothing/cycle detection for trading | A **low-lag trend/cycle** alt to our vanilla velocity-z (problem D) | D-med 🔶 | ⬜ |
| **Zero-lag / adaptive Kalman moving averages** | Kalman-tuned MA used as a trading indicator | Drop-in **trend feature** vs velocity-z | D-med | ⬜ |
| **Dynamic factor models (DFM) via KF** | Compress many series into few latent factors | **Fuse VIX+breadth+rates+skew → latent risk factors** | R-high ⭐⭐ | ⬜ |
| **Affine term-structure / Nelson–Siegel dynamic KF** | Filters yield-curve factors (level/slope/curv) | Turns the **rates feed** into 3 clean state features | R-med ⭐ | ⬜ |
| **Bayesian online changepoint detection (BOCPD)** | Online regime/changepoint probability | **Sit-out trigger** at regime breaks | R-med, X-med ⭐ | ⬜ |
| **Wiener filter** | Classical optimal linear filter (stationary) | Historical precursor; little marginal value | Low | ⬜ |

> **Picks: Dynamic Factor Model + SV particle filter + Markov-switching regime** — the three highest-value
> finance-native tools for **problem R**, and the natural engines for the parked **WS-SIG-FUSION** diverse-input
> fusion. A DFM/KF is arguably *the* right way to fuse VIX/breadth/rates/skew into a small risk-state the policy
> head can act on.

---

## 7. Category G — Advanced signal fusion & learned state estimators

Beyond Kalman: how to **combine many predictors/signals** or learn the filter itself. Relevant to **problem R**
(fusion) and to blending alphas.

| Method | One-line mechanism | Fit | Status |
|---|---|---|---|
| **Bayesian Model Averaging / Mixture of Experts** | Probability-weighted blend of models | R-med ⭐ | ⬜ |
| **Covariance Intersection** | Fuse estimates with unknown cross-correlation (no double-counting) | R-med (fuse correlated feeds) | ⬜ |
| **Dempster–Shafer evidence theory** | Combine beliefs under ignorance | R-low | ⬜ |
| **Factor graphs / belief propagation** | Graphical-model inference over a state network | R-med | ⬜ |
| **Gaussian-Process state-space models (GP-SSM)** | Nonparametric dynamics with uncertainty | R-med ⭐ | ⬜ |
| **Deep Kalman Filters / Kalman-VAE / structured inference nets** | Neural state-space; learn f/h + inference jointly | R-high (if data-rich) ⭐ | ⬜ |
| **Normalizing-flow / particle-flow filters** | Flexible non-Gaussian posteriors via learned transports | R-med | ⬜ |
| **RNN/LSTM/Transformer as a learned filter** | Sequence model as an implicit state estimator | D/R-med (overfit risk ⚠️) | ⬜ |
| **Stacking / gradient-boosted meta-fusion** | ML meta-learner over signal features | R-med (walk-forward-gated) ⚠️ | ⬜ |
| **RL policy over the state** | Learn sizing/sit-out directly from the regime state | R-high (ties to policy head) ⭐ | ⬜ |

> **Caution flag:** every ML method here (deep filters, RNNs, stacking, RL) carries **high overfitting risk** on
> our ~2-year window — the exact failure mode that killed M2/M3 on a single split. Gate hard with walk-forward and
> prefer the smallest model that clears the bar.

---

## 8. Prioritized shortlist for a re-open (ranked for OUR problem)

If this workstream is revisited, attack in this order — cheapest, highest-fit, most finance-native first:

1. **⭐ Markov-switching / HMM regime state** (Cat D/F) → policy head. Directly replaces M3's crude terciles with a
   principled regime posterior. *Needs the WS-SIG-FUSION data.*
2. **⭐ Dynamic Factor Model (KF)** (Cat F) → fuse VIX/breadth/rates/skew into a small latent risk-state. *The
   canonical fusion engine for the parked signal workstream.*
3. **⭐ Stochastic-volatility particle filter** (Cat B/F) → a live vol/jump state for **sizing & sit-out** (problem
   R/X), and to move payoff off 0.74 (problem X).
4. **Robust (Huber) KF + adaptive Q/R** (Cat C) → the original "M2b"; cheap, fat-tail-matched. Re-test on price
   (problem D) *only* to formally close the "did a better filter on price help?" question.
5. **Ehlers low-lag / adaptive-Kalman trend** (Cat F) → a drop-in alternative trend feature vs velocity-z for D.
6. **UKF / Rao-Blackwellized PF** (Cat A/B) → infrastructure for 1–3 once a nonlinear/switching state is chosen.
7. **Deep state-space / RL policy** (Cat G) → only if 1–3 show promise *and* more data exists; walk-forward-gated.

**The through-line:** the highest-value re-open is **not a fancier filter on price** (problem D — near-random input,
"sophistication ≠ information"); it is a **regime/factor state fused from diverse inputs** (problem R) — which is
exactly `WS-SIG-FUSION`. This backlog is that workstream's *methods menu*.

---

## 9. Re-open protocol (unchanged discipline)

1. Pick one method from §8, targeting one sub-problem (D/R/X).
2. Build it off the production path (golden gate must stay 6/6).
3. **Walk-forward from the start** — no single-split headline numbers (the M2 lesson).
4. Gate: does it beat the champion / the bar (§0) out-of-sample across a majority of folds? Yes → proceed; No →
   record the verdict and close, same as M1/M2/M3.

*Cross-refs: `RESEARCH_KALMAN_FUSION_STUDY.md` (closed study + scope), `KALMAN_FUSION_TRIALS_DEEPDIVE.md` (the
reusable rig + walk-forward machinery), `EXOGENOUS_SIGNALS_FUSION_WISHLIST.md` (the diverse-input data these methods
would consume), `WORKSTREAMS.md` (WS-KALMAN / WS-SIG-FUSION).*
