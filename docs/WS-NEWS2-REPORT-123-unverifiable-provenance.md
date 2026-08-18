---
name: ws-news2-report-123-unverifiable-provenance
description: "The provenance check on Phase 2's only capturable finding: the series turned out to be a private trade-association report with no public archive, so the verification method that cleared the other four series cannot be run at all. Why 'cannot verify' is a different statement from 'unverified', and the experiment this points to instead."
type: report
date: 2026-08-15
issues: [111, 116, 117, 119, 120, 121, 123]
---

# #123 — a finding that cannot be checked

**Phase 2's only capturable result sits on a private subscription report with no public archive.** The
method that verified every other series in this study has **no reference to compare against**, so a
whole class of contamination is not merely unchecked — it is **unfalsifiable**.

---

# PART 0 — THE ONE-PAGE VERSION

| | |
|---|---|
| **What was checked** | can `actual` / `previous` / `forecast` be verified for the CL / API crude-oil series? |
| **Why it mattered** | it is the **only capturable finding** in the entire programme (#116 S4) |
| ⭐⭐ **What was discovered** | the survivor is the **American Petroleum Institute** — a *private trade association*, not the EIA |
| **FRED / ALFRED coverage** | **zero** — 0 search hits, 5 plausible IDs all HTTP 400 |
| ⛔ **Verdict** | **CANNOT BE VERIFIED**, which is stronger than "not yet verified" |
| **Does it change a decision?** | **No** — the effect was never tradeable (57.4% vs a 71% break-even) |
| ⭐ **What it points to** | a cheap, falsifiable experiment that needs **no** unverifiable data |

---

# PART 1 — WHY THIS CHECK WAS THE NEXT STEP

Phase 2 closed with exactly one capturable result:

> **CL / API Crude Oil Stock Change** — post-jump drift, ρ = **−0.247**, p = 5.2e-05, n = **262**,
> permutation p = 0.001, matched-non-event control null. Found independently by **two** search designs:
> an after-the-fact follow-up on 23 pairs, and a pre-registered systematic search of all 612.

That is a well-supported effect on the **price** side, which is fully verified (#121: 100.0000% overlap
agreement with the engine's own frame, volume-profile ρ = 1.000).

**But the *event* side had never been checked.** #119 cleared `actual` and #120 cleared `previous` on
**four** series — nonfarm payrolls, CPI, retail sales, durable goods. **The API series is not among
them.**

> ⭐ So the honest next step was a provenance check, **not** a trading experiment. Carrying an
> unverified series into #117 as a latency target would have put the weakest data in the study at the
> head of the next phase.

---

# PART 2 — WHAT THE CHECK FOUND

## 2.1 ⭐⭐ The survivor is the *private* report, not the government one

I had been treating "EIA crude" and "API crude" as one family. **They are two different releases from
two different organisations.** The data says so itself:

| | `source` field | release time | weekday |
|---|---|---|---|
| **API Crude Oil Stock Change** ⬅ **the survivor** | **American Petroleum Institute (API)** | **16:30 ET** | Tuesday (397 of 457) |
| EIA Crude Oil Stocks Change | U.S. Energy Information Administration | 10:30 ET | Wednesday (600 of 699) |

**The American Petroleum Institute is a trade association.** Its weekly inventory estimate is
distributed to **subscribers**; it is not an open government statistic.

⚠️ **This distinction had been invisible to me because the two titles look alike and sit adjacent in
every table.** It is exactly the class of error the project has hit repeatedly — `indicator` versus
`title` in #114, `previous` meaning different things per series in #120 — where two things that render
similarly are not the same thing.

## 2.2 FRED and ALFRED carry nothing

I searched rather than guessing identifiers — guessing is a mistake already made twice in this
workstream (invented EDGAR accession numbers; invented FRED-to-TradingView title mappings):

```
search "crude oil stocks ending"     ->  0 hits
search "weekly natural gas storage"  ->  0 hits
search "gasoline stocks weekly"      ->  1 hit — the Weekly Economic Index, unrelated
```

And five plausible identifiers — `WCESTUS1`, `WCRSTUS1`, `WGTSTUS1`, `WDISTUS1`, `WNGSTUS1` — **all
return HTTP 400, not in FRED.**

## 2.3 ⛔ So the verification method cannot be run

#119 and #120 both work the same way: compare TradingView's value against **ALFRED's point-in-time
archive**, which records what a given statistic looked like on a given morning.

> **There is no ALFRED series for these inventories. There is no reference. The check cannot be
> executed at all.**

And for a **private** report, no public substitute exists: there is no open record of what the API
number was on a given Tuesday evening.

---

# PART 3 — ⚠️⚠️ "CANNOT VERIFY" IS A DIFFERENT STATEMENT FROM "UNVERIFIED"

This distinction is the point of the whole report.

| | the four cleared series | **API crude** |
|---|---|---|
| was the check possible? | ✅ yes | ⛔ **no** |
| was it run? | ✅ yes | — |
| did it pass? | ✅ yes | — |
| could a contaminated value be **detected**? | ✅ yes | ⛔ **no** |

For nonfarm payrolls, a back-filled `actual` would have been caught: March 2020 payrolls were revised
from −701k to −1,398k, and TradingView carries −701k. **The test had teeth.**

For API crude, a back-filled `actual`, a revised `previous`, or a late `forecast` would all be
**invisible**. There is no observation that could distinguish a clean series from a contaminated one.

> ⭐ **An unfalsifiable claim is not a weak claim — it is a different kind of claim.** It cannot be
> promoted by gathering more of the same evidence, because no amount of that evidence bears on it.

---

# PART 4 — WHAT THIS DOES AND DOES NOT MEAN

## It does NOT mean the finding is wrong

The effect has genuine support:

| | |
|---|---|
| found by an after-the-fact follow-up on 23 pairs | ✅ |
| **and** by a pre-registered systematic search of 612 with its own α | ✅ |
| permutation control | p = 0.001 |
| matched-non-event control | null |
| sample | n = 262 |
| the **price** side | fully verified (#121) |

⭐ **Two independent search designs agreeing is strong.** If the effect existed only in the
after-the-fact look it would be a selection artefact; it does not.

## It DOES mean the result cannot be promoted

A whole class of contamination is unfalsifiable here, so the finding cannot be treated as being on the
same footing as anything resting on the four cleared series.

## ⚠️ And it changes no decision, because it was never tradeable

| | |
|---|---|
| accuracy | **57.4%** [51.2, 63.4] |
| break-even (#111) | **71%** |
| shortfall even at the optimistic end | **~8 points** |

**The provenance gap is recorded so the result is not carried into #117 as a target, not because it
alters what we would do.**

---

# PART 5 — ⭐ THE MECHANISM THIS SUGGESTS, AND WHY IT IS TESTABLE

## 5.1 The hypothesis

The API figure is released **Tuesday 16:30 ET**; the EIA figure **Wednesday 10:30 ET**. The API number
is widely treated as a **preview** of the EIA one.

> **So a post-release drift after API may simply be the market repricing toward the EIA figure it now
> expects. That requires no inefficiency at all.**

## 5.2 ⚠️ And the contrast that makes this sharp

S4 searched **both** series across all 612 pairs. It found:

| | result |
|---|---|
| **API** crude (private, Tuesday) | ⭐ **the only survivor**, ρ = −0.247 |
| **EIA** crude (government, Wednesday) | **null** |

**The effect is only in the private preview, not in the official release.** That is either:

1. a **real information mechanism** — the preview genuinely moves expectations, and the official number
   arrives already priced; or
2. an **artefact** of a series whose provenance cannot be checked.

⭐ **These two explanations make different predictions**, which is what makes the question answerable
without any unverifiable data.

## 5.3 The experiment

Everything it needs — the price frames, and both releases' published values — is already in hand, and
the price side is fully verified.

| test | what it asks | what the repricing story predicts |
|---|---|---|
| **A** | does the API number actually forecast the EIA number? | **strong positive correlation** — otherwise the mechanism is impossible |
| **B** | is the post-API drift *anticipatory*? | the EIA-day reaction should be **muted** when the API drift already moved price the right way |
| **C** | what happens when API and EIA **diverge**? | the drift should **reverse** on divergence weeks — the market mispriced toward a preview that turned out wrong |

⚠️ **Test A is a premise check, not evidence for the story.** If API does not forecast EIA, the
repricing explanation is dead regardless of B and C.

⭐ **Test C is the discriminating one.** An artefact has no reason to reverse specifically on weeks
where the preview was misleading; a repricing mechanism must.

---

# PART 6 — WHAT WENT WELL, WHAT WENT WRONG

## What went well

1. ⭐⭐ **The provenance check was run before anything was built on the finding**, rather than after
   #117 had spent effort on it.
2. ⭐ **The API/EIA distinction was discovered by reading the data's own `source` field** rather than
   assuming two similar titles were one family.
3. **FRED was searched, not guessed.** Five plausible identifiers all turned out to be wrong — exactly
   what guessing would have produced as a false negative or, worse, a false positive on a similar-named
   series.
4. **The outcome was stated as "cannot verify" rather than folded into "unverified"**, because the two
   licence different conclusions.
5. **The dead end produced a live experiment.** The EIA-null / API-positive contrast is more
   informative than either result alone.

## What went wrong

1. ⚠️⚠️ **I treated API and EIA as one family throughout Phase 2** — in the matrix, in the S2 probe
   grouping, and in every summary table that said "energy releases". They are different organisations,
   different days, different times, and one is private.
2. ⚠️ **The "unverified provenance" label I applied from S3 onward was too weak.** It implied a check
   that had not yet been done, when in fact no such check exists.
3. ⚠️ **This was foreseeable at the point the energy series were added to Phase 1** (#122). I flagged
   them as not provenance-cleared, but never asked *whether they could be*.

## ⭐ The rule this produces

> **Before labelling something "unverified", establish whether it is verifiable.** Those are different
> states with different consequences: one is a task, the other is a permanent property of the evidence.
> Recording the second as the first quietly implies a check that will never come.

---

# PART 7 — WHERE THIS LEAVES THE PROGRAMME

| | status |
|---|---|
| **Phase 1** (#115, #122) | ✅ closed — no tradeable entry across 8 instruments |
| **Phase 2** (#116) | ✅ closed — **market efficiency, not an edge**; 0 of 612 reach break-even |
| **Phase 3** (#117) | ⏳ open — its only concrete target is provenance-blocked |
| **#123** | 🆕 this finding |

## ⛔ Recommendation on #117

**Do not carry the CL/API result into #117 as a latency target.** It is unverifiable in provenance and
~14 points short of paying, so latency work on it would be optimising the reach toward something that
does not pay even if reached perfectly.

⭐ **Run the API→EIA experiment first.** It costs little, uses only verified price data, and it
distinguishes a real information mechanism from an artefact — which is the question that decides
whether there is anything here at all.

**Proceeding to that experiment now.**
