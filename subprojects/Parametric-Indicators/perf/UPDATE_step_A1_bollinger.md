# Update Report — Phase 1 · Step A1: Vectorize `bollinger` (rolling std)

**Date:** 2026-06-11 · branch `dev` · task #210 · **biggest single safe win**
**Type:** speed only — **results provably unchanged**, and here **bit-identical** on the real series.

---

## 1. What changed (plain + professional)

**Professional.** `indicators/classic.py:bollinger` computed a rolling **population standard deviation**
(`ddof=0`) with a per-bar loop calling `np.std` ~487k times. Replaced with a single batched pass:
`std[n-1:] = sliding_window_view(close, n).std(axis=1)`. Same per-window reduction, edge convention
preserved (NaN for `t<n-1`, NaN for any window containing a NaN, NaN when `len<n`).

**Baby.** Bollinger Bands measure how "wiggly" price has been over the last N minutes, every minute. We
used to re-measure all N numbers from scratch each minute (half a million times). Now we measure every
window in one big sweep. The wiggliness numbers came out **exactly the same** — not even a rounding
difference — just ~40× faster.

---

## 2. Before / after

| | Before (loop) | After (vectorized) |
|---|---|---|
| `bollinger` (win 45) on 486,969 1-min bars | **6,375 ms** | **159 ms** → **40× faster** |
| mid / upper / lower on real 1-min close | reference | **bit-identical** (`max|Δ|=0.0`, NaN-for-NaN) |
| 4h full backtest | ~36 s | bollinger was ~10.7 s of cProfile time → expect a clear drop; full re-bench at the Phase-1 boundary |

The hoped-for outcome (the `%D` precedent) held: `sliding_window_view().std(axis=1)` reproduces the loop's
`np.std` **exactly**, so not a single discrete vote moved.

---

## 3. Code touched / links

| File | Change |
|------|--------|
| `indicators/classic.py` (`bollinger`) | per-bar `np.std` loop → `sliding_window_view(c,n).std(axis=1)`; docstring notes parity + reference |
| `indicators/_reference.py` | added frozen `bollinger_ref` (verbatim original loop) — the immutable spec |
| `tests/test_speedopt_equiv.py` | added bollinger equivalence: 12 random (window × size combos) + adversarial edge cases + window>series |

Related: `optimize/REPORT_backtester_speed_optimization.md` (Option A), `perf/check_golden.py`.

---

## 4. Verification evidence (all green)

| Gate | Result |
|------|--------|
| Equivalence unit tests (tight tol, random + adversarial) | ✅ 21 passed |
| Bit-exactness on the real 486,969-bar 1-min close | ✅ **max\|Δ\| = 0.0** (mid/upper/lower) |
| bollinger micro-benchmark | ✅ 40× faster |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **109 passed** (95 prior + 14 new) |
| Golden byte-match, coarse TFs (4h/2h/1h) | ✅ ALL MATCH — incl. the **bollinger vote-hash** identical |

The stricter precision bar (vote-hash must stay byte-identical) was met without any fallback.

---

## 5. Reverting Step A1

```bash
git revert --no-edit <STEP_A1_COMMIT>     # undo just A1 (keeps Phase 0 + Step D)
git reset --hard f9d6f36                  # or hard-reset to the Phase-0 rollback point
```
`indicators/_reference.bollinger_ref` preserves the exact original for diffing even after revert.

---

## 6. Status

- ✅ Step A1 complete, committed, **bit-identical** results.
- ▶️ Next proposed: **Step A2 — vectorize `cci`** (rolling mean-abs-deviation, ~6 s) — pending approval.

**Step A1 commit:** _(filled at commit)_
