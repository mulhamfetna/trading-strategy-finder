# Update Report — Axis B · Step B3a: numpy `df_4h` row access

**Date:** 2026-06-12 · branch `dev` · task #210
**Type:** speed — **results byte-identical (all 6 golden TFs MATCH)**. No new dependency.
**Plan:** `perf/ACTION_PLAN_axisB.md` §4 · **builds on:** B1, B2

---

## 1. What changed (plain + professional)

**Professional.** The engine loop built a fresh pandas Series for **every** decision bar via
`candle = df_4h.iloc[idx]` (the profiler's `fast_xs`, ~26 s cumulative on 15m). B3a pre-extracts the two
columns the loop actually reads — `Date` and `Close` — into numpy arrays **once** (`d4_dates`, `d4_close`),
and the per-bar hot path now indexes those arrays. `df_4h.iloc[idx-1]` survives **only** in the
`signals=None` parity branch (where `_stage1_candle_signal` needs the full row); the
signal-injected path (every `build_payload` backtest) no longer touches `.iloc` for the signal/entry.

**Baby.** Instead of photocopying a whole spreadsheet row every bar just to read two numbers, we copied
those two columns into fast lists once and read straight from them. Same numbers, no photocopier.

---

## 2. Before / after (clean benchmark, idle box)

| TF | baseline | B2 | **B3a** | cumulative Δ |
|----|--------:|---:|--------:|-------------:|
| 4h | 13.73 s | 11.52 s | 11.85 s | −14 % |
| 1h | 21.19 s | 16.69 s | 16.84 s | −21 % |
| 15m | 43.73 s | 27.86 s | **23.93 s** | **−45 %** |
| 5m | 96.29 s | 46.33 s | **37.52 s** | **−61 %** |
| 2m | 269.10 s | 113.03 s | **91.53 s** | **−66 %** |

(4h/1h are within run-to-run noise — they have too few decision bars for `fast_xs` to matter; the win is
all on the fine TFs, as expected.) Remaining fine-TF cost is the 1-min **exit walk**
(`df_1min.iloc[lo:hi].itertuples()`) — **Step B3b**.

---

## 3. Why it's exact
- `Date` is tz-naive `datetime64[us]` (verified) ⇒ `to_numpy()` is a zero-copy view and
  `pd.Timestamp(d4_dates[i]) == pd.Timestamp(df_4h['Date'].iloc[i])`.
- `d4_close = df_4h['Close'].to_numpy(float)` ⇒ `float(d4_close[i]) == float(df_4h['Close'].iloc[i])`
  bit-for-bit.
- The three entry-price reads (`entry_px`, carry-mode `sclose` ×2) all used `signal_candle['Close']` =
  `d4_close[idx-1]`; replacing them also removed the last `signal_candle` reference from the
  signal-injected path (it now lives solely in the `signals=None` branch).
- **Confirmed by the 6-TF golden byte-match** (summary + trades-SHA + vote-SHA) + the full parity suite.

---

## 4. Code touched / links
| File | Change |
|------|--------|
| `engine.py` (`SimpleStrategy.backtest`) | + `d4_dates`/`d4_close` numpy extraction; loop uses `pd.Timestamp(d4_dates[idx])`; `signal_candle = df_4h.iloc[idx-1]` moved into the `signals=None` branch only; entry/sclose reads use `d4_close[idx-1]`. |

Only `engine.py`. No signature change. `_stage1_candle_signal` (the `signals=None` reference path) untouched.

---

## 5. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `perf/check_golden.py 4h 2h 1h 15m 5m 2m` | ✅ **ALL 6 MATCH** |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_fast_parity.py` + `test_indicator_parity.py` | ✅ OK |
| Full `pytest` | ✅ **166 passed** |
| Benchmark `B3a_d4_numpy` | ✅ 15m −45 %, 5m −61 %, 2m −66 % vs baseline |

---

## 6. Reverting Step B3a
```bash
git revert --no-edit <STEP_B3a_COMMIT>   # restores df_4h.iloc[idx] row access (B1+B2 stay)
git reset --hard f9d6f36                 # or hard-reset to the Phase-0 anchor
```

## 7. Status & next
- ✅ Step B3a complete, committed, all 6 golden TFs byte-identical. Fine TFs −45 %…−66 % cumulative.
- ▶️ **Next: Step B3b** (approval-gated, the riskiest sub-step) — rewrite `_walk_exit_for_4h` to iterate
  pre-extracted 1-min numpy arrays (`Date/High/Low/Close`) instead of `df_1min.iloc[lo:hi].itertuples()`,
  preserving the exact per-bar exit priority + soft-consec-counter logic. Acceptance: all 6 golden TFs
  byte-identical.
