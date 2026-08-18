---
name: issue-88-prereg-round5
description: "#88 round 5 — the cold-start question settled properly: best-anywhere as PRIMARY, on FRESH seeds 9-16 so the hypothesis is not tested on the data that generated it. Written and committed BEFORE the run."
type: pre-registration
date: 2026-08-03
issue: 88
---

# #88 round 5 — declared before the run

**Committed before the run starts.** Rounds 1–4 stand recorded and are not withdrawn.

---

## 1. Why there is a round 5

Round 4 (cold) failed its primary at 3/8, and #88 was reopened with the claim narrowed to warm-started
search. But that round's **pre-declared secondary** — best elite anywhere in the archive — swept **8/8**,
$23,891 → $37,033, **+55%**.

I refused to promote it, because the round-4 pre-registration said no further criterion would be invented
after that run. That was the right call: promoting a secondary after watching it pass is exactly what
pre-registration prevents.

**But refusing to promote it is not the same as refusing to test it.** The correct move is to declare it
as the primary *in advance* and test it on **data that has not been seen**.

### Why the champion-zone metric was the wrong instrument cold

Round 4 measured it: **3 of 8 cold seeds produced no 3–10-indicator elite at all in either arm.** The
metric is undefined there and scored as a non-win under the declared rule, so nearly 40% of the
experiment carried no information. Best-anywhere is defined in every run.

That is a reason grounded in a *measured property of cold search*, not in which metric looked better.

---

## 2. Fresh seeds — the part that makes this legitimate

**Seeds 9–16.** Rounds 1–4 used seeds 1–8, and #101 used seeds 1–8. The best-anywhere signal was observed
on seeds 1–8; testing it again on seeds 1–8 would be scoring the hypothesis on the data that generated
it.

Nothing else changes: NQ 4h, 1-minute frame, **cold start**, 4,000 evaluations per arm, control =
`ind_bucket` replaced by the identity (the pre-#88 raw-count axis), both arms in one process, the axis
the only difference. `--stepping-stones` OFF (refuted, #101).

---

## 3. The criterion

**PRIMARY:**

> **`best_median_pnl` (bucketed axis) > (raw axis) in ≥ 6 of 8 seeds (9–16).**

**SECONDARY, reported, not decisive:** `zone_best_median_pnl`, `zone_entries`, `filled`, and the discard
split.

### What each outcome means

- **Passes** → the #88 fix improves outcomes **cold as well as warm**, on a metric declared in advance
  and tested on unseen seeds. The claim is restored to its general form and **#88 closes as a win** —
  with the honest note that it took five rounds and two wrong instruments to establish.
- **Fails** → then the cold best-anywhere sweep in round 4 was **seed-specific luck**, and #88 stays
  narrowed to warm-started search permanently. I will say that the earlier 8/8 did not replicate, which
  is a stronger statement against the fix than round 4 alone.
- **Split** → inconclusive, reported as such, and #88 stays narrowed.

**This is the final #88 experiment.** Whatever it returns, no round 6, and no further criterion.

---

## 4. Prediction, recorded so it can be wrong

I expect this to **pass**. Round 4's cold sweep was 8/8 with a large margin (+55% median), and #101's
control arm — the same configuration, seeds 1–8 — independently reproduced the same $37,033 median. Two
separate runs agreeing is why this is worth one more experiment rather than a shrug.

If it fails, that prediction is on the record as wrong.
