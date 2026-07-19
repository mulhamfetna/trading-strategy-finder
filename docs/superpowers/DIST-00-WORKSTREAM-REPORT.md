# DISTRIBUTION · 00 — THE COMPLETE WORKSTREAM REPORT (#7: fit our own distribution)

**#7, start to finish. The goal: stop assuming our risk is Gaussian and characterize the fat tail that
kept making real-looking edges statistically invisible — so stop and sizing decisions rest on correct
probabilities. The workstream did that rigorously, produced one actionable idea (a volatility-scaled stop),
tested it, and found it does NOT help. That is a success: it prevented a plausible-but-wrong change and
explained why the current fixed stop is already right. $0, production byte-identical, nothing adopted.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Detail: [`DIST-01`](DIST-01-RESEARCH-tail-fitting-recipe.md)
(research) · [`DIST-02`](DIST-02-D1-per-trade-pnl-is-truncated.md) (D1) · [`DIST-03`](DIST-03-D2-raw-return-tail-index.md)
(D2) · [`DIST-04`](DIST-04-D3-conditional-tail.md) (D3) · [`DIST-05`](DIST-05-D4-vol-scaled-stop-rejected.md) (D4).

---

## PART 0 — THE GREAT PICTURE

> **🍼 In one paragraph** — Market returns are wildly non-Gaussian: extreme minutes happen far more often
> than a bell curve allows (our data: 99 excess kurtosis, tail index ≈ 3). We wanted to know what that
> means for *our* stops and sizing. The first surprise: **our own per-trade profit/loss is NOT fat-tailed
> — the stop truncates it into a bounded, two-outcome (win +60 / lose −40) shape.** The fat tail is in the
> raw market, and the stop holds it at bay. The one idea that seemed to follow — set the stop as a multiple
> of current volatility instead of a fixed 40 points — we built and tested, and it **made things worse**,
> because a fixed stop *and* a fixed take-profit already balance out across all volatility regimes (a
> gambler's-ruin fact). So the honest conclusion is: **keep the fixed stop; it's well-designed.** The real
> residual risk (a live price gap blowing *through* the stop) is an execution/fill matter, not a stop
> setting — and it's exactly what the rejected "assist" idea (FA-v2 B3) would have amplified.

| Step | Question | Answer |
|---|---|---|
| **Research** | How do you fit a fat tail? | EVT/GPD on GARCH-filtered residuals, asymmetric tails, a mixture for trade P&L. All sources daily → re-estimate on our data. |
| **D1** | Is our per-trade P&L fat-tailed? | ❌ **No — TRUNCATED** by the stop. Bounded [−40,+60], bimodal, *light* tails (excess kurt −1.82). |
| **D2** | Where is the real fat tail? | In **raw returns**: α ≈ 3 (heavier than daily), ~symmetric, heavier *shape* overnight. |
| **D3** | How big is the tail, given the regime? | The 40-pt stop's blow-through safety swings ~100× — 2.6 pts (quiet) to 164 pts (extreme). RTH more dangerous in absolute terms. |
| **D4** | Does a vol-scaled stop help? | ❌ **No.** Worse tail, no P/L gain, *less* consistent — the fixed stop/TP is already regime-invariant (gambler's ruin). **Keep the fixed stop.** |

---

## PART 1 — THE DISCOVERIES

1. **Our per-trade P&L is truncated, not fat-tailed (D1).** Across 7,356 trades, 0 lost more than the
   stop; excess kurtosis −1.82 (light). The "±$1,600 fat tail" is really a **bimodal win/lose spread**
   (~$960) — a near-binary payoff. *That* binary variance is what buries small edges, not a heavy tail.
2. **Raw returns are genuinely fat (D2):** α ≈ 3 (the inverse-cubic law), heavier than daily equities;
   loss and gain tails ~symmetric intraday (unlike daily's crash asymmetry).
3. **The tail is heavier *in shape* overnight, but more dangerous *in magnitude* in RTH (D2+D3).** Two true
   things: overnight = thin-liquidity rare violent gaps (heavy shape); RTH = high scale, frequent large
   moves (matching S3's 56% stop-out rate). Scale beats shape for the absolute blow-through (RTH 19.7% of
   bars vs overnight 3.3%).
4. **The stop converts a fat-tailed return process into a bounded trade P&L (D1+D3).** That's the stop
   *working* — and it's why keep-the-stop (report 04/06) and never-assist (B3) are both right: the fat tail
   comes roaring back the instant you remove or double past the stop.
5. **The fixed stop is regime-invariant by construction (D4):** fixed stop + fixed TP ⇒ P(stop) ≈
   60/(40+60) = 60%, independent of volatility (gambler's ruin). You cannot improve a balance that is
   already scale-free — which is why the vol-scaled stop failed.

---

## PART 2 — WHAT WENT WELL / WHAT WENT WRONG

**Well:** research-first gave the exact recipe and the right skepticism (report ranges not points; the
threshold instability); D1's truncation finding corrected the plan *before* we wasted effort fitting EVT to
a bounded distribution; D4's honest test killed the workstream's own proposed deliverable rather than
shipping it. The discipline (test before build, dumb control, honest read) worked end to end.

**Wrong / caught:** D3 *proposed* the vol-scaled stop as "the deliverable"; D4 then falsified it. That's
the process functioning — a hypothesis, then its test — not an error, but worth noting that the
intermediate report (DIST-04) over-committed to an idea the next test overturned. Also: full GARCH MLE was
impractical at 5.3M points, so D3 used an EWMA filter (a defensible McNeil–Frey variant) — stated plainly.

---

## PART 3 — VERDICT & WHAT REMAINS

**#7 is complete. The recommendation is: keep the fixed stop.** The distribution is now understood —
truncated trade P&L, fat raw returns (α≈3), a regime-conditional gap tail — and the one change it suggested
does not survive its own test. Nothing is adopted; production is byte-identical.

**The one genuinely open thread with potential value — fat-tail-aware SIZING:**
- The research (DIST-01) flagged the **sizing / Kelly** decision layer as thinly covered and needing its
  own pass. It is *separate* from stop distance (which D4 settled).
- The mechanism is real: under fat tails, **full Kelly is dangerous** and a fractional Kelly is standard —
  but *how much* to fraction as α drops toward the danger zone is exactly the unanswered question, and it's
  where the D2/D3 tail estimates (α≈3, regime-conditional) could actually feed a decision.
- This is the natural next research→test cycle.

**Also open (unchanged):** GC distribution work frozen (2025–2026 only, long GC history needed); task #16
(assess the user's external data sources).

**→ Next: a deep-research pass on fat-tail-aware position sizing (fractional Kelly / risk-of-ruin under a
measured tail index), then test on our ledgers.**
