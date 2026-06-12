# MASTER REPORT — Backtester Speed Optimization (task #210), end-to-end

**Date:** 2026-06-12 · branch `dev` (local only, **nothing pushed**) · single consolidated record.
**Scope:** every change from the Phase-0 safety net through Axis-A indicator vectorization (D/A1/A2/E/C′)
to the Axis-B engine rewrite (B1/B2/B3a/B3b). **All numbers below are pre-extracted** from
`perf/bench_history.json`, the per-step `perf/UPDATE_step_*.md`, and the equivalence runs already executed —
nothing was re-run to produce this document.
**Languages:** professional + **baby**. **Result invariant:** every step is proven trade-for-trade
byte-identical (golden summary + trades-SHA + per-indicator vote-SHA). **166 tests passing.**

---

## 0. The one-screen summary

> A single backtest got **~3× faster on coarse timeframes** (4h 36.2 s → 11–12 s) and **3–7× faster on fine
> timeframes** (2m >600 s → 89 s; 5m 113 s → 35 s), **without changing a single trade**. Two independent
> fronts did it: **Axis A** vectorized the indicator math that dominates coarse TFs; **Axis B** removed the
> per-bar pandas overhead in the engine that dominates fine TFs. Each step is one commit, one revert point,
> and was gated by a four-layer parity net.

**Baby.** We made the strategy-tester much faster two different ways — one for the big-timeframe tests, one
for the small-timeframe tests — and we proved with a "lie detector" that it still makes the exact same
trades every time. If anything ever differed, we'd undo it.

---

## 1. The map — why there were two fronts

A backtest's time lives in two places that scale **oppositely** with timeframe:

| Axis | What runs | Scales with | Dominates | Fixed by |
|------|-----------|-------------|-----------|----------|
| **A — 1-minute indicator compute** | each indicator across all 486,969 one-minute bars | (constant — same 1-min history at every TF) | **coarse** TFs (4h/2h/1h) | D, A1, A2, E, C′ |
| **B — per-decision-bar engine loop** | entry rule + exit walk, once per decision bar | **decision-bar count** | **fine** TFs (5m/2m) | B1, B2, B3a, B3b |

Decision-bar counts (why fine TFs explode): 4h ≈ 2,119 · 2h ≈ 4,236 · 1h ≈ 8,121 · 15m ≈ 32,467 ·
5m ≈ 97,401 · **2m ≈ 243,504**.

---

## 2. Full commit chain (every change, in order) — the rollback map

| # | SHA | Step | Axis | What changed (one line) | Result |
|--:|-----|------|:----:|-------------------------|--------|
| 0 | `f9d6f36` | Phase 0 safety net | — | golden baselines (6 TFs) + `check_golden` + `bench` + equivalence framework | **the rollback anchor** |
| 1 | `e764482` | D — obv | A | `np.cumsum(sign(diff)*vol)` replaces sequential loop | 64×, bit-identical |
| 2 | `1f1c29f` | A1 — bollinger | A | rolling std via `sliding_window_view().std()` | 40×, bit-identical |
| 3 | `f178ec3` | A2 — cci | A | rolling mean-abs-deviation vectorized | 4×, bit-identical |
| 4 | `08b8c77` | E — order_blocks sampled | A | per-bar OB signal only at sampled indices (`signal_at`) | −9 s, byte-identical |
| 5 | `5d1945e` | C′ — order_blocks numpy zones | A | live zones Python lists → numpy arrays (overlap `np.any`, prune mask) | 2.8×, byte-identical |
| 6 | `6b89b22` | **B1 — vectorize decision_signals** | B | per-bar pandas signal loop → numpy gather + array ops; +18 equiv tests | signal 100–490×, bit-identical |
| 7 | `6bab4e2` | **B2 — inject signal into engine** | B | `engine.backtest(signals=…)` reads precomputed array, not per-bar `_stage1` | fine TFs −36…−58%, byte-identical |
| 8 | `e20c8b8` | **B3a — numpy df_4h rows** | B | pre-extract `Date/Close`; loop indexes arrays, not `df_4h.iloc[idx]` | fine TFs further −14…−19%, byte-identical |
| 9 | `7fc9655` | **B3b — numpy 1-min exit walk** | B | `_walk_exit_for_4h` over numpy arrays, not `iloc[lo:hi].itertuples()` | Axis B complete, byte-identical |
| — | `2208fd8` | docs | — | STATUS + ROI report pinned with Axis-B results | — |

