---
name: ws-news2-phase2-s2-four-fixes-to-one-gate
description: "Phase 2 stage S2: probing all 643 pairs for statistical power before running any of them. Four successive fixes to the same gate, the diagnostic that found the root cause, and the pre-registration file that turned out never to have been committed."
type: report
date: 2026-08-15
issues: [94, 116, 118, 122]
---

# Phase 2 · S2 — four fixes to one gate

**S2 asks one question of all 643 pairs: *can this pair detect an effect if one is there?*** The answer
is yes for 612 of them. Getting to that answer required fixing the gate four times, and the sequence of
mistakes is more useful than the result.

---

# PART 0 — THE ONE-PAGE VERSION

| | |
|---|---|
| **What S2 is** | plant a synthetic effect in every pair and require the pipeline to find it |
| **Why before S3, not after** | a null from a pipeline that *couldn't* detect anything is **not a negative result** |
| **Result** | **612 PASS · 31 VOID (4.8%)** |
| ⭐ **And ~30 VOIDs are expected by chance** | so there is **no evidence any pair is genuinely underpowered** |
| ⭐⭐ **The confirming diagnostic** | the pass rate is **flat across sample size** (0.933–0.962) — as it must be |
| ⚠️⚠️ **Fixes required** | **four**, taking the VOID rate 94% → 59% → 46% → 4.8% |
| ⚠️ **A separate error it exposed** | the Phase 2 **pre-registration file had never been committed** |

---

# PART 1 — WHY THE PROBE RUNS BEFORE THE STUDY

With 643 pairs, most results will be nulls. And:

> **A null from a pipeline that could not have detected an effect is not a negative result. It is an
> absence of measurement — and in a summary table it is indistinguishable from the real thing.**

This is not hypothetical here. **Phase 1 already produced one**: RTY/verified came back "NEGATIVE" until
the probe showed that pipeline could only detect r ≥ 0.4, at which point the honest verdict became
**VOID**.

⭐ Running the probe **after** S3 would mean publishing a table of nulls and then retracting some of
them. Running it first means the VOIDs are never claimed as findings in the first place.

## The design

For each pair: plant a synthetic feature that **is the outcome plus noise**, calibrated to a range of
effect sizes, 25 draws each, and ask whether the pipeline recovers it at the pair's own resolution.

---

# PART 2 — ⚠️⚠️ FOUR FIXES TO THE SAME GATE

| # | VOID rate | the defect | the kind of mistake |
|---|---|---|---|
| 1 | **94%** | grid ceiling below most pairs' MDE | a **coding** mistake |
| 2 | **59%** | threshold set equal to the quantity being tested | a **statistics** mistake |
| 3 | **46%** | asking whether power *exceeds* nominal instead of whether it is *significantly worse* | a **wrong hypothesis** |
| 4 | **4.8%** | planting in Pearson, measuring in Spearman | **the root cause the other three were symptoms of** |

## 2.1 Fix 1 — the grid ceiling (94% VOID)

The probe used a **fixed** grid of effect sizes topping out at **r = 0.40**. The median pair here has an
**MDE of 0.412**.

So for **587 of 643 pairs there was nothing at or above the MDE to test**. The "detected at/above MDE"
set was empty, and the pair auto-failed.

**The dividing line was exactly the top of my grid:**

| | pairs | passing |
|---|---|---|
| MDE > 0.40 | 587 | **0** |
| MDE ≤ 0.40 | 56 | **41** |

**Fix:** the grid now adapts per pair, always including that pair's own MDE.

⚠️ 41/643 reads as *"this matrix is hopeless"* — a conclusion about the **data** produced entirely by a
constant in my code.

## 2.2 Fix 2 — a threshold equal to what it tests (59% VOID)

The probe required **≥80% detection** at the MDE. But **the MDE is *defined* as the effect size
detectable at 80% power.** A correctly-powered pair sits exactly on that line:

```
P(X ≥ 20 of 25 | true power = 0.80) = 0.617
⇒ a perfectly healthy pair fails 38% of the time BY CHANCE
```

**That is not a gate, it is a lottery.**

## 2.3 Fix 3 — the wrong hypothesis (46% VOID)

The patch was to judge at **1.25 × MDE**, where true power is ~0.95 and the test is no longer borderline.

