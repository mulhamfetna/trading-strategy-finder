# Update Report — Phase 1 · Step A2: Vectorize `cci` (rolling mean-abs-deviation)

**Date:** 2026-06-11 · branch `dev` · task #210
**Type:** speed only — **results bit-identical** on the real series.

---

## 1. What changed (plain + professional)

**Professional.** `cci` computed a rolling **mean-absolute-deviation** with a per-bar loop
(`mad = mean(|tp[window] − sma|)`, then `cci = (tp−sma)/(0.015·mad)` with a `mad==0 → 0` guard).
Replaced the loop with `|sliding_window_view(tp,n) − sma[n-1:,None]|.mean(axis=1)` — the same per-window
reduction in one batched pass; the zero-MAD guard and NaN/edge conventions preserved exactly.

**Baby.** CCI asks "how far is price from its recent average, compared to how far it *usually* strays?"
The "usually strays" part (average distance from the average) used to be recomputed by hand every minute;
now it's done for all windows in one sweep. Identical numbers, ~4× faster.

---

## 2. Before / after

| | Before (loop) | After (vectorized) |
|---|---|---|
| `cci` (win 138) on 486,969 1-min bars | **3,567 ms** | **925 ms** → **4× faster** |
| Output on real 1-min data | reference | **bit-identical** (`max|Δ|=0.0`, NaN-for-NaN) |

The factor is smaller than bollinger's 40× because MAD needs the full `(len−n+1, n)` window matrix
materialized (memory-bandwidth bound) — but it is **exact and safe**, which is the priority. (A later
cumsum-free refinement could push it further if needed.)

---

## 3. Code touched / links

| File | Change |
|------|--------|
| `indicators/classic.py` (`cci`) | per-bar MAD loop → `sliding_window_view` MAD; `mad==0→0` via `np.where` |
| `indicators/_reference.py` | added frozen `cci_ref` (verbatim original) |
| `tests/test_speedopt_equiv.py` | added cci equivalence: 16 random (window × size) + adversarial edges + a dedicated **constant-price `mad==0`** case |

---

## 4. Verification evidence (all green)

| Gate | Result |
|------|--------|
| Equivalence unit tests (random + adversarial + mad==0) | ✅ 18 passed |
| Bit-exactness on the real 486,969-bar 1-min series | ✅ **max\|Δ\| = 0.0** |
| cci micro-benchmark | ✅ 4× faster |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **127 passed** (109 prior + 18 new) |
| Golden byte-match, coarse TFs (4h/2h/1h) | ✅ ALL MATCH — incl. the **cci vote-hash** identical |

---

## 5. Reverting Step A2
```bash
git revert --no-edit <STEP_A2_COMMIT>     # undo just A2
git reset --hard f9d6f36                  # or hard-reset to the Phase-0 rollback point
```

## 6. Status
- ✅ Step A2 complete, committed, bit-identical results.
- ▶️ Next proposed: **Step A3** — vectorize the remaining rolling-window classics
  (`stochastic` roll-max/min, `atr`/`keltner`, `mfi`) — pending approval.

**Step A2 commit:** _(filled at commit)_
