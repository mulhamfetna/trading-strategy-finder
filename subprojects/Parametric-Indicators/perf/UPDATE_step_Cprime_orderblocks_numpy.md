# Update Report — Phase 2 · Step C′: `order_blocks` numpy-zone rewrite

**Date:** 2026-06-11 · branch `dev` · task #210
**Type:** speed only — **results byte-identical**. No new dependency (numba was ruled out — see §0).

---

## 0. Why C′ instead of C (Numba)
The approved step was **C — Numba `@njit`** the SMC loops. On attempting it: this environment is
**Python 3.14.4 + numpy 2.3.5**, and (a) pip is **externally-managed (PEP 668)** — installing would need
`--break-system-packages`, which risks the system Python that runs everything; (b) numba has **no wheel
for Python 3.14** and would fail regardless. Installing numba was therefore **declined as unsafe/unviable**
and we pivoted to the **dependency-free numpy rewrite (C′)** — same exact results, no install.

---

## 1. What changed (plain + professional)

**Professional.** `order_blocks` kept its live supply/demand zones in **Python lists** and did the per-bar
zone **overlap** (a `for z in bull` scan) and **pruning** (`[z for z in bull if …]` list rebuild) in pure
Python — O(N·zones) interpreter work over 486,969 bars. C′ stores the zones as **numpy arrays**
(`bull_lo/bull_hi/bear_lo/bear_hi`): overlap becomes `np.any((l≤hi)&(h≥lo))` and pruning becomes a boolean
mask — **the identical operations**, executed at C speed. Appends (rare, on breaks) use `np.append`.

**Baby.** Same zone bookkeeping as before, but instead of checking/trimming a list of ~200 boxes one box
at a time in slow Python every minute, we check/trim them all at once with one fast array operation.
Exactly the same boxes, same answers — just done in bulk.

---

## 2. Before / after

| | list version | numpy version (C′) |
|---|---|---|
| `order_blocks` **full** (swing_l 10), 486,969 bars | 16.6 s | **10.6 s** |
| `order_blocks` **sampled** (Step E + C′ together) | 9.90 s | **5.83 s** → **2.8× vs the original 16.6 s** |
| `order_blocks(signal_at=None)` output | reference | **bit-identical** |
| **4h full backtest** | 16.5 s (after E) | **12.1 s** — and **36.2 s → 12.1 s vs baseline (−67%)** |

---

## 3. Why it's exact
Every list operation maps to its numpy equivalent with the same comparison:
- overlap: `for z in bull: l[t]≤z[1] and h[t]≥z[0]` ⇒ `np.any((l[t]≤bull_hi) & (h[t]≥bull_lo))` (order
  irrelevant for "any overlap"; bull still preferred via `if/elif`);
- prune bull: keep `not (c[t]<z[0])` = `z[0]≤c[t]` ⇒ `keep = bull_lo ≤ c[t]`;
- prune bear: keep `not (c[t]>z[1])` = `z[1]≥c[t]` ⇒ `keep = bear_hi ≥ c[t]`.
Proven: `order_blocks(signal_at=None) == _reference.order_blocks_ref` and `…(signal_at=S)[S] == ref[S]`
bit-for-bit on the real 1-minute series, and the **golden order_block vote-hash is unchanged**.

---

## 4. Code touched / links
| File | Change |
|------|--------|
| `indicators/smc.py` (`order_blocks`) | live zones: Python lists → numpy arrays; overlap `np.any`, prune boolean mask; `signal_at` (Step E) preserved |
| `tests/test_speedopt_equiv.py` | (unchanged — the Step-E order_blocks tests already assert full==ref + sampled[S]==ref[S], now re-verifying the numpy path) |

No interface/signature change; `_reference.order_blocks_ref` (the original list loop) remains the spec.

---

## 5. Verification evidence (all green)
| Gate | Result |
|------|--------|
| Equivalence (full==ref; sampled[S]==ref[S]; unsampled==0) | ✅ 21 passed |
| Real-1m bit-check | ✅ `full==ref` and `sampled[S]==ref[S]` |
| order_blocks micro-benchmark | ✅ sampled 9.90 s → 5.83 s |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **148 passed** |
| Golden byte-match 4h/2h/1h (incl. order_block vote-hash) | ✅ ALL MATCH |

---

## 6. Reverting Step C′
```bash
git revert --no-edit <STEP_Cprime_COMMIT>   # undo just C′ (keeps D/A1/A2/E)
git reset --hard f9d6f36                    # or hard-reset to the Phase-0 rollback point
```

## 7. Status
- ✅ Step C′ complete, committed, byte-identical. **4h: 36.2 s → 12.1 s (−67%).**
- Remaining order_blocks cost ≈ 5.8 s is now the **outer Python loop + `market_structure` (~2.2 s)** —
  further gains would need Numba (blocked here) or vectorising `market_structure`.
- ▶️ Next candidates: A3 (stochastic deque / mfi / keltner — helps fine TFs), or `market_structure`
  vectorization. Pending approval.
