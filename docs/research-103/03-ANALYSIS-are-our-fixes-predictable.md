---
name: issue-103-are-our-fixes-predictable
description: "#103 Q2 — measured from our own record: of 8 pre-registered criteria, 1 passed. We have no predictive model of which search fix will help, and the one pass did not generalise."
type: analysis
date: 2026-08-03
issue: 103
---

# #103 Q2 — are the effects of our fixes linear? Are they predicted?

The question was: *"is the effect of the fixes linear — is it proved — is it predicted, at least with a
positive win score?"*

We can answer this without any literature, because we have been pre-registering criteria. That record is
the evidence.

---

## 1. Every pre-registered criterion, and how it went

| # | issue | criterion, declared before the run | result |
|---|---|---|---|
| 1 | #88 R1 | improvements ≥ 2× control, 400 evals | **FAIL** — 1/8 seeds |
| 2 | #88 R2 | improvements ≥ 2× control, 4,000 evals, ≥5/8 | **FAIL** — 0/8, and *inverted* (0.39×) |
| 3 | #88 R2 | comparisons ≥ 2× (secondary) | **FAIL** — 0/8 |
| 4 | #88 R3 | best champion-zone elite, ≥6/8 | **PASS** — 8/8, +23.1% |
| 5 | #88 R4 | same, cold start | **FAIL** — 3/8 |
| 6 | #88 R5 | best-anywhere, cold, fresh seeds | **FAIL** — 5/8 |
| 7 | #101 | best elite with stepping stones, ≥6/8 | **FAIL** — 1/8, peak *worse* |
| 8 | #99 | conditional parameter drawing — adopt? | **FAIL** — do not adopt |

**1 pass in 8. And the single pass did not generalise** — it held warm-started (#88 R3) and failed both
cold replications (R4, R5).

Add the one explicit *prediction* I recorded rather than just a threshold:

> #88 round 5 pre-registration: *"I expect this to pass."* → **it failed.**

---

## 2. What that says about Q2

### Is the effect linear?

**Unanswerable as posed, because the effects are not reliably positive.** Linearity is a question about
how benefits compose; we do not have a set of established benefits to compose. Of the four scaling
repairs shipped (#81 genome shape, #88 archive axis, #89 budget call sites, #101 parent pool):

- #88 is demonstrated **only under warm start**,
- #101 is **refuted** — it made the peak worse while doing exactly what it was designed to do,
- #81 and #89 were correctness repairs whose *outcome* benefit was never isolated at all.

### Is it proved?

No. One narrow, condition-dependent pass.

### Is it predicted with a positive win score?

**No — measured at 1/8.** We are not selecting fixes that work; we are proposing plausible fixes and
discovering afterwards that most of them do not help. That is an honest description of a programme
operating without a model of the thing it is modifying.

---

## 3. The interesting part: the failures were informative even though the fixes were not

Three of the failures taught more than the pass did:

| failure | what it taught |
|---|---|
| #88 R2 *inverted* | **a counter that rises as the thing gets worse is a wrong instrument, not a weak one** — an archive of junk is easy to improve |
| #88 R4 | **a default you did not choose is a condition of your experiment** — 48 runs were warm-started by omission |
| #88 R5 | **fresh seeds are not a formality** — 8/8 at +55% became 5/8 at −4% |
| #101 | **widening the parent pool trades peak quality for coverage** — the mechanism worked and the outcome got worse |

So the process is producing real knowledge at a good rate. What it is *not* producing is search
improvements.

---

## 4. What this implies for #103

A 1-in-8 hit rate on carefully-reasoned interventions is itself evidence about the object being
modified. Two readings, and they are distinguishable:

**Reading A — we keep picking the wrong fixes.** Then better diagnosis raises the hit rate, and the
programme continues.

**Reading B — the search is not limited by any of the things we have been fixing.** Then the hit rate
stays near zero whatever we fix next, because the binding constraint is elsewhere: coverage is 10^−32 at
any budget, and there are **10^8.4 candidate structures per decision bar** (part 1).

**Reading B predicts exactly what we observe**, including the shape of the failures: #101's fix worked
mechanically and still lost; #88's win evaporated when the seed was removed. Both are what you would see
if the outcome is dominated by something other than search efficiency.

That does not prove Reading B. It does mean the next experiment should be aimed at **distinguishing A
from B**, not at another fix — which is what #103's Q1/Q3 and the #104 rank-correlation test are for.

---

## 5. The honest summary for Q2

| sub-question | answer |
|---|---|
| are the effects linear? | **cannot be asked yet** — there is not a stable set of positive effects to compose |
| is it proved? | **no** — 1 pass in 8, and that one is condition-dependent |
| is it predicted with a positive win score? | **no — measured 1/8**, plus one explicit prediction that was wrong |
| is the programme producing value? | **yes, but as knowledge, not as search improvement** — the failures were the informative part |
