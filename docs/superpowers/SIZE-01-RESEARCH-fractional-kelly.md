# SIZING · 01 — RESEARCH: fractional Kelly under a small edge and a fat tail

**The deep-research pass on position sizing, done before any sizing code (task #17). 107 agents, 24 of 25
claims verified (3-0). The theory here is settled, non-perishable mathematics with four independent primary
sources — and it hands us our exact number. The one-line answer: our full-Kelly bet is ~6.7% of
capital-at-risk, but the honest size is a small FRACTION of that, because our edge is tiny and uncertain
and our tail is fat.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Method: `deep-research` workflow.

---

## ⚡ THE 60-SECOND VERSION — the recipe

| Step | What | For us |
|---|---|---|
| **1. Full Kelly** | `f* = edge/odds = (B·p − q)/B`, B = win/loss ratio | B=60/40=1.5, p≈0.44 → **f\* ≈ 6.7%** of capital-at-risk per trade |
| **2. Jensen haircut** | dispersed payoff (our time-capped exits) ⇒ true optimum **< plug-in** | small downward nudge |
| **3. Fractionalize for edge uncertainty** | half/quarter Kelly — because Kelly is **~10–20× more sensitive to the EDGE than to variance**, and our p is estimated on a finite (fluke-window) ledger | **the dominant cut** — quarter-Kelly or less |
| **4. Tail/gap haircut + hard cap** | fat tails (α≈3) ⇒ ruin from a **single gap**, not accumulation ⇒ cap absolute exposure against one catastrophic fill | a further cut + a hard contract cap |
| **5. Scale by volatility** | prefer inverse-vol / vol-target contract scaling, integer + cost constraints | layer on top |

**Honest verdict (from the research):** *"start from Kelly, discount heavily for uncertainty and tails, and
cap exposure — a small fixed fraction with a hard cap is a fully defensible endpoint."* **Over-Kelly
leverage is never rational.**

---

## ✅ WHAT IS REAL — settled mathematics

### K1 — The exact formula, and our number
`f* = (B·p − q)/B`, from maximizing `g(f) = p·log(1+Bf) + q·log(1−f)` (strictly concave, unique max).
For our near-binary trade — **win ~44% at +60, lose ~56% at −40** (B = 1.5): **f\* ≈ (1.5·0.44 − 0.56)/1.5
≈ 6.7%** of the amount risked. That small number reflects a **tiny edge on a high-variance bet** (expectancy
≈ 0.44·60 − 0.56·40 ≈ **+4 pts/trade ≈ +$80**, against a ±$960 swing — the same tiny edge we've measured all
along). *Sources: Pérez-Marco; MacLean–Thorp–Ziemba; Kelly–Ziemba (Springer).*

### K2 — Full Kelly is the ceiling; over-betting is dominated
At **2× Kelly the long-run growth rate collapses to zero**; beyond that, growth turns negative while risk
rises. Log utility has near-zero risk aversion (`R_A = 1/w`) — "the most risky utility one should ever
consider." So full Kelly is a **hard upper bound**, and anything above it is strictly worse on both growth
*and* risk. *Sources: MacLean–Thorp–Ziemba (Management Science 1992).*

### K3 — 🔴 Kelly is acutely sensitive to the EDGE (this is our biggest risk)
Errors in the **mean/edge** matter **~10–20× more** than errors in variance (Chopra–Ziemba 1993: 20:2:1
for means:variances:covariances, rising to ~100:3:1 for a log/Kelly investor). **Our f\* depends directly on
p, which we estimated from a finite ledger in the 2025–2026 fluke window.** If p is over-estimated, f\*
collapses. **This alone justifies quarter-Kelly or lower, before any tail haircut.** *Sources:
Chopra–Ziemba (JPM 1993) via MacLean–Thorp–Ziemba.*

### K4 — Fractional Kelly: huge security for a small growth cost
Growth-rate ratio of betting fraction c of Kelly is exactly **c(2−c)**: **half-Kelly keeps 75% of the
growth** while cutting the probability of a 50% drawdown from 50% to **~12.5%**. Quarter-Kelly keeps ~44%.
A large security gain for a small growth sacrifice. *Sources: MacLean–Thorp–Ziemba; Entropy 2023.*
**Caveat:** c(2−c) and the 12.5% figure are exact only in the Gaussian approximation — our fat tails make
them **best-case**.

### K5 — Dispersed payoff ⇒ size smaller (Jensen)
When the payoff is a random variable (our time-capped exits, any slippage around ±60/−40), the true Kelly
optimum is **strictly smaller** than the fraction from the average payoff. *Source: Pérez-Marco Thm 3.2.*

### K6 — Fat tails ⇒ the catastrophe principle ⇒ cap against ONE gap
Under heavy tails (subexponential; our raw α≈3 process), **ruin comes from a single extreme jump**, not
accumulated losses (`P(Sₙ>x) ~ n·P(X>x)`). Our *truncated* trade P&L is not subexponential (D1), but the
*raw* fat-tailed process reaches the book via **gap/slippage through the stop** (D3). So sizing must be
**bounded against one catastrophic gap**, not against average variance — and a small repeated ruin
probability **converges to certain ruin** (absorbing barrier). *Sources: Taleb (Statistical Consequences of
Fat Tails); Embrechts–Klüppelberg–Mikosch; Entropy 2023 (Lomax sims: complete ruin at 1–2% risk under heavy
tails, impossible under bounded loss).*

---

## ❌ REFUTED / ⚠️ OPEN

- **Refuted (1-2):** the claim that Kelly *requires* a hard bounded loss only satisfiable by binary options.
  Do not rely on it.
- **No closed-form tail haircut exists.** The literature supports the *direction* (shrink as α falls toward
  2–3, cap against one jump) but **no coefficient**. The composite recipe is a defensible *engineering
  synthesis*, not a cited theorem (the research flagged it medium-confidence).
- **Vol-targeting vs fixed-fractional out-of-sample** was *not* settled by the sources — must A/B test on
  our own ledgers.

---

## 🎯 THE ON-DATA PLAN (the open questions → our tests)

| # | Test | Why |
|---|---|---|
| **Z1** | **Compute f\* on our actual NQ + GC ledgers** (realized p, B) and **bootstrap the CI on p** | K3 says edge error dominates — quantify how far f\* moves across the p confidence interval; that sets how deep below full Kelly we must sit for *parameter safety alone* |
| **Z2** | **Simulate the ledger with gap-through-stop fills** (an EVT/GPD tail overlay on the stop, reusing #7's D2/D3 tail fits) and find the fraction that holds ruin probability below a threshold | the empirical answer to K6's "no closed-form haircut" — read off the tail-safe fraction |
| **Z3** | **A/B fixed-fractional vs vol-targeting** on the champion ledgers, net of costs + integer contracts | the unresolved Part-4 question |
| **Z4** | **Recompute for our PnL:DD objective** (Maier-Paape–Zhu drawdown-risk frontier) rather than raw log-growth | our accepted objective is PnL:DD, not growth — size to *that* |

**→ Next: Z1** — compute f\* on our ledgers and bootstrap the edge. It is the foundation (everything scales
off f\* and the uncertainty in p), it needs only data we have, and it directly answers the research's
single loudest warning: **our edge estimate is the thing most likely to be wrong, and Kelly punishes that
hardest.**

**Standing guardrail:** any sizing change is a live-capital risk decision, not just a backtest number.
Nothing here gets adopted without the tail-safe (Z2) and OOS (Z3) checks — and the honest prior, given a
tiny fluke-window edge and a fat tail, is a **small fixed fraction with a hard exposure cap.**
