# NQ Box Strategy — Research & Roadmap

*A self-contained briefing: what the system is, the research we ran to improve it, what we proved, and what's
next. No prior context or repository access required. All figures are from the 2025–2026 research window.*

> **Status (2026-07-02):** the Kalman/fusion research (§4) is **complete and closed**. The next workstream —
> exogenous signal fusion (§5A) — is **waiting on market-data feeds from the team leader** (start with **VIX**).
> Until those arrive, active development has moved to other features.

---

## 1. What the system is (in one breath)

A rules-based futures strategy on the **Nasdaq-100 (NQ)** (and portable to ES/S&P). Each bar, a **"box" signal**
may fire a long/short suggestion. A **volatility gate** and a **veto layer** of technical judges then decide
whether to actually take it. Trades exit on fixed **take-profit / stop-loss** distances resolved on 1-minute data.
The whole thing is tuned by a multi-objective optimizer and validated by a byte-exact regression gate.

**The champion strategy** (the current best, used as the baseline throughout this document):

| Metric | Value |
|---|---|
| Total P/L | **$142,203** |
| Trades | 214 |
| Win rate | 69.2% |
| Payoff ratio (avg win ÷ avg loss) | 0.74 |
| Signals *taken* (of those that fired) | ~31% |

> A newer production champion of record reaches **$153,321** (max drawdown $9,589), out-of-sample verified. This
> document's research anchors on the $142,203 4h champion for clean comparison.

---

## 2. The question we spent this research program answering

The champion **drops ~69% of the signals that fire** (the vol gate + veto layer filter them out). Natural question:

> **Can we safely take far more of the dropped signals — pushing from ~31% toward ~75% taken — without hurting
> profit-per-trade, so total profit rises?**

The honest answer we arrived at, after four disciplined experiments, is **"not on the data we have"** — but *how*
we proved that produced a durable, reusable insight. Here it is.

---

## 3. The one law that governs everything: profit-per-trade is fixed, so the only lever is direction

Expected profit per trade is

$$\mathbb{E}[\text{P/L}] = p\,W - (1-p)\,L$$

where $p$ = win rate, $W$ = average win size, $L$ = average loss size. With payoff ratio $\varphi = W/L$, the trade
breaks even when

$$\boxed{\,p^\* = \dfrac{1}{1+\varphi}\,}$$

**Key fact:** the exits (take-profit ≈ 120 pts, stop ≈ 167 pts) fix the *sizes* of wins and losses. So the payoff
ratio is **pinned at ≈ 0.74 no matter which signals you admit** — we confirmed this empirically across every
experiment. Therefore:

$$p^\* = \frac{1}{1+0.74} \approx \mathbf{57.5\%}.$$

```mermaid
flowchart LR
  A["admit more signals<br/>(trade more often)"] --> B["payoff STAYS ≈ 0.74<br/>(exits fix win/loss sizes)"]
  A --> C["win-rate MOVES<br/>(depends on direction skill)"]
  C --> D["is win-rate &gt; 57.5% ?<br/>YES → profit rises · NO → profit falls"]
  classDef k fill:#eef,stroke:#3355cc; class B,D k;
```

**Consequences that shaped every experiment:**
1. Trading more often **cannot** lower payoff — it's a constant of the exit rules. The goal "trade more, keep
   payoff" is *free* as long as exits are untouched.
2. So the entire problem reduces to **direction / win-rate**: any admitted signal helps only if we can call its
   direction right **more than 57.5%** of the time.
3. The *only* way to move payoff itself is to **change the exits** — which one experiment (M3) tried.

---

## 4. The research program — four experiments (M0 → M3)

Each was tested with rising rigor. The recurring lesson: **results that look great on one data split shrink or
vanish under honest across-time (walk-forward) testing.**

### M0 — the ceiling ("is there a prize at all?")
Replayed every dropped signal both directions and took a hypothetical **perfect-direction oracle** (an upper
bound, cheats by peeking). Result: the oracle earns **~$1.3M vs the champion's $142k — about 9×.** So the dropped
signals carry *enormous* directional information; the whole gap is a **direction** problem, not a "no edge"
problem. **→ Worth chasing.**

### M1 — fuse faster-timeframe votes (recover direction from 1h/15m/5m box directions)
Weighted vote of finer timeframes, weights fit on 2025. The faster charts turned out only **~55–58% reliable** —
barely better than a coin flip — and out-of-sample the admitted signals won just **56.7%**, *below* the 57.5%
breakeven. Adding them **turned a +$28,899 out-of-sample profit into a loss.** **→ STOP.**

### M2 — Kalman trend filter (recover direction from a continuous price-trend estimate)
A 2-state Kalman filter estimates trend *strength*; admit dropped signals only on strong trends, in the trend's
direction. On a single 2025/2026 split this **beat the champion: +$41,200 out-of-sample (+43%), trading more.**
Exciting — but the knob was chosen on one lucky split. Under honest **walk-forward** (knob chosen only from past
quarters, applied forward) the edge **deflated to +8%, winning only 2 of 4 quarters.** **→ Not confirmed.**

### M3 — volatility-regime exits (the only lever that can move payoff itself)
Sort bars into calm / normal / stormy by volatility; learn the best exit width per regime on the past, apply
forward. Result: it **lost to the champion (−12%)** out-of-sample and the learned rule was **unstable across
quarters** — classic overfitting, no real regime→exit relationship. **→ DEAD.**

### Scoreboard

