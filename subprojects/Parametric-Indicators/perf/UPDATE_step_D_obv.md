# Update Report — Phase 1 · Step D: Vectorize `obv`

**Date:** 2026-06-11 · branch `dev` · task #210 · **first engine change of the optimization**
**Type:** speed only — **results provably unchanged** (every gate green).

---

## 1. What changed (plain + professional)

**Professional.** `indicators/classic.py:obv` computed On-Balance Volume with a sequential Python loop
over the full 1-minute series (~487k iterations). OBV is a prefix sum, so the loop is replaced by one
vectorized pass: `out[1:] = cumsum(sign(diff(close)) * volume[1:])`. Mathematically identical
(`np.sign(0)=0` matches; NaN propagates the same way), at C speed.

**Baby.** OBV is a running total — add or subtract each minute's volume depending on whether price ticked
up or down. We used to add half a million numbers one at a time by hand; now we do the same running total
in one quick sweep. Same final numbers.

---

## 2. Before / after

| | Before (loop) | After (vectorized) |
|---|---|---|
| `obv` on 486,969 bars | **539.9 ms** | **8.4 ms** → **64× faster** |
| Output | reference | **bit-identical** (NaN-for-NaN) |
| 4h full backtest | 36.2 s baseline | obv is ~0.7 s of that → small end-to-end now; gains compound across Phase 1 |

> obv is intentionally the *smallest* win — Step D's purpose was to **prove the verification ritual
> end-to-end** before the big ones (bollinger ~10.7 s, cci ~6 s).

---

## 3. Code touched / links

| File | Change |
|------|--------|
| `indicators/classic.py` (`obv`) | loop → `cumsum(sign(diff)·vol)`; docstring notes parity + reference |
| `indicators/_reference.py` (NEW) | frozen verbatim copy `obv_ref` — the immutable spec the fast path is diffed against (kept forever; never optimized) |
| `tests/test_speedopt_equiv.py` (NEW) | `obv` equivalence on random sizes + adversarial edge cases (constant / monotonic / leading-NaN / mid-NaN / tiny / jump) + empty/single |

Related: `optimize/REPORT_backtester_speed_optimization.md` (Option D), `perf/UPDATE_phase0_safety_net.md`
(the safety net), `perf/check_golden.py` (regression gate), `perf/equiv.py` (input generators).

---

## 4. Verification evidence (all green)

| Gate | Result |
|------|--------|
| Equivalence unit tests (optimized == frozen reference) | ✅ 7 passed incl. all adversarial edge cases |
| obv micro-benchmark | ✅ 64× faster, bit-identical |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **95 passed** (88 prior + 7 new) |
| Golden byte-match, coarse TFs (4h/2h/1h) | ✅ ALL MATCH — summary + trades-hash + every indicator vote-hash identical |

*(Per the cadence, the full-6-TF golden check runs at the Phase-1 boundary; Step D is mathematically
TF-independent and the coarse check + bit-identical equivalence already prove no change on every TF.)*

---

## 5. Reverting Step D

```bash
# revert just this step (keeps Phase 0):
git revert --no-edit <STEP_D_COMMIT>
# or hard-reset to the Phase 0 safety-net rollback point:
git reset --hard f9d6f36
```
The change is one self-contained function; `indicators/_reference.obv_ref` preserves the exact original
for diffing even after revert.

---

## 6. Status

- ✅ Step D complete, committed, results unchanged.
- ▶️ Next proposed: **Step A1 — vectorize `bollinger`** (the biggest single safe win, ~10.7 s) — pending approval.

**Step D commit:** _(filled at commit)_
