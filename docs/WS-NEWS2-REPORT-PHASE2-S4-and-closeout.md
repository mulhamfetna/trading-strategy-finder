---
name: ws-news2-phase2-s4-and-closeout
description: "Phase 2 stage S4 and the phase closeout: a systematic search of the only window a trader can actually reach returns exactly one effect out of 612, it is the same pair an earlier follow-up found, and it falls ~14 points short of paying. Includes the full S0-S4 record and the pattern now visible across three workstreams."
type: report
date: 2026-08-15
issues: [109, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122]
---

# Phase 2 · S4 and closeout — the capturable window

**S3 found large effects that cannot be traded. S4 asked whether anything survives into the window a
trader can actually reach. The answer is one pair out of 612, and it loses money.**

---

# PART 0 — THE ONE-PAGE VERSION

| | |
|---|---|
| **The question S4 asks** | is there **any** effect in the window a reactive trader can reach? |
| **Pairs searched** | **612** powered, all of them |
| **α** | **0.05/612 = 0.0000817** — its own family, not S3's budget |
| **Survivors** | **1** — CL / API Crude Oil Stock Change |
| ⭐ **And it is the same pair S3's follow-up found** | two independent search designs agree |
| ⭐ **611 of 612 are null** | matching round 1 (t = 0.52) and S0 (p ≥ 0.46) |
| ⚠️⚠️ **Accuracy** | **57.4% [51.2, 63.4]** against a **71%** break-even |
| ⛔ **Tradeable edge** | **EXCLUDED at 95% across the entire matrix** |
| ⚠️ **And the survivor** | is the **least provenance-verified series in the study** |

---

# PART 1 — WHY S4 EXISTED AT ALL

## 1.1 What S3 left unresolved

S3 established two things:

1. The surprise explains the **release-minute jump** extremely well — ρ up to **−0.63**, p to
   **1.9 × 10⁻¹⁰**, on 23 of 612 pairs, with both controls null.
2. **That is not tradeable.** `surprise = actual − forecast` cannot be known before the release, and
   the jump is finished by the time it can be.

So the only question that could still produce something was:

> **Does anything survive into the post-jump window — the earliest price a reactive trader can obtain?**

## 1.2 ⚠️ Why it needed a pre-registered test rather than a footnote

S3 answered that question **as an unplanned follow-up on 23 pairs**, and found one hit (CL / API Crude
Oil).

**That is not a systematic search.** Looking only where an effect was already found, and then reporting
what turns up, is the classic route to an artefact — and it would have left the programme's *only*
capturable finding resting on an unplanned check of a subset.

⭐ So S4 searched **all 612**, with a **pre-registered decision rule and its own correction**.

## 1.3 ⚠️ Why the α is separate

S4 is **612 new tests on a different outcome**. Reusing S3's α = 0.000078 would be **spending the same
false-positive budget twice**.

The two families are corrected independently, and **neither number is ever quoted for the other**.

| stage | outcome | α |
|---|---|---|
| S3 | open-anchored 15 min (**jump-inclusive**) | 0.05/643 = **0.000078** |
| **S4** | **close-anchored 15 min (post-jump)** | 0.05/612 = **0.0000817** |

## 1.4 The prediction, filed before the run

> **I expected this to be negative almost everywhere.** Round 1 measured gold's post-print residue at
> **t = 0.52** — noise — and S0 reproduced exactly that: every close-anchored measure came back
> **p ≥ 0.46** while the jump-inclusive ones ran **p < 0.0001**.
>
> **If CL/API survived a systematic search with its own correction, that would be meaningfully stronger
> than finding it in a follow-up. If it did not, the only capturable candidate disappears and that
> should be said plainly.**

---

# PART 2 — THE RESULT

## 2.1 One survivor out of 612

| | |
|---|---|
| pairs tested | **612** |
| clear α | **1** |
| ⭐ confirmed — permutation **and** matched-non-event control null | **1** |
| rejected by controls | 0 |
| median rule accuracy across all 612 | **53.9%** |
| **pairs whose 95% accuracy LOWER bound reaches 71%** | **0** |

### The survivor

| instrument | release | n | Spearman | p | permutation | control | accuracy [95% CI] |
|---|---|---|---|---|---|---|---|
| **CL** | **API Crude Oil Stock Change** | **262** | **−0.247** | 5.2e-05 | **0.001** | null | **57.4%** [51.2, 63.4] ⚠️ |

## 2.2 ⭐ Why the agreement between two search designs matters

| | how CL/API was found | scope |
|---|---|---|
| **S3** | re-measuring 23 already-significant pairs, **after the fact** | 23 pairs, unplanned |
| **S4** | **pre-registered systematic search**, own α | **612 pairs** |

> **If the two designs had disagreed, one of them was fishing.** A hit that appears only in the
> after-the-fact look is a selection artefact; a hit that appears only in the systematic search would
> suggest the follow-up was mis-specified. **They agree — so this is a real post-release drift.**

## 2.3 ⭐ And 611 of 612 are null — three independent measurements of the same emptiness

