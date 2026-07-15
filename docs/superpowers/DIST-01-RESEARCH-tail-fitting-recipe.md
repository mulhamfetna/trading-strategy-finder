# DISTRIBUTION · 01 — RESEARCH: the tail-fitting recipe (real methods vs traps)

**Task #7, phase 1: the deep-research mining pass, done before writing a line of fitting code. 111
research agents, 25 claims adversarially verified (22 confirmed, 3 refuted). This gives us a concrete,
defensible recipe for characterizing the fat tail that has defeated every edge in this project — and,
just as important, tells us exactly which numbers we must re-estimate on our own data rather than import.**

Date: 2026-07-14 · Branch `fundamental-analysis` · Method: `deep-research` workflow.

---

## ⚡ THE 60-SECOND VERSION — the recipe

| Step | What | Why |
|---|---|---|
| **0. Kill the Gaussian** | Assume nothing is normal | Empirically the tail is power-law; a normal would need ~30 degrees of freedom, real data shows **2–3** |
| **1. Don't fit body and tail with one law** | Fit the **body** with a heavy-tailed distribution; fit the **tail** separately with EVT | One distribution that fits the middle will misestimate the rare large loss — the only part that matters for stops/sizing |
| **2. Filter volatility first** | **McNeil–Frey two-step**: fit a GARCH, take the standardized residuals, fit the tail to *those* | Raw returns are volatility-clustered (not independent), which breaks EVT. This is also **how you condition the tail on session/volatility state** — exactly what S3 showed we need |
| **3. Fit the tail with EVT** | Peaks-over-threshold + **Generalized Pareto**, or block-maxima + GEV | Models the rare large loss *directly*, not as a by-product |
| **4. Fit the two tails ASYMMETRICALLY** | Loss (left) tail is **heavier** than gain (right) tail — fit them separately | Our per-trade P&L is exactly this: heavy losses, gains capped by the take-profit |
| **5. Report ranges, never one number** | Tail index / threshold estimates are unstable in finite samples | A single Hill or GPD point estimate is unreliable; give a band + diagnostics |

> **🍼 The one-sentence version** — *filter out the volatility clustering, then fit the rare-large-loss tail
> on its own with Extreme Value Theory, separately for losses and gains, and never trust a single tail
> number.* That is the whole recipe. Everything below is detail and evidence.

---

## ✅ WHAT IS REAL — the verified methods

### D-R1 — The tail is severely fat, and it's a power law (not Gaussian)

Empirical tail heaviness for equity-type returns: **Student-t degrees of freedom ≈ 2–3** (2.1 on raw
returns, rising to ~3.25 after GARCH filtering), Hill/WLS **tail index ≈ 2–6** (US index ~4.2 on the gain
side, ~5.3 on the loss side). A tail index above 2 means the mean and variance exist but **higher moments
may not** — the returns are genuinely power-law fat-tailed. A Gaussian would need df > ~30.
*Sources: Eom/Kaizoji/Scalas (Physica A); LeBaron (Brandeis, EVT & Fat Tails).*

### D-R2 — Volatility clustering explains PART of the tail, not all of it

After you filter with a GARCH, the standardized residuals are **still fat-tailed** — every fitted df stays
below the normal expectation. So you cannot just say "it's all volatility clustering"; you need a
fat-tailed residual distribution *inside* the GARCH too. *Source: Eom/Kaizoji/Scalas.*

### D-R3 — EVT (peaks-over-threshold + Generalized Pareto) is the right tail tool

Model **exceedances over a threshold** with a Generalized Pareto Distribution (or block-maxima with GEV),
because it fits the rare large loss directly. Threshold selection uses the **mean-residual-life plot**:
above a valid threshold the mean excess is linear in the threshold — pick the threshold where it becomes
linear. This is a genuine **bias–variance tradeoff**: too low biases the fit (violates the GPD
asymptotics), too high leaves too few exceedances (inflates variance, destabilizes VaR/Expected Shortfall).
*Sources: Davison & Smith / Coles canonical EVT; McNeil/Frey/Embrechts.*

