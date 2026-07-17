# DISTRIBUTION · 04 — D3: the CONDITIONAL tail (how many points a stop must clear, given the regime)

**#7, third on-data test — and the actionable payoff. D2 gave the tail *shape* (α≈3, scale-free); D3 gives
the *magnitude* in points, conditioned on the current volatility state, via the McNeil–Frey pipeline
(EWMA vol filter → GPD on the standardized residuals → absolute tail move per regime). The result is a
concrete, regime-dependent answer to "how safe is the 40-point stop?" — and it reconciles the D2 paradox.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Code: `optimize/fundamentals/study_conditional_tail.py`
· Raw: [`results/conditional_tail_nq.txt`](results/conditional_tail_nq.txt) · 5.3M NQ 1-min residuals.

**Method note (honest):** the volatility filter is an **EWMA/RiskMetrics** conditional variance (λ=0.97) —
a special case of the GARCH family and the standard choice at 5.3M-point scale; full GARCH MLE is
impractical here and the de-clustering mechanism is identical. It is causal (σ[t] uses only returns to t−1).

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **De-clustering removes much of the tail, not all** | Excess kurtosis **+98.6 → +54.6** after EWMA filtering; residual GPD ξ = **+0.32** (still heavy). Exactly as the research said: volatility clustering explains *part*, not all. |
| **The residual is far from Gaussian** | The 99.99% standardized move is **12σ** (Gaussian: 3.9σ) — a Gaussian VaR under-states the deep tail **~3×**. |
| **The 40-pt stop's safety is CONDITIONAL** | 99.9% 1-min move: **2.6 pts** (quiet) → **8.9** (normal) → **37.8** (loud) → **90.6** (very loud) → **163.6** (extreme). In loud/event regimes a *single minute* can blow through the stop. |
| **🔑 The D2 paradox resolved** | RTH has the higher *absolute* blow-through exposure (**19.7%** of bars vs overnight **3.3%**) — RTH's *scale* dominates overnight's heavier *shape*. Two true things, reconciled. |
| **The deliverable** | Stop distance / size should **scale with the EWMA volatility** (and the A2 event burst). A fixed 40-pt stop is regime-blind — needlessly wide when quiet, dangerously tight when loud. |

---

## 1 — The absolute 1-minute tail move, by regime

`z_q × σ_pts` — the deep-quantile residual times the conditional 1-sd move in points:

| Regime (vol %ile) | 1σ (pts) | 99% move | 99.9% move | 99.99% | vs 40-pt stop |
|---|---|---|---|---|---|
| **quiet** (10th) | 0.4 | 1.4 | **2.6** | 5.3 | stop is ~100σ away — untouchable |
| **normal** (50th) | 1.5 | 4.8 | **8.9** | 18.0 | safe |
| **loud** (90th) | 6.4 | 20.4 | **37.8** | 76.0 | at the edge |
| **very loud** (99th) | 15.3 | 49.0 | **90.6** | 182.6 | 🔴 **a single 1-min move blows through** |
| **extreme** (99.9th) | 27.5 | 88.4 | **163.6** | 329.5 | 🔴 **blows far through** |

> **🍼 In plain words** — the same 40-point stop is a completely different stop depending on the regime. In
> a quiet market it sits ~100 standard deviations away — a 1-minute move essentially can't reach it. In a
> very loud or event regime, a *single minute's* rare move (1-in-1000) is **90 points** — it gaps straight
> through the 40-point stop. **The stop's real protection is not the 40 points; it's the 40 points
> *relative to the current volatility*** — and that ratio swings by 100× across regimes.

---

## 2 — By session: the D2 paradox, resolved

| Session | median 99.9% move | 90th %ile | **blow-through exposure** |
|---|---|---|---|
| **RTH** (loud) | 13.4 pts | 55.7 pts | **19.7% of bars** |
| **Overnight** (quiet) | 7.3 pts | 24.2 pts | **3.3% of bars** |
| All | 8.9 pts | 37.8 pts | 8.9% of bars |

*(blow-through exposure = fraction of bars in a regime loud enough that a 1-in-1000 minute-move would
exceed the 40-pt stop.)*

> **🔑 This resolves the D2 paradox.** D2 found the overnight tail is heavier in *shape* (α≈2.5 vs RTH
> α≈3.5). D3 finds RTH is more dangerous in *absolute points* (19.7% vs 3.3% blow-through). Both are true:
> **RTH's higher volatility SCALE dominates overnight's heavier tail SHAPE.** The honest synthesis:
> **RTH is dangerous OFTEN** (high scale → frequent large moves, matching the S3 56% stop-out rate);
> **overnight is dangerous RARELY but with a fatter tail when it is** (thin-liquidity gaps). A risk model
> needs both — scale for the everyday, shape for the freak.

---

## 3 — What this reconciles across the project

| Finding | Now explained |
|---|---|
| **D1:** backtest shows 0% of trades lose > the stop | idealized fill; the backtest can't gap through. **D3 quantifies the live gap risk it hides.** |
| **S3:** stop-out rate 56% RTH vs 16% overnight | RTH's higher *scale* → the fixed stop is reached far more often. |
| **D2:** overnight tail heavier in shape | real, but small scale → rarely a 40-pt move; the *shape* matters for the rare overnight shock. |
| **B3:** the assist is ruinous | doubling down re-exposes the position to *this* conditional tail at 2× size, in exactly the loud regime where it's largest. |

---

## 4 — VERDICT & the concrete deliverable (D4)

**#7 has produced its actionable result:** the fixed 40-point stop is **regime-blind.** The genuine tail
risk — the chance a single minute gaps through the stop — is negligible when quiet and material when loud
(≈20% of RTH bars, and worst around the A2 event bursts). The concrete improvement is a **volatility-scaled
stop / size**: set the stop distance as a multiple of the current EWMA σ (so it's a constant number of
standard deviations, not a constant number of points), and/or reduce size when σ is high.

**→ D4 (next):** turn this into a concrete rule and *test it on the champion ledgers* — does a
vol-scaled stop (constant-σ instead of constant-40-pt) improve the risk/return vs the fixed stop, net of
its own effects on entries and exits? **Caveat (DIST-01):** the sizing/Kelly half still needs its own
research pass before any position-sizing rule; D4 starts with the stop-distance question, which is
self-contained. And any engine change re-runs the golden gate — production stays byte-identical until a
change is proven and adopted.
