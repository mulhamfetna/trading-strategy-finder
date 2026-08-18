# Issue #4 — Does gold really move *against* economic news? · **OPEN, NOT STARTED**

**Date:** 2026-07-29 · **Status:** untouched. This report describes what it is and how to do it properly.

---

## 1. What was found (and why it isn't trusted yet)

When US economic data is released, there is a "surprise": the gap between what economists predicted and
what the number actually was.

Looking back over 17 years, an earlier study (GC-01) found that **gold tends to move in the *opposite*
direction to the surprise** — a better-than-expected economy nudges gold *down*, a worse one nudges it
*up*. Which is economically sensible: gold is the thing people buy when they're nervous.

The evidence looked unusually good:

| | |
|---|---|
| rank correlation | **−0.193** |
| how many years it held | **15 of 16** |
| sample | n = 866 releases, 99% statistical power |

**And yet it is not tradeable.** Acting one second after the release earned **+$49.90 per event**
(t = 3.40) — a real, statistically solid effect — but it **dies completely once you allow 5 ticks of
slippage**. It is real and too small to touch.

⭐ **The genuinely valuable lesson from GC-01 was a methods lesson:** the ordinary correlation
(Pearson) showed **−0.012 — essentially nothing**. The rank-based correlation (Spearman) showed
**−0.193**. Fat-tailed financial data hides real relationships from ordinary correlation. *Always run
both.*

## 2. So why does this issue exist?

Because the finding is **post-hoc** — we went looking through history and found a pattern. That is the
easiest way in the world to fool yourself: search enough history and patterns appear by luck alone.

The cure is a **pre-registered forward test**: write down the exact prediction **before** the data
exists, then wait for new releases and check. No adjusting afterwards.

The prize isn't a trading strategy — we already know it's untradeable at that size. The prize is a
**directional prior**: a trustworthy statement of the form *"when a big macro surprise lands, gold's
short-term direction is more likely to be X."* That could inform position sizing or a veto, even if it
can't be traded on its own.

## 3. What "pre-registered" must mean here (write this down FIRST)

Before any new data is examined, commit in writing to:

1. **Which releases count** (e.g. Non-Farm Payrolls, CPI, FOMC) — the exact list, fixed.
2. **How "surprise" is computed** — the exact formula and data source.
3. **The measurement window** — e.g. gold's return from 1 second to 30 minutes after release.
4. **The statistic and the threshold** — e.g. *Spearman rank correlation, one-sided, p < 0.05*.
5. **How many events before judging**, decided in advance from a power calculation.
6. **What counts as failure** — stated as plainly as what counts as success.

> ⚠️ The single most important rule: **no changing any of the above once the data starts arriving.**
> The moment the window or the release list is adjusted to improve the result, this becomes another
> post-hoc study and the whole exercise is worthless.

## 4. Cost

**Cheap.** The tooling exists from the fundamentals workstream (the release calendar, the surprise
computation, the gold data). The real cost is **calendar time** — you must wait for genuinely new
releases to accumulate.

## 5. Why it is worth doing anyway

Nearly everything in this project's research history has come back **negative**: scheduled macro news is
already priced in, the session-of-day edge isn't tradeable, regime-switching didn't pay, volatility
gating didn't help. This gold result is one of the few effects that **replicated across years**.

Even confirming it is untradeable-but-real has value: it is a rare piece of *structure* in a project
where the recurring finding is "the fat per-trade tail defeats every edge."

## 6. What went well / what went wrong

- **Went well:** the original study was properly powered (n=866, 99% power) and honest about the effect
  dying under realistic costs — it did not oversell itself. The Pearson-vs-Spearman discovery is a
  permanent methods upgrade for the whole project.
- **Went wrong:** nothing yet — but note this issue has sat open since 21 July while being described as
  "cheap". It is now the **only** open issue with no dependencies, so if you want a clean win it is the
  one to start.