### D-R4 — McNeil–Frey conditional EVT is how you handle session/volatility dependence

The defensible pipeline for non-i.i.d. data: **fit GARCH(1,1) → extract standardized residuals → fit the
EVT/GPD tail to the residuals.** This is the ~2,000-citation foundation of conditional EVT and it is
**exactly the mechanism for conditioning the tail on the current volatility/session state** — which S3
showed matters (our loss tail is far heavier in the NY session than overnight). Fit per-session, or
condition on the GARCH volatility, then apply GPD to residuals so the same-size shock is scaled by current
volatility. *Source: McNeil & Frey (2000); arXiv 2407.05933.*

### D-R5 — Fit the two tails ASYMMETRICALLY; the loss tail is heavier

No single distribution fits both tails; the **loss (left) tail is empirically heavier and riskier** than
the gain (right) tail, so they must be fitted separately with the downside as the heavier one. For a
skewed, asymmetric-tail target, the **GH skew-Student-t** is uniquely suited — it is the *only* Generalized
Hyperbolic subclass with **one polynomial (heavy) tail and one exponential (light) tail.** That is a
remarkably exact fit for our per-trade P&L: heavy losses, gains capped light by the take-profit.
*Sources: EFMA 2017 (with a sign-convention caveat); Aas & Haff 2006 (JFEC).*

### D-R6 — A mixture of Student-t components maps onto regimes / trade modes

A **3-component Student-t mixture** (degrees of freedom fixed a priori) beats single distributions by
KS/AD/AIC/BIC: the low-df component governs the *extremes*, the moderate-df the *moderate* moves, the
high-df the *small* ones. For a strategy's per-trade P&L this directly supports **modeling it as an
explicit mixture** — a winner mode (from the take-profit), a loser mode (from the stop), and a heavy
small-df component for the slippage/gap/sweep losses beyond the stop. *Source: Massing & Ramos (Physica A).*

### D-R7 — For commodity futures, GH/NIG beat the normal (but don't privilege NIG)

On daily commodity futures (gas, gold, platinum, copper, sugar, cattle), the Normal-Inverse-Gaussian and
Generalized Hyperbolic fit materially better than the normal. **Note:** the claim that *NIG specifically*
beats full-GH was **refuted** — treat both as viable and select empirically. *Source: Pal 2023 (Applied
Economics).*

---

## ⚠️ THE PITFALLS — verified, and they will bite

| Pitfall | The evidence | What to do |
|---|---|---|
| **Threshold sensitivity of the GPD shape** | The shape parameter ξ can swing from −0.44 to +1.92 across labeling quantiles; deep 99% Expected Shortfall ranged from ~$54k to **infinity** (ES is infinite when ξ≥1) | **Never trust a single ξ.** Lean on **quantile/ES** estimates (comparatively robust in a moderate threshold band) over the raw shape, and always show a threshold-sensitivity band |
| **Single tail-index estimate is unreliable** | Across 17,918 stocks, method-to-method tail-index differences were **0.39–1.44** — enough to flip whether the 4th moment exists. MSE-minimizing k rules pick too-high k (biased) | Report the tail index as a **range with a Hill plot**; for the **deep loss quantile** that drives stops, use a **small-k / high-threshold** estimate — *not* a body-fitted threshold |
| **You need enough tail** | Estimates stabilize around **~200–250 tail observations**; DuMouchel's rule uses the top ~10% | Ensure the exceedance count supports the quantile you're estimating; the deep tail rests on a few hundred points at most |
| **Non-stationarity** | Fitted tails **change over time**; single point estimates are unstable out-of-sample | Roll the fit; treat a drifted tail as a signal to re-set stops/sizing |

---

## ❌ REFUTED / AVOID

| Claim | Vote |
|---|---|
| NIG *specifically* beats full-GH for commodity futures | 0-3 |
| Tail shape is governed by an L-kurtosis regime split (GLO vs GEV years) | 0-3 |
| GPD shape instability *doesn't* translate into unstable tail risk | 1-2 (it **can** — deep ES → ∞ when ξ≥1) |

---

