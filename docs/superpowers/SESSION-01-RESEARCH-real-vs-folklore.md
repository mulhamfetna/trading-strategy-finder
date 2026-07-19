# SESSION WINDOWS · 01 — RESEARCH: what is REAL vs FOLKLORE

**Task #5, phase 1: the deep-research mining pass, done BEFORE writing a line of study code (per the
standing rule). 101 research agents, 19 sources fetched, 65 claims extracted, 25 adversarially verified
(3-vote, need 2/3 to kill). This separates the session effects that survived from the ones that didn't —
so we test the real ones on our own data and never waste a run on folklore.**

Date: 2026-07-14 · Branch `fundamental-analysis` · Workstream: trading-session windows
Method: `deep-research` workflow · full raw output archived in the session transcript.

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **The single most useful finding** | The intraday **session shape is a CONFOUND that must be removed** before any volatility / event / causality estimate — it manufactures **spurious persistence and spurious causality**. This is *exactly why our 09:30 open contaminates event studies.* It is not folklore; it is the mechanism. |
| **The strongest real effect** | The **U-shaped RTH volatility curve** — loud at the 09:30 open, quiet at midday ("lunch lull"), loud into the 16:00 close. ~**2× open/close-vs-midday**. Replicated for Nasdaq & S&P futures specifically. |
| **The big structural split** | **Overnight (Globex) and RTH are segmented regimes**, not a continuum — different expected-return *and* volatility properties. Historically nearly all of SPY's gain accrued **overnight**. ⚠️ Equity-specific, and **weakened post-2015**. |
| **The verdict that shapes our design** | **Naive session-timing TRADES mostly fail after costs.** On Nasdaq micro futures, Asia-session breakouts *reverse* and overnight gaps *don't reliably fill*. **Session structure is a regime/context FILTER, not a standalone entry signal.** |
| **What died** | Four popular claims were **refuted** — including the "entire equity premium in a 2–3am window" and a London-session edge that flipped sign with a **1-bar entry delay**. |

**Design implication, up front:** this points us at using session structure as a **filter / sizing /
estimation-control** layer — which is exactly where our workstream already wants to go (regime-aware, not
new entry signals). It does **not** point at a new session-timing entry.

---

## ✅ WHAT IS REAL — confirmed, verified, with sources

### R1 — The U-shaped RTH volatility curve (HIGH confidence, 3-0)

Index futures show a robust **U-shape** in Regular-Trading-Hours volatility and volume:

| Time (ET) | Avg abs 5-min return (S&P futures) | Character |
|---|---|---|
| **09:30 open** | **~0.095%** | loud — the opening burst |
| ~12:00 noon | **~0.055%** | the **"lunch lull"** — quiet, muted, low volume |
| **16:00 close** | **~0.105%** | loud — the closing ramp |

Roughly a **2× ratio** open/close-vs-midday. Replicated **explicitly for Nasdaq and S&P 500 futures**
(not just equities). Related markets echo it: Euro FX ramps from the London open (03:00 ET); WTI peaks
over its pit hours (09:00–14:30 ET).
*Sources: Andersen & Bollerslev 1997 (J. Empirical Finance); Örebro WP-14-2025; Quantpedia.*

### R2 — The session shape is a CONFOUND that must be removed (HIGH confidence, 3-0)

**This is the most important finding for us.** The intraday periodicity is not merely descriptive — it is
a **first-order statistical trap**:

- The daily periodicity induces a **spurious U-shaped return-autocorrelation** that ARCH/GARCH models
  **mistake for volatility persistence**.
- Failing to strip the seasonal shape produces **spurious volatility-spillover causality** between
  markets.
- Only **after** removing it do the true intraday and cross-market dynamics become recoverable.
- After controlling for **public-information arrival**, the U/L shapes **flatten** — so the pattern is
  driven by *information flow*, not by strategic informed-trader timing.

> **🍼 In plain words** — the market is loud at the open and close and quiet at lunch **for boring,
> predictable reasons.** If you measure "did news move the market?" or "did volatility spike?" without
> first subtracting that predictable daily shape, **you will find effects that are just the time of day.**
> This is precisely the mechanism behind our own finding that the 09:30 cash open contaminates the news
> event studies. **We already tripped this wire; the literature names it.**
*Sources: Andersen & Bollerslev 1997; Alemany/Aragó/Salvador 2019 (Quantitative Finance); Eaves & Williams
2010 (AJAE — caveat: agricultural call-auction data).*

### R3 — Volume-time-of-day is the largest driver of intraday variance (HIGH confidence, 3-0)

A volume-driven time-of-day component is the **single largest explainable driver** of intraday variance
in exactly our instruments:

