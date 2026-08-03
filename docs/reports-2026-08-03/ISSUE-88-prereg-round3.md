---
name: issue-88-prereg-round3
description: Pre-registration for the third and final #88 A/B — stops counting the archive's process and measures what the archive CONTAINS. Written and committed BEFORE the run.
type: pre-registration
date: 2026-08-03
issue: 88
---

# #88 round 3 — declared before the run

**Committed before the run starts.** Rounds 1 and 2 stand recorded and are not withdrawn.

---

## 1. Two criteria, both failed — and the second failure is the informative one

| round | budget | criterion | result |
|---|---|---|---|
| 1 | 400 evals × 8 seeds | improvements ≥ 2× control | **FAILED** — 1/8 seeds, median 1.55× |
| 2 | 4,000 evals × 8 seeds | improvements ≥ 2× control (≥5/8 seeds) | **FAILED** — 0/8, median **0.39×** |
| 2 | " | comparisons ≥ 2× control (secondary) | **FAILED** — 0/8, median 1.30× |

At the larger budget the control has **two and a half times MORE improvements than the treatment**. The
criterion did not merely fail to pass; it inverted.

### Why it inverted — and why that condemns the metric, not the fix

| | control (1,494 niches) | treatment (81 niches) |
|---|---:|---:|
| niches filled (median) | 260 | 33 |
| improvements | 296 | 114 |
| comparisons | 962 | 1,285 |

The treatment does **more** comparing (1,285 vs 962) and **wins fewer** of them. That is exactly what a
working elites archive looks like:

> **An archive full of weak first arrivals is easy to improve. An archive of genuine elites is hard to
> improve.** The improvement count therefore *rises* as the archive gets *worse*.

The metric I registered is **anti-correlated with the property it was standing in for.** No budget and
no number of seeds can fix that — it is the wrong measurement, and running it a third time would be
running a broken instrument again.

---

## 2. What round 3 measures instead

A portfolio of elites is judged by **what is in it**, not by how busy it was. Deployed champions use
**3–10 indicators**, so that region is where the archive has to be good.

For each arm, from the final archive:

- `zone_best_median_pnl` — best median fold P/L among elites with 3–10 indicators
- `zone_total_median_pnl` — sum of elite fitness across that region (rewards being good *across* it,
  not one lucky point)
- `zone_entries` — how many distinct elites the archive holds there
- `best_median_pnl` — best anywhere in the archive

**These have never been computed for either arm.** The bench discarded the archive contents; it recorded
only counters. This is a blind prediction in a way rounds 1 and 2's secondary metric was not.

---

## 3. The criterion — declared now

**PRIMARY:**

> **`zone_best_median_pnl` (treatment) > `zone_best_median_pnl` (control) in ≥ 6 of 8 seeds.**

Same run shape as round 2: NQ 4h, 1-minute frame, 4,000 evals per arm, seeds 1–8, control = the
identity `ind_bucket` (the pre-#88 raw-count axis), both arms in one process, axis the only difference.

**SECONDARY, reported but not decisive:** `zone_total_median_pnl`, `zone_entries`, `best_median_pnl`.

### What each outcome means

- **Primary passes** → the bucketed archive produces better strategies where strategies actually get
  deployed. #88 is a win, on an outcome measure, and I say so.
- **Primary fails** → then the honest conclusion is that **the shape defect is real but does not affect
  what the archive delivers.** #88 becomes a correctness fix with no demonstrated benefit — the "keep
  the first, not the best" characterisation stays true and tested, but the claim that it *mattered* is
  withdrawn, and I will say that plainly rather than keep hunting for a metric that passes.
- **Split (e.g. best is better, total is worse)** → reported as inconclusive. No third criterion gets
  invented afterwards.

**This is the last A/B for #88.** If the primary fails, the issue is closed as "shape fixed, benefit not
demonstrated" and the effort moves to **#101** — where 68% of every evaluation is discarded before it
reaches the archive at all.

---

## 4. Still out of scope

- Validating earlier MAP-Elites results (**#90**).
- Comparing MAP-Elites against the ordinary optimizer.
- The 68% discard rate (**#101**) — identical in both arms, so it cannot explain a difference between
  them, but it caps what either can achieve.