## 🚨 THE TWO THINGS THE RESEARCH COULD NOT GIVE US

1. **None of the primary sources are on 1-minute CME futures.** The df≈2–3 is Korean *daily* equities; the
   tail-index ≈2–6 is *daily* equity indices; the GH/NIG result is *daily* commodities; the mixture is
   daily+hourly. **Intraday tails are HEAVIER than daily** (aggregation thins tails via a CLT effect), so
   we should expect **lower df / smaller α at 1-minute** and we **must re-estimate on our own data.** The
   literature gives us the *method and the expected magnitude*, not the number.
2. **The decision layer is thinly covered.** Stop placement from tail quantiles is straightforward, but
   **fractional-vs-full Kelly under heavy tails, and risk-of-ruin, were not covered by surviving claims.**
   The only verified decision-relevant result is that VaR/ES within a moderate threshold band is
   comparatively robust. **The sizing rules will need their own targeted research** (open question: how
   much to haircut Kelly as α drops from 4 toward 2).

---

## 🎯 THE ON-DATA TEST LIST (phase 2)

The research hands us a prioritised, defensible plan. Each fits on our own data with the usual discipline
(out-of-sample, ranges-not-points, diagnostics):

| # | Test | What it answers | Data |
|---|---|---|---|
| **D1** *(recommended first)* | **Fit the champion's PER-TRADE P&L distribution as a mixture** (winner mode / loser mode / heavy tail component), directly on the trade ledger | *This is the tail that defeated every edge.* Characterizing it tells us the true probability of the large loss and whether "±$1,600 swing" is 2-modal or genuinely heavy-tailed | champion ledgers (all TFs) |
| **D2** | **Estimate the tail index of NQ 1-min returns** — Hill plot + GPD peaks-over-threshold, **per session** (NY vs overnight) | The actual α on *our* data (literature says <3 intraday, heavier in NY — must measure); the number that should set stop distance | 17y NQ 1-min |
| **D3** | **McNeil–Frey conditional tail** — GARCH filter → GPD on residuals | Whether conditioning on volatility state removes the session-dependence S3 found, or a fat residual tail remains | 17y NQ 1-min |
| **D4** | **Turn the fit into decisions** — stop distance from tail quantiles, VaR/Expected Shortfall, and a sizing rule | The payoff — but the **sizing/Kelly half needs its own research pass first** (flagged above) | fitted models |

**Recommendation: start with D1.** It is the most directly useful and needs no new data — just the
champion trade ledgers we already generate. It attacks the project's central obstacle head-on: *what is
the true shape of our per-trade P&L, and how heavy is the loss tail really?* The research says model it as
a mixture (D-R6) with an asymmetric heavy loss tail (D-R5); D1 tests that on our actual trades and gives
us, for the first time, a defensible probability for the large loss instead of a Gaussian guess we know is
wrong.

---

## Appendix — source quality ledger

| Source | Tier | Used for |
|---|---|---|
| Aas & Haff 2006 (J. Financial Econometrics) — GH skew-t | **primary, top** | D-R5 |
| Massing & Ramos (Physica A) — 3-component t-mixture | **primary** | D-R6 |
| Eom/Kaizoji/Scalas (Physica A) — df 2.1→3.25 | **primary** | D-R1, D-R2 |
| LeBaron (Brandeis) — EVT tail indices | **primary** | D-R1 |
| McNeil & Frey 2000 + arXiv 2407.05933 — conditional EVT | **primary, foundational** | D-R4 |
| Bank of Canada SWP 2019-28 — tail-index k selection | **primary** | pitfalls |
| PMC9818059 (Risk Management 2022) — threshold robustness | **primary** | pitfalls (split vote) |
| Pal 2023 (Applied Economics) — GH/NIG commodities | **primary** | D-R7 |
| EFMA 2017 #0582 — GEV, asymmetric tails | conference (sign-convention caveat) | D-R5 |

**Frequency caveat (repeat, because it matters):** the numbers are daily/hourly; **we re-estimate at
1-minute and expect heavier tails.** The method transfers; the parameters do not.
