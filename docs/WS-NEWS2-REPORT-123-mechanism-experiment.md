---
name: ws-news2-report-123-mechanism-experiment
description: "Testing an unverifiable finding from the other side: if provenance cannot be checked, does the effect at least BEHAVE like a real mechanism? The premise passes decisively, the discriminating test cannot resolve a realistic difference, and the power arithmetic says no achievable sample would change the decision."
type: report
date: 2026-08-15
issues: [111, 116, 117, 119, 120, 121, 123]
---

# #123 — attacking an unverifiable finding from the other side

**When provenance cannot be checked, behaviour still can.** This experiment asked whether Phase 2's
only capturable effect behaves the way a real mechanism would. The premise passed at ρ = +0.742. The
test that would have decided it could not resolve a realistic difference — **and the power arithmetic
says no achievable sample would change what we do.**

---

# PART 0 — THE ONE-PAGE VERSION

| | |
|---|---|
| **The problem** | the CL/API drift is real but its provenance is **unfalsifiable** (#123) |
| **The move** | stop asking *is the data clean?* and ask *does the effect behave like a mechanism?* |
| **A · premise** | ✅ **PASS** — the private preview forecasts the official number at **ρ = +0.742, p = 3.7e-51** |
| **B · anticipation** | ⚠️ marginal, and the **wrong sign** for the hypothesis |
| **C · discriminator** | ⚠️ right direction (**−0.284 → −0.149**) but **Fisher z p = 0.237** |
| ⛔ **Verdict** | **INCONCLUSIVE** — possible, not demonstrated |
| ⭐ **The arithmetic that ends it** | resolving C needs ~**4× the sample ≈ 21 years**, and even success leaves **57.4% vs a 71% break-even** |

---

# PART 1 — WHY THIS EXPERIMENT AT ALL

## 1.1 The dead end it works around

Phase 2 ended with exactly one capturable effect:

> **CL / API Crude Oil Stock Change** — post-jump drift, ρ = **−0.247**, p = 5.2e-05, n = **262**,
> permutation p = 0.001, matched-non-event control null, found by **two independent search designs**.

And its provenance **cannot** be verified: the American Petroleum Institute is a private trade
association, FRED and ALFRED carry nothing, and no public archive exists. A back-filled `actual` would
be **invisible**.

⭐ **So the usual move — gather better evidence about the inputs — is unavailable.** There is no better
evidence to gather.

## 1.2 The move: test the behaviour instead

If the effect is a **real mechanism**, it should behave in specific ways. If it is an **artefact of
unverifiable data**, it has no reason to.

⭐⭐ **And the setup is unusually clean**, because S4 searched *both* crude releases across all 612 pairs:

| release | organisation | timing | S4 result |
|---|---|---|---|
| **API Crude Oil Stock Change** | American Petroleum Institute — **private** | Tue 16:30 ET | ⭐ **the only survivor**, ρ = −0.247 |
| **EIA Crude Oil Stocks Change** | U.S. Energy Information Administration — **government** | Wed 10:30 ET | **null** |

**The effect is in the private preview and absent from the official release.** That asymmetry is what
makes the question answerable.

## 1.3 The two hypotheses, and why they are separable

| | hypothesis | prediction |
|---|---|---|
| **H1** | the preview genuinely moves expectations; the official number arrives **already priced** | the drift should be **anticipatory**, and should **weaken when the preview misleads** |
| **H2** | an artefact of a series whose provenance cannot be checked | **neither** |

⚠️ Everything below uses only **verified price data** (#121: 100.0000% overlap agreement, volume-profile
ρ = 1.000) and **both releases' published values**. **It does not require the provenance question to be
answerable** — which is the whole point.

---

# PART 2 — TEST A: THE PREMISE

> **Does the API number actually forecast the EIA number?**

**286 API releases matched forward to the next EIA release (≤ 3 days), 2016+.**

| | |
|---|---|
| **Spearman** | **+0.742** (p = 3.7 × 10⁻⁵¹) |
| **Pearson** | **+0.738** (p = 2.4 × 10⁻⁵⁰) |
| n | 286 |

## ⭐ Result: PASS, decisively

The private Tuesday preview is a **genuinely strong predictor** of Wednesday's official figure. So the
repricing story is **mechanically possible** — it is not a narrative invented to explain an awkward
result.

## ⚠️ One design point that mattered

The join is `merge_asof` **forward**: each API release is matched to the **next** EIA release, never a
prior one.

> **A backward match would have paired Tuesday's preview with LAST week's official number — and would
> have manufactured exactly the relationship test A is checking for.** The direction of a time-based
> join is not a detail here; it is the difference between a test and a tautology.

## ⚠️⚠️ And a limit that must be stated immediately

**A strong premise is not evidence for the mechanism.** Test A shows only that H1 is *possible*. It
does nothing whatever to distinguish H1 from H2 — both are perfectly consistent with API forecasting
EIA, because that is a fact about the two data series, not about why price drifts.

---

# PART 3 — TEST B: IS THE DRIFT ANTICIPATORY?

> **If Tuesday's drift is the market pre-pricing Wednesday's number, the EIA-day jump should be muted
> when the drift already moved the right way.**

| | |
|---|---|
| Pearson | **+0.115** (p = 0.053) |
| Spearman | +0.107 (p = 0.071) |
| n | 284 |
| MDE at 80% power | 0.166 |

## ⚠️ Marginal, and the sign is wrong for H1

The relationship is **positive**: the EIA-day jump goes the **same** way as Tuesday's drift. That is
**continuation**, not the pre-pricing H1 predicts, which would show attenuation or reversal.

⚠️ **But it is underpowered (MDE 0.166 against an observed 0.107) and sits either side of p = 0.05.**
**It should not be read in either direction**, and it is recorded here rather than either dropped or
promoted.

---

# PART 4 — ⭐⭐ TEST C: THE DISCRIMINATOR

> **On the weeks where the preview turned out to be misleading, does the drift weaken?**
>
> **An artefact has no reason to behave differently there. A repricing mechanism must.**

Split on the **pre-registered median** |API − EIA| = 2.289 — a median fixed in advance, not a threshold
chosen after looking at the outcome.

| | n | surprise → drift (Spearman) | p | MDE |
|---|---|---|---|---|
| **agreement** weeks — the preview was right | 143 | **−0.284** | **0.001** | 0.232 |
| **divergence** weeks — the preview misled | 141 | **−0.149** | 0.079 | 0.234 |

## The direction is exactly as H1 predicts

The drift is **roughly half as strong** on the weeks where the preview turned out to be misleading.
Read casually, that looks like a confirmation.

## ⚠️⚠️ And the test cannot resolve it

A **Fisher z test on two independent correlations**:

```
difference        +0.135   in the PREDICTED direction
Fisher z          +1.18
p                  0.237

Smallest difference this design could detect at 80% power: 0.336 in Fisher z
  ≈ a gap from ρ = −0.284 all the way to ρ = +0.044
```

> ⭐⭐⭐ **The design could only have resolved a gap so large it would have meant the drift REVERSING
> outright. A halving — the realistic prediction — was never within reach.**

**So test C is UNDERPOWERED, not answered.** Reporting "−0.284 versus −0.149" as *"the drift weakens
when the preview misleads"* would be **presenting an underpowered null as evidence** — precisely the
error the power-analysis rule exists to prevent, and precisely the error that once cost this project a
retracted workstream at 12% power.

---

# PART 5 — THE VERDICT, AND THE ARITHMETIC THAT ENDS IT

## 5.1 Verdict: INCONCLUSIVE

| question | answer |
|---|---|
| is the mechanism **possible**? | ⭐ **yes** — ρ = +0.742 |
| is it **demonstrated**? | ⛔ **no** |
| is the drift **explained**? | ⛔ **no** |
| is the series **verifiable**? | ⛔ **no** |
| is it **tradeable**? | ⛔ **no** — 57.4% vs 71% |

**The drift remains both unverifiable in provenance and unexplained in mechanism.**

## 5.2 ⭐ What would settle it — and why it will not be run

Resolving a difference of ~0.135 between two correlations at 80% power needs roughly **four times the
sample**:

| | |
|---|---|
| have | **286** matched weeks (2016 →) |
| need | ≈ **1,100** matched weeks |
| that is | ≈ **21 years** of weekly API releases |

⚠️ **And even a clean H1 confirmation changes nothing**, because the effect it would explain is:

| | |
|---|---|
| accuracy | **57.4%** [51.2, 63.4] |
| break-even (#111) | **71%** |
| shortfall at the optimistic end | **~8 points** |

> ⭐⭐ **The experiment that would settle the science cannot be run, and would not change the decision if
> it could.** That is the honest place to stop — not because the question is uninteresting, but because
> no achievable answer alters what we would do.

---

# PART 6 — WHAT WENT WELL, WHAT WENT WRONG

## What went well

1. ⭐⭐ **An unfalsifiable finding was attacked from a direction that *was* falsifiable.** Provenance was
   a dead end; behaviour was not. That reframing is reusable whenever a source cannot be checked.
2. ⭐ **The premise test was decisive and cheap** — ρ = +0.742 on n = 286 settles "is this even
   possible?" in one line.
3. **The join direction was specified and justified**, because a backward match would have manufactured
   the result.
4. ⭐⭐⭐ **The Fisher z test was computed rather than the point estimates being eyeballed.** −0.284
   versus −0.149 *looks* like a confirmation. It is p = 0.237.
5. **The power arithmetic was carried through to a decision** — 21 years, and it would not matter
   anyway — rather than ending on "more data would help".
6. **Test B's inconvenient sign was reported**, not quietly dropped for being off-hypothesis.

## What went wrong

1. ⚠️ **Test C was underpowered by design and I did not compute that before running it.** The
   pre-registration flagged the arms as "~130 each, underpowered for anything subtle" — but a flag is
   not a number. **Computing the detectable difference in advance would have shown the test could only
   resolve an outright reversal**, and the experiment could have been designed differently or declared
   futile before it ran.
2. ⚠️ **My reversal threshold (0.15) was arbitrary** and, by coincidence, sat just above the observed
   gap of 0.135. Had it been 0.13 the verdict string would have flipped while the statistics stayed
   identical. **A pre-registered threshold that is not derived from power is a coin toss with extra
   steps** — the Fisher z test is what actually decided this, and it should have been the pre-registered
   rule from the start.

## ⭐ The rules this produces

> 1. **Compute the detectable effect size BEFORE running a split-sample test, not after.** "Each arm is
>    ~130, this may be underpowered" is a worry; "this design can only resolve a gap of 0.336" is a
>    decision.
> 2. **Pre-register the STATISTIC, not a threshold on the point estimate.** A cutoff on an observed
>    correlation is arbitrary; a test with a stated α is not.
> 3. **When provenance is unfalsifiable, test the behaviour** — and say plainly which of the two you
>    have established.

---

# PART 7 — WHERE THIS LEAVES THE PROGRAMME

| | status |
|---|---|
| **Phase 1** (#115, #122) | ✅ closed — no tradeable entry across 8 instruments |
| **Phase 2** (#116) | ✅ closed — **market efficiency, not an edge**; 0 of 612 reach break-even |
| **#123** | ✅ closed out — unverifiable series, possible-but-undemonstrated mechanism |
| **Phase 3** (#117) | ⏳ open — **and it now has no viable target** |

## ⛔ Recommendation on #117

**Do not carry the CL/API result into Phase 3.** Latency work on it would be optimising the *reach*
toward something that **does not pay even if reached perfectly**.

⭐ Phase 2 established where a tradeable effect could still hide: **inside the release minute**, where
the input is unknowable in advance. And Christensen, Timmermann & Veliyev (2025) put price discovery
there at **milliseconds to seconds**, with a **5-second delay** removing significance.

> **So Phase 3's honest framing is not "can we get there faster?" but "is there anything reachable at
> all?" — and three phases of evidence now say no.**

## ⭐ The through-line, across three workstreams

| workstream | what was found | why it did not pay |
|---|---|---|
| **WS-EARN** | earnings move NQ **4.98×** | **magnitude, not direction** |
| **round 1 / S0** | gold responds at **5.5σ** | **62–63%** vs a 71% break-even |
| **Phase 2** | surprises explain the jump at **ρ −0.63** | **over before the input is knowable** |
| **#123** | a real post-release drift on crude | **57.4%** vs 71%, unverifiable, unexplained |

> **Four independent attacks. Four real, replicated effects. Not one of them tradeable.**
>
> ⭐ **That is a finding about the problem, not a failure of the method** — and it is a far more useful
> thing to know than another inconclusive maybe.