| source | measurement of the post-print window | verdict |
|---|---|---|
| **round 1** | post-print residue **t = 0.52** | noise |
| **S0** (this phase) | every close-anchored measure **p ≥ 0.46** | noise |
| **S4** | **611 of 612 pairs** fail to clear α | noise |

Three different samples, three different designs, one answer. **The post-jump window is empty almost
everywhere**, and that is now established rather than assumed.

---

# PART 3 — ⚠️⚠️ IT STILL DOES NOT PAY

| | |
|---|---|
| CL/API directional accuracy | **57.4%** |
| 95% confidence interval | **[51.2, 63.4]** |
| required to cover costs (#111) | **71%** |
| shortfall at the point estimate | **~14 points** |
| **shortfall even at the optimistic end of the interval** | **~8 points** |

> ⛔ **A tradeable edge is EXCLUDED at 95% across the entire matrix — all 612 pairs, both windows,
> both stages.**

## ⭐ Why the interval is doing the real work here

S3 produced **seven** pairs whose *point estimate* exceeded 71%, including NQ Inflation Rate MoM at
**71.7%** with **p = 1.9e-10**. Reported without an interval, that reads as a trading system.

**Not one of them had a 95% lower bound that reached the break-even.** The same is true here.

> **"71.7% accuracy, p = 1.9 × 10⁻¹⁰" and "not established as tradeable" are both true of the same
> number.** The interval is what keeps those two facts from collapsing into each other.

---

# PART 4 — ⚠️ THE COINCIDENCE WORTH NAMING

**The single capturable finding in the entire programme sits on the least-verified data in the study.**

| | |
|---|---|
| #119 verified `actual` is a first print | on **4 series** — NFP, CPI, retail sales, durable goods |
| #120 verified `previous` is point-in-time | on the **same 4** |
| **API Crude Oil** | ⛔ **neither** |

So for CL/API we do **not** know that:

- its `actual` is the number published at the release second rather than a later revision;
- its `previous` is the value that stood that morning rather than a back-filled one.

⚠️ **This is not a reason to dismiss the finding, and it is not a reason to trust it.** It is a reason
that the *next* step is a provenance check, not a trading experiment.

---

# PART 5 — PHASE 2, COMPLETE

| stage | question | result |
|---|---|---|
| **S0** | does the pipeline reproduce a **known** effect? | ✅ PASS — gold's inverse response, ρ = −0.273 (round 1: −0.193), Pearson blind in both. ⚠️ **Failed first**, and the cause was my outcome anchor — a defect that had already been published in Phase 1 |
| **S1** | are the features strictly past-only? | ✅ PASS — prefix invariance **0 mismatches / 303 rows**; planted leak caught **207/207** |
| **S2** | can each pair detect an effect at all? | ✅ **612 powered**, 31 VOID (≈ the ~30 expected by chance) — after **four** fixes to the probe |
| **S3** | does the surprise explain the release reaction? | ⭐ **23 survivors, ρ to −0.63** — and **22 of 23 live inside the jump** |
| **S4** | does anything survive into the **capturable** window? | ⭐ **1 of 612**, at **57.4%** against a 71% break-even |

## ⭐⭐⭐ The finding, in one sentence

> **The surprise explains the release-minute jump extremely well and explains essentially nothing
> afterwards — which is a measurement of market efficiency, not an edge.**

## ⭐ What Phase 2 also produced as by-products

1. **The published consensus is ~50% stronger than round 1's statistical proxy** in rank terms
   (−0.415 vs −0.273 on the gold jump), and lifts Pearson from blind (p = 0.50) to significant
   (p < 0.0001). Round 1 declined consensus data **because it cost money**; this quantifies what that
   cost in signal — and the data turned out to be free.
2. **The economics came out right without being imposed**: inflation surprises **negative** on all four
   equity indices and gold; jobless claims **positive**, because a higher claims number is bad news.
   Correct signs on five instruments, from a pipeline never told which way anything should go.
3. **`actual − previous` means different things on different series** (#120 Test C, independently
   replicated in S1 on a different code path: CPI 95.1% vs payrolls 2.4%).

---

# PART 6 — ⚠️ THE PATTERN ACROSS THREE WORKSTREAMS

| workstream | what was found | size | why it did not pay |
|---|---|---|---|
| **WS-EARN** (#109–113) | earnings move NQ | **4.98×** normal volatility | ⚠️ **magnitude, not direction** — and we cannot express magnitude with 1 contract and no options |
| **round 1 / S0** | gold responds to macro surprises | **5.5σ**, 15 of 16 years | ⚠️ **62–63% accuracy** vs a 71% break-even |
| **Phase 2 / S3–S4** | surprises explain the release jump | **ρ up to −0.63**, p to 1.9e-10 | ⚠️ **the jump is over before the input is knowable** |

> ⭐⭐ **The programme keeps finding real, large, replicated effects. Every one of them is either the
> wrong *kind* of quantity — magnitude when we can only trade direction — or arrives on the wrong
> *side* of the moment we could act.**

**That is a finding about the problem, not a failure of the method.** Three independent attacks, three
different data sources, three confirmations of the same structural obstacle.

---

# PART 7 — WHAT WENT WELL, WHAT WENT WRONG

## What went well

1. ⭐⭐⭐ **The capturable question was promoted from a footnote to a pre-registered test.** It would
   have been easy to report CL/API from S3's follow-up and move on. Searching all 612 with its own α is
   what turned it from a plausible number into a supported one.
2. ⭐ **Two search designs agreeing is stronger than either alone**, and the disagreement case was
   specified in advance.
3. **The 611 nulls were checked against two prior measurements** rather than reported in isolation.
4. **The accuracy interval separated "significant" from "tradeable"** at every stage — seven times in
   S3 alone.
5. **The provenance weakness was named as the next step**, not buried in a caveat.

## What went wrong

1. ⚠️ **`N_PERM` was undefined in the module** and S3 crashed on its first survivor — a code path that
   *only* runs when there is something to report, i.e. the one least likely to be exercised and most
   likely to matter.
2. ⚠️ **My V1 check inverted the project's own Pearson/Spearman rule** and would have discarded 6 of
   the 23 survivors. Caught only because the ledger refused to pass.
3. ⚠️ **The S2 probe needed four fixes**, three of which lowered the failure rate without addressing
   the cause.
4. ⚠️ **The Phase 2 pre-registration file had never been committed** — discovered when S4's predecessor
   crashed on the server looking for it.

## ⭐ The rules this phase produced

> 1. **State the anchor to the bar AND the side of the bar.** "After the release" is not a
>    specification; open-versus-close was the difference between a 5.5σ effect and noise.
> 2. **When a gate rejects most of its subjects, read it as evidence about the gate first.** Five for
>    five in this project.
> 3. **A metric moving in the right direction is not evidence the cause has been found.** Three
>    successive probe fixes each lowered the VOID rate while the real defect went untouched.
> 4. **Promote the decisive follow-up into a pre-registered test.** If a result is going to carry the
>    phase, it should not rest on where you happened to look.

---

# PART 8 — WHAT COMES NEXT

## ⛔ The prerequisite, before anything rests on CL/API

**Run #119's and #120's provenance checks on the EIA/API series.** The entire capturable finding depends
on data whose `actual` and `previous` have never been verified. That is a two-hour check against ALFRED
and the EIA's own archive, and it gates everything downstream.

⚠️ Note one likely complication, stated now: **EIA inventories may not have an ALFRED vintage series at
all**, in which case the check needs a different reference and the honest outcome may be *"cannot
verify"* rather than pass or fail.

## ⛔ UPDATE — the check was run, and the outcome is exactly that (#123)

**The provenance of this series cannot be verified at all**, and the reason is sharper than expected:

1. ⭐ **The survivor is the *private* report, not the government one.** The data's own `source` field
   reads **"American Petroleum Institute (API)"** — a trade association distributing to subscribers —
   released **Tuesday 16:30 ET**. The EIA series is a separate release, **Wednesday 10:30 ET**, from
   the U.S. Energy Information Administration.
2. **FRED carries no EIA/API inventory series at all.** Searching (rather than guessing identifiers)
   returned **0 hits** for "crude oil stocks ending" and "weekly natural gas storage". Five plausible
   IDs all return HTTP 400.
3. **So the method that cleared `actual` (#119) and `previous` (#120) — comparison against ALFRED's
   point-in-time archive — has no reference series and cannot be run.**

> ⚠️⚠️ **This is stronger than "unverified".** For the four cleared series the check was possible and
> passed. Here it is **not possible with any source available to us**, so a whole class of
> contamination is **unfalsifiable** for this series.

⚠️ It changes no decision — the effect was never tradeable (57.4% vs 71%) — but it means the result
must not be carried into #117 as though it stood on the same footing as the verified four.

⭐ **And it suggests the better experiment.** The API figure is widely treated as a *preview* of the next
morning's EIA number, so a post-release drift may simply be the market repricing toward the EIA figure
it now expects — no inefficiency required. That predicts something testable: **the drift should track
how well API forecasts EIA, and should vanish when the two diverge.** That experiment is cheap, uses
only verified price data, and should come before any latency work.

## Then #117 — with a concrete target for the first time

Phase 3's latency question now has **a measured target instead of a speculative one**:

| | |
|---|---|
| the effect | CL / API Crude Oil post-jump drift |
| size | ρ = **−0.247**, accuracy **57.4%**, n = **262** |
| the bar it must clear | **~14 more points of accuracy**, or the drift is not worth reaching |

⚠️ And #117's own prior is discouraging: Christensen, Timmermann & Veliyev (2025) put price discovery
in **milliseconds to seconds**, with a **5-second delay** removing significance. **A drift measured over
15 minutes is a different animal from the sub-second effects that literature describes — which is
mildly encouraging, and worth stating precisely rather than assuming either way.**