⚠️ **This lowered the VOID rate without fixing the logic.** It moved the goalposts to an arbitrary place
and left the underlying question wrong.

⭐ **The right question is not *"is this pipeline better than its nominal power?"* but *"is it
significantly worse?"*** — is the measured detection rate incompatible with 80%? That is a one-sided
binomial test, and it fires only when something is actually wrong:

```
P(X ≤ 16 | 25, 0.80) = 0.047   ⇒ fail at ≤ 16 of 25
P(X ≤ 17 | 25, 0.80) = 0.109   ⇒ 17 IS consistent with 80% power
```

## 2.4 ⭐⭐ Fix 4 — the root cause, found by a pattern running backwards

After fix 3 the VOID rate was still 46%, which was still too high to believe. The tell was not the
*rate* — it was the **shape**:

| | pairs | passing | median MDE |
|---|---|---|---|
| n 200–600 | 56 | **17** | **0.206** |
| n ≤ 60 | 47 | **23** | **0.595** |

**The best-powered pairs were failing most.**

> ⭐⭐⭐ **Power at the MDE is 80% by definition at every sample size. So the pass rate must be FLAT
> across n. A gate whose failure rate runs opposite to power is not measuring power.**

That inversion pointed straight at a metric mismatch: the probe **planted an effect calibrated in
Pearson terms on the raw outcome values**, then **measured Spearman**. Those are not the same number.

### Measured recovery — achieved Spearman ÷ planted target

| series | n | excess kurtosis | plant on **values** | plant on **ranks** |
|---|---|---|---|---|
| PCE Price Index YoY | 49 | 2.0 | **0.76 – 0.92×** | **1.01 – 1.09×** |
| EIA Crude Oil Stocks | 548 | 4.4 | **0.90 – 0.95×** | **0.98 – 1.02×** |

**The probe was quietly testing a smaller effect than it claimed, and reporting the shortfall as the
pipeline being underpowered.**

**Fix:** plant on **standardised ranks**. Spearman is a rank statistic; the planted effect has to live
in the same space as the measurement.

⚠️ Note the attenuation was **roughly uniform across kurtosis** — so it was not a fat-tail artefact
affecting some pairs. It was a systematic mis-calibration affecting all of them, which is precisely why
it showed up as a *shape* problem rather than as scatter.

---

# PART 3 — THE RESULT

| | |
|---|---|
| pairs probed | **643** |
| **PASS** | **612** |
| **VOID** | **31 (4.8%)** |
| **expected VOIDs by chance alone** | **~30** |

> ⭐ **The observed VOID count is indistinguishable from the false-positive rate of the test itself.**
> There is **no evidence any pair is genuinely underpowered.** The VOID list means *"not established"*,
> never *"these 31 are broken."*

## ⭐⭐ The flatness, which is the real confirmation

| sample size | pairs | passing | rate | median MDE |
|---|---|---|---|---|
| n ≤ 60 | 47 | 45 | **0.957** | 0.595 |
| 60–80 | 75 | 70 | **0.933** | 0.527 |
| 80–120 | 177 | 167 | **0.944** | 0.471 |
| 120–200 | 288 | 277 | **0.962** | 0.409 |
| 200–600 | 56 | 53 | **0.946** | 0.206 |

A spread of **0.029** across a 10× range of sample size. **This is the diagnostic that both exposed the
bug and confirms the fix** — the same statistic, read twice.

## By instrument

| | CL | ES | GC | HG | NG | NQ | RTY | SI |
|---|---|---|---|---|---|---|---|---|
| pass | 81 | 79 | 77 | 75 | 77 | 76 | 67 | 80 |
| void | 1 | 3 | 5 | 7 | 4 | 6 | 3 | 2 |

---

# PART 4 — ⚠️ THE PRE-REGISTRATION THAT WAS NEVER COMMITTED

S2 crashed on the server:

```
FileNotFoundError: .../optimize/fundamentals/phase2_pairs.csv
```

**That file is not a working file. It IS the Phase 2 pre-registration** — it fixes which 643 pairs may
be tested and at what α.

The repository's blanket `*.csv` ignore rule had caught it, so it existed on **one machine only** — while
I had already told the owner it was *"committed as `phase2_pairs.csv`"* and that the pre-registration
was *"machine-checkable rather than a number in a comment."*

