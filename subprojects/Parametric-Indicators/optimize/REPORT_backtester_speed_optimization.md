> # ⚠️ SUPERSEDED — DO NOT OPTIMIZE FROM THIS PROFILE
>
> **Profile valid as of 2026-06-11, at ~21 indicators.** The library has since grown to **165**, and the
> cost distribution moved **entirely**. This document's hot list (`smc.order_blocks` 18.5 s, `bollinger`
> 10.7 s, `cci` 6 s) is **no longer where the time goes**.
>
> **What was actually true on 2026-07-27:** one indicator, **`dfa`, was 81% of all indicator compute**
> (up to 756 s for a single compute) — it did not exist when this was written. See
> **`REPORT_indicator_cache_acceleration.md`** for the current profile, and
> **`REPORT_post_dfa_tail.md`** for the worst-case-parameter picture.
>
> This document is retained for its **method** (how to profile, the options taxonomy) and as the origin of
> several still-valid conclusions — e.g. that GPU/Dask are the wrong tool for this workload, which the 2026-07
> work independently re-confirmed. Its **numbers** are historical.
>
> Nearly optimizing from this stale report is the incident that produced
> **`docs/EXPANSION_ROUND_PLAYBOOK.md`** (rule **P1**: never optimize from an old profile; re-profile after
> every expansion round).

# Backtester Speed Optimization — Deep Analysis & Improvement Study

**Date:** 2026-06-11 · branch `dev` · relates to task #210
**Subject:** Since indicators moved to the **1-minute frame**, a single backtest went from sub-second to
**~37 seconds**. This report profiles the system, pinpoints exactly where the time goes, and studies
every realistic speed-up — each with professional detail, a plain-language ("baby") explanation, and an
honest pros/cons + risk assessment. **Hard rule throughout: speed only — results must not change**
(parity `$7,735 / $3,670 / n=66`; the wsh4 4h champion `$142,203`).

---

## 0. TL;DR

| | |
|---|---|
| **Measured cost** | one 4h backtest = **37.1 s** warm; ~99% is indicator compute on the 487k-row 1-minute series. |
| **#1 culprit** | `smc.order_blocks` ≈ **18.5 s** (50%) — a stateful per-bar Python loop, run **~2× redundantly**. |
| **#2–#3 culprits** | `bollinger` ≈ **10.7 s**, `cci` ≈ **6 s** — per-bar Python loops calling `np.std`/`np.mean` **~487,000 times** each. |
| **Not the problem** | the trade/exit engine (`fast_engine`) ≈ 1.3 s; data load 0.6 s; HAR-RV 0.05 s. |
| **Biggest, safest win** | **vectorize the rolling-window classic indicators** (bollinger/cci/…): ~17 s → <1 s, low risk. |
| **Biggest win overall** | **Numba-JIT + de-duplicate the SMC indicators**: ~22 s → ~1–2 s, medium risk. |
| **Realistic target** | **37 s → 2–4 s per backtest (≈10×)**; the multi-hour optimizer sweep shrinks proportionally. |

**Baby version:** The calculator that scores a strategy used to read a short book (a few thousand rows).
Now it reads a giant book (half a million rows) and — worse — it re-reads tiny passages one word at a
time in slow Python instead of skimming whole pages at C speed. Two fixes: (1) teach it to skim whole
pages (vectorize), and (2) stop it from reading the hardest chapter twice (de-duplicate) and let a
turbo-compiler (Numba) handle the unavoidable word-by-word part.

---

## 1. How the backtester works (the pipeline being optimized)

One backtest (`strategy.build_payload`) runs this chain:

1. **Load** decision-frame candles (e.g. 4h, ~2,119 bars) + the **1-minute** frame (~**486,969 bars**) +
   box levels.
2. **HAR-RV volatility forecast** over the 1-minute returns.
3. **`indicator_source_1min`** — for each decision bar, find its last-closed 1-minute candle (the causal
   sampling map).
4. **`compute_votes`** — for each enabled indicator, compute its signal **across the full 1-minute
   series**, then read off the value at each decision bar.
