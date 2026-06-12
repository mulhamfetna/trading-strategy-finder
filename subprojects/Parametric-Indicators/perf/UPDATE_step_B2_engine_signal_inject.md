# Update Report — Axis B · Step B2: inject precomputed signal into the engine

**Date:** 2026-06-12 · branch `dev` · task #210
**Type:** speed — **results byte-identical (all 6 golden TFs MATCH)**. First step that changes the
backtester's core engine hot path. No new dependency.
**Plan:** `perf/ACTION_PLAN_axisB.md` §3 · **builds on:** Step B1 (`perf/UPDATE_step_B1_vectorized_signal.md`)

---

## 1. What changed (plain + professional)

**Professional.** `engine.SimpleStrategy.backtest` gained an optional `signals=None` parameter — a
precomputed per-decision-bar Stage-1 signal array (object `'long'/'short'/'hold'`, aligned 1:1 with
`df_4h`). When supplied, the entry branch reads `signals[idx-1]` instead of recomputing
`_stage1_candle_signal(df_4h.iloc[idx-1], box.loc[...])` per bar. `strategy.build_payload` now precomputes
this array **once** (the vectorized `optimize.signals.decision_signals` from B1) and passes it in.
**`signals=None` ⇒ the original per-bar path runs verbatim**, so every other caller and every parity test is
unchanged.

**Baby.** The engine used to stop on every single bar and slowly work out "buy/sell/wait" with the
spreadsheet method. Now we hand it the whole answer-sheet (made in one fast sweep in B1) and it just reads
the row it needs. Same trades — proven on all six timeframes — just much less waiting on the fine ones.

---

## 2. Before / after (clean benchmark, idle box)

| TF | baseline `manual_bg` | **B2 `B2_signal_inject`** | Δ | golden |
|----|---------------------:|--------------------------:|----:|:------:|
| 4h | 13.73 s | **11.52 s** | −16 % | ✅ MATCH |
| 1h | 21.19 s | **16.69 s** | −21 % | ✅ MATCH |
| 15m | 43.73 s | **27.86 s** | **−36 %** | ✅ MATCH |
| 5m | 96.29 s | **46.33 s** | **−52 %** | ✅ MATCH |
| 2m | 269.10 s | **113.03 s** | **−58 %** | ✅ MATCH |

The reduction grows with decision-bar count (the Axis-B signature): coarse TFs gain a little, fine TFs are
cut by half or more. The remaining fine-TF cost is the `df_4h.iloc[idx]` row build (`fast_xs`) + the 1-min
exit walk — the **Step B3** targets.

> Note: `build_payload` still calls `df_4h.iloc[idx-1]` for the entry close price (`signal_candle['Close']`),
> so `fast_xs` is not yet removed — that is deliberately deferred to B3 to keep B2's blast radius minimal.

---

## 3. Why it's exact
`signals[idx-1]` is `decision_signals(d4, box)[idx-1]`, which B1 proved equals
`_stage1_candle_signal(d4.iloc[idx-1], box.loc[_candle_to_box_date(...)])` **element-for-element on all 6
real TFs (0 mismatches)**. The engine consumes the signal at the identical index (`idx-1`, the just-closed
bar) and feeds it through the unchanged flip/scope/gate/veto/carry-mode/exit logic. Therefore the trade
stream is identical — confirmed by the **6-TF golden byte-match** (summary + trades-SHA + vote-SHA) and the
parity suite.

---

## 4. Code touched / links
| File | Change |
|------|--------|
| `engine.py` (`SimpleStrategy.backtest`) | + `signals=None` param; length guard; entry branch reads `signals[idx-1]` when provided, else the original `_stage1_candle_signal` + `box.loc` path (verbatim). |
| `strategy.py` (`build_payload`) | + `from optimize.signals import decision_signals`; precompute `sig_arr = decision_signals(d4, box)` once; pass `signals=sig_arr` to `.backtest(...)`. |

No signature change for any existing caller (new param is keyword-optional, default `None`).
`_stage1_candle_signal` remains the frozen reference.

---

## 5. Verification evidence (all green)
| Gate | Result |
|------|--------|
| `perf/check_golden.py 4h 2h 1h 15m 5m 2m` | ✅ **ALL 6 MATCH** (summary + trades-SHA + vote-SHA) |
| `optimize/test_parity.py` | ✅ `$7,735 / $3,670 / n=66` |
| `optimize/test_fast_parity.py` | ✅ OK (6 scenarios, mismatch=0) |
| `optimize/test_indicator_parity.py` | ✅ OK (5 scenarios, mismatch=0) |
| Full `pytest` | ✅ **166 passed** |
| Benchmark `B2_signal_inject` | ✅ fine TFs −36 %…−58 % (see §2) |

---

## 6. Reverting Step B2
```bash
git revert --no-edit <STEP_B2_COMMIT>   # restores the inline _stage1_candle_signal path (B1 stays)
git reset --hard f9d6f36                # or hard-reset to the Phase-0 rollback anchor
```
B2 touches only the signal *source*. Reverting restores the per-bar computation; B1's vectorized
`decision_signals` (still used by the optimizer) is unaffected.

## 7. Status & next
- ✅ Step B2 complete, committed, all 6 golden TFs byte-identical. Fine-TF backtests −36 %…−58 %.
- ▶️ **Next: Step B3** (approval-gated) — numpy-fy the remaining per-bar row access: pre-extract `df_4h`
  `Date/O/H/L/C` arrays (kill `fast_xs`/`signal_candle['Close']`) and rewrite `_walk_exit_for_4h` over 1-min
  numpy arrays instead of `df_1min.iloc[lo:hi].itertuples()`. Largest engine surface → split into B3a/B3b,
  each golden-checked. Acceptance: all 6 golden TFs byte-identical.