Revert any single step: `git revert <sha>`. Full Axis-B rollback: `git revert 7fc9655 e20c8b8 6bab4e2 6b89b22`.
Pre-optimization nuke: `git reset --hard f9d6f36`.

---

## 3. MASTER timing table — full backtest per TF (the headline)

All values are recorded `perf/bench_history.json` labels. `baseline` = Phase-0 (pre-everything);
`manual_bg` = post-Axis-A (after C′); `B2/B3a/B3b` = the Axis-B series. (Some `baseline`/`manual_bg` runs
carried mild background load; the B-series ran on a quiet box — directional conclusions are unaffected.)

| TF | `baseline` (pre-all) | `manual_bg` (post-Axis-A) | `B2` | `B3a` | `B3b` (final) | **total Δ vs baseline** | Δ vs post-Axis-A |
|----|--------------------:|--------------------------:|-----:|------:|--------------:|------------------------:|-----------------:|
| 4h | 36.19 s | 13.73 s | 11.52 | 11.85 | **11.10 s** | **−69 %** | −19 % |
| 2h | 17.90 s | 10.69 s | — | — | (golden MATCH) | (Axis A −40 %) | — |
| 1h | 36.09 s | 21.19 s | 16.69 | 16.84 | **15.84 s** | **−56 %** | −25 % |
| 15m | 84.38 s | 43.73 s | 27.86 | 23.93 | **21.91 s** | **−74 %** | −50 % |
| 5m | 113.38 s | 96.29 s | 46.33 | 37.52 | **35.23 s** | **−69 %** | −63 % |
| 2m | >600 s (budget) | 269.10 s | 113.03 | 91.53 | **89.38 s** | **≥ −85 %** | −67 % |

> **Reading it.** Axis A did most of the coarse-TF win (4h 36→14, 2h 18→11). Axis B did most of the
> fine-TF win (2m 269→89, 5m 96→35, 15m 44→22). The two fronts are complementary — together they cut every
> timeframe.

**Baby.** Big-timeframe tests: roughly a third of the old time. Small-timeframe tests: down to a third or
even less. The 2-minute test went from "over ten minutes" to "a minute and a half".

---

## 4. Per-change BEFORE / AFTER detail

### 4.1 Axis A — indicator micro-benchmarks (real 486,969-bar 1-minute series, bit-identical)
| Step | Indicator | Before | After | Speedup | Method |
|------|-----------|-------:|------:|--------:|--------|
| D | `obv` | 540 ms | **8 ms** | 64× | `np.cumsum(np.sign(np.diff(c))*vol[1:])` |
| A1 | `bollinger` std | 6,375 ms | **159 ms** | 40× | `sliding_window_view(c,n).std(axis=1)` |
| A2 | `cci` MAD | 3,567 ms | **925 ms** | 4× | `sliding_window_view` mean-abs-deviation |
| E+C′ | `order_blocks` (sampled) | 16,600 ms | **5,830 ms** | 2.8× | sampled `signal_at` + numpy zone arrays |

Net Axis-A effect on the **4h** full backtest: **36.2 s → 12.1 s (−67 %)** (clean, per `STATUS`).