5. **`build_layer`** — combine votes into the K-of-N confirm gate + veto mask + entry resolver.
6. **`generate_structures`** — (only when SMC indicators are on) build the market-structure report.
7. **Engine backtest** — walk trades; resolve each exit on the 1-minute frame.
8. Assemble summary + drawdown breaker.

> **Baby:** Step 4 is the slow one. We compute every indicator over the *whole* one-minute history (half a
> million numbers) even though we only *use* one reading per 4-hour bar (~2,000 readings). We still need
> the full history to "warm up" rolling indicators — but the way we compute it is the problem, not the
> fact that we compute it.

---

## 2. The measurement (don't guess — profile)

Single 4h-champion backtest (8 indicators incl. 2 SMC), all-history data:

```
load:           0.59 s   (df4=2,119 bars, df1=486,969 bars)
vol_forecast:   0.05 s
build_payload: 37.06 s   ← everything is here
```

`cProfile` (sorted by self-time) — the honest hot list:

| Function | self-time | calls | what it is |
|----------|----------:|------:|------------|
| `smc.order_blocks` | **14.97 s** | 2 | stateful per-bar OB zone tracking (+ inner zone-overlap loop) |
| numpy `reduce` | 5.62 s | 3.79 M | underlying sums/min/max of the per-bar windows |
| `_var` | 4.57 s | **486,925** | variance **per 1-minute bar** (bollinger's `np.std`) |
| `smc.market_structure` | 3.04 s | 5 | per-bar fractal swing detection (`.all()` on slices) |
| `classic.cci` | 2.06 s | 1 | per-bar mean-abs-deviation loop |
| `_mean` | 1.12 s | 486,835 | rolling means per bar |
| `_std` | 1.07 s | 486,925 | rolling std per bar |
| `classic.bollinger` (cum) | **10.68 s** | 1 | drives the `_var`/`_std` storm above |
| `classic.obv` | 0.74 s | 1 | sequential cumulative loop |
| `smc.structure_trend` (cum) | 4.26 s | 2 | calls `market_structure` + a swing loop |
| `engine._walk_exit_for_4h` | 1.32 s | 2,333 | the actual trade-exit walk — **small** |

**Reading the tea leaves:** the `486,925`-call counts on `_var`/`_std`/`_mean` are a dead giveaway —
those are **one numpy call per 1-minute bar**, i.e. a Python `for t in range(...)` loop instead of a
single vectorized pass. And `order_blocks` ncalls=**2** reveals it is computed **twice** (once for the
vote, once for the structure report).

> **Baby:** The profiler is a stopwatch on every function. It shows three things eating the clock: a hard
> chapter read twice (order_blocks), and two indicators (bollinger, cci) that recompute a fresh average
> from scratch for every single one of the half-million rows instead of sliding a window along once.

---

## 3. Root causes (precisely, with code)

### 3.1 Per-bar Python loops in classic indicators (≈17 s)
`indicators/classic.py`:
```python
def bollinger(close, n, k):
    ...
    for t in range(n - 1, len(c)):
        std[t] = np.std(c[t - n + 1:t + 1])          # 486k np.std calls
def cci(high, low, close, n):
    ...
    for t in range(n - 1, len(c)):
        mad = np.mean(np.abs(tp[t-n+1:t+1] - m[t]))  # 486k np.mean calls
def _roll_max / _roll_min (stochastic):              # 486k np.max / np.min calls
def obv(...):
    for t in range(1, len(c)): out[t] = out[t-1] + ... # sequential cumsum
```
Each recomputes a statistic over a length-`n` window from scratch, for every one of ~487k bars →
**O(n · window)** Python-level work. A rolling std/mean is a textbook **one-pass vectorized** operation.

> **Baby:** To get the average temperature of every 45-day window in a year, they re-add 45 numbers for
> each day. The smart way slides the window: subtract the day that left, add the day that joined — one
> pass. numpy/pandas do this in C.

### 3.2 SMC indicators are stateful per-bar loops — and run twice (≈22 s, ~9 s of it redundant)
`indicators/smc.py` `order_blocks` and `structure_trend` are genuinely **sequential** (each bar updates
live zones / swing lists, with breaks and conversions) — they *can't* be a one-liner. Two problems:
- **Inner overlap loop:** every bar scans `for z in bull: ... for z in bear:` to test zone overlap —
  even though the result is only *read* at ~2,119 decision bars, it's *computed* at all 487k.
- **Redundant recompute:** `order_blocks` (ncalls=2) and `market_structure` (ncalls=5) run multiple times
  because `compute_votes` and `generate_structures` each build the SMC structures independently.

> **Baby:** This chapter genuinely has to be read in order (each page depends on the last). But we read it
> twice, and on every page we check a list of "zones" we only actually look at twice a day. Read it once,
> and only check zones when someone's looking.

### 3.3 Everything scales with the 1-minute frame
The 1-minute series is **~230× longer** than the 4h decision frame (486,969 vs 2,119). Moving indicators
onto it multiplied every per-bar cost by ~230×. The engine's exit walk did **not** blow up (it was always
1-minute-based) — confirming the regression is purely in indicator compute.

