---
name: issue-88-round5-final
description: "#88 final — the cold best-anywhere criterion FAILED on fresh seeds (5/8, needed 6/8). Round 4's 8/8 sweep did NOT replicate. My recorded prediction was wrong. The benefit stays scoped to warm-started search, permanently."
type: measurement
date: 2026-08-03
issue: 88
---

# #88 round 5 — final. The criterion failed, and my prediction was wrong.

**NQ 4h · 1-minute frame · cold start · 4,000 evaluations per arm · FRESH seeds 9–16 · bucketed axis vs
the pre-#88 raw-count axis · both arms in one process.**

Criterion pre-registered in `ISSUE-88-prereg-round5.md` (8aae9ad), before the run:

> **`best_median_pnl` (bucketed) > (raw) in ≥ 6 of 8 seeds.**

---

## 1. Result

| | |
|---|---|
| **bucketed wins** | **5 of 8** |
| **threshold** | 6 of 8 |
| **verdict** | **FAILED** |

| seed | raw axis | bucketed | bucketed wins |
|---:|---:|---:|:--:|
| 9 | $25,011 | $41,230 | ✅ |
| 10 | $32,227 | $35,324 | ✅ |
| 11 | $18,463 | $20,453 | ✅ |
| 12 | $25,335 | $24,389 | ❌ |
| 13 | $20,126 | $22,385 | ✅ |
| 14 | $30,904 | $32,603 | ✅ |
| 15 | $16,494 | $13,356 | ❌ |
| 16 | $27,885 | $23,962 | ❌ |

Median best elite: **$25,173 → $24,176 (−4.0%)**. Per-seed median uplift **+7.6%** — the two disagree
because seed 9's large win does not move the median of medians.

---

## 2. My prediction was wrong, and it is on the record

From the pre-registration:

> I expect this to **pass**. Round 4's cold sweep was 8/8 with a large margin (+55% median)… If it
> fails, that prediction is on the record as wrong.

It failed. **The prediction was wrong.**

---

## 3. What the fresh seeds bought

| | seeds 1–8 (round 4) | seeds 9–16 (round 5) |
|---|---:|---:|
| bucketed wins on best-anywhere | **8/8** | **5/8** |
| median best elite, raw | $23,891 | $25,173 |
| median best elite, bucketed | $37,033 | $24,176 |
| median uplift | **+55%** | **−4.0%** |

**An 8/8 sweep with a +55% margin became 5/8 with −4%.** Nothing changed but the seeds.

That is precisely what testing a hypothesis on the data that generated it would have concealed. Had I
promoted round 4's secondary — which passed 8/8, on a huge margin, and which #101's control arm
independently reproduced — #88 would have been closed as a general win on a result that does not
replicate.

> **Two independent runs agreeing on the same seeds is not replication. It is the same eight rolls of
> the same dice, counted twice.**

---

## 4. Final status of #88

| claim | status |
|---|---|
| the archive shape defect is real — 1,494 niches, 0.27 visits ⇒ "keep the first, not the best" | **ESTABLISHED** (arithmetic + tests) |
| the fix removes it — 81 niches, registry-independent forever | **ESTABLISHED** (tests) |
| the fix improves outcomes **when the search is warm-started** | **ESTABLISHED** — 8/8, +23.1% (round 3) |
| the fix improves outcomes **cold** — champion zone | **REFUTED** — 3/8 (round 4) |
| the fix improves outcomes **cold** — best anywhere | **REFUTED** — 5/8 on fresh seeds (round 5) |

**#88's benefit is scoped to warm-started search, permanently.** As declared: no round 6, no further
criterion.

The fix stays in. It is correct on its own terms — the archive genuinely was keeping first arrivals, that
is arithmetic and it is pinned by tests — and it demonstrably helps when the search is seeded. It is not
demonstrated to help a cold search, and it will not be claimed to.

---

## 5. The five rounds, in one table

| round | seeds | start | criterion | result |
|---|---|---|---|---|
| 1 | 1–8, 400 evals | warm | improvements ≥2× | **FAIL** 1/8 |
| 2 | 1–8, 4,000 | warm | improvements ≥2× | **FAIL** 0/8 — *inverted* |
| 2 | " | warm | comparisons ≥2× (secondary) | **FAIL** 0/8 |
| 3 | 1–8, 4,000 | warm | champion-zone best | **PASS** 8/8, +23.1% |
| 4 | 1–8, 4,000 | **cold** | champion-zone best | **FAIL** 3/8 |
| 5 | **9–16**, 4,000 | **cold** | best anywhere | **FAIL** 5/8 |

**Four failures, one pass, and the pass is real but narrow.** Every criterion was committed to git before
its run, which is the only reason the four failures are visible at all — and the only reason the one pass
can be trusted.

### Three lessons, in order of how much they cost

1. **A counter that rises as the thing gets worse is a wrong instrument, not a weak one.** (rounds 1–2)
2. **A default you did not choose is a condition of your experiment.** Warm start silently defined 48
   runs. (round 4)
3. **Fresh seeds are not a formality.** 8/8 and +55% became 5/8 and −4%. (round 5)
