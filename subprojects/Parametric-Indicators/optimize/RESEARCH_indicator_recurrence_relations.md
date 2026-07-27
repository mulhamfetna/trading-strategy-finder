# Research — Indicator Incremental-Recurrence Study

> **⚠️ SCOPE NOTE (added 2026-07-27):** this study classifies the **original 21** indicator functions. The
> library is now **165**, and the indicators that actually dominate cost today (`dfa`, `autocorr`,
> `hurst_exp`, `sinewave`, `ifvg`, …) **are not covered here**. Its *conclusions remain valid for the
> functions it examines* — and one of them proved directly load-bearing: it correctly identified that the
> expensive cases are **batch recomputation**, not streaming, which is why the 2026-07 fixes used
> closed-form/Numba rather than an incremental rewrite. For the current cost picture see
> `REPORT_indicator_cache_acceleration.md` and `REPORT_post_dfa_tail.md`.

**Date:** 2026-06-11 · task #210 side-research · branch `dev`
**Question.** Our indicators are computed over a **moving window**. For each one, does it admit an
**incremental recurrence** — i.e. can `Uₙ` be obtained from the *previous* output `Uₙ₋₁` (or a small,
fixed amount of carried state) plus the new candle, instead of recomputing the whole window?
Formally: does the window form `Uₙ = f(window of n candles)` collapse to `Uₙ = g(Uₙ₋₁, new, old)`?

This is the classic **batch → online/streaming** transformation. Below: every indicator in the library,
classified; and for the ones that qualify — previous formula, recurrence formula, computational cost
(old vs new), implementation complexity, and time complexity.

> **Baby framing.** "Recompute the window" = every minute, re-add the last 45 numbers from scratch.
> "Recurrence" = keep the last answer and just nudge it with the one new number (and drop the one that
> fell off the back). The question is which indicators allow that nudge, exactly.

---

## 0. The four classes (definitions)

| Class | Meaning | One-line test |
|------:|---------|----------------|
| **A** | **True O(1) value recurrence** `Uₙ = g(Uₙ₋₁, …)` | the next value is the previous value plus a fixed arithmetic nudge |
| **B** | **O(1)-amortized incremental, but needs an auxiliary structure** (not a plain arithmetic recurrence) | a sliding ext\-rema / order statistic — needs a deque, not a formula |
| **C** | **No incremental form** — must touch the whole window each bar | the per-element contribution changes when the window's summary changes |
| **D** | **Already sequential/stateful** (online by construction; no window to collapse) | it already carries running state per bar |