| Instrument | Variance explained by volume-ToD |
|---|---|
| **Nasdaq** | **45.4%** |
| **S&P 500** | **38.9%** |
| Euro FX | 39.4% |
| WTI | 33.0% |

And the volume→volatility amplification is **non-constant across the day** — it swings sharply near the
**16:00 ET US close** and the **08:15 ET ECB fixing**. Those boundary times are where the relationship is
*least stable* — directly relevant to any sizing/stop logic. *Source: Örebro WP-14-2025 (strong, but a
2025 working paper, not yet peer-reviewed).*

### R4 — Overnight and RTH are SEGMENTED regimes (HIGH confidence, 3-0; equity-specific)

Overnight (Globex, close-to-open) and RTH (open-to-close) behave as **effectively separate markets** with
structurally different returns:

- Over 1999–2014, US equity-index **overnight returns are positive AND lower-volatility**, while **RTH
  returns are negative** — an anomaly inconsistent with the usual risk-return tradeoff.
- Historically **nearly all** of SPY's ~30-year appreciation accrued overnight: **$1 → ~$1.21** held
  intraday-only vs **$1 → ~$17.17** held overnight-only.
- The overnight long-short "drift" had a Sharpe **~10× momentum** ("grandmother of all anomalies").

> **⚠️ Two caveats that matter enormously for us:** (1) the evidence is **equities / index-ETFs**, NOT
> gold or oil — do not extrapolate to metals/energy without testing; (2) the drift **weakened / partly
> reversed post-2015** (NY Fed, "The Disappearing Overnight Drift"; the NightShares ETFs closed). So on
> our 2025–2026 data the magnitude will likely be **much smaller** than the historical headline.
*Sources: Liu & Tse 2017; Lou/Polk/Skouras 2019 (JFE); Dutta 2012; Elm Wealth/Haghani.*

### R5 — Overnight carries some predictive info for RTH (HIGH confidence, but economically small)

Overnight returns forecast the next RTH session with a **negative** relation to the **first half-hour**
(09:30–10:00) and a **positive** relation to the **last half-hour** (15:30–16:00), in- and out-of-sample.
The overnight-vs-intraday "tug-of-war" spread forecasts future returns (1 SD ≈ +1% ≈ 18% of monthly vol).

> **⚠️** The predictability is **economically small** and **execution-timing-fragile**, and the tug-of-war
> evidence is an equity **cross-section** long-short — the mechanism may not transfer to single-instrument
> futures. Treat as a **hypothesis to test locally**, not a fact. *Sources: Liu & Tse 2017; Lou/Polk/
> Skouras 2019.*

### R6 — Naive session TRADES fail after costs → use session as a FILTER, not a signal (MEDIUM confidence)

The most directly on-instrument evidence — a **cost-inclusive falsification study on Nasdaq micro futures
(MNQ, 2021–2025)**:

- **Asia-session (20:00–02:00 ET) range-expansion breakouts REVERSE** rather than continue (T = **−10.96**)
  — the directional move is **fully consumed inside the expansion bar** before a bar-close entry can fire.
- **Overnight gaps do NOT reliably fill** in RTH — gap-fill fades are indistinguishable from noise at
  every entry time (T = −0.44 to −0.59).
- A gap-continuation short had a strong point estimate (T = 3.23, +14.52 pts, 68% win) but **fired only 22
  times in 3 years and decayed** — too rare to bank.

> **🍼 The takeaway that shapes our whole design** — session structure is **real** but it is **context, not
> a trigger.** The move you can see (the breakout, the gap) is already spent by the time a candle closes.
> So the right use is **regime/filter/sizing** — "am I in the loud open or the quiet lunch?", "is this the
> segmented overnight regime?" — feeding the *existing* strategy, **not** a new session entry signal.
*Source: Mesfin 2026, "Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures" (arXiv:2605.04004
— rigorous but single-author, non-peer-reviewed preprint).*

### R7 — The session boundary times to anchor on (MEDIUM confidence)

From the sources (and to be **confirmed against CME product specs before hard-coding**):

| Boundary (ET) | What it is |
|---|---|
| **Sun 18:00 → Fri 17:00** | The Globex week; **daily 60-min halt 17:00–18:00 ET** |
| **09:30–16:00** | RTH cash session |
| **16:00** | US equity close — volatility/volume **inflection** (also WTI) |
| **~03:00** | London open — Euro/European activity ramp |
| **08:15** | ECB fixing — Euro-FX inflection |
| **09:00–14:30** | WTI historical pit window |
| **~20:00–02:00** | Asia/overnight Globex regime |

*(E-mini equities also had a 16:15–16:30 ET maintenance break until it was lifted in June 2021.)*

---

## ❌ WHAT IS FOLKLORE — refuted by adversarial verification (do NOT test these as if true)

