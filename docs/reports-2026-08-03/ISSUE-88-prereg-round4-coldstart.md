---
name: issue-88-prereg-round4-coldstart
description: Pre-registration for the #88 cold-start replication — every earlier round was warm-started, and the headline finding is defined in terms of the seeded champion. Written and committed BEFORE the run.
type: pre-registration
date: 2026-08-03
issue: 88
---

# #88 round 4 — the cold-start replication, declared before the run

**Committed before the run starts.** Rounds 1–3 stand recorded and are not withdrawn.

---

## 1. The confound

**Every #88 experiment — rounds 1, 2 and 3, 24 runs in total — ran with `warm_start=True`.** That was
the default, and I did not choose it or state it.

Round 3's headline is:

> the broken archive's best 3–10-indicator elite **is exactly the seeded champion** in 5 of 8 seeds

That sentence is *defined* in terms of an object that only exists because of warm start. Cold, there is
no seeded champion to return, so the finding cannot be restated, let alone reproduced, without re-running
it. Worse, warm start plausibly *drives* the effect rather than merely enabling it: seeding one strong
genome into a 1,494-niche archive gives mutation an enormous number of empty niches to spill into, which
is exactly the regime that produces first-fills rather than comparisons. The bucketed archive has 81, so
mutation pressure concentrates. **The axis and the seeding interact, and round 3 measured them together.**

So the correct status of round 3 is: **a real result about warm-started MAP-Elites, not yet a result
about MAP-Elites.**

---

## 2. The run

Identical to round 3 in every respect **except** `--no-warm-start` (now the default, #102):

**NQ 4h · 1-minute indicator frame · 4,000 evaluations per arm · seeds 1–8 · control = `ind_bucket`
replaced by the identity (the pre-#88 raw-count axis) · both arms in one process · COLD START.**

---

## 3. The criterion — the same one, unchanged

**PRIMARY:**

> **`zone_best_median_pnl` (treatment) > (control) in ≥ 6 of 8 seeds.**

Deliberately identical to round 3 so the two are directly comparable. No new metric, no adjusted
threshold.

**SECONDARY, reported:** `zone_total_median_pnl`, `zone_entries`, `best_median_pnl`, and the
`invalid / pnl_neg / dd_over` discard split (#101) — cold start should change the discard mix, and if it
does that is worth knowing regardless of the primary.

### What each outcome means

- **Passes cold too** → the axis fix stands on its own. Warm start was a condition of the experiment,
  not the cause of the result. #88's conclusion holds and is now stated without the seeding caveat.
- **Fails cold** → then **round 3's result is a property of warm-started search, and #88's claimed
  benefit is withdrawn to that scope.** The shape defect remains real and tested; the benefit becomes
  "demonstrated only when the search is seeded". I will say exactly that, and #88 is reopened with the
  narrower claim rather than left closed on a finding that does not generalise.
- **Both arms collapse cold** (e.g. almost nothing feasible without a seed) → reported as an
  inconclusive replication, and the reason becomes evidence for **#101**.

**No further criterion will be invented after this run.**

---

## 4. What is deliberately NOT being re-run

Rounds 1 and 2 measured process counters that were shown to be the wrong instrument. They are not
repeated cold — repeating a broken measurement under a new condition produces a new broken measurement.