### 4.2 Axis B — Step B1: `decision_signals` precompute (per TF, real frames, exact)
| TF | bars | before (per-bar pandas) | **after (numpy)** | speedup | mismatches |
|----|-----:|------------------------:|------------------:|--------:|:----------:|
| 4h | 2,119 | 443.5 ms | **4.2 ms** | 105.6× | 0 |
| 2h | 4,236 | 829.1 ms | **4.0 ms** | 209.7× | 0 |
| 1h | 8,121 | 1,508.3 ms | **7.6 ms** | 197.8× | 0 |
| 15m | 32,467 | 5,829.7 ms | **15.9 ms** | 366.8× | 0 |
| 5m | 97,401 | 17,019.8 ms | **34.9 ms** | 488.0× | 0 |
| 2m | 243,504 | 41,948.6 ms | **127.1 ms** | 330.0× | 0 |

### 4.3 Axis B — Steps B2/B3a/B3b: full-backtest progression (fine TFs)
| TF | post-Axis-A | B2 (signal inject) | B3a (df_4h numpy) | B3b (exit walk numpy) | cumulative Δ |
|----|-----------:|-------------------:|------------------:|----------------------:|-------------:|
| 4h | 13.73 s | 11.52 | 11.85 | **11.10** | −19 % |
| 1h | 21.19 s | 16.69 | 16.84 | **15.84** | −25 % |
| 15m | 43.73 s | 27.86 | 23.93 | **21.91** | −50 % |
| 5m | 96.29 s | 46.33 | 37.52 | **35.23** | −63 % |
| 2m | 269.10 s | 113.03 | 91.53 | **89.38** | −67 % |

> B2 removed the per-bar `_stage1_candle_signal` (~27 s profile cost). B3a removed the per-bar
> `df_4h.iloc[idx]` (`fast_xs`, ~26 s). B3b removed the `df_1min.iloc[lo:hi].itertuples()` exit walk
> (smaller, since it only runs on open-trade windows).

---

## 5. The profiler evidence that drove Axis B (15m, cProfile, pre-Axis-B)

| hot spot | calls | cum time | nature | fixed by |
|----------|------:|---------:|--------|----------|
| `engine._stage1_candle_signal` | 95,495 | 27.2 s | per-bar entry rule (pandas scalars) | **B1+B2** |
| `pandas fast_xs` (`df.iloc[idx]`) | 159,238 | 25.8 s | per-bar Series build | **B3a** |
| `Series.__getitem__` | 3.48 M | 20.3 s | scalar cell reads | B1+B2+B3a |
| `datetimelike.__getitem__` | 331 k | 22.1 s | per-bar timestamp boxing | B3a |
| Py-3.14 `typing`/`annotationlib` | ~12 M | ~8 s | overhead dragged in by the above | removed with the above |
| `smc.order_blocks` + `market_structure` | 6 | ~15 s | the actual indicator math (Axis A) | already optimized |

Full investigation: `perf/INVESTIGATION_axisB_per_decision_loop.md`. Plan: `perf/ACTION_PLAN_axisB.md`.

---

## 6. File-by-file change map (every file touched)

| File | Steps | What changed | Reference doc |
|------|-------|--------------|---------------|
| `indicators/classic.py` | D, A1, A2 | `obv`/`bollinger`/`cci` vectorized | `UPDATE_step_D_obv.md`, `…_A1_bollinger.md`, `…_A2_cci.md` |
| `indicators/smc.py` | E, C′ | `order_blocks` `signal_at` + numpy zones | `UPDATE_step_E_orderblocks_sampled.md`, `…_Cprime_…md` |
| `indicators/library.py`, `runner.py` | E | `_supports_signal_at` capability flag + forwarding | `…_E_…md` |
| `indicators/_reference.py` | Phase 0 | frozen verbatim originals (`obv_ref`, `bollinger_ref`, `cci_ref`, `order_blocks_ref`) | `UPDATE_phase0_safety_net.md` |
| **`optimize/signals.py`** | **B1** | `decision_signals` numpy + `decision_signals_ref` frozen + `_box_dates_vec` | `UPDATE_step_B1_vectorized_signal.md` |
| **`engine.py`** | **B2, B3a, B3b** | `backtest(signals=…)`; numpy `d4_dates/d4_close`; numpy `md/mh/ml/mc_arr` exit walk | `UPDATE_step_B2/B3a/B3b_*.md` |
| **`strategy.py`** | **B2** | precompute `decision_signals(d4, box)` once, pass `signals=` | `UPDATE_step_B2_engine_signal_inject.md` |
| `tests/test_speedopt_equiv.py` | D/A1/A2/E/C′ | equivalence tests vs `_reference` | — |
| **`tests/test_axisB_signal_equiv.py`** | **B1** | 18 tests (random + adversarial + real) | `UPDATE_step_B1_…md` |
| `perf/` (golden, bench, check, equiv) | Phase 0 + all | safety net + benchmark history | `STATUS_optimization.md` |

