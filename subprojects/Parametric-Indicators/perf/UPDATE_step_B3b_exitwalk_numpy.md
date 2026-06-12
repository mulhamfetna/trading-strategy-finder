# Update Report — Axis B · Step B3b: numpy 1-min exit walk

**Date:** 2026-06-12 · branch `dev` · task #210
**Type:** speed — **results byte-identical (all 6 golden TFs MATCH)**. No new dependency. The riskiest
sub-step (it touches the SL/TP exit-resolution core) — gated by the full golden + parity suite.
**Plan:** `perf/ACTION_PLAN_axisB.md` §4 · **builds on:** B1, B2, B3a · **completes Axis B**

---

## 1. What changed (plain + professional)

**Professional.** `_walk_exit_for_4h` resolved each open trade's exit by slicing
`df_1min.iloc[lo:hi]` into a DataFrame and iterating `.itertuples()`, reading `Date/High/Low/Close` via
`getattr` per 1-min bar. B3b pre-extracts those four 1-min columns into numpy arrays **once**
(`md_arr/mh_arr/ml_arr/mc_arr`) and the walk now iterates `for t in range(lo, hi)` indexing them directly.
The **exact** exit logic is preserved unchanged: per-bar priority (hard-SL/hard-TP/soft in each mode), the
2-consecutive-close soft counter, the no-look-ahead `sub_ts < entry_time` skip, and the fill/timestamp
materialisation. Per-bar values are still wrapped in `float()` / `pd.Timestamp()` so the trade dicts are
bit-for-bit identical.

**Baby.** The part that decides when a trade hits its stop or target used to copy a slab of the minute
chart and walk it row-by-row the slow way. Now it walks the same minutes straight from fast arrays. Same
exits, same prices, same timestamps — proven on all six timeframes.

---

## 2. Before / after (clean benchmark, idle box)

| TF | baseline | B2 | B3a | **B3b** | total Δ |
|----|--------:|---:|----:|--------:|--------:|
| 4h | 13.73 s | 11.52 | 11.85 | **11.10 s** | **−19 %** |
| 1h | 21.19 s | 16.69 | 16.84 | **15.84 s** | **−25 %** |
| 15m | 43.73 s | 27.86 | 23.93 | **21.91 s** | **−50 %** |
| 5m | 96.29 s | 46.33 | 37.52 | **35.23 s** | **−63 %** |
| 2m | 269.10 s | 113.03 | 91.53 | **89.38 s** | **−67 %** |

B3b's incremental gain is smaller than B3a's: the exit walk only iterates the 1-min windows that hold an
**open** trade (not every bar), so removing its `itertuples` overhead helps less than killing the per-bar
`df_4h.iloc`. The remaining fine-TF cost is now the **shared Axis-A 1-min indicator compute (~flat ~15 s)**
plus the per-trade event-assembly loop in `build_payload` — outside Axis B's engine scope.

---

## 3. Why it's exact
- `md_arr` (1-min Date) is tz-naive `datetime64`; the skip `md_arr[t] < np.datetime64(entry_time)` is the
  same instant comparison as the original `pd.Timestamp(sub.Date) < entry_time`.
- `float(mh_arr[t])`/`float(ml_arr[t])`/`float(mc_arr[t])` == `float(getattr(sub, …))` bit-for-bit (same
  underlying float64); the soft-fill uses the same `m_close`, hard-fills use the dict line values.
- The exit timestamp is materialised only on exit as `pd.Timestamp(md_arr[t])` == the original
  `pd.Timestamp(sub.Date)`, so `exit_time` / `blocked_until` are identical.
- Branch order, soft-counter increments/resets, and the `return`-on-first-exit are unchanged.
- **Confirmed by the 6-TF golden byte-match** (summary + trades-SHA + vote-SHA) + the full parity suite.

> Scope note: the carry-mode resolver slice (`sub_w = df_1min.iloc[...]`, used only when retrace/wait is
> active) was intentionally left unchanged — it crosses the `entry_resolver` interface and is out of B3b's
> minimal scope.

---

## 4. Code touched / links
| File | Change |
|------|--------|
| `engine.py` (`backtest` + `_walk_exit_for_4h`) | + `md_arr/mh_arr/ml_arr/mc_arr` 1-min numpy extraction; `_walk_exit_for_4h` iterates `range(lo,hi)` over arrays instead of `df_1min.iloc[lo:hi].itertuples()`; exit logic unchanged; `sub_ts` materialised at exit only. |

Only `engine.py`. No signature change.

---

## 5. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `perf/check_golden.py 4h 2h 1h 15m 5m 2m` | ✅ **ALL 6 MATCH** |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_fast_parity.py` + `test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **166 passed** |
| Benchmark `B3b_exitwalk_numpy` | ✅ 15m −50 %, 5m −63 %, 2m −67 % vs baseline |

---

## 6. Reverting Step B3b
```bash
git revert --no-edit <STEP_B3b_COMMIT>   # restores df_1min.iloc[lo:hi].itertuples() (B1+B2+B3a stay)
git reset --hard f9d6f36                 # or hard-reset to the Phase-0 anchor
```

## 7. Status
- ✅ Step B3b complete, committed, all 6 golden TFs byte-identical. **Axis B done.**
- Cumulative (baseline→B3b): 4h −19 %, 1h −25 %, 15m −50 %, 5m −63 %, **2m −67 % (269 s → 89 s)**.
- Remaining fine-TF cost is the shared Axis-A indicator compute (already optimized in D/A1/A2/E/C′) + the
  per-trade event loop — both outside the engine. Further Axis-B gains would need Numba (blocked) or a
  vectorized event-assembly pass (separate, lower-ROI).