| Refuted claim | Vote | Why it matters |
|---|---|---|
| A distinct 08:35–08:40 CST vol spike **caused by 08:30 macro releases** | **0-3** | Our own 17-year study already reached the compatible conclusion (scheduled macro is priced in); don't re-attribute the open burst to news |
| **The entire equity premium accrues in a narrow 02:00–03:00 ET window** | 0-3 / 1-2 | A popular "trade the 2am drift" claim — **killed.** The overnight drift is real (R4) but **not** concentrated in one magic hour |
| A **post-lunch positive "lunch effect"** (returns flip up after lunch) | 1-2 | The lunch **lull in volatility** is real (R1); a lunch **return** signal is not |
| A **London-session GMM edge** (T=5.15, Sharpe 5.09, p<0.001) | **0-3** | Passed five validation criteria — then **flipped from T=+5.15 to −3.56 with a 1-bar entry delay.** The cautionary tale for the whole workstream: **session edges are lethally execution-timing-sensitive.** |

---

## ❓ OPEN QUESTIONS the research could NOT answer (→ our data must)

1. **Exact CME Globex session/halt/rollover times per product** (index vs gold vs oil) — no authoritative
   CME-spec source survived; and **contract-rollover gap handling was not covered at all.** Needs a direct
   CME product-spec pass before hard-coding boundaries.
2. **Do the overnight / segmentation / predictability effects hold for GOLD and OIL**, or are they
   equity-index-specific? All primary overnight evidence is equities/ETFs.
3. **Do any of these survive on 2025–2026 data at 1-minute resolution**, given the documented post-2015
   weakening? Historical headlines will overstate current magnitudes.
4. **Is the London–NY overlap (~08:00–11:00 ET) a genuinely distinct regime for index futures?** Only
   indirectly touched; the one London edge tested was refuted. Unresolved.

---

## 🎯 WHAT THIS MEANS FOR OUR BUILD (the bridge to phase 2)

**The research converges on one design principle:** *session structure is a **regime/context filter and an
estimation control**, not a new entry signal.* That is a perfect fit for where this workstream already is
(regime-aware improvements to L1, not new triggers).

Concretely, it hands us a **prioritised, pre-registered test list** for our own data — real effects only,
each with the discipline that ran the rest of this workstream (dumb control, noise check, power):

| # | Hypothesis (from a REAL finding) | On our data |
|---|---|---|
| **S1** | **Characterise our own session shape** — the U-curve of 1-min volatility & volume by minute-of-day, per market. *Foundation + the confound-removal control.* | NQ first, then all 9 |
| **S2** | **Overnight vs RTH segmentation** — are our markets' close-to-open and open-to-close returns distributionally different? Test **per market** (equities vs metals vs energy — R4 says likely equity-only). | all 9, split by class |
| **S3** | **Does our strategy's edge concentrate by session?** Bucket existing champion trades by entry session; is P/L / win-rate / the 80-pt stop-out tail **session-dependent**? *This is the filter test.* | champion trades |
| **S4** | **Session-aware sizing/gating as a FILTER** — only if S1–S3 show a real, stable, **cost-and-noise-surviving** session dependence. **Never a standalone session entry** (R6). | L1, gated |

**Explicitly NOT on the list:** Asia-breakout continuation, gap-fill fades, a 2am-drift trade, a
London-session timing entry. The research already falsified those; re-testing them is archaeology.

**Next step (phase 2):** start with **S1 on NQ** — characterise our own session shape on the 17-year
1-minute frame (where we have the power) and the 2025–2026 multi-market frame. It is the foundation for
everything else *and* doubles as the confound-removal control that R2 says we need. Then S2/S3.

---

## Appendix — source quality ledger

| Source | Tier | Used for |
|---|---|---|
| Andersen & Bollerslev 1997 (J. Empirical Finance) | **primary, top** | R1, R2 |
| Lou, Polk & Skouras 2019 (JFE) | **primary, top** | R4, R5 |
| Liu & Tse 2017 (Int. Rev. Econ & Finance) | **primary** | R4, R5 |
| Alemany/Aragó/Salvador 2019 (Quantitative Finance) | **primary** | R2 |
| NY Fed Staff Report 917 ("Overnight Drift") | **primary** | R4 (and refuted the 2am-window claim) |
| Örebro WP-14-2025 | primary, **not yet peer-reviewed** | R1, R3, R7 |
| Mesfin 2026 (arXiv:2605.04004) | rigorous **preprint, single-author** | R6 |
| Dutta 2012 | low-tier (survives on corroboration) | R4 |
| Elm Wealth / Quantpedia / tradingstats | secondary / blog | context only |

**Interval caveat:** most volatility work is 5-minute; ours is 1-minute — re-derive shapes locally.
**Asset-transfer caveat:** overnight/segmentation evidence is equities; gold/oil are open questions.
