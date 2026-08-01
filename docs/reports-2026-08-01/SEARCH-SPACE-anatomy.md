---
name: search-space-anatomy
description: Every one of the 466 strategy dimensions and the 10 fixed fusion dimensions, named individually — what "strategy" means next to champion and playbook, and whether encoding off inside a parameter value would work.
type: reference
date: 2026-08-01
issue: 96
---

# What the search space is actually made of

Written because "the strategy's own 470 dimensions" is not a self-explaining phrase. Every number here
is read from the code, not remembered.

---

## 1. "Strategy" vs "champion" vs "playbook"

These are three different things and the words get used interchangeably, which is what made the
question necessary.

| term | what it is |
|---|---|
| **the strategy** | the *shape* — one box-breakout algorithm with a fixed set of knobs. It is not a name, it is a **space**: 466 numbers you could set. There is exactly one strategy. |
| **a champion** | **one point in that space.** A specific setting of all 466 knobs that won a search for one instrument on one timeframe. `NQ 4h` has a champion; `GC 15m` has a different one. 54 champions = 54 points in the same space. |
| **a playbook** | the human-readable document describing a champion — its rules, its numbers, its behaviour. A rendering, not a separate object. |

So when the plan says **466 dimensions**, it means: *the optimizer is choosing 466 numbers, and any
choice of all 466 is a candidate strategy.* A champion is the choice that won.

---

## 2. Does removing a dimension halve the space?

**No — and the difference matters for deciding what to remove.**

Halving is only true for a **binary** dimension. The space is a *product* of each axis's cardinality:

| dimension type | example | what removing it divides the space by |
|---|---|---|
| binary | `flip`, `en_cap_bars` | **2** |
| integer | `cooldown` (`0…cap`) | **cap + 1** — for a 4h cap that is ~30, not 2 |
| continuous | `dd_limit`, `sl_soft` | **infinite** — a float axis has no finite count |

So retiring `dd_limit` did not halve anything: it removed an entire continuous axis. Retiring
`cooldown` removed an axis with tens of values, not two.

**What is linear rather than multiplicative is the BUDGET.** `--auto-trials` charges
`dimensions × 100`, so each retired dimension is worth exactly 100 trials, no matter its type. Those
are two different quantities and it is easy to conflate them:

- **budget** — linear. 470 → 466 dims = 47,000 → 46,600 trials.
- **volume** — multiplicative, and dominated by the continuous axes.

The honest summary of these four retirements: a **small** budget saving (−400 trials) and a
**large** structural saving, because two of the four axes were unbounded.

---

## 3. The dimensions today — 466

Read from the code at registry size 165, `--force-eod` (the standard), bars cap pinned off, no split
SL/TP, no intracandle, no fusion.

### 3.1 Base — 6 dimensions

| # | dimension | type | what it does |
|---|---|---|---|
| 1 | `sl_soft` | continuous | soft stop distance |
| 2 | `sl_hard_delta` | continuous | how far the hard stop sits beyond the soft one |
| 3 | `tp` | continuous | take-profit distance |
| 4 | `gate_pct` | continuous | volatility gate percentile |
| 5 | `flip` | categorical | whether a reverse signal flips the position |
| 6 | `k` | integer `1…5` | how many confirming votes an entry needs |

### 3.2 Retired from the search — 4 dimensions gone