---

## 4. Improvement options — deep study, pros/cons each

Each option lists: what it is, expected gain (from the profile), effort, risk, and the
parity/baby notes. Ordered by leverage-to-risk.

### Option A — Vectorize the rolling-window classic indicators ⭐ (do first)
**What:** replace the per-bar loops in `bollinger`, `cci`, `stochastic` (`_roll_max/min`),
`keltner`/`atr`, `mfi`, `rsi` with vectorized rolling — pandas `Series.rolling(n)` or numpy
`sliding_window_view` / cumulative-sum tricks. (The codebase already did exactly this for `stochastic`'s
`%D`, noting it is *"bitwise-identical to the loop"* — so the pattern and the parity bar are established.)
**Gain:** the ~17 s of bollinger+cci+obv collapses to **<1 s**. Net: **37 s → ~20 s** on its own.
**Effort:** Low (a few funcs, ~1 day). **Risk:** Low–Medium — must match float semantics exactly
(population std `ddof=0`, NaN at window edges, mean-abs-deviation order of ops). Guarded by `test_parity`.

- ✅ Pros: biggest safe win; pure-Python deps already present (numpy/pandas); no new toolchain; per-indicator and incremental.
- ⚠️ Cons: rolling-std/MAD must reproduce the loop's exact rounding to keep byte-parity (doable; precedent exists).

> **Baby:** Teach the slow indicators to *slide the window* instead of recomputing from scratch. Same
> answer, ~50× faster, and we already proved the trick is safe on one indicator.

### Option B — De-duplicate the SMC computation ⭐ (do first; tiny + safe)
**What:** compute `market_structure` / `order_blocks` **once** and share between `compute_votes` and
`generate_structures` (memoize by `(id(close), swing_l)` within a backtest).
**Gain:** removes the duplicate `order_blocks` (~9 s) and extra `market_structure` calls. Net: **−9 s**.
**Effort:** Very low (a cache dict / pass the precomputed structures through). **Risk:** Very low (same
numbers, just computed once).

- ✅ Pros: ~25% off the total for almost no code; zero algorithmic change → trivially parity-safe.
- ⚠️ Cons: must thread the shared object through two call sites cleanly.

> **Baby:** Stop reading the hardest chapter twice. Read it once, hand the notes to whoever needs them.

### Option C — Numba-JIT the SMC sequential loops ⭐⭐ (biggest single win)
**What:** `@njit` the bodies of `order_blocks`, `market_structure`, `structure_trend`, `fvg` (rewrite the
Python lists of zones as preallocated typed arrays so Numba can compile them to machine code).
**Gain:** the remaining ~13 s of SMC compute → **~0.5–1 s** (10–30× typical for tight numeric loops).
Net (with B): SMC ~22 s → ~1 s.
**Effort:** Medium (Numba constraints: no Python lists/dicts of objects, typed everything). **Risk:**
Medium — JIT warm-up (~1 s first call, amortized over a sweep); float ops reproduce identically if
written carefully. Adds a dependency (`numba`).

