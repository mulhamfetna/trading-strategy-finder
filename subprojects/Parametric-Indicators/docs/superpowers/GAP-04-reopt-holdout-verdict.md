# GAP-04 — Honest-fill re-optimization, judged on a real holdout: **ADOPT NOTHING**

**Date:** 2026-07-30 · **Issue:** #2 · **Study prefix:** `wshgap4`
**Supersedes:** [GAP-03](./GAP-03-reoptimization-before-after.md) (retracted — wrong baseline, contaminated holdout)

---

## Verdict

**No champion is adopted. The deployed set wins on every slot that moved.**

| | train 2025 (what the optimizer saw) | **holdout 2026 (never seen)** |
|---|---:|---:|
| deployed (`best_*`) | $501,126 | **$309,072** |
| re-optimized (`wshgap4`) | **$761,472** | **$67,419** |
| delta | **+$260,346** | **−$241,653** |

| slots better on the holdout | **0** |
|---|---|
| slots worse | **9** |
| slots unchanged (warm start could not be beaten) | 3 |
| re-optimized slots that turn **negative** in 2026 | **6** |

The re-optimization gained **+52% on the year it was allowed to look at** and lost **−78% on the year it
was not**. That is textbook over-fitting, and it is visible only because this run finally had a genuine
holdout.

## The full table

| slot | train 2025 | holdout 2026 | holdout drawdown |
|---|---|---|---|
| NQ 4h | 90,054 → 90,054 | 61,601 → 61,601 | 15,560 → 15,560 |
| NQ 2h | 41,657 → 97,898 | 40,745 → **−21,830** | 5,645 → 24,266 |
| NQ 1h | 56,620 → 75,245 | 27,203 → 5,040 | 7,825 → 10,784 |
| NQ 15m | 22,515 → 29,835 | 21,306 → **−298** | 4,939 → 2,853 |
| NQ 5m | 13,091 → 21,109 | 2,600 → **−343** | 1,521 → 3,295 |
| NQ 2m | 26,010 → 25,608 | 4,545 → **−5,003** | 3,833 → 9,993 |
| GC 4h | 54,782 → 121,292 | 34,290 → **−16,090** | 7,969 → 16,178 |
| GC 2h | 58,828 → 134,191 | 26,101 → **−20,524** | 15,649 → 24,863 |
| GC 1h | 58,228 → 88,632 | 28,740 → 12,301 | 21,007 → 21,091 |
| GC 15m | 44,713 → 44,713 | 37,897 → 37,897 | 7,583 → 7,583 |
| GC 5m | 9,619 → 7,884 | 10,346 → 971 | 3,905 → 1,116 |
| GC 2m | 25,008 → 25,008 | 13,699 → 13,699 | 3,825 → 3,825 |

Look at **GC 2h**: training profit more than doubled ($58,828 → $134,191) while the holdout went from
+$26,101 to **−$20,524** and drawdown grew 59%. Every ingredient of a strategy that has memorised its
training year.

## ⚠️ What this does and does not prove

**It proves:** none of these twelve re-optimized champions should be adopted. That decision is solid —
zero of them improve the untouched year, and half of them lose money in it.

**It does NOT prove that re-optimizing under honest fills is worthless**, and the reason is a limitation
of my own design, not of the result:

> The deployed champions were tuned on the **full history**. `wshgap4` was restricted to **2025 only**
> (`--train-window 2025`), because that is what creates a genuine 2026 holdout. So the comparison
> confounds two changes: *honest fills* and *a training window less than half as long*.

Less training data over-fits more. A fair test of "does honest-fill re-tuning help?" would need either a
longer training window with a later holdout, or walk-forward folds that preserve a true out-of-sample
year at each step. **That experiment has not been run.** What has been established is that **one year of
training is not enough for this search space** — 471 dimensions against 1,534 decision bars.

## How this run differed from the retracted July one

| | July (`wshgap`) — retracted | this run (`wshgap4`) |
|---|---|---|
| warm-start seed | `wsh4_*` — **retired 2026-07-14** | **`best_*`**, resolved through the deployed-set resolver, printed per study |
| baseline compared against | the same retired set | the deployed set |
| "out-of-sample" year | **inside the training data** | **genuinely held out** (`--train-window 2025`) |
| indicator scope | 18 (its worktree predated the library) | 18, **deliberately** — the adopt gate (#14) leaves the other 147 default-off |
| parameter precision | `round(x, 4)` | **exact** (`_exact`, no rounding) |
| trial budget | 5,900 (59 dims) | 5,900 (59 dims) — after fixing an 8× over-budget |

July reported **+$35,475 "out-of-sample"**. Measured properly, the same exercise is **−$241,653**.

## What was verified rather than assumed

* every study printed its seed: `[warm-start] … seeded from best_champions_full.json (DEPLOYED set)`;
* every study printed `TRAIN WINDOW = 2025 only … 2026 is HELD OUT and never seen by this search`;
* extraction ran on the current engine, and the champions carry full precision
  (`sl_soft=63.670615777194996`, versus July's `69.2488`);
* both sides were scored by the same engine through `build_view_payload`, each champion running its own
  parameters, under mandatory gap-aware fills.

## Consequences

1. **The deployed `best_*` set stands unchanged.** No proposal, no swap.
2. **GAP-03 stays retracted.** Its three "winners" were an artifact of the wrong baseline; this run
   confirms the direction independently.
3. **Issue #2 closes.** The question it asked — *"if we re-tune honestly, do we get better champions?"* —
   is answered for the configuration tested: **no**.
4. **A follow-up is worth opening** for the experiment this run could not perform: honest-fill re-tuning
   with a training window long enough to generalise, and a holdout that is still genuinely held out.

## What went well / what went wrong

* **Went well:** the holdout did its job. Nine slots looked like improvements on the training year and
  every one of them was a mirage — exactly the outcome the July run was structurally unable to detect.
  Three defects (retired seed, 8× over-budget, wrong indicator scope) were caught *before* the run rather
  than after.
* **Went wrong:** the training-window confound above is mine. I chose 2025-only to buy a clean holdout
  and did not flag loudly enough, at the time, that it also halves the training data — which makes the
  headline number partly a statement about data volume rather than about honest fills.
