---
name: scaling-and-autocorrelation-study
description: Brainstorm + empirical test of ALL target-scaling transforms (exp(change), sign×magnitude, z-score, vol-scaling, tanh/arcsinh, Box-Cox/Yeo-Johnson, rank, etc.) for the 1-min direction problem, measured by autocorrelation on real NQ data. Verdict no monotone rescale creates direction predictability (ACF invariant); the "wins" are artifacts; the only real signal is volatility. Also scaling matters for training stability (explains NBEATS blow-up), not for edge.
type: explainer
---

# Can a scaling transform make 1-min direction predictable? (full brainstorm + measured ACF)

> **Your idea:** 1-min changes are tiny, so train on `exp(change)`, and for direction use
> `exp(change)` multiplied by sign (− down / + up) — magnify the small numbers while keeping
> direction. **The right way to judge this (or any rescale):** does it raise the
> **autocorrelation** of the target? Autocorrelation = "does the last value echo into the
> next?" — the only thing a model can learn. If ACF stays ~0, no transform can help.
> I brainstormed the whole family of scaling techniques and **measured ACF(1) on all 486,968
> real NQ 1-min bars.** Script: `scripts/41_scaling_autocorrelation_study.py`.

---

## 1. The measured table (white-noise band = ±0.0028)

### Group 1 — direction-bearing rescales (monotone / sign-preserving)
| Transform | ACF(1) | verdict |
|---|---:|---|
| `r` log return (BASE) | −0.0061 | the signal: ~zero |
| `s` simple return | −0.0061 | identical |
| **`exp(r)` gross return ("exp the change")** | **−0.0061** | **identical — no effect** |
| `exp(s)` | −0.0061 | identical |
| **YOUR `sign·(exp|r|−1)` (smooth)** | **−0.0060** | **identical — no effect** |
| z-score(r) | −0.0061 | identical |
| min-max(r) | −0.0061 | identical |
| tanh(k·r) | −0.0112 | ~zero |
| arcsinh(k·r) | −0.0100 | ~zero |
| sign·log1p(k·|r|) | −0.0108 | ~zero |
| Yeo-Johnson(r) | −0.0058 | identical |
| vol-scaled `r/std₆₀` | −0.0085 | ~zero |

### Group 2 — transforms that *looked* predictable but are TRAPS
| Transform | ACF(1) | why it's a trap |
|---|---:|---|
| `diff(r)` | **−0.5076** | artifact: differencing white noise *manufactures* an MA(1) ≈ −0.5. Pure illusion, nothing to trade. |
| gaussian-rank(r) | +0.1715 | artifact: 1-min returns have huge **ties** (tick granularity, many exact-0 bars); ranking ties creates fake blocks → spurious ACF. |
| `sign·exp|r|` (discontinuous) | −0.0224 | this ≈ `sign(r)` itself (the exp magnitude is dwarfed by the ±1 jump). It only exposes the sign autocorrelation below. |
| `sign(r)` only | −0.0224 | the one *real* (tiny) effect — see §3. |

### Group 3 — different QUANTITY (volatility / even transforms) = the real signal
| Transform | ACF(1) | multi-lag |
|---|---:|---|
| `|r|` abs return | **+0.3758** | L1 .38 → L10 .32 (persistent) |
| `range` (hi−lo)/c | **+0.7476** | L1 .75 → L10 .64 (very persistent) |
| log|r| | +0.1364 | — |
| r² squared | +0.0430 | (low: fat tails dominate; |r|/range are the robust measures) |

---

## 2. The verdict on your idea (and all rescales)

**A monotone/affine rescale of the target cannot create predictability — and the data proves
it:** `exp(change)`, z-score, min-max, tanh, arcsinh, Yeo-Johnson, and your smooth
`sign·(exp|r|−1)` all land at **ACF ≈ −0.006**, byte-for-byte the same as the raw return. This
is expected: autocorrelation measures the *pattern*, and stretching the axis (which is all a
rescale does) doesn't add a pattern that wasn't there. `exp(r)` is literally the gross return
`Pₜ/Pₜ₋₁` — we'd already studied it (notes 19–23); it's the same information in new units.

**The transforms that appeared to "win" are illusions:**
- `diff(r)` = −0.51 is the textbook trap of **over-differencing**: differencing noise injects a
  fake −0.5 correlation that vanishes the moment you try to use it.
- gaussian-rank = +0.17 is a **ties artifact** — 1-min bars repeat exact values constantly, and
  ranking them fabricates structure. (A real danger: a naive pipeline could "discover" this and
  think it found signal.)
