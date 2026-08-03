---
name: issue-88-round4-coldstart-result
description: "#88 cold-start replication — the pre-registered criterion FAILED (3/8). The round-3 benefit is a property of warm-started search and the claim is narrowed to that scope. A pre-declared secondary won 8/8, and is reported without being promoted to the verdict."
type: measurement
date: 2026-08-03
issue: 88
---

# #88 round 4 — cold start. The criterion failed, and the claim narrows.

**NQ 4h · 1-minute frame · 4,000 evaluations per arm · 8 seeds · COLD START · control = the pre-#88
raw-count axis · both arms in one process.**

Criterion pre-registered in `ISSUE-88-prereg-round4-coldstart.md`, committed before the run, deliberately
identical to round 3:

> **`zone_best_median_pnl` (treatment) > (control) in ≥ 6 of 8 seeds.**

---

## 1. Result

| | |
|---|---|
| **treatment wins** | **3 of 8** |
| **verdict** | **FAILED** |

| seed | control zone best | treatment zone best | wins | ctl zone entries | trt zone entries |
|---:|---:|---:|:--:|---:|---:|
| 1 | $20,393 | $26,765 | ✅ | 19 | 10 |
| 2 | — | — | ❌ | **0** | **0** |
| 3 | $12,779 | $12,401 | ❌ | 17 | 11 |
| 4 | $18,822 | $31,403 | ✅ | 20 | 17 |
| 5 | — | — | ❌ | **0** | **0** |
| 6 | $8,647 | $10,618 | ✅ | 7 | 7 |
| 7 | $16,115 | $16,115 | ❌ (tie) | 3 | 5 |
| 8 | — | — | ❌ | **0** | **0** |

---

## 2. What this does to the #88 claim

Stated in the pre-registration, before the numbers existed:

> **Fails cold** → then round 3's result is a property of warm-started search, and #88's claimed benefit
> is withdrawn to that scope.

So, applied:

| claim | status |
|---|---|
| The archive shape defect is real (1,494 niches, 0.27 visits ⇒ "keep the first") | **stands** — arithmetic, and pinned by tests |
| The fix removes it (81 niches, registry-independent) | **stands** — pinned by tests |
| The fix improves champion-zone strategy quality **when the search is warm-started** | **stands** — 8/8, +23.1% |
| The fix improves champion-zone strategy quality **in general** | **WITHDRAWN** — 3/8 cold |

**#88 is reopened with the narrower claim.** It was closed on a result that does not generalise, and
leaving it closed would misrepresent what was shown.

---

## 3. Why the criterion degenerates cold — analysis, not a rescue

**In 3 of 8 seeds neither arm produced a single 3–10-indicator elite.** The metric is undefined there;
under the rule I declared, an undefined comparison is not a win, so those seeds count against the
treatment while carrying no information about it.

Of the 5 seeds where the zone was populated at all: treatment won 3, tied 1, lost 1.

That is a weakness of the *criterion applied cold*, and it is worth recording — but it does **not**
change the verdict. I registered the rule knowing ties and empties would count as non-wins, and rewriting
the scoring after seeing which seeds came up empty is exactly the move the pre-registration exists to
prevent.

---

## 4. The secondary that won, reported and NOT promoted

Declared in the pre-registration as a reported secondary:

| | control median | treatment median | treatment wins |
|---|---:|---:|---:|
| **best elite anywhere in the archive** | **$23,891** | **$37,033** | **8 / 8** |
| zone total elite P/L | $39,299 | $56,317 | 3/8 |
| zone entries | 5 | 6 | 1/8 |

**Best-anywhere is a clean 8/8 sweep, +55% on the median.** That is a strong signal that the fix does
help cold — just not in the region the primary looked at, because cold search rarely reaches that region
at all.

**It is not the verdict.** The pre-registration says *"no further criterion will be invented after this
run"*, and promoting a secondary to primary after seeing it pass is precisely what that sentence
forbids. If this is to become a claim, it needs its own pre-registered test, run separately.

---

## 5. What cold start also revealed

| | warm (rounds 2–3) | cold (round 4) |
|---|---:|---:|
| evaluations discarded before reaching a niche | ~68% | **~74%** |
| control niches filled (median) | 260 | 219 |
| treatment niches filled (median) | 33 | 29 |
| seeds with an empty champion zone | 0 | **3 of 8** |

Cold search **discards more and reaches the deployable region less often**. Both feed **#101**: the
binding constraint on this archive is the feasibility rate, and removing the champion seed makes it
worse.

This is also the measured cost of the #102 decision, stated plainly: cold start removes the
≥-champion floor, and in 3 of 8 runs it produced **nothing at all** in the 3–10 indicator band where
strategies are actually deployed.

---

## 6. Status

- **#88 reopened**, claim narrowed to warm-started search.
- **#101** (68→74% discarded) is now the blocking question for both.
- **#90** (re-validating results produced under the broken shape) untouched and still open.
- **#102** (cold start default) shipped; its cost is recorded above rather than discovered later.

Raw: `optimize/results/issue88r4/r4_seed{1..8}.json`.
