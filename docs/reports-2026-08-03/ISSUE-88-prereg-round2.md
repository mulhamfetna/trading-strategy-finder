---
name: issue-88-prereg-round2
description: Pre-registration for the second #88 A/B — same primary criterion, at a budget where the archive is actually exercised. Written and committed BEFORE the run.
type: pre-registration
date: 2026-08-03
issue: 88
---

# #88 round 2 — declared before the run

**This file is committed before the run starts.** Its purpose is to fix what counts as a pass while the
answer is still unknown. Round 1's result stands recorded in `ISSUE-88-measured-result.md` and is not
withdrawn.

---

## 1. What round 1 showed

The pre-registered criterion — **improvements ≥ 2× control** — **failed: 1 of 8 seeds, median 1.55×.**

Two facts came out of it that make a second round worth running:

**a) At 400 evaluations the archive is barely exercised.** Measured (4 seeds, medians):

| | control | treatment |
|---|---:|---:|
| barely traded (<5 trades/fold) | 99 (25%) | 90 (23%) |
| lost money | 36 (9%) | 34 (8%) |
| drew down > 25% of profit | 140 (35%) | 148 (37%) |
| **discarded before reaching a niche** | **274 (69%)** | **272 (68%)** |

So ~130 of 400 evaluations reach the archive. 400 was never justified as sufficient — it is the
documented default, nothing more.

**b) The registered metric is biased against the treatment, and this is derivable without the data.**

*Improvements* counts only the comparisons the newcomer **wins**. But the two arms have systematically
different incumbents:

- **Control**: 1,494 niches, ~82 first-fills, so a typical incumbent is a **random first arrival** —
  easy to beat.
- **Treatment**: 81 niches, ~24 first-fills, so a typical incumbent has **already survived several
  challenges** — hard to beat.

The treatment therefore does more comparing while winning a *smaller share* of them. Counting only wins
understates exactly the thing the fix was meant to produce. That is a property of the design, not a
post-hoc excuse — but it was my error to register it, and the failed result stands.

---

## 2. The run

**NQ 4h · 1-minute indicator frame · 8 seeds (1–8) · `--evals 4000` per arm · control = `ind_bucket`
replaced by the identity, i.e. the pre-#88 raw-count axis · both arms in one process.**

10× the round-1 budget. At ~10 s per 400-eval arm on the server this is ~30 minutes total.

**Nothing else changes.** Same bootstrap, same mutation operator, same feasibility rule, same evaluator.
The axis remains the only difference between arms.

---

## 3. What counts as a pass — declared now

**PRIMARY — unchanged from round 1, so that a pass is a pass on the criterion I originally set:**

> **improvements ≥ 2× control, in a majority of the 8 seeds (≥5/8).**

The seed-majority requirement is added because round 1 proved a single seed can produce a false pass —
seed 1 alone read 2.06× while the median was 1.55×. It makes the criterion **harder**, not easier.

**SECONDARY — reported alongside, with a disclosure:**

> comparisons per evaluation (`improvements + rejected`) ≥ 2× control, in ≥5/8 seeds.

**Disclosure: I have already seen this quantity at 400 evaluations** — control 46, treatment 110, ~2.4×.
So it is *not* a blind prediction and cannot carry the verdict on its own. It is listed because it is
the metric that directly answers "does the archive compare things?", and stating it in advance is better
than introducing it after the fact.

**If the primary fails again, #88 does not get called a win.** The shape fix stays (it is correct on its
own terms and the tests pin it), the report says the criterion failed twice, and the open question moves
to #101 — where 68% of the search budget is being discarded.

---

## 4. What this run cannot settle

- It does not validate any earlier MAP-Elites result — those came from the broken shape (**#90**).
- It does not compare MAP-Elites against the ordinary optimizer.
- It does not address **#101**: ~68% of evaluations are discarded in *both* arms, so a larger budget
  buys proportionally more waste. This run measures the axis, not the waste.
