# Closeout — The Adopt Gate for the 143-Indicator Library (2026-07-28)

**Issue:** #14 (part of #12) · **Branch:** `research/14-adopt-gate` · **Status:** *(pending verdict)*

---

## 1. What the gate is for

#12 added **125 + 18 = 143 indicators**, taking the registry from 18 to 165. The temptation is to let the
optimizer search them and adopt whatever wins. That is precisely the multiple-comparisons trap: search
165 candidates against one price series and *something* will look excellent on the training window by
chance alone.

The gate exists so a lucky in-sample winner cannot become a champion. A candidate must beat **four**
numbers, not one:

| | what it is | why |
|---|---|---|
| **baseline** | the deployed champion, indicator layer frozen, on the 2026 holdout | the thing to beat |
| **treatment** | re-optimize with the whole library searchable, **on 2025 only**, then score best-on-train on 2026 | the candidate |
| **dumb control** | the identical search at the identical budget, with **placebo** votes | beating zero is not enough when a search over noise also produces a positive number |
| **noise** | the winner's own votes scrambled, 200 permutations | if the edge survives a shuffle it never came from the indicators |

Plus a **power** statement, because a null at low power says nothing and a positive without controls
says nothing either.

---

## 2. Three defects found before a single verdict was produced

This is the part worth reading. Each was found by measuring something rather than assuming it, and each
would have produced a **confident, meaningless** result.

### 2.1 The optimizer had no holdout at all

`score_walkforward` splits the **whole** series into folds — so 2025 *and* 2026 were both training data.
"Out-of-sample 2026" would have been nothing of the kind.

Fixed with `--train-window 2025`, which truncates every frame before anything is computed. Verified:
**2,119 → 1,534 decision bars**, exactly the split the issue specifies.

### 2.2 `--max-enabled` was testing the wrong indicators — all of them

`--max-enabled 3` caps how many indicators a trial may enable. The repair kept **"the first 3 in
REGISTRY order"**. That reads as neutral bookkeeping. It is not:

- registry positions **0–17** = the **original 18** indicators
- registry positions **18–164** = the **147 added by #12** — the ones this gate exists to evaluate

An original always won the tie. Measured on the live 16,000-trial study:

| | |
|---|---|
| trials sampled | 1,500 |
| trials containing **any** new-library indicator | **0 — 0.00%** |
| ten most-kept keys | `ema_trend`(0) `sma_trend`(1) `cci`(6) `macd`(2) `vwap`(3) `rsi`(7) `structure_trend`(12) `mfi`(9) `keltner`(4) `obv`(5) |

**A search built to evaluate 143 new indicators had, in 16,000 trials, tested none of them.** Both runs
were stopped mid-flight rather than spend another 2.5 hours measuring nothing.

The repair now draws an unbiased subset seeded by the trial number — reproducible per trial, independent
of registry position. After the fix, on live data: **98.1%** of trials contain a new-library indicator,
mean kept registry position **80.3** against an unbiased expectation of ~82.

> ⚠️ **This is a pre-existing flaw in `--max-enabled`, shipped with the library in #12 — not introduced
> here.** Any earlier run that used it believing it was "searching the 143 indicators" was also
> searching only the original 18.

`optimize/test_max_enabled_unbiased.py` pins it, and the tests were **verified to fail against the old
repair** (2 of 6) — a regression test that does not fail on the bug is worthless.

### 2.3 The dumb control was going to be scored with real votes

`extract` runs in a fresh process, so the control's winner would have been scored with **real**
indicator votes. The control asks *"what does this procedure score when the indicators carry no
information?"* — a statement about the whole pipeline under the null — so its holdout must be scored
with the **same placebo votes the search trained on**. With real votes it silently measures something
else (what an arbitrary real configuration earns) and stops being a null.

Fixed: `extract --scramble-seed <seed>` reinstalls the identical scrambler.

---

## 3. The power ceiling — measured three ways, and they agree

Before any verdict, the question that decides how to read it: **could this design detect an improvement
at all?**

