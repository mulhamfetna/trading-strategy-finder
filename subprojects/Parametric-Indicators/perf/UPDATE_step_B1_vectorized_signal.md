# Update Report — Axis B · Step B1: vectorized `decision_signals`

**Date:** 2026-06-12 · branch `dev` · task #210
**Type:** speed + foundation — **results byte-identical**. No new dependency. **Engine/backtester hot path
NOT changed yet** (that is Step B2); this step adds a vectorized signal + proves it identical.
**Plan:** `perf/ACTION_PLAN_axisB.md` §2 · **Investigation:** `perf/INVESTIGATION_axisB_per_decision_loop.md`

---

## 1. What changed (plain + professional)

**Professional.** `optimize/signals.decision_signals(df_dec, box)` — the param-independent Stage-1
long/short/hold signal — was a **per-bar pandas loop** calling `engine._stage1_candle_signal(df.iloc[i], …)`
for every decision bar (reading OHLC + box levels as pandas scalars). It is now a **pure-numpy vectorized**
computation: one `box.reindex(box_dates)` gather + array comparisons across the 16 level pairs, with **zero
per-bar pandas access**. The original loop is preserved verbatim as `decision_signals_ref` (the frozen
spec). Callers (`optimizer.py`, `core.py`, `runner.py`, `sl_tp_bounds.py`, the parity tests) are unchanged —
same name, same signature, same output.

**Baby.** The "should I buy/sell/wait on each bar?" list used to be worked out one bar at a time with a slow
spreadsheet method. Now we work out the whole list in one fast sweep of array math. Same answers — we
proved it on every timeframe, down to the last bar — just ~100–490× faster to produce.

---

## 2. Before / after

### 2.1 Signal compute time (real frames, idle box) — identical output
| TF | bars | ref (per-bar loop) | **vec (numpy)** | speedup | mismatches |
|----|-----:|-------------------:|----------------:|--------:|:----------:|
| 4h | 2,119 | 443.5 ms | **4.2 ms** | 105.6× | 0 |
| 2h | 4,236 | 829.1 ms | **4.0 ms** | 209.7× | 0 |
| 1h | 8,121 | 1,508.3 ms | **7.6 ms** | 197.8× | 0 |
| 15m | 32,467 | 5,829.7 ms | **15.9 ms** | 366.8× | 0 |
| 5m | 97,401 | 17,019.8 ms | **34.9 ms** | 488.0× | 0 |
| 2m | 243,504 | 41,948.6 ms | **127.1 ms** | 330.0× | 0 |

### 2.2 What this does and does NOT speed up (honest scope)
- **Immediately faster:** the optimizer's `decision_signals` precompute (`optimizer.py:130`) and any path
  that calls it — now ~100–490× cheaper.
- **Not yet faster:** a single `strategy.build_payload` backtest — the engine still computes the signal
  inline via `_stage1_candle_signal`. **Step B2 wires this vectorized array into the engine**, at which
  point the ~27 s per-bar signal cost on fine-TF backtests is removed. B1 is the foundation that makes B2
  safe.

---

## 3. Why it's exact (the equivalence argument)

Each scalar operation maps to its numpy equivalent on the **same float64 values** (`.to_numpy(float)` yields
the identical bytes the scalar path read), so comparisons are exact, not approximate:

| Scalar rule (`engine._stage1_candle_signal`) | Vectorized form |
|---|---|
| `color`: green=`close>open`, red=`close<open`, doji⇒hold | `green=C>O`, `red=C<O`; doji ⇒ neither ⇒ hold |
| box row absent (`.loc` KeyError ⇒ None) ⇒ hold | `box.reindex(box_dates)` ⇒ NaN row ⇒ pair invalid ⇒ hold |
| `pd.isna(u) or pd.isna(l): continue` | `valid = ~isnan(up) & ~isnan(lo)` |
| `upper_col not in box_row.index: continue` | `if col not in sub.columns: continue` |
| `touched = low≤u and high≥l` | `touched = valid & (L≤up) & (H≥lo)` |
| `green and close>u ⇒ long`; `red and close<l ⇒ short` | `has_long\|=green&touched&(C>up)`; `has_short\|=red&touched&(C<lo)` |
| **long returned before short** (ties) | assign `short` then `long` last ⇒ long wins |
| box-date roll: `hour≥18 ⇒ next day`, normalize | `_box_dates_vec` vectorizes `_candle_to_box_date` verbatim |

**Proven:** `decision_signals == decision_signals_ref` **element-for-element on all 6 real TFs (0
mismatches, 243,504 bars at 2m)** and on synthetic random + adversarial frames (doji-heavy, all-dates-
missing, all-levels-NaN, absent columns, exact-boundary touches, empty).

---

## 4. Code touched / links
| File | Change |
|------|--------|
| `optimize/signals.py` | added `decision_signals_ref` (frozen original loop) + `_box_dates_vec` (vectorized box-date roll) + rewrote `decision_signals` as numpy. Public name/signature unchanged. |
| `tests/test_axisB_signal_equiv.py` (NEW) | 18 tests: 8 random seeds + 6 adversarial edge cases + empty + real 4h/2h/1h/15m. Exact element-for-element. |

No interface/signature change. `decision_signals_ref` is now the immutable spec for B2/B3.

---

## 5. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `tests/test_axisB_signal_equiv.py` | ✅ 18 passed |
| Full 6-TF real-data equivalence (vec==ref) | ✅ 0 mismatches (4h→2m) |
| `optimize/test_fast_parity.py` (uses `decision_signals`) | ✅ OK, mismatch=0 (6 scenarios) |
| `optimize/test_indicator_parity.py` (uses `decision_signals`) | ✅ OK, mismatch=0 (5 scenarios) |
| `perf/check_golden.py 4h 2h 1h` | ✅ ALL MATCH |
| Full `pytest` | ✅ **166 passed** (148 + 18 new) |

---

## 6. Reverting Step B1
```bash
git revert --no-edit <STEP_B1_COMMIT>   # undo B1 (isolated — nothing depends on it yet)
git reset --hard f9d6f36                # or hard-reset to the Phase-0 rollback anchor
```
B1 is the safest possible step: it adds a function + a test and only changes `decision_signals`, which the
backtester (`build_payload`) does **not** call until B2. Reverting it cannot affect any existing result.

## 7. Status & next
- ✅ Step B1 complete, committed, byte-identical. Optimizer signal precompute ~100–490× faster.
- ▶️ **Next: Step B2** (approval-gated) — add an optional `signals=` arg to `engine.SimpleStrategy.backtest`
  (default `None` = current behaviour verbatim) and have `build_payload` precompute the signal once and pass
  it in, removing the ~27 s per-bar `_stage1_candle_signal` cost on fine-TF backtests. Acceptance: **all 6
  golden TFs byte-identical** + all parity layers + full pytest.