---

## 7. Verification matrix (what proved each step)

| Gate | Catches | Axis A | B1 | B2 | B3a | B3b |
|------|---------|:------:|:--:|:--:|:---:|:---:|
| `perf/check_golden.py` (6-TF byte-match: summary+trades-SHA+vote-SHA) | any trade/value drift | ✅ | ✅(3TF) | ✅(6TF) | ✅(6TF) | ✅(6TF) |
| `tests/test_speedopt_equiv.py` / `test_axisB_signal_equiv.py` | function vs frozen ref | ✅ | ✅ 18 | — | — | — |
| `optimize/test_parity.py` (`$7,735/$3,670/n=66`) | build_payload summary | ✅ | ✅ | ✅ | ✅ | ✅ |
| `optimize/test_fast_parity.py` + `test_indicator_parity.py` | engine ⇄ fast_engine ⇄ signals | ✅ | ✅ | ✅ | ✅ | ✅ |
| full `pytest` | everything | 148 | **166** | 166 | 166 | 166 |

Extra B1 proof: `decision_signals == decision_signals_ref` **element-for-element on all 6 real TFs, 0
mismatches** (incl. 243,504 bars at 2m).

---

## 8. Scope & honesty notes (carried from the investigation)
- The slow `engine.SimpleStrategy` is used **only** by `strategy.build_payload` (dashboard + standalone
  backtester + bench). The **optimizer sweeps already use the vectorized `optimize/fast_engine.py`** — Axis
  B did **not** change sweep speed (already fast); it sped the **interactive/dashboard** path.
- `fast_engine` could **not** simply replace the slow engine in `build_payload`: it is a feature subset
  (no `entry_resolver`/retrace, veto, blocked-log, or per-trade line fields the WS-I champions need).
- Numba (`C`) remains **blocked** here (Python 3.14 has no wheel + PEP 668); `C′` was the dependency-free
  substitute. `A3` (stochastic/mfi/keltner) and `market_structure` vectorization remain **HOLD** (low ROI,
  re-validation tax) per `REPORT_optimization_roi_and_decision.md`.

---

## 9. What remains (optional, lower-ROI)
The remaining fine-TF cost is the shared **Axis-A indicator compute (~flat ~15 s)** plus the per-trade
**event-assembly loop** in `build_payload` (building the dashboard events/attribution from the trade list).
Both are outside the engine and lower-ROI. Bigger cuts would need Numba (blocked) or a vectorized
event-assembly pass. Recommendation stands: **good place to stop** unless a specific need arises.

---

## 10. Cumulative bottom line

| Metric | Before (Phase 0) | After (B3b) |
|--------|------------------|-------------|
| 4h backtest | 36.2 s | **11.1 s** (−69 %) |
| 15m backtest | 84.4 s | **21.9 s** (−74 %) |
| 5m backtest | 113.4 s | **35.2 s** (−69 %) |
| 2m backtest | > 600 s | **89.4 s** (≥ −85 %) |
| signal precompute (2m) | 41,949 ms | **127 ms** (330×) |
| tests | 148 | **166** |
| results | — | **byte-identical at every step** |

All local on `dev`, nothing pushed; every step independently revertible; the running dashboard
(restarted 2026-06-12) now serves the optimized code.
