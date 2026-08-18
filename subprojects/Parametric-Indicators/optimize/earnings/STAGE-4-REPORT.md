---
name: ws-earn-stage-4-report
description: "WS-EARN Stage 4 (#113) — H1 index aggregation lag tested on 1-second NQ bars across 783 earnings events, 2010-2026. REJECTED: 0 of 8 pre-registered cells pass, in every arm. The first properly-powered null this workstream has produced."
type: report
date: 2026-08-06
issue: 113
workstream: earnings
verdict: H1 REJECTED — null result, as predicted
---

# WS-EARN Stage 4 — H1 rejected

**Pre-registered in #113 before the data existed. Predicted outcome: all eight cells fail. They did.**

---

## The result

| arm | events | cells passing |
|---|---:|---:|
| **A — all events** (headline) | 783 | **0 of 8** |
| **B — flagged outliers excluded** (robustness) | 732 | **0 of 8** |
| **Dumb control** — non-announcement, time-of-day matched | 783 | **0 of 8** |
| Validity check — era 2010–2015 | 177 | 0 of 8 |
| Validity check — era 2016–2026 | 421 | 0 of 8 |

**H1 is rejected.** After a mega-cap earnings release, NQ does not continue in the direction
established in the first seconds by enough to pay for the trade — at any delay from 5 to 60 seconds,
at either hold, in either era.

### Arm A in full (the pre-registered headline)

| delay | hold | n | n_eff | gross $ | net $ | t | win % |
|---|---|---:|---:|---:|---:|---:|---:|
| 5 s | 60 s | 519 | 512 | −26.43 | −35.93 | −2.99 | 45.3% |
| 5 s | 300 s | 519 | 477 | −28.72 | −38.22 | −1.57 | 49.1% |
| 10 s | 60 s | 555 | 549 | −20.59 | −30.09 | −2.65 | 50.5% |
| 10 s | 300 s | 555 | 512 | −39.02 | −48.52 | −2.14 | 45.0% |
| 30 s | 60 s | 579 | 568 | −8.74 | −18.24 | −1.37 | 49.1% |
| 30 s | 300 s | 579 | 533 | −42.36 | −51.86 | −2.30 | 46.8% |
| 60 s | 60 s | 598 | 580 | **+15.88** | +6.38 | 0.58 | 49.7% |
| 60 s | 300 s | 598 | 550 | −15.58 | −25.08 | −1.22 | 49.5% |

**Win rates 45–51%.** Coin flips. The single positive cell (60 s/60 s) reaches t = 0.58 — nowhere near
the 2.734 threshold, and it is the cell you would expect to look best by chance out of eight.

---

## ⚠️ The negative t-statistics are NOT a reversal edge

Several cells show |t| > 2.734 in the **negative** direction, and the dumb control shows them too
(30 s/60 s reaches t = −3.68). It would be easy — and wrong — to report that as a discovered
mean-reversion effect.

Testing the **gross** return, before costs, settles it. An edge must exist before you pay for it:

| set | cell | gross $ | **t (gross)** | t (net) |
|---|---|---:|---:|---:|
| Arm A | 5 s/60 s | −26.43 | **−2.20** | −2.99 |
| Arm A | 10 s/60 s | −20.59 | **−1.82** | −2.65 |
| Arm A | 60 s/60 s | +15.88 | **+1.44** | 0.58 |
| **Control** | 30 s/60 s | −1.79 | **−0.58** | **−3.68** |
| **Control** | 60 s/60 s | +0.32 | **+0.11** | **−3.08** |

**Maximum |t_gross| anywhere is 2.20 — below the threshold.** There is no edge in either direction.

The control rows are the giveaway: gross t of −0.58 and +0.11 are *nothing at all*, yet their net
t-statistics are −3.68 and −3.08. That is entirely the fixed $9.50 round trip divided by the small
variance of quiet non-announcement periods.

> **A significant negative net-t means "you paid costs and earned nothing", not "you found a reversal."**
> Without the dumb control this would have been reportable as a t = −3.68 finding.

---

## The validity check, and its honest limit

| era | cells passing | note |
|---|---:|---|
| 2010–2015 | 0 of 8 | the period the literature says an edge existed |
| 2016–2026 | 0 of 8 | the period the literature says it closed |

Christensen, Timmermann & Veliyev (2025, *JFE* 167) found a post-announcement strategy on the
**announcing stock** worth 2.30%/trade frictionless in 2008–2015, collapsing to insignificant after
2016. We do not reproduce an early-era edge **on the index**.

⚠️ **This does not confirm our pipeline, and that was recorded before the run.** Pre-2019 after-hours
1-second density is only **24–42%** (vs 75–86% post-2022), so a 5-second measurement in 2013 reads a
price that may be several seconds stale. A null in the early era is **uninformative about our code**.
It is also not surprising: the published edge was on the *announcing stock*, not the index, so there is
no strong reason to expect it here.

---

## What this does and does not establish

**Establishes:**

- No tradeable directional continuation in NQ after a mega-cap earnings release, at 5–60 s delays,
  60 s or 300 s holds, across **783 events and 16 years**.
- The result holds with outliers excluded, in both eras, and the control behaves as a control should.
- The negative cells are cost drag, not a reversal signal — demonstrated, not asserted.

**Does not establish:**

- That earnings announcements don't move NQ. **They plainly do** — 4.98× normal volatility at the
  announcement minute (Stage 2), independently confirmed by the literature (#112). **Volatility is not
  direction.**
- That no edge exists anywhere in this space. It rules out **one specific, well-motivated hypothesis**,
  which is what one pre-registered test can do.
- Anything about pre-market announcements, removed with WMT/ASML when the universe narrowed.
- Anything about cross-sectional stock strategies — our system trades one instrument, one contract,
  with no sizing layer.

---

## Budget consumed

Stage 2 established the sample supports **2–6 independent approaches** at a realistic 55–60% accuracy.
This spent **one**. Five at most remain, and any further test must be pre-registered the same way.

⚠️ **The "try 2,000 approaches" plan remains off the table.** At 2,000 attempts the best result from
pure noise reaches t = 3.45; nothing here comes close, and a search that size would have manufactured
an apparent winner from exactly the coin-flip data above.

---

## Caveats carried through

- ⚠️ **#110 criterion C4 — the human TradingView check — has still not returned.** At 1-second
  resolution timestamp accuracy matters more than anywhere else in this workstream. The null is
  *robust* to timestamp error in one direction (error destroys edges, it does not create them), so a
  null is the safe direction to be wrong in — but a *positive* result would have needed C4 first.
- ⚠️ 95 of 783 events had no usable 1-second window; 688 were covered.
- ⚠️ Today's top-12 applied back to 2010 is a survivorship/look-ahead bias. Early events involve
  companies too small at the time to move the index, which biases toward **null**.
- ⚠️ INTC's ~7-minute filing lag is uncorrected; it contributes noise, again toward null.

---

## Why a null is worth having

This workstream's sibling ran 8 pre-registered criteria and passed 1. The value there was not the pass
— it was that the failures were on the record and believable.

This is the same thing: a hypothesis chosen from the literature, budgeted in advance, tested once, with
the prediction filed before the run. **The prediction was correct**, which is a small thing on its own —
but it means the apparatus is calibrated rather than hopeful.

Eleven silent data defects had to be found and fixed to get a trustworthy 783-event table. Any one of
them left in place would have produced a *different* null — and an untrustworthy one.