## ⚠️⚠️ Why this is worse than the case it mirrors

This is the **#94 inversion** — a deliverable that lives locally and vanishes from the repo. The
earnings-data version of it cost reproducibility. This version is worse:

> **A pre-registration that can be silently regenerated with different contents is not a
> pre-registration at all.** The entire purpose of fixing the matrix in a file was that it could not
> drift.

## ⭐ And it exposed a blind spot in the ledger itself

`PHASE2-MATRIX-221-DECIDABLE` had been **passing the whole time by reading an untracked file**. The
ledger verifies a number against a file — but never checked that the file is **under version control**.

That is a general weakness, not a one-off: any claim can be satisfied by a local artefact that no one
else can reproduce.

---

# PART 5 — WHAT WENT WELL, WHAT WENT WRONG

## What went well

1. ⭐⭐ **The probe ran before the study, not after.** Had S3 run first, some of its nulls would have
   been published and then retracted — which is the exact loop this whole verification programme exists
   to break.
2. ⭐⭐⭐ **The root cause was found by a *shape*, not a *number*.** Three successive threshold
   adjustments each lowered the VOID rate without fixing anything. Only the inverted pass-rate-versus-n
   pattern identified the real defect.
3. **No fix was tuned toward a target pass rate.** Each was diagnosed from a symptom. Tuning a gate
   until the "right" fraction of data passes is itself a defect — and would have buried the metric
   mismatch under a plausible number.
4. **The result is stated against its own chance expectation**, so 31 VOIDs are not reported as 31
   broken pairs.
5. **A crash surfaced a governance error** the tests could not: the pre-registration was untracked.

## What went wrong

1. ⚠️⚠️ **Four fixes to one gate in one stage.** The first three each *looked* like progress — the VOID
   rate fell every time — while the underlying defect was untouched. **A metric moving in the right
   direction is not evidence that the cause has been found.**
2. ⚠️ **I published a pre-registration that was not under version control**, and described it as
   committed and machine-checkable. It was neither.
3. ⚠️ **This is the fifth and sixth cry-wolf failure in this project** (#94's dirty-tree preflight,
   #118's retraction scanner, #121's acceptance gate, #122's single-draw probe, and now S2 twice over).
   The pattern is consistent enough to state as a rule.

## ⭐ The rule this produces

> **When a gate rejects most of its subjects, read it as evidence about the GATE first — every time.**
> In five of five occurrences in this project, a high rejection rate on real data has been the gate's
> fault, not the data's.
>
> And when a gate's failures **correlate with the thing it claims to measure in the wrong direction**,
> that is not noise — it is a specification error, and no threshold adjustment will fix it.

---

# PART 6 — ⚠️ WHAT S2 DOES NOT ESTABLISH

Stated explicitly, because an unstated limit becomes an assumed guarantee:

- **It tests POWER, not CORRECTNESS.** A pipeline that reliably detects a planted effect can still be
  measuring the wrong thing entirely — that is S0's job (outcome anchor) and S1's (feature leakage), and
  a defect in either is **invisible here**.
- It ran on **one outcome** (the open-anchored 15-minute return). A pair could be well powered there and
  thin at another horizon.
- The planted effect is **monotone**, so S2 says nothing about power against a **threshold** effect.
- **The 31 VOIDs cannot be distinguished from chance**, so the list is a caution, not a diagnosis.

---

# PART 7 — WHAT S2 HANDS S3

| | |
|---|---|
| **612 powered pairs** | the inference set |
| **31 VOID pairs** | reported as **unanswered**, never pooled into a null |
| **α = 0.000078** | fixed in `phase2_pairs.csv`, now actually committed |
| ⚠️ **One primary test per pair** | the α was computed as 0.05/643, which assumes **one test per pair** — so S3 must designate a single primary feature and outcome, with everything else explicitly exploratory |

⚠️ **That last point is a live constraint, not a formality.** Four features × seven outcomes per pair
would be 18,004 tests, and the pre-registered α does not cover them. **S3 pre-registers `surprise` against
the open-anchored 15-minute return — the same outcome S2 probed — as the single primary test**, and
everything else is reported as exploratory and excluded from inference.

**Next: S3 — run the 612 powered pairs.**