- ✅ Pros: turns the unavoidable sequential work into C speed; in-process; massive on the #1 cost.
- ⚠️ Cons: new dependency; rewrite of list-based zone logic into arrays; first-call JIT lag; must re-prove parity.

> **Baby:** The chapter we *must* read in order — hand it to a turbo-compiler that reads in order but at
> machine speed instead of slow Python.

### Option D — Vectorize `obv` (trivial)
**What:** `obv = np.concatenate([[0], np.cumsum(np.sign(np.diff(c)) * vol[1:])])`.
**Gain:** ~0.7 s → ~0.005 s. **Effort:** Minutes. **Risk:** Very low.
- ✅ Pros: free. ⚠️ Cons: none of note (match the `sign(0)=0` convention).

### Option E — Compute SMC overlap signal only at sampled points
**What:** the per-bar zone-overlap inner loop produces a value used **only** at decision bars; keep the
sequential zone *state* updating every bar, but compute the overlap/emit only at the ~2,119 sampled
1-minute indices.
**Gain:** cuts `order_blocks`' inner O(n·zones) loop sharply (extra few seconds). **Effort:** Medium
(careful: state still advances every bar; only the *emit* is gated). **Risk:** Medium (must not change
which bar's value is read).
- ✅ Pros: attacks the inner loop Numba can't fully remove. ⚠️ Cons: subtle causality — easy to get the "last-closed" index wrong; needs strong parity tests.

### Option F — Cache the param-independent `indicator_source_1min` across trials
**What:** the 1-minute sampling map (decision bar → last-closed 1m index) depends only on (timeframe,
data), **not** on the tuned params. During an optimizer study every trial recomputes it; cache once per
worker.
**Gain:** small per single backtest, but removes a fixed cost from **every** optimizer trial (thousands).
**Effort:** Low. **Risk:** Low (pure memoization keyed by data identity).
- ✅ Pros: speeds the sweep, not just one run; trivial. ⚠️ Cons: must invalidate the cache if data/TF changes (key on both).

### Option G — Parallelize the independent indicators (threads)
**What:** the 8 indicators are independent; numpy/Numba release the GIL, so a thread pool can compute them
concurrently on multi-core.
**Gain:** up to ~#cores× on the *compute* phase — but bounded by the **slowest single indicator**
(order_blocks), so only worth it *after* A–C shrink the long pole. **Effort:** Medium. **Risk:** Medium
(thread-safety of shared numpy buffers; the optimizer already saturates cores with process-level workers,
so this mainly helps the *single-backtest dashboard*, not the sweep).
- ✅ Pros: helps interactive dashboard latency. ⚠️ Cons: redundant with the optimizer's existing process parallelism; only helps once the per-indicator costs are balanced.

### Option H — Numba the engine exit-walk
**What:** `@njit` `fast_engine`'s trade/exit loop. **Gain:** ~1.3 s → ~0.1 s — **small** (it's not the
bottleneck). **Effort:** Medium. **Risk:** Medium. **Verdict:** defer; low priority until A–C are done.

### Options explicitly rejected (for "speed only, no result change")
- **Coarsen the indicator frame** (use 5-min instead of 1-min): would be fast but **changes results** —
  forbidden.
- **Drop SMC indicators:** changes the champion — forbidden.
- **Approximate rolling stats (e.g. EWMA instead of SMA std):** changes numbers — forbidden.
- **GPU/Dask:** wrong tool — data is tiny (28 MB, in-RAM), the cost is per-bar Python overhead, not data
  volume or memory (see `optimize/server/REPORT_system_scaling_study.md`).

---

## 5. Decision matrix

| Option | Gain (of 37 s) | Effort | Risk | Order |
|--------|---------------:|:------:|:----:|:-----:|
| A. Vectorize classic rolling | −16 s | Low | Low | **1** |
| B. De-dup SMC compute | −9 s | V.low | V.low | **1** |
| D. Vectorize obv | −0.7 s | Mins | V.low | **1** |
| F. Cache 1m sampling map (sweep) | sweep-wide | Low | Low | **2** |
| C. Numba SMC loops | −12 s | Med | Med | **2** |
| E. Sampled SMC overlap | −(few) s | Med | Med | 3 |
| G. Thread indicators (dashboard) | balance-dependent | Med | Med | 3 |
| H. Numba engine walk | −1.2 s | Med | Med | 4 |