**Per timeframe** (α=0.05, power=0.80, from each deployed champion's own 2026 holdout trades):

| TF | OOS trades | OOS P/L | smallest detectable improvement | as % of the whole OOS P/L |
|---|---:|---:|---:|---:|
| 4h | 81 | $61,601 | $55,920 | **91%** |
| 2h | 50 | $40,745 | $32,180 | 79% |
| 1h | 38 | $27,203 | $32,829 | 121% |
| 15m | 73 | $21,306 | $23,799 | 112% |
| 5m | 16 | $2,600 | $4,908 | 189% |
| 2m | 149 | $4,545 | $11,791 | 259% |

**Not one timeframe can detect an improvement smaller than ~79% of the strategy's entire holdout
profit.**

**Would pooling fix it?** Pooling raw dollars across all 9 instruments does not — mixing silver
($5,000/point) with Nasdaq ($20/point) inflates variance faster than *n* grows (MDE stays at 112% of
pooled P/L). Pooling **volatility-standardized** per-trade P/L is better but still weak:

| pooled n | MDE as % of the existing edge |
|---:|---:|
| 81 — NQ 4h alone, as the issue scopes it | **347%** |
| 400 | 156% |
| 1,571 — every live instrument×TF slot | **79%** |
| 4,000 | 49% |

**Does pairing fix it?** Partly, and less than I first claimed. Matching two strategies bar-by-bar makes
every shared trade contribute an exactly-zero difference, so only disagreements carry variance:

| | SE of the total difference | smallest detectable |
|---|---:|---:|
| unpaired | $36,352 | $101,844 |
| **paired** | **$23,045** | **$64,562** |

**1.58× more sensitive — measured, not asserted.** Pairing helps only in proportion to how many trades
the two variants share, and here they agree on just 45% of bars.

The paired machinery was validated against itself first: **champion vs champion → 81 paired bars, 100%
identical, total difference $0, CI [0, 0], p = 1.0.**

> A bug the self-check caught: the pairing key was `entry_time`, which `backtest_metrics` trades do not
> carry. Every lookup returned `None`, all 81 trades collapsed into one bucket, and the test silently
> degenerated to n=1. It is `entry_idx`; a missing key now raises.

**Bottom line on power: a candidate must roughly DOUBLE the strategy to register on this design.**

---

## 4. A finding that arrived for free

The paired ablation of the **deployed champion** — its 8 indicators ON vs the identical parameters with
them OFF:

| | |
|---|---:|
| indicators ON | $61,601 (81 trades) |
| indicators OFF | $22,138 (157 trades) |
| **paired difference** | **+$39,463** |
| 95% bootstrap CI | **[−$4,548, +$83,514]** |
| p | 0.089 |

The current champion's indicator layer looks worth ~$39k on the holdout — **but the interval crosses
zero.** Positive, and not distinguishable from luck at this sample size. That is a statement about the
test, not about the indicators.

---

## 5. Verdict — **DEFAULT-OFF**

47,100 trials of treatment and 47,100 of dumb control, both on the 2025 training window only, both
warm-started, `--max-enabled 3`, scored on the never-seen 2026 holdout.

| | holdout P/L | trades | indicators |
|---|---:|---:|---|
| **baseline** (deployed champion) | **$61,601** | 81 | the 8 original |
| **treatment** (best-on-train of 47,100) | **$18,827** | 157 | `apo`, `pivot_camarilla`, `dfa` |
| **dumb control** (placebo votes) | $14,039 | — | `hma`, `vidya`, `mama_fama` |

| # | criterion | result |
|---|---|---|
| 1 | beats baseline? | **NO** — Δ **−$42,774** |
| 2 | beats the dumb control? | YES — Δ +$4,788 |
| 3 | edge vanishes when its own votes are scrambled? | **NO** — permutation p = **0.124** (null mean $6,655, n=200) |
| 4 | paired 95% CI excludes zero? | **NO** — Δ −$42,774, CI **[−$92,499, +$6,432]**, p = 0.094 |

**⇒ DEFAULT-OFF. Nothing from the new library is adopted.**

### Read the rejection correctly

The verdict classifies itself as **CANNOT TELL**, not **NO EFFECT**: |−$42,774| < the minimum
detectable $71,183. Two different statements follow, and conflating them would be the mistake:

* **The decision is solid.** A candidate that lost by $42,774, cannot be shown to beat a placebo by
  more than $4,788, and whose edge does not survive scrambling its own votes, does not get adopted.
* **The scientific claim is not.** This design could not have detected a *real* improvement of the
  size observed, so the result is **not evidence that the 143 indicators are useless.** It is evidence
  that *this test cannot answer the question.*

### The pattern in the front — descriptive, and it should not be over-read

All five feasible front members, scored on the holdout:

| indicators | train (2025) | **holdout (2026)** | composition |
|---|---:|---:|---|
| `cci`, `structure_trend`, `order_block` | $99,580 | **$55,066** | all ORIGINAL |
| `obv`, `structure_trend`, `order_block` | $72,879 | **$52,438** | all ORIGINAL |
| `pvi`, `force_index`, `td_combo` | $88,680 | $20,295 | all NEW |
| `apo`, `pivot_camarilla`, `dfa` ← selected | $62,356 | $18,827 | all NEW |
| `ppo`, `smi`, `disparity` | $79,019 | $18,820 | all NEW |

Front members built from the **original** indicators hold out at ~$52–55k; those built from the **new**
library hold out at ~$19–20k, despite comparable or better training scores. That is a clean
train/holdout divergence in exactly the direction the multiple-comparisons trap predicts.

**Three caveats, all load-bearing:**
1. **n = 5.** This is a suggestive pattern, not a measurement.
2. Reading the best-*holdout* member would be **selecting on the test set** — the very trap the gate
   exists to prevent. $55,066 is a post-hoc observation, not "the treatment result".
3. **Even that best holdout member still loses to the baseline** ($55,066 vs $61,601).

### Why `selected` is not the highest train P/L in that table

The gate ranks the front by the optimizer's own objective — **median fold P/L** (walk-forward) — not by
the full-2025-window backtest shown in the column. They rank differently. Ranking by the optimizer's
objective is the defensible choice: it is the quantity the search actually maximised.

---

## 6. What was built

| file | purpose |
|---|---|
| `optimize/adopt_gate.py` | the gate: `baseline` · `search` (treatment/control) · `extract` · `paired` · `noise` · `verdict` |
| `optimize/optimizer.py` | `--train-window 2025` (a real holdout); unbiased `--max-enabled` repair; per-trial progress hook; trials record their enabled layer verbatim |
| `optimize/test_max_enabled_unbiased.py` | pins the anti-bias repair; verified to fail on the old one |
| `optimize/perf/check_max_enabled_bias.py` | reads a LIVE study and reports what the cap actually kept — run it before trusting any `--max-enabled` verdict |
| `optimize/perf/finish_adopt_gate.sh` | the closing pipeline as a real file, not a string through three layers of shell quoting |

---

## 6a. A fourth defect — caught because the number was too clean

The first verdict reported criterion 3 as `p = 1.0000, null mean $18,827` — the null mean *exactly*
equalling the observed value. Checking the distribution: **sd = $0.00.** All 200 permutations returned
the identical number. That is not a null distribution; it is a point mass wearing a p-value.

The two candidate causes were distinguished rather than guessed:

* *are the winner's indicators simply inert?* No — ON $18,827 / 157 trades vs OFF $12,271 / 193 trades.
* *is the harness broken?* **Yes.** `vote_cache`'s key is `(slice, indicator, mode, params)` — it knows
  nothing about the scramble seed. Permutation #1 wrote its scrambled votes to disk and permutations
  #2–200 read them straight back.

Redirecting the cache (which the code already did) is **not** enough — it has to be bypassed. Fixed,
plus a guard that now refuses to emit a p-value from a zero-spread null. The corrected run gives a real
distribution: **mean $6,655, sd $7,740, p = 0.124**.

The verdict's *direction* did not change — criteria 1 and 4 already failed decisively — but the reason
recorded for criterion 3 was wrong, and in a research record a wrong reason is worth as much as a wrong
result.

---

## 7. The through-line

Every one of the three defects had the same shape: **something that looked like neutral bookkeeping was
silently answering a different question.** Walk-forward folds that quietly included the holdout. A cap
that quietly excluded the entire library under test. A control that would quietly have been scored with
real data. None was visible by reading the code; each took a measurement — and the measurement was
cheap compared to the four hours of compute it saved or the wrong conclusion it prevented.