| dimension | was | now | why |
|---|---|---|---|
| `dd_limit` | continuous `0…max` | **pinned 0** | user decision, 2026-08-01 |
| `cooldown` | integer `0…cap` | **pinned 0** | user decision, 2026-08-01 |
| `en_cap_bars` | categorical | **pinned False** | `--search-cap-bars` puts it back |
| `cap_1min` | integer `1…1440` | **not drawn** | it is only read when the bars cap is on; searching it while the cap is pinned off is a knob nothing reads |
| `en_cap_eod` | categorical | **pinned True** | earlier — the end-of-day close is the standard (#79) |

> ⚠️ **Retired from the SEARCH, not deleted from the ENGINE — and the measurement is why.**
> `dd_limit` is non-zero in **54 of 54** deployed champions (100%); `cooldown` in **40 of 54** (74%).
> Deleting the terms from the engine would change every deployed trade ledger and break all six golden
> baselines at once. New champions train without them; existing ones keep running until retrained.
> That is the same split #79 made for the end-of-day close. **Deleting the engine terms is available
> on request — it is a deliberate retirement of the whole deployed book, not a side effect.**

### 3.3 Indicator layer — 460 dimensions

| part | count |
|---|---:|
| on/off flags (`en_<name>`) | **165** |
| parameters | **295** (142 of the 165 indicators have at least one) |

**460 of the 466 are the indicator layer.** The box itself is now 6. §5 is about whether those 460
can be compressed.

### 3.4 Totals

| configuration | dimensions | ∝ budget |
|---|---:|---:|
| **default today** | **466** | 46,600 |
| `--search-cap-bars` | 468 | 46,800 |
| + one fusion contributor | 936 | 93,600 |

---

## 4. The fusion block — 470 per token, and 10 fixed

### 4.1 The fixed dimensions, each named

"Fixed" means **they do not scale with the registry** — 15 indicators or 165, these are always the
same count. Every one is searched.

| # | parameter | choices | what it decides |
|---|---|---|---|
| 1 | `es_state` | `touch / traversal` | how ES's own box state is defined |
| 2 | `es_sig_enc` | `none / stance / truthtable` | which encoding turns ES's state into a vote |
| 3 | `es_sig_mode` | `confirm / veto / both` | whether that vote can confirm, block, or either |
| 4 | `es_tt_long_long` | `confirm / veto / ignore` | NQ long **&** ES long |
| 5 | `es_tt_long_short` | `confirm / veto / ignore` | NQ long **&** ES short |
| 6 | `es_tt_long_hold` | `confirm / veto / ignore` | NQ long **&** ES flat |
| 7 | `es_tt_short_long` | `confirm / veto / ignore` | NQ short **&** ES long |
| 8 | `es_tt_short_short` | `confirm / veto / ignore` | NQ short **&** ES short |
| 9 | `es_tt_short_hold` | `confirm / veto / ignore` | NQ short **&** ES flat |
| 10 | `es_k_es` | integer `1…5` | how many ES committee votes count as agreement |

Rows 4–9 are the **six-cell truth table**: two NQ directions × three ES states.

> **`es_enabled` was #11 and is gone (2026-08-01).** Whether the fusion block participates is a
> **human switch**, not an optimizer choice. You have already had to name the token *and* acknowledge
> the opt-in; spending trials re-deciding the question after two deliberate acts is absurd. It also
> wasted half of every trial's contributor work on genomes where `es_enabled=False`.

### 4.2 The other 460

The **committee** — the same 165 flags and 295 parameters as §3.3, again, on ES's own bars. A second
complete copy of the indicator search. **10 + 460 = 470 per token**, against a strategy search of 466.
One contributor still roughly doubles the problem; that is #96's open question.

---


## 5. Your idea — can "off" live inside the parameter value?

**The proposal:** drop the 165 `en_<name>` flags and let a parameter value encode the off state — e.g.
`n = 0` means *this indicator is off*. One unified axis per indicator instead of a flag plus params.

**Verdict: the compression is real, but this particular encoding would make every indicator
permanently ON. Your instinct about the genetic algorithm is exactly right, and it is worse than
"might not reach zero".**

### 5.1 Why, precisely

Today the flag is `suggest_categorical([False, True])`, so **P(off) = 0.5 exactly, by construction**.
Now put "off" inside the value:

| parameter type | example | P(sampling the off value) on a fresh draw |
|---|---|---|
| **continuous float** | `k = 4.3` in `[0.5, 5.0]` | **exactly 0** — a single point on a real interval has zero measure. The optimizer will *never* sample it, not "rarely" |
| **integer** | `n` in `[5, 400]` | **~1/396 ≈ 0.25%** |
| **categorical** | a 3-choice param | 1/3 |

So for the 142 indicators that have parameters, "off" goes from **a 50% chance to somewhere between
0.25% and literally never**. The search would not be choosing indicators any more — it would be
running all 165 and tuning them.

**That is the failure you predicted**, and it is not a tuning problem: for float parameters it is a
mathematical impossibility, not an unlucky sampler.

### 5.2 The genetic operators make it worse, not better

NSGA-III moves by crossover and mutation **on the values**. There is no "snap to off" move. An
indicator that is on can only become off if some operator lands exactly on the off value — so on a
float axis the off state is unreachable *even in principle*, and on an integer axis it is a ~0.25%
lottery per mutation. Once every indicator is on, nothing pulls any of them back off.

### 5.3 What it actually saves is less than it looks

It removes 165 **binary** axes. Per §2, each is worth a factor of 2 in volume and 100 trials in
budget — so **−16,500 trials**, which is real. But it keeps all 295 parameter axes, which are the
continuous and integer ones — **the axes that dominate the volume stay exactly as they are.**

### 5.4 The real waste is somewhere else — and I verified it

`_suggest_indicators` draws **every indicator's parameters on every trial, whether or not that
indicator is enabled.** The space is deliberately "rectangular" so NSGA-III sees a fixed dimension
set.

So on a trial with 7 indicators enabled — a realistic champion — **the search is still drawing all
295 parameters, 288 of which are read by nothing.** That is the compression worth chasing, and it does
not require touching the on/off semantics at all.

### 5.5 Two versions that would work

**(a) Conditional parameters.** Draw an indicator's parameters *only when its flag is on*. Optuna
supports this — the search space becomes dynamic per trial. Nominal dimensions stay 466, but the
**effective** dimensionality of a typical trial falls from ~460 to ~20. Keeps P(off) = 0.5 exactly.
Open question: how well NSGA-III's crossover behaves when two parents have different parameter sets.

**(b) Count-then-membership** — the fix already adopted for MAP-Elites (#81). Sample *how many*
indicators are on, then *which*. This makes the on/off structure explicit and low-dimensional, and it
is immune to the registry growing, which is the whole S2 lesson.

These are complementary: (b) controls the shape, (a) removes the dead draws.

### 5.6 The proof of concept you asked for

You are right that this needs evidence, not argument, and right that it is cheap next to an 18-day
run. Design:

1. **Instrumentation first.** Log, per trial, how many indicators were enabled and which. That alone
   answers "does it reach off" for any encoding, and we currently do not record it.
2. **Three arms, identical seed and budget:** today's flags · value-encoded off · conditional params.
3. **The measurement that decides:** the distribution of *enabled count* across trials. Today's arm
   should centre near 82 (half of 165); the value-encoded arm is predicted to sit at or very near
   **165 — every indicator always on**. If it does, the encoding is refuted without needing any P&L.
4. **Only if it survives that**, compare scores at equal budget.
5. Short timeframe, small trial count — this is a *sampling* question, not a profitability one, so it
   does not need a champion-grade run.

The prediction in step 3 is falsifiable and cheap. That is the point: it fails fast if I am wrong.

---

## 6. Why the fusion block is behind a two-step opt-in

It was already off by default. That was not enough, because **off-unless-you-type-a-flag is not the
same as cannot-be-switched-on-by-accident** — `--contributors ES` is one word, and everything above is
invisible until much later.

It now takes **two deliberate acts**: naming the tokens, *and* `--enable-fusion-contributors` (or
`WSH_ENABLE_FUSION_CONTRIBUTORS=1`). Refusing prints the cost rather than just saying no, and exits
with code **4** — distinct from the preflight refusal (3) and from a crash — so a launcher can tell
"you did not opt in" from "the run failed".

The gate applies in **both** optimizers and in `RunSpec`, so the control centre cannot acknowledge on
the operator's behalf: a `RunSpec` that merely names tokens hits the same refusal a human would.

Only the literal `"1"` enables it via the environment. A stray `WSH_ENABLE_FUSION_CONTRIBUTORS=false`
in a shell profile must not turn it on — an ambiguous opt-in is not an opt-in.

**This does not remove the capability.** ES-as-a-contributor stays fully usable for the fusion studies
it belongs to; it simply cannot arrive by accident in ordinary optimizer work.

---

## 7. The open question this leaves

**Can the second full-registry copy be avoided?** Ideas to test are yours (#96). Options already
visible from here:

- **scope the committee** — restrict it to the original 18 (what every deployed champion uses).
  `suggest_contributor` already accepts `only_committee`; the L1 optimizer never passes it, so
  `--only-indicators` currently scopes the strategy layer and **not** the committee.
- **fix the strategy, search only the contributor block** — cheapest, and aimed directly at "does the
  other market add anything".
- **accept it as is** — which is a legitimate answer once the cost is on the table rather than hidden.