- `sign·exp|r|` just collapses to the sign (see §3) — the exponential adds nothing.

---

## 3. The one genuinely real (but un-tradeable) direction effect

`sign(r)` has ACF −0.0224, i.e. the next 1-min move continues the last direction only **46.3%**
of the time → a slight **mean-reversion** (it reverses 53.7%). That's real microstructure
(bid-ask bounce / tick mean-reversion), but it's (a) tiny and (b) exactly the kind of edge that
**transaction costs and the bid-ask spread eat alive** at 1-minute frequency. Your `sign·exp|r|`
construction surfaces this (its −0.0224 = sign's −0.0224), but the `exp` part contributes
nothing — and 0.02 is not a tradeable edge.

---

## 4. The nuance that IS true: scaling matters for *training*, not for *edge*

Your instinct isn't wrong about *something* — just aimed at the wrong outcome. Scaling **does**
matter, but for **numerical stability of the model**, not for predictability:
- This explains the C1 result: **NBEATS scored −531%** (RMSE 58.7) while **LSTM/Transformer tied
  naive** (−0.005%). Why? Darts internally scales the LSTM/Transformer targets, so they
  optimised cleanly and converged to the (correct) "≈ no change" answer. NBEATS as configured
  fit the raw tiny numbers, the loss was ill-conditioned, and it blew up.
- **Lesson:** always standardize/scale the target (z-score, or predict in "ticks") as hygiene —
  it prevents blow-ups and speeds convergence. But it raises the *floor*, never the *ceiling*:
  a well-scaled model still only *ties* naive on direction, because the ceiling is set by the
  autocorrelation (≈ 0), not by the units.

So: **use scaling everywhere as good practice; never expect it to manufacture an edge.**

---

## 5. Full brainstorm catalog (for the record) — and where each lands
| Family | Examples | Effect on direction ACF | Use it? |
|---|---|---|---|
| Identity/affine | raw, z-score, min-max | none (invariant) | yes (hygiene) |
| Monotone nonlinear | exp, log, sqrt, tanh, arcsinh, Box-Cox, Yeo-Johnson, signed-log | none meaningful | optional hygiene |
| Sign×magnitude | `sign·exp|r|`, `sign·sqrt|r|` | collapses to sign (~−0.02) | no edge |
| Distributional | gaussian-rank, quantile | **spurious** (ties) — avoid on tick data | caution |
| Differencing | `diff(r)`, fractional diff | **artifact** (induced MA) | no |
| Volatility-scaling | `r/σ` (devolatized) | still ~0 for direction | for vol-normalisation only |
| **Change the target** | `|r|`, `r²`, `range`, realized-vol | **+0.38 … +0.75 (REAL)** | **YES — this is the signal** |

The table's bottom row is the whole point: **stop transforming the direction target; switch to a
volatility target.** That is Workstream C2.

---

## 6. Conclusion → next step
1. **No scaling technique makes 1-min direction predictable.** Proven empirically — every
   monotone rescale gives ACF ≈ −0.006; the apparent wins are differencing/ties artifacts; the
   only real direction effect (−0.02 mean-reversion) is sub-cost.
2. **Scale targets anyway for training stability** (it's why NBEATS blew up and LSTM didn't).
3. **The predictable thing is volatility** (range ACF 0.75, persistent to lag 10). 
   → **Proceeding to C2: deep learning on the 1-min volatility/range target**, where scaling +
   data + model capacity finally have real signal to work with.

## 7. One-paragraph summary (baby)
We asked whether shrinking-then-magnifying the tiny 1-minute change (your `exp(change)` ×
sign idea) — or any other rescaling trick — could make the *direction* predictable. We measured
the autocorrelation of ~20 different transforms on half a million real bars. Answer: **no.**
Stretching the numbers doesn't add a pattern; `exp(change)` and friends have the exact same
near-zero autocorrelation as the raw change. A couple of transforms *looked* promising but were
mirages (differencing and rank-on-tied-data invent fake patterns), and the only genuine effect
(prices slightly bounce back over one minute) is too small to beat trading costs. The real,
honest takeaway is twofold: (1) always scale your targets so models train cleanly — that's why
the unscaled NBEATS exploded while the scaled LSTM behaved — but (2) scaling fixes *stability*,
never *predictability*. The thing that genuinely echoes minute-to-minute is **volatility**
(how big the move is), so that's exactly where we point the models next.
