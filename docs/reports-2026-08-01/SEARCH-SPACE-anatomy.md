---
name: search-space-anatomy
description: Every one of the 470 strategy dimensions and the 11 fixed contributor dimensions, named individually — and what "strategy" means next to champion and playbook.
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
| **the strategy** | the *shape* — one box-breakout algorithm with a fixed set of knobs. It is not a name, it is a **space**: 470 numbers you could set. There is exactly one strategy. |
| **a champion** | **one point in that space.** A specific setting of all 470 knobs that won a search for one instrument on one timeframe. `NQ 4h` has a champion; `GC 15m` has a different one. 54 champions = 54 points in the same space. |
| **a playbook** | the human-readable document describing a champion — its rules, its numbers, its behaviour. A rendering, not a separate object. |

So when the plan says **470 dimensions**, it means: *the optimizer is choosing 470 numbers, and any
choice of all 470 is a candidate strategy.* A champion is the choice that won.

---

## 2. The 470 dimensions, itemised

Measured today at registry size 165, `force_eod=True`, no split SL/TP, no intracandle.

### 2.1 Base — the box and the risk rules (10 dimensions)

| # | dimension | type | range | what it does |
|---|---|---|---|---|
| 1 | `sl_soft` | continuous | per-instrument bounds | the soft stop distance |
| 2 | `sl_hard_delta` | continuous | `0 … sl_hard_max` | how far the hard stop sits beyond the soft one |
| 3 | `tp` | continuous | per-instrument bounds | take-profit distance |
| 4 | `gate_pct` | continuous | `0 … 100` | volatility gate percentile |
| 5 | `dd_limit` | continuous | `0 … DD_LIMIT_MAX` | drawdown breaker in dollars |
| 6 | `cooldown` | integer | `0 … cap` | bars to wait after an exit |
| 7 | `k` | integer | `1 … 5` | how many confirming votes an entry needs |
| 8 | `cap_1min` | integer | `1 … 1440` | maximum holding time in minutes |
| 9 | `flip` | categorical | `False / True` | whether a reverse signal flips the position |
| 10 | `en_cap_bars` | categorical | `False / True` | whether the bar-count cap is active |

> **`en_cap_eod` is not in this list any more.** The end-of-day close became the standard for all
> training on 2026-07-30 (#79), so it is **pinned ON** rather than searched — which is why base
> categorical is 2 and not 3. Pinning a knob removes a dimension.

### 2.2 Indicator layer (460 dimensions)

| part | count | what it is |
|---|---:|---|
| on/off flags | **165** | one `en_<name>` categorical per indicator in the registry |
| parameters | **295** | every parameter of every indicator (142 of the 165 have at least one) |

**460 of the 470 dimensions are the indicator layer.** The box itself is 10. That ratio is worth
holding on to: this is overwhelmingly a search over *which indicators, at what settings*, and only
marginally a search over stops and targets.

### 2.3 Not counted here

| | when it appears |
|---|---|
| `split` = 6 | `--split-sltp` — separate long/short SL/TP |
| `intracandle` = 3 | `--intracandle` |
| `contributors` = 471/token | `--contributors` **+ the fusion opt-in** (§3) |

---

## 3. The contributor block — 471 dimensions per token

This is the cross-instrument fusion feature: feeding ES bars into NQ's decisions.

### 3.1 The 11 fixed dimensions, each one named

"Fixed" means **they do not scale with the registry.** However many indicators exist — 15, 18, 165 —
these eleven are always eleven. That is the only sense in which they are fixed; every one of them is
searched.

| # | parameter | type | choices | what it decides |
|---|---|---|---|---|
| 1 | `es_enabled` | categorical | `False / True` | whether the contributor participates at all. **Searched, not forced** — the optimizer may decide the answer is "no" |
| 2 | `es_state` | categorical | `touch / traversal` | how ES's own box state is defined: price *touching* a level, versus *traversing* it |
| 3 | `es_sig_enc` | categorical | `none / stance / truthtable` | which encoding turns ES's state into a vote — no signal, a directional stance, or the full truth table |
| 4 | `es_sig_mode` | categorical | `confirm / veto / both` | whether that vote can confirm an entry, block one, or do either |
| 5 | `es_tt_long_long` | categorical | `confirm / veto / ignore` | NQ long **&** ES long |
| 6 | `es_tt_long_short` | categorical | `confirm / veto / ignore` | NQ long **&** ES short |
| 7 | `es_tt_long_hold` | categorical | `confirm / veto / ignore` | NQ long **&** ES flat |
| 8 | `es_tt_short_long` | categorical | `confirm / veto / ignore` | NQ short **&** ES long |
| 9 | `es_tt_short_short` | categorical | `confirm / veto / ignore` | NQ short **&** ES short |
| 10 | `es_tt_short_hold` | categorical | `confirm / veto / ignore` | NQ short **&** ES flat |
| 11 | `es_k_es` | integer | `1 … 5` | how many ES committee votes are needed to count as agreement |

Rows 5–10 are the **six-cell truth table**: two NQ directions × three ES states. It is the exhaustive
statement of "what does it mean when the other market is doing X while I want to do Y".

### 3.2 The other 460

The **committee** — the same 165 on/off flags and 295 parameters as §2.2, *again*, computed on ES's own
bars.

**That is the whole problem in one line: the contributor block contains a second complete copy of the
indicator search.** 11 + 165 + 295 = **471**, against a strategy search of 470. One contributor
**doubles** the problem. At the dimension-proportional budget: 94,100 trials × 8.4 s measured =
**≈ 9.1 days for one run** (#96).

---

## 4. Why it is now behind a two-step opt-in

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

## 5. The open question this leaves

**Can the second full-registry copy be avoided?** Ideas to test are yours (#96). Options already
visible from here:

- **scope the committee** — restrict it to the original 18 (what every deployed champion uses).
  `suggest_contributor` already accepts `only_committee`; the L1 optimizer never passes it, so
  `--only-indicators` currently scopes the strategy layer and **not** the committee.
- **fix the strategy, search only the contributor block** — cheapest, and aimed directly at "does the
  other market add anything".
- **accept it as is** — which is a legitimate answer once the cost is on the table rather than hidden.