Notation: `N` = series length (~486,969 for the 1-minute frame), `n` = window length, `W=n`.
"Per-bar" cost × `N` = total. Current Python implementations differ from the *algorithmic* class — a thing
can be Class A yet still coded as a slow loop (that's a *constant-factor* problem, not a complexity one).

---

## 1. Master classification (all 21 functions)

| # | Indicator | Math core | Class | Has recurrence? | Already exploited? |
|--:|-----------|-----------|:-----:|:---------------:|--------------------|
| 1 | `sma` | rolling mean | **A** | ✅ | ✅ (cumsum) |
| 2 | `ema` | exponential MA | **A** | ✅ (intrinsic) | ✅ (loop = the recurrence) |
| 3 | `rma` (Wilder) | exponential MA, α=1/n | **A** | ✅ (intrinsic) | ✅ (loop) |
| 4 | `rsi` | RMA of gains/losses | **A** | ✅ (via RMA) | ✅ (loop) |
| 5 | `true_range` | pointwise max of 3 | — | n/a (no window) | ✅ vectorized |
| 6 | `atr` | RMA(true_range) | **A** | ✅ (via RMA) | ✅ (loop) |
| 7 | `macd` | EMA−EMA, EMA of that | **A** | ✅ (via EMA) | ✅ (loop) |
| 8 | `obv` | signed cumulative volume | **A** | ✅ (prefix sum) | ✅ (cumsum, Step D) |
| 9 | `vwap` | session cumulative Σtp·v / Σv | **A** | ✅ (running sums) | ✅ (loop) |
| 10 | `mfi` | rolling sums of ± money flow | **A** | ✅ (sliding sum) | ◑ (window-view, not true sliding) |
| 11 | `bollinger` (std) | rolling population std | **A\*** | ✅ via moments **(precision-unsafe)** | ✗ (uses exact window-view) |
| 12 | `keltner` | EMA ± m·ATR | **A** | ✅ (via EMA+ATR) | ✅ |
| 13 | `adx` | RMA of DM/TR, RMA of DX | **A** | ✅ (via RMA) | ✅ (loops) |
| 14 | `stochastic` (%K) | rolling max & min | **B** | ⚠️ via **monotonic deque** | ✗ (per-bar `np.max/min` loop) |
| 15 | `stochastic` (%D) | SMA of %K | **A** | ✅ (sliding mean) | ✅ |
| 16 | `cci` | rolling **mean-abs-deviation** | **C** | ❌ **none** | — (vectorized only, Step A2) |
| 17 | `market_structure` | local fractal extrema (±swing\_l) | **B**\* | ⚠️ tiny fixed window | ✗ (small `.all()` loop) |
| 18 | `structure_trend` | swing HH/HL vs LH/LL stance | **D** | ✅ (carries swing lists) | ✅ (already stateful) |
| 19 | `order_blocks` | live supply/demand zones | **D** | ✅ (carries zones) | ◑ stateful, but inner O(zones) scan |
| 20 | `fvg` / `fvg_active_direction` | 3-bar gap + carry last dir | **D** | ✅ (pointwise + carry) | ✅ |
| 21 | `golf_candle` | N-bar engulfing | — | n/a (fixed pattern, O(n) pointwise) | ✅ |

**Headline counts:** **HAS a usable recurrence (A) — 12** (sma, ema, rma, rsi, atr, macd, obv, vwap, mfi,
keltner, adx, stochastic-%D). **Incremental-via-structure (B) — 2** (stochastic max/min, market_structure
extrema). **No recurrence (C) — 1** (cci). **Already-stateful (D) — 3** (structure_trend, order_blocks,
fvg). The rest are pointwise (no window).

---

## 2. Class A — true O(1) recurrences (full detail)

### 2a. The EMA family — `ema`, `rma`, `rsi`, `atr`, `macd`, `keltner`, `adx`
These are **intrinsically recursive already** — there is no "window" to collapse; the definition *is* the
recurrence. They are algorithmically optimal (O(N)); the only available speed-up is the **constant factor**
(replace the Python loop with a C-level pass).

| | |
|---|---|
| **Previous formula** | `ema[t] = α·x[t] + (1−α)·ema[t−1]`, α=2/(n+1) (EMA); `rma[t] = (1/n)·x[t] + (1−1/n)·rma[t−1]` (Wilder). RSI/ATR/MACD/Keltner/ADX are compositions of these + pointwise terms. |
| **"New" formula** | identical — it already is `Uₙ=f(Uₙ₋₁)`. |
| **Cost (old)** | Python loop: **O(N)** flops but slow per-iteration (interpreter overhead). |
| **Cost (new)** | same O(N), but vectorizable via `scipy.signal.lfilter([α],[1,−(1−α)],x)` or a Numba `@njit` loop → ~50–100× constant-factor. |
| **Impl complexity** | EMA/RMA: **trivial** (one `lfilter` call) — but mind the seed (`out[0]=x[0]`) and RMA's NaN-hold rule. |
| **Time complexity** | **O(N)** (unchanged); only the constant shrinks. |
| **Precision** | `lfilter` reproduces the recurrence in float64 to ~1 ULP; must verify bit-identity (the seed + NaN-hold are the only subtleties). |

### 2b. `sma` — rolling mean
| | |
|---|---|
| **Previous** | `sma[t] = (1/n)·Σ_{i=t−n+1}^{t} x[i]` → O(n)/bar naively. |
| **Recurrence** | `sma[t] = sma[t−1] + (x[t] − x[t−n]) / n` (add the entrant, drop the leaver). |
| **Cost** | old O(N·n) naive; **new O(N)**. (Repo already uses `cumsum` → O(N), equivalent.) |
| **Impl** | **trivial**. | **Time** | **O(N)**. | **Precision** | cumsum is exact-ish; the +new/−old form can drift over very long N (running-sum rounding) — cumsum preferred. |

### 2c. `mfi` — rolling sums of positive / negative money flow
| | |
|---|---|
| **Previous** | `MF±[t] = Σ_{window} pos/neg flow`; `MFI = 100 − 100/(1+ Σpos/Σneg)` → O(n)/bar. |
| **Recurrence** | `Spos[t] = Spos[t−1] + pos[t] − pos[t−n]`; `Sneg` likewise → O(1)/bar. |
| **Cost** | old O(N·n); **new O(N)**. (Repo currently uses `sliding_window_view(...).sum` — O(N·n) work + O(N·n) memory; a true sliding sum or cumsum-diff is O(N) and memory-light.) |
| **Impl** | **easy**. | **Time** | **O(N)**. | **Precision** | cumsum-diff is exact for integers-ish; running-sum drift negligible at N~5e5. |

### 2d. `obv`, `vwap` — cumulative recurrences
| | |
|---|---|
| **obv prev/new** | `obv[t] = obv[t−1] + sign(c[t]−c[t−1])·v[t]` — already a pure recurrence; **Step D** implemented it as `cumsum`. O(N). |
| **vwap** | within a session: `cpv[t]=cpv[t−1]+tp·v`, `cv[t]=cv[t−1]+v`, `vwap=cpv/cv`; reset on session change. O(1)/bar, O(N). Already a loop = the recurrence. |
| **Impl** | trivial. **Time** O(N). **Precision** exact (cumsum) / running-sum (fine). |

### 2e. `bollinger` rolling std — recurrence exists but is **precision-unsafe** ⚠️
| | |
|---|---|
| **Previous** | `std[t] = sqrt( (1/n)·Σ(x_i − mean[t])² )` over the window → O(n)/bar. |
| **Recurrence (moments)** | keep `S1[t]=S1[t−1]+x[t]−x[t−n]` and `S2[t]=S2[t−1]+x[t]²−x[t−n]²`; then `var[t]=S2[t]/n − (S1[t]/n)²`, `std=√var`. **O(1)/bar**. |
| **Cost** | old O(N·n); recurrence O(N). |
| **Impl** | moderate. **Time** O(N). |
| **⚠️ Precision** | **catastrophic cancellation.** NQ prices ≈ 21,000, window std ≈ tens. `S2/n ≈ 4.4×10⁸` and `(S1/n)² ≈ 4.4×10⁸` — subtracting two huge near-equal numbers destroys ~8 significant digits → the result is **not** bit-identical and can flip discrete votes. The exact windowed std (our Step A1 `sliding_window_view().std`) avoids this and is already 40×. **Verdict: the recurrence exists but we must NOT use it** under the bit-identical mandate. (A *windowed Welford* removal is more stable but still not exact and far more complex.) |

---

## 3. Class B — incremental, but needs a data structure (not a value recurrence)

### 3a. `stochastic` %K — rolling **max** and **min**
| | |
|---|---|
| **Previous** | `hh[t]=max(x[t−n+1..t])`, `ll[t]=min(...)` → O(n)/bar (current `_roll_max/_roll_min` Python loops → O(N·n)). |
| **"New"** | **monotonic deque**: maintain a deque of indices whose values are decreasing (for max); on each bar pop smaller values off the back, append `t`, evict the front if it fell out of the window; the front is the window max. **Amortized O(1)/bar** (each index pushed/popped once). |
| **Cost** | old O(N·n); **new O(N) amortized**. |
| **Impl** | **moderate** (deque bookkeeping; mirror for min; NaN handling). Not a one-liner, but a textbook pattern. |
| **Time** | **O(N) amortized** (worst-case O(N) too). |
| **Precision** | **exact** — it selects actual array elements, no arithmetic → bit-identical. **This is the cleanest genuine algorithmic win available** (O(N·n)→O(N), exact). |

### 3b. `market_structure` — local fractal extrema over ±`swing_l`
Same *shape* as 3a but the window is tiny (`swing_l` ~2–10) and symmetric, so it's effectively O(1)/bar
already; a deque would help only at large `swing_l`. Low priority. **Class B**, but marginal.

---

## 4. Class C — NO incremental recurrence

### `cci` — rolling **mean-absolute-deviation**
| | |
|---|---|
| **Formula** | `MAD[t] = (1/n)·Σ |tp_i − mean[t]|`, `cci = (tp − mean)/(0.015·MAD)`. |
| **Why no recurrence** | when the window slides, `mean[t]` shifts, so **every** term `|tp_i − mean|` changes — and the absolute value is **non-linear / non-separable**, so you cannot update `MAD[t]` from `MAD[t−1]` by an add/drop. (Variance works because squares expand into separable moments; absolute value does not.) |
| **Best achievable** | O(N·n) (exact) — our Step A2 vectorized it (sliding window, 4×) but it remains window-bound. Sub-O(N·n) only via **approximation** (e.g. order-statistic trees for a *median*-abs-dev, or histogram bucketing) — which would **change the numbers** and is therefore disallowed here. |
| **Impl / Time** | impl: n/a (no exact recurrence). Time: **O(N·n)** unavoidable for the exact value. |

> **This is the single indicator that genuinely "doesn't have it."** Its cost is intrinsic.

---

## 5. Class D — already sequential / stateful (online by construction)

`structure_trend`, `order_blocks`, `fvg`/`fvg_active_direction` do **not** recompute a window — they carry
running state per bar (swing lists, live zones, last-gap direction). They are already "`Uₙ = f(state, new)`".
- **structure_trend**: O(1) amortized per bar (appends swings). Fine as-is.
- **order_blocks**: O(1) state update **but** an inner per-bar loop scans live zones → O(zones). The *recurrence* isn't the issue; the **zone scan** is. Fix is (a) cap/prune zones, (b) compute the overlap only at sampled bars, or (c) Numba — **not** a window-recurrence question.
- **fvg**: pointwise 3-bar pattern + a carried "last direction" → already O(1)/bar.

---

## 6. So what should we actually do? (ties to task #210)

Filtering the above by our hard rule (**bit-identical results, speed only**):

| Opportunity | Class | Exact? | Gain | Worth it? |
|-------------|:-----:|:------:|------|-----------|
| **stochastic max/min → monotonic deque** | B | ✅ exact | O(N·n)→O(N) | **Yes** — genuine algorithmic win, bit-identical (best new finding) |
| **mfi → true sliding sum / cumsum-diff** | A | ✅ exact | O(N·n)→O(N) + less memory | **Yes** (small, clean) |
| **EMA-family → `lfilter`/Numba** | A | ✅ ~exact | constant-factor ~50–100× on the loops (ema/rma/rsi/atr/adx/macd/keltner) | **Yes** — big constant-factor, but verify bit-identity of the seed/NaN-hold |
| **sma / obv / vwap** | A | ✅ | already O(N) | already done |
| **bollinger moments recurrence** | A\* | ❌ precision | O(N) | **No** — breaks bit-identity; keep the exact window-view (Step A1) |
| **cci** | C | — | none exact | **No recurrence exists**; vectorization (done) is the ceiling |

**Net new actionable items surfaced by this study** (beyond the original plan):
1. **stochastic deque** (exact O(N·n)→O(N)) — add to Phase 1/A3.
2. **mfi sliding-sum** (exact, memory-light) — refine Step A3.
3. **EMA-family constant-factor** via `scipy.signal.lfilter` or Numba — a Phase-2 acceleration of the
   recurrences we already have (ema/rma/rsi/atr/adx are Python loops today).
4. Confirmed: **bollinger** must stay window-exact (no recurrence) and **cci** has **no** recurrence —
   so neither should be "optimized" past their current exact vectorization.

---

## 7. One-screen summary

```
HAS recurrence (use it, exact):   sma, mfi, obv, vwap, stochastic-%D            → sliding sum/mean
HAS recurrence (intrinsic loop):  ema, rma, rsi, atr, macd, keltner, adx        → speed via lfilter/Numba
HAS recurrence (DO NOT use):      bollinger std (moments)                       → precision-unsafe
INCREMENTAL via deque (exact):    stochastic max/min, (market_structure)        → monotonic deque, O(N)
NO recurrence (window-bound):     cci (mean-abs-deviation)                       → exact cost is O(N·n)
ALREADY stateful/online:          structure_trend, order_blocks, fvg            → fix zone-scan, not window
POINTWISE (no window):            true_range, golf_candle                       → already O(N)
```

**Bottom line:** of the windowed indicators, **only `cci` truly lacks an incremental recurrence.**
Everything else is either already incremental, or can be made so exactly — with the important exception
that **`bollinger`'s** recurrence is mathematically real but numerically unsafe, so we deliberately keep
its exact window form. The highest-value *new* exact win this study surfaces is the **monotonic-deque
rolling max/min for `stochastic`** (O(N·n)→O(N), bit-identical).