| Experiment | Idea | Best single-split | Honest walk-forward | Verdict |
|---|---|---|---|---|
| **M0** | Perfect-direction ceiling | ~9× ($1.3M) upper bound | — | Prize is real; it's a *direction* problem |
| **M1** | Fuse faster-TF votes | — | 56.7% < 57.5% | **STOP** — near-random inputs |
| **M2** | Kalman trend filter | +$41k (+43%) ✨ | +8%, 2/4 quarters | **Not confirmed** — over-fit |
| **M3** | Vol-regime exits | — | −12%, 2/4 quarters | **DEAD** — unstable |

**Bottom line:** the signals the champion drops are **genuinely hard to trade** — neither their direction (M1, M2)
nor their exits (M3) carry an edge that survives across time on ~2 years of data. The study is **closed**.

> **Scope note (important):** this study tested the **standard (vanilla) Kalman filter** and simple fusions —
> **not** the advanced variants (Extended/Unscented/adaptive Kalman, particle filters) or advanced state fusion
> (regime-switching / factor / machine-learning models). Those were deliberately **gated behind the standard
> version first showing an edge, which it didn't** — so building something fancier on the *same price input* was
> not justified. The genuinely different, still-untested idea is **fusing diverse *external* signals** (§5A) — that
> is where advanced fusion would actually earn its keep, and it's the parked next workstream.

### What's worth keeping regardless
1. **A structural law** — with fixed exits, win-rate is the only lever; breakeven 57.5%. Any future entry work
   should chase *directional accuracy past that bar*, not trade count.
2. **A discipline that repeatedly caught a false positive** — M2 would have shipped as a "+43% win" on one split;
   walk-forward correctly deflated it. This is the same rigor that governs every promotion decision here.
3. **A reusable research toolkit** — isolated re-simulation, causal multi-timeframe alignment, a compact Kalman
   filter, and walk-forward validation — all off the production path, ready for the next idea.

---

## 5. Roadmap — two open workstreams (both parked pending inputs)

### 5A. ⭐ Exogenous signals to fuse (BLOCKED — needs data you can provide)

The M1/M2 experiments failed partly because faster timeframes and sister indices (ES) are **already inside NQ's own
price** — not truly new information. The promising redirection is to fuse NQ with **genuinely orthogonal** market
signals, and use them **not** for entry direction but for a **regime / risk state** that drives *position sizing,
stop/target width, and when to sit out.*

**These are external data feeds I cannot derive from price — please provide them as CSV** (2025-01 → present,
daily is fine, intraday better; one header row):

| Priority | Signal | What it is / why it's orthogonal | Columns to provide |
|:--:|---|---|---|
| **1** | **VIX (+ VIX3M)** | Forward-looking implied volatility & fear premium; term-structure slope flags stress | `Date, VIX, VIX3M` |
| 2 | **Put/Call ratio** | Options positioning / tail-risk pricing | `Date, PutCallRatio` |
| 3 | **Market breadth** | Participation across the market (narrow vs broad moves), invisible in the index level | `Date, TICK, ADD, TRIN` |
| 4 | **Rates + Dollar** | Macro risk-on/off backdrop | `Date, UST2Y, UST10Y, DXY` |
| 5 | **Options skew / gamma** *(if available)* | Dealer positioning; pin vs squeeze regimes | `Date, Skew25d, GEX` |

**How each would be used (same pipeline for all):**
1. Align each feed causally to the decision bars (only values known *at that time* — no look-ahead).
2. Engineer simple features: level, z-score, slope, percentile.
3. **Run a cheap one-feature test first** — does conditioning on *any single* signal (e.g. a VIX regime) improve
   **risk-adjusted** return via sizing or sit-out, walk-forward, vs the champion? **If no single signal helps,
   stop** — no fancy fusion will save it.
4. Only if a signal passes → fuse several into a regime/risk state → drive the sizing / stop / sit-out policy.
   **Never** the entry direction (the hard-won lesson from the sister-index study).

> **One feed — VIX — is enough to run the decisive test** and tell us whether this whole direction is worth
> building. That's the single most valuable thing to provide.

### 5B. Technical-indicator open items (already built; minor decisions)

The strategy's full technical-indicator suite — moving averages, MACD, RSI, ADX, ATR, Bollinger/Keltner, plus the
Smart-Money structures (Fair-Value-Gaps, order blocks, breaker blocks, market structure, CISD/"golf candle") — is
**already implemented and validated.** Only a few small product decisions remain:

1. **Order-block / breaker entry timing** — enter immediately, at the mid, at the top, or wait for confirmation?
   (Currently: wait for full confirmation.)
2. **"Golf candle" threshold** — how many prior candles it must exceed (default 3).
3. **Which key-level lines** to activate (weekly/monthly opens are on).
4. **One small build** — make the entry "retrace + wait" controls global instead of per-indicator.
5. **Optional prune** — an ablation study to drop indicators that cost ≤5% profit (tooling exists), for a leaner
   live system.

---

## 6. How to move forward

| If you want to… | Do this |
|---|---|
| **Unblock the highest-upside idea** | Provide the **VIX (+VIX3M)** CSV → we run the one-feature sizing/sit-out test |
| Lean out the live system | Run the indicator-ablation prune (§5B.5) |
| Ship the SMC entry rules | Answer the four §5B decisions |
| Re-open the Kalman thread | Only worth it once a longer out-of-sample window accrues (M2 had one genuine winning quarter) |

---

*Prepared as a standalone briefing. Every research figure is reproducible from the underlying study code; this
document requires no access to it.*
