---
name: ws-earn-stage-3-prior-art
description: "WS-EARN Stage 3 — prior-art pass. The literature confirms our volatility finding independently, and says the tradeable window is SECONDS not minutes and closed after 2016. Redirects Stage 4 from 1-minute bars to the 1-second archive and to the one question the literature leaves open."
type: research
date: 2026-08-06
issue: 112
workstream: earnings
---

# WS-EARN Stage 3 — what is already known

Run before Stage 4, per the standing **deep-research-first** rule. At the 2–6 approach budget Stage 2
established, choosing *what* to test matters far more than how many things we try — so this pass is
worth more than any amount of extra searching.

**It changed the plan.** Two of our own findings are confirmed independently, and the design we were
heading toward is aimed at a window the literature says closed a decade ago.

---

## 1. The single most relevant paper

**Christensen, Timmermann & Veliyev (2025)**, *"Warp speed price moves: Jumps after earnings
announcements"*, **Journal of Financial Economics 167**.
[arXiv:2601.08962](https://arxiv.org/abs/2601.08962) ·
[ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X25000182)

| | |
|---|---|
| sample | **2008–2020, 50 stocks** |
| data | **89+ billion** after-hours quotes, ~8 billion after-hours transactions |
| method | microstructure-noise-robust jump test |

### Findings that matter to us

**(a) The co-jump to the index is real — our 4.98× is independently confirmed.**
Earnings announcements *"significantly raise the probability of price co-jumps in non-announcing firms
and the market"*, and the paper reports a significant rise in **market-index** jump probability when
many firms announce together, **after controlling for the mechanical effect** of announcing firms being
index constituents.

> We do not need to spend any of our 2–6 approach budget establishing that the effect exists. It is
> established. The open question was always whether it is *directional and tradeable*.

**(b) Price discovery happens in milliseconds to seconds — not minutes.**

**(c) The tradeable window closed around 2016.**

| period | frictionless | midquote | with 10-second delay |
|---|---:|---:|---:|
| **2008–2015** | 2.30% per trade | 2.00% | **0.80% (still significant)** |
| **2016–2020** | significantly positive | positive | **small and insignificant, or negative** |

With a **5-second** execution delay profits become insignificant. Beyond **10 seconds**, even in the
profitable early period, returns are no longer statistically meaningful. The authors conclude the market
has become *"extremely fast and increasingly efficient."*

**(d)** More than **95%** of US firms announce outside regular trading hours — consistent with our
universe being 100% after-the-close.

---

## 2. What this does to our plan

### 🔴 Our Stage 4 design was aimed at the wrong resolution

We were heading toward 1–15 minute windows on **1-minute bars**. The literature says the entire
adjustment is finished in **seconds**, and that a mere 5-second delay erases the edge. **A 1-minute bar
cannot see this.** By the time our first bar closes, the event is long over.

Worse: our sample (2024–2026, and most of the 16-year extension for these companies) sits **entirely
inside the post-2016 regime the paper describes as efficient.**

### ✅ The asset we need already exists

`NQ_1s.csv` — **7.77 GB of 1-second NQ bars, 2010 → 2026**, on the server, with loaders already written
(`extended_data.load_1s`, `load_1s_windows`, used by `optimize/fundamentals/gc_costs.py`).

This project has already used second-resolution data to answer a question minutes could not: the
2025-03-07 payrolls bar went **down 46 points and up 141 points inside the same minute**, and a
1-minute OHLC candle cannot tell you the order.

### 🟡 The one question the literature leaves open

The JFE paper tests a strategy on **the announcing firm's own stock**. It documents that the index
co-jumps, but it does not test an **index-level** strategy.

> **Open question:** is the *index's* reaction to a mega-cap earnings announcement slower than the
> announcing stock's own reaction — an aggregation lag — and if so, does it survive costs?

The lead-lag literature is not encouraging: index futures typically lead the cash index by 0–5 minutes,
and such effects are *"short-lived because market participants quickly recognize and act on these
patterns."* But the specific case — **mega-cap earnings → Nasdaq-100 futures, at second resolution** —
does not appear to have been tested directly.

That is a narrow, theoretically-motivated, falsifiable hypothesis. **It is exactly the shape a 2–6
approach budget requires.**

---

## 3. Two of our own findings, independently confirmed

| our finding | literature |
|---|---|
| Announcement minutes move **4.98×** a matched normal minute | co-jump probability in the market index rises significantly around announcements |
| **BMO events are weak (1.36×)** vs AMC (~3×) | pre-open announcements show *"lower earnings response coefficients, lower volatility, lower trading volume, and greater PEAD"* than post-close |

The second is a pleasing result: we found it, flagged it as an unexplained oddity with n=18, then
declared it out of scope when the universe narrowed. The literature says it is a real and known
asymmetry — so the instinct to flag rather than dismiss was right.

---

## 4. What the earnings-announcement-premium literature does *not* give us

There is a well-documented **earnings announcement premium** — monthly strategies earning 7–18% a year,
Sharpe ratios above other anomalies, and option straddles that become profitable net of costs
*conditional on high ex-ante risk premia*
([NBER w13090](https://www.nber.org/system/files/working_papers/w13090/w13090.pdf),
[Quantpedia](https://quantpedia.com/strategies/earnings-announcement-premium)).

⚠️ **This is a cross-sectional stock strategy** — hold announcing stocks over their announcement window
— not an index-timing strategy. Our system trades **one instrument, one contract, and has no
position-sizing layer at all**, so it cannot express a cross-sectional portfolio. Citing that 7–18% as
encouragement for this workstream would be a category error, and it is recorded here explicitly as
**not applicable**.

---

## 5. Revised recommendation for Stage 4

**Do not** run a 1-minute directional search. The literature says the effect lives in seconds, our
period is post-2016, and Stage 2 says we could only detect a ~71% accurate rule anyway.

**Do, as a single pre-registered hypothesis:**

> **H1 — index aggregation lag.** Following a mega-cap earnings release, does NQ take measurably longer
> to reach its post-announcement level than the seconds-scale adjustment documented for the announcing
> stock? Measured on 1-second bars, with a pre-registered execution delay and realistic cost.

Design constraints that follow directly from this pass:

1. **1-second resolution, not 1-minute.** Non-negotiable — the effect is smaller than one bar.
2. **Pre-register an execution delay** (the paper's own break points: 0 s, 5 s, 10 s). A frictionless
   result is not evidence of anything tradeable.
3. **Split 2010–2015 vs 2016–2026.** If we find an edge only in the early period, that reproduces the
   published result and is a validity check on our pipeline rather than a discovery.
4. **The expected outcome is null.** Say so now. A null result here is a *good* outcome — it would be
   the first properly-powered null this workstream has produced, and it costs 1 approach out of 2–6.

---

## 6. Consequence for the 16-year extension, stated plainly

The 16-year **1-minute** collection now in progress is still worth having — it is the event list, and
event lists are reusable. But its value has shifted: the extra years are most useful for the
**2010–2015 versus 2016–2026 split** (a validity check against a published result), not for raising
power on a 1-minute directional test that the literature says should not work.

**The 1-second archive, not the 1-minute frame, is the asset this question actually needs.**

---

## Sources

- Christensen, Timmermann & Veliyev (2025), *Warp speed price moves: Jumps after earnings announcements*,
  **JFE 167** — [arXiv](https://arxiv.org/abs/2601.08962) ·
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X25000182) ·
  [Aarhus](https://pure.au.dk/portal/en/publications/warp-speed-price-moves-jumps-after-earnings-announcements)
- Xia, *What moves the market? Individual firms' earnings* —
  [AUT Centre for Financial Research](https://acfr.aut.ac.nz/__data/assets/pdf_file/0012/686748/2b-Jingjing-Xia.pdf)
- Frazzini & Lamont, *The Earnings Announcement Premium and Trading Volume* —
  [NBER w13090](https://www.nber.org/system/files/working_papers/w13090/w13090.pdf)
- *Earnings Announcement Premium* — [Quantpedia](https://quantpedia.com/strategies/earnings-announcement-premium)
- *The time-varying lead-lag relationship between index futures and the cash index* —
  [Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/1331677X.2022.2090404)
- *Do ETFs lead the price moves? Evidence from the major US markets* —
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521917301904)
- *Post–earnings-announcement drift* — [Wikipedia overview](https://en.wikipedia.org/wiki/Post%E2%80%93earnings-announcement_drift)
