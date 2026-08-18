---
name: issue-101-result
description: "#101 — stepping stones FAILED the pre-registered criterion 1/8. The mechanism worked exactly as designed (parent pool 29→92) and the peak got WORSE. Widening the pool trades peak quality for coverage."
type: measurement
date: 2026-08-03
issue: 101
---

# #101 — the population was not the limit. Result: FAIL, 1 of 8.

**NQ 4h · 1-minute frame · cold start · 4,000 evaluations · 8 seeds · bucketed axis in both arms ·
`--stepping-stones` the only difference · both arms in one process.**

Criterion pre-registered before the run (`ISSUE-101-diagnosis-and-prereg.md`, 497b77d):

> **`best_median_pnl` (stepping stones ON) > (OFF) in ≥ 6 of 8 seeds.**

---

## 1. Result

| | |
|---|---|
| **treatment wins** | **1 of 8** |
| **verdict** | **FAILED** |

| seed | OFF best | ON best | ON wins | OFF pool | ON pool | stones kept |
|---:|---:|---:|:--:|---:|---:|---:|
| 1 | $38,818 | $27,422 | ❌ | 43 | 93 | 243 |
| 2 | $41,763 | $29,208 | ❌ | 22 | 93 | 252 |
| 3 | $30,448 | $28,284 | ❌ | 38 | 95 | 229 |
| 4 | $38,737 | $37,385 | ❌ | 42 | 90 | 248 |
| 5 | $34,408 | $29,577 | ❌ | 23 | 90 | 259 |
| 6 | $24,354 | $52,894 | ✅ | 29 | 89 | 221 |
| 7 | $40,663 | $29,385 | ❌ | 29 | 94 | 230 |
| 8 | $35,329 | $29,544 | ❌ | 19 | 92 | 243 |

Median best elite: **$37,033 → $29,464.** Not merely "no better" — **materially worse, in 7 of 8 seeds.**

---

## 2. The mechanism worked. That is what makes the result informative.

This was not a broken implementation producing a null.

| | OFF | ON | ON wins |
|---|---:|---:|---:|
| **parent pool** | 29 | **92** | **8/8** |
| niches filled | 29 | **37** | 6/8 |
| 3–10 indicator entries | 6 | **12** | 7/8 |
| 3–10 zone best | $11,510 | **$18,457** | 6/8 |
| **best anywhere** | **$37,033** | $29,464 | **1/8** |
| improvements | 118 | 74 | 0/8 |

The pool tripled exactly as intended. The archive got **broader**: more niches filled, twice as many
elites in the deployable band, and a better champion-zone best. And the **peak got worse**.

> **Widening the parent pool trades peak quality for coverage.** Mutation budget spent exploring from
> near-misses is budget not spent refining the best thing found so far.

---

## 3. Verdict, applied as declared

From the pre-registration, written before the numbers existed:

> **Fails** → the ~30-genome population is **not** what limits this search, and the discard rate is a
> property of the space rather than a defect. #101 closes as **measured and accepted**, with the
> population fact recorded so nobody re-derives it. The flag stays available and off.

Applied:

- **`--stepping-stones` stays OFF.** It is kept, working and tested, so that the exploration/exploitation
  trade can be revisited deliberately rather than re-implemented.
- **The discard rate is accepted as a property of the search space, not a defect.** 70–75% of genomes in
  this space genuinely do not trade enough, lose money, or breach the drawdown cap.
- **The population fact is recorded**: MAP-Elites here runs with ~30 parents, and *that is not what is
  limiting it*.

**I am not promoting the coverage numbers to a win.** They were pre-declared as secondary, and 3 of 5
went the treatment's way — but the criterion I registered was the peak, and the peak lost 7/8. If
coverage is the thing worth optimising, that is a different objective and needs its own pre-registered
test, not a reinterpretation of this one.

---

## 4. What this leaves

**`invalid` — the biggest group — was never addressed.** 45% of a cold run is genomes where a fold had
fewer than `min_trades`=5 trades, so `score_walkforward` returns nothing at all: no metrics, no niche, no
violation to rank by. Stepping stones structurally cannot reach them, which was stated before the run.

That is the remaining open question, and it is a different one: not *"can we use the near-misses?"* but
*"why does nearly half the search space fail to trade?"* — a question about `min_trades`, `gate_pct`,
`k`, and the shape of the sampled space, not about the archive.

---

## 5. Honest summary

| claim | status |
|---|---|
| ~70–75% of evaluations are discarded | **measured**, warm 69.2% / cold 74.6% |
| the archive is the population, and it holds ~30 genomes | **measured** |
| that small population is what limits the search | **REFUTED** — tripling it made the peak worse |
| widening the pool improves coverage | **observed** (secondary, not a registered claim) |
| the 45% "barely traded" group is understood | **no** — untouched, and the largest single cause |