**Projected:** A+B+D (Phase 1, low risk) → **37 s ≈ 11 s**. Add C (Phase 2) → **≈ 2–4 s**. That is the
**~10× target**, with the optimizer sweep shrinking in proportion (the wsh4 run that took ~14 h → ~1.5–3 h).

---

## 6. Recommended roadmap (phased, parity-gated)

**Phase 1 — "vectorize + de-dup" (low risk, ~1–1.5 days) → ~3×**
1. B: share `market_structure`/`order_blocks` between votes and the structure report.
2. A: vectorize `bollinger`, `cci`, `_roll_max/min` (stochastic), `atr`/`keltner`, `mfi`.
3. D: vectorize `obv`.
4. Gate every change on `optimize/test_parity.py` + `optimize/test_indicator_parity.py` + full `pytest`
   (88) + the wsh4 4h reproduction ($142,203). A new micro-benchmark records before/after.

**Phase 2 — "JIT the sequential core" (medium risk, ~2–3 days) → ~10× total**
5. C: add `numba`; rewrite `order_blocks`/`market_structure`/`structure_trend`/`fvg` zone logic as typed
   arrays under `@njit`. Keep the pure-Python versions behind a flag for parity cross-checks.
6. F: memoize `indicator_source_1min` per (TF, data) for the optimizer.

**Phase 3 — "polish" (optional)**
7. E (sampled overlap), G (thread the dashboard backtest), H (Numba the exit walk) — only if still needed.

**Guardrails (every phase):** speed only; parity is a hard gate; keep a reference pure-Python path to
diff against the optimized one; benchmark each step so we never trade correctness for speed unknowingly.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| Vectorized rolling std/MAD diverges in the last digit | Med | High (breaks parity) | reproduce loop's exact ops; `ddof=0`; test_parity + indicator_parity as hard gates; precedent: stochastic %D |
| Numba float results differ from Python | Low–Med | High | keep pure-Python reference; assert bitwise/â‰ˆ equality on a fixed dataset before switching |
| Numba JIT warm-up adds latency to a single run | High | Low | amortized across a sweep; `cache=True` persists compiled code |
| New `numba` dependency / install friction on the server | Med | Med | pin in requirements; it's CPU-only, widely available; gate behind a feature flag |
| De-dup changes call order / introduces stale cache | Low | Med | key cache on data identity + swing_l; clear per backtest |
| "Sampled overlap" (E) shifts which bar is read | Med | High | strong causal tests; do last, only if needed |

---

## 8. How we'll prove "no result change"

Every optimization is accepted **only** if all of these still hold, on the same machine/data:
- `optimize/test_parity.py` → `$7,735 / $3,670 / n=66`.
- `optimize/test_indicator_parity.py` (the vectorized-vs-loop indicator gate) → pass.
- Full `pytest` → 88 passed.
- wsh4 4h champion via the standalone bundle → `$142,203` (± rounding).
- A new `bench_backtest.py` prints before/after wall-clock so the speed-up is recorded, not assumed.

---

## 9. Bottom line

The slowdown is **not** the data size, the engine, or the architecture — it is **two fixable things**:
(1) classic indicators recomputing rolling stats one bar at a time in Python, and (2) the SMC indicators
running twice and doing per-bar work that's only read occasionally. Vectorizing the first and
JIT-compiling + de-duplicating the second is projected to take **one backtest from ~37 s to ~2–4 s (≈10×)**
and the multi-hour optimizer sweep down with it — **without changing a single result**, enforced by the
existing parity gates.

> **Baby, in one line:** make the calculator skim whole pages instead of re-reading word-by-word, stop it
> reading the hard chapter twice, and give the unavoidable slow part a turbo engine — same answers, ten
> times faster.
