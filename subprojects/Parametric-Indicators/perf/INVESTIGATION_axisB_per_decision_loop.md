# Deep Investigation — Axis B: the per-decision-bar engine loop (task #210)

**Date:** 2026-06-12 · branch `dev` (local only) · task #210 · **status: INVESTIGATION ONLY — no code changed**
**Author note:** written in both **professional** and **baby** language. This is the evidence + design
record that must exist *before* any implementation. Nothing in this document modifies the system.
Implementation is gated on explicit per-step approval (plan in §8).

---

## 0. Executive summary (one box)

> The backtester is fast on coarse timeframes (4h ≈ 12 s) but slow on fine ones (5m ≈ 96 s, 2m > 600 s).
> Profiling proves the slowness is **NOT the indicator math** — it is **pandas per-bar access inside the
> engine's Python loop** (`engine.SimpleStrategy.backtest`), which scales with the number of decision bars.
> The single biggest culprit is `engine._stage1_candle_signal`, a per-bar function that reads OHLC and box
> levels as pandas scalars; it is **parameter-independent** (depends only on price + box, never on SL/TP/
> indicators) and can be computed **once, vectorized in numpy**. The fix lives entirely inside `engine.py`
> (the optimizer already uses a separate fast engine), must stay **trade-for-trade byte-identical**, and is
> protected by an existing four-layer parity net. Expected result: fine-TF single backtests roughly
> **−50 % to −70 %**, largest in absolute terms at 2m.

**Baby version.** The robot re-reads the price chart one row at a time using a slow "spreadsheet" method,
and on small timeframes there are hundreds of thousands of rows, so it crawls. The part that decides
"buy/sell/wait" doesn't depend on any of the knobs we tune, so we can work it out for the whole chart in
one fast sweep instead of row-by-row. Same decisions, far less waiting.

---

## 1. Why this investigation exists (the question)

From `perf/REPORT_optimization_roi_and_decision.md`, the backtester has **two cost axes**:

| Axis | What it is | Where it dominates | Prior work |
|------|-----------|--------------------|-----------|
| **A — 1-minute indicator compute** | each indicator computed across all 486,969 one-minute bars | **coarse** TFs (4h/2h/1h) | D/A1/A2/E/C′ — mostly done (4h −67 %) |
| **B — per-decision-bar loop** | the entry/exit engine, executed once per decision bar | **fine** TFs (5m/2m) | **untouched until now** |

Axis A was optimized to the point of diminishing returns. The ROI report named **Axis B** the real
remaining prize *and* warned it is exactly the layer the planned "more complicated operations" expansion
will make heavier (more indicators / instruments / per-bar logic all pour into the per-decision loop). The
user chose to open Axis B. This document is the investigation that precedes any change.

---

## 2. Measurement first (no guessing) — the profile

**Method.** A single `strategy.build_payload(...)` run on the **15m** champion preset, wrapped in
`cProfile`, sorted by `tottime` (self-time). 15m was chosen as the smallest fine TF that still exposes Axis
B at scale: **32,467 decision bars** over the same 486,969 one-minute bars. Script: `/tmp/profile_axisB.py`
(throwaway investigation tool, not committed).

> ⚠️ **Timing caveat.** This profile ran **while the all-TF benchmark (`manual_bg`, PID 14065) was still
> executing the 2m run AND the dashboard server was up** — so the *absolute* wall time below (112.6 s) is
> inflated by CPU contention versus the clean 15m time of **43.7 s** (recorded by the benchmark). **Call
> counts are exact regardless of load, and the relative breakdown is load-invariant** — those are what this
> investigation relies on. Clean before/after wall times will be re-measured on an idle box at
> implementation time.

### 2.1 Top self-time consumers (15m, cProfile, `tottime`)

| # | ncalls | tottime | cumtime | function | what it really is |
|--:|-------:|--------:|--------:|----------|-------------------|
| 1 | 45,647,497 | 7.04 s | 8.69 s | `builtins.isinstance` | pandas internal type checks (dragged in by per-cell access) |
| 2 | 3,689,704 | 5.27 s | 5.27 s | `numpy.ufunc.reduce` | per-window indicator reductions (**Axis A**, shared) |
| 3 | **159,238** | 4.82 s | **25.81 s** | `pandas …managers.fast_xs` | **`df_4h.iloc[idx]` — a Series built per decision bar** |
| 4 | 3,480,926 | 4.51 s | 20.33 s | `pandas Series.__getitem__` | scalar cell reads: `candle['Open']`, `box_row[col]` |
| 5 | 331,824 | 4.41 s | 22.11 s | `datetimelike.__getitem__` | per-bar timestamp boxing |
| 6 | 1,327,296 | 3.45 s | 7.31 s | `typing._type_check` | **Python 3.14 typing overhead** dragged in by the above |
| 7 | 3,480,926 | 3.25 s | 8.93 s | `pandas Series._get_value` | scalar getter backing #4 |
| 8 | **95,495** | 3.17 s | **27.21 s** | **`engine._stage1_candle_signal`** | **the per-bar entry rule — the prime mover** |
| 9 | 3,709,725 | 3.16 s | 4.07 s | `pandas Index.get_loc` | label lookups: `box_row[col]`, `box.loc[box_date]` |
| 10 | 2,986,416 | 3.15 s | 5.28 s | `annotationlib.__hash__` | Python 3.14 annotation overhead |
| 11 | 4,054,021 | 2.92 s | 4.98 s | `indexing.check_dict_or_set_indexers` | pandas indexer validation per access |
| 12 | **2** | 2.66 s | 10.22 s | `smc.order_blocks` | **Axis A** indicator (shared, already optimized in E/C′) |
| 13 | 3,232,760 | 2.38 s | 2.86 s | `Index.__contains__` | "is this column present" per cell |
| 14 | **4** | 2.05 s | 4.93 s | `smc.market_structure` | **Axis A** indicator (shared) |
| 15 | 95,495 | 1.46 s | 1.46 s | `box_lookup._candle_to_box_date` | per-bar box-date mapping |

(15 of 577 rows shown; the long tail is more of the same pandas-per-cell machinery.)

### 2.2 How to read this table (baby + professional)

**Professional.** Group the rows by origin:

- **Axis A (indicator math), shared & already optimized:** rows 2, 12, 14 ≈ `order_blocks` 10.2 s cum +
  `market_structure` 4.9 s cum + their reduces ≈ **~15–20 s of the 112 s**. This is the *same absolute cost
  at every TF* (always 486,969 one-minute bars) — at 4h it's most of the 12 s; at 15m it's a small slice.
- **Axis B (engine per-bar pandas overhead), the target:** rows 1, 3, 4, 5, 7, 8, 9, 11, 13, 15 — all
  pandas single-row / single-cell access and the Python-3.14 typing machinery it drags in. This is the
  **clear majority** of the run and it is **multiplied by decision-bar count**.

The two giant cumulative numbers — **`fast_xs` 25.8 s** (row access) and **`_stage1_candle_signal` 27.2 s**
(per-bar entry rule) — are the headline. They overlap: `_stage1_candle_signal` *contains* a lot of the
`Series.__getitem__` / `get_loc` cost because it reads `box_row[col]` and `candle['Open']` cell-by-cell.

**Baby.** Imagine reading a giant spreadsheet by clicking each cell with a mouse, one click at a time. Every
click is tiny, but you do **tens of millions** of clicks. Two activities do almost all the clicking:
(a) grabbing a whole row for each bar, and (b) the "should I buy or sell here?" check, which clicks several
cells per bar. The chart math (the indicators) is fast by comparison.

### 2.3 The scaling law (why fine TFs explode)

`_stage1_candle_signal` and `fast_xs` are called **once per decision bar**. Decision-bar counts:

| TF | decision bars | clean backtest (manual_bg) | dominated by |
|----|--------------:|---------------------------:|--------------|
| 4h | ~2,119 | 13.7 s | Axis A (indicators) |
| 2h | ~4,200 | 10.7 s | mixed |
| 1h | ~8,400 | 21.2 s | mixed |
| 15m | **32,467** | 43.7 s | **Axis B** |
| 5m | ~97,000 | 96.3 s | **Axis B** |
| 2m | ~240,000 | > 600 s | **Axis B (overwhelming)** |

> Axis A is a **flat ~10–15 s tax** (same 1-minute history at every TF). Everything *above* that flat tax,
> as the TF gets finer, is Axis B. At 2m, Axis A is noise and the per-bar pandas loop is essentially the
> entire runtime.

---

## 3. Root cause, precisely, with code

### 3.1 The engine loop — `engine.SimpleStrategy.backtest` (`engine.py:320`)
```python
for idx in range(len(df_4h)):
    candle = df_4h.iloc[idx]                       # ← fast_xs: builds a Series every bar (row 3)
    ts_new_bar_start = pd.Timestamp(candle['Date'])
    _walk_exit_for_4h(idx)                         # ← 1-min exit walk (see §3.3)
    if open_trade is None and idx >= 1:
        ...
        signal_candle = df_4h.iloc[idx - 1]        # ← another fast_xs
        box_date = BoxLookup._candle_to_box_date(signal_ts)   # ← row 15
        box_row = box_df_indexed.loc[box_date]     # ← Index.get_loc, NO caching (row 9/13)
        signal = _stage1_candle_signal(signal_candle, box_row)   # ← row 8, the prime mover
```
Every decision bar pays: one (often two) `df.iloc[idx]` Series construction, a non-cached box `.loc`, and a
`_stage1_candle_signal` call that itself reads ~6–10 pandas scalars.

### 3.2 The per-bar entry rule — `engine._stage1_candle_signal` (`engine.py:97`)
```python
opn = float(candle['Open']); high = float(candle['High'])      # pandas scalar reads
low = float(candle['Low']);  close = float(candle['Close'])
...
for upper_col, lower_col, _label in _LEVEL_PAIRS:              # weekly + monthly level pairs
    if upper_col not in box_row.index or lower_col not in box_row.index:  # Index.__contains__
        continue
    u = box_row[upper_col]; l = box_row[lower_col]             # Series.__getitem__ → get_loc
    if pd.isna(u) or pd.isna(l): continue
    touched = (low <= float(u)) and (high >= float(l))
    if not touched: continue
    if color == 'green' and close > float(u): has_long = True
    elif color == 'red' and close < float(l): has_short = True
```
**Crucial property:** this function's output depends **only** on the decision-bar OHLC and the box level
columns. It does **not** read `sl_soft`, `tp`, `gate`, indicators, or any tuned parameter. It is therefore
**parameter-independent** → computable **once** for the whole frame, in vectorized numpy, with no per-bar
Python.

### 3.3 The exit walk — `_walk_exit_for_4h` (`engine.py:228`)
```python
sub_bars = df_1min.iloc[lo:hi]                  # slices a DataFrame per open-trade window
for sub in sub_bars.itertuples(index=False):   # itertuples is OK-ish, but the slice + attr access add up
    m_high = float(getattr(sub, 'High')); ...
```
Secondary cost (depends on how many windows hold an open trade). Targeted in sub-step **B3**, not B1.

---

## 4. Scope analysis — what this work does and does NOT touch

### 4.1 Who uses the slow engine
`grep` across the project (evidence captured 2026-06-12):

| Caller | Engine used | Implication |
|--------|-------------|-------------|
| `strategy.build_payload` (dashboard, standalone backtester, `perf/bench.py`) | **`engine.SimpleStrategy`** (slow) | **the optimization target** |
| `optimize/optimizer.py`, `optimize/core.py` (the NSGA-III sweeps) | **`optimize/fast_engine.py`** (vectorized) | already fast — **not affected** |
| `optimize/cooldown.py` (one-time bound derivation) | `engine.SimpleStrategy` | runs rarely; benefits for free |
| `optimize/test_*_parity.py` | both (as the parity reference) | **the safety net** (see §6) |

> **Honest ROI scope:** Axis-B work speeds up **interactive single backtests** (dashboard + the shareable
> standalone backtester + `bench.py`), **biggest on fine timeframes**. It does **not** speed up the optimizer
> sweeps — those already run on the vectorized `fast_engine`. This is the correct, non-inflated framing.

### 4.2 Why we cannot "just reuse fast_engine"
`optimize/fast_engine.fast_backtest` (read in full) is a **subset** of `engine.SimpleStrategy`. It supports
the plain box + volatility-gate path, but it does **NOT** implement:

- `entry_resolver` — the retrace / carry-mode fill (`indicators/timing.py`); used whenever
  `retrace_amount > 0` or `wait_bars > 0`;
- `veto_mask` / `veto_as_flip` — the indicator veto and veto→flip reversal;
- `blocked_log` — the NOENTRY diagnostics the dashboard shows;
- per-trade line fields (`sl_soft_line`, `sl_hard_line`, `tp_soft_line`, `tp_hard_line`), `signal_idx`,
  `veto_flip` — which `build_payload`'s event/attribution loop (`strategy.py:302–338`) consumes.

**Every WS-I champion uses the indicator/retrace/veto layer**, so `fast_engine` cannot reproduce their
trades. Therefore the fix must be made **inside `engine.py`**, preserving 100 % of its features. (It also
means `build_payload` can't be re-pointed at `fast_engine` wholesale.)

### 4.3 The `decision_signals` finding (the lever)
`optimize/signals.decision_signals(df_dec, box)` (`optimize/signals.py:27`) already exists and is described
as "param-independent … mirrors `engine._stage1_candle_signal` + the box-date mapping exactly." **But on
reading it, it is still a per-bar pandas loop** — it calls `_stage1_candle_signal(df_dec.iloc[i], …)` for
every bar. Its only speedups are (a) it caches box rows by box-date, and (b) the optimizer computes it
**once** and reuses it across thousands of trials.

Consequences:
- For the **optimizer**, `decision_signals` is already "fast enough" (amortized over a sweep).
- For a **single `build_payload`**, computing the signal once via `decision_signals` is the **same** count
  of slow `_stage1_candle_signal` calls as the engine does inline — so simply calling it buys little.
- **The genuine win requires writing a *truly vectorized* (numpy) signal** — no per-bar pandas — and proving
  it identical to `_stage1_candle_signal`. That vectorized function then benefits **both** `build_payload`
  (single backtest) **and** the optimizer's precompute.

This is the foundation step **B1**.

---

## 5. The proposed transformation (design, not yet built)

### 5.1 Vectorized Stage-1 signal — the math
Inputs as numpy arrays aligned to the N decision bars: `O,H,L,C` (float64), and, for each of the
`_LEVEL_PAIRS` (weekly+monthly), per-bar `upper_p[i]`, `lower_p[i]` gathered from each bar's box row
(NaN where the column is absent/NaN). Then:
```
green = C > O ;  red = C < O                       # doji (C==O) ⇒ neither ⇒ hold
for each pair p:
    valid_p   = ~isnan(upper_p) & ~isnan(lower_p)
    touched_p = (L <= upper_p) & (H >= lower_p) & valid_p
    long_p    = green & touched_p & (C >  upper_p)
    short_p   = red   & touched_p & (C <  lower_p)
has_long  = OR_p long_p ;  has_short = OR_p short_p
signal = where(has_long, 'long', where(has_short, 'short', 'hold'))   # long wins ties (matches scalar)
```
Every operator (`<=`, `>=`, `>`, `<`) is an **exact float64 comparison** on the **same values** the scalar
path reads (`.to_numpy()` yields identical float64), so the result is **bit-identical**, not merely close.
The only non-trivial part is the **gather**: mapping each decision bar → its box row → the level-pair
columns. That reuses `BoxLookup._candle_to_box_date` + a cached `box.loc` (once per unique date), then
stacks the columns into per-pair arrays.

### 5.2 Tie-break & edge fidelity (must match `_stage1_candle_signal` exactly)
- **long beats short** when both fire (scalar returns `'long'` first) → encode via `where(has_long, …)` first.
- **doji** (`close == open`, scalar `color=='none'`) → `green=red=False` → `hold`. ✔
- **missing box row** (`box.loc` KeyError → `None`) → all pairs invalid → `hold`. ✔
- **NaN level** → that pair invalid (matches `pd.isna(u) or pd.isna(l): continue`). ✔
- **column absent for a pair** → treat as NaN/invalid (matches `upper_col not in box_row.index`). ✔

### 5.3 Sub-step decomposition (each independently approval-gated)

| Step | Change | Files | Risk | Win |
|------|--------|-------|------|-----|
| **B1** | Write vectorized numpy `decision_signals` (new fn or replacement) + **equivalence test** vs `_stage1_candle_signal` on real + adversarial frames, bit-identical. **Engine unchanged.** | `optimize/signals.py`, `tests/` | **LOW** | foundation; also speeds optimizer precompute |
| **B2** | Add optional `sig_int` arg to `engine.SimpleStrategy.backtest`; when present, read `sig_int[idx-1]` instead of per-bar `_stage1_candle_signal` + box `.loc`. `build_payload` precomputes once and passes it. | `engine.py`, `strategy.py` | **MED** | removes the ~27 s `_stage1_candle_signal` cost |
| **B3** | numpy-fy the remaining row access: pre-extract `df_4h` `Date/O/H/L/C` arrays (kill `fast_xs`); pre-extract 1-min arrays for `_walk_exit_for_4h` (kill the `iloc[lo:hi]`+`itertuples`). | `engine.py` | **MED-HIGH** | removes the ~26 s `fast_xs` + exit-walk overhead |

> B1 is deliberately **zero-risk to existing results** (it adds a function + a test; it does not change any
> code path the backtester runs until B2 wires it in). That is why it is first.

---

## 6. Safety net (already in place — this is why Axis B is approachable)

`engine.SimpleStrategy` is the **most safety-critical code in the repo**, but it is wrapped in a four-layer
parity net that makes a byte-identical refactor verifiable:

1. **`optimize/test_fast_parity.py`** — `fast_engine` must match `SimpleStrategy` trade-for-trade across
   normal/flip/gate-on/gate-off/wide/tight. (Indirectly pins `decision_signals` ≡ `_stage1_candle_signal`.)
2. **`optimize/test_indicator_parity.py`** — the indicator/confirm path matches the engine trade-for-trade.
3. **`perf/golden/<tf>.json` + `_trades.csv` + `_votes.npz`** — frozen 6-TF baselines: summary bytes,
   trades-SHA, and per-indicator vote-SHA. `perf/check_golden.py` byte-compares.
4. **`optimize/test_parity.py`** — `build_payload` reproduces the locked `$7,735 / $3,670 / n=66` reference.

Plus the new **equivalence test (B1)**: vectorized signal == scalar signal, NaN-for-NaN, on random +
adversarial inputs (constant / monotonic / leading-NaN / mid-NaN / doji-heavy / level-touch boundary).

**Acceptance for every B sub-step:** all four layers + the equivalence test stay green, and the golden
byte-match is unchanged on **all 6 TFs** (coarse per-step, full 6-TF at the phase boundary). Any drift =
revert.

---

## 7. Risks, unknowns, and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Vectorized signal disagrees with scalar on a corner (doji, NaN, tie, boundary `<=` vs `<`) | medium | bit-identical equivalence test with adversarial cases **before** wiring in; B1 changes no live path |
| The box-row **gather** mis-maps a bar→date (esp. the `_candle_to_box_date` 18:00 roll rule) | medium | reuse the *exact* existing `_candle_to_box_date`; assert the gathered matrix reproduces `box.loc` per unique date |
| Float drift from `.to_numpy()` dtype coercion | low | assert dtype float64; compare with `==` (not `isclose`) in the test |
| Engine refactor (B2/B3) breaks an edge: re-entry gate, soft-consec counter, carry-mode, veto→flip | medium | keep `_stage1_candle_signal` as the frozen reference; change only the *source* of the signal, not the decision logic; golden+parity gate each sub-step |
| Python-3.14 typing overhead (rows 6/10) persists | low | it is *dragged in* by pandas per-cell access; removing the access removes most of it. Residual is acceptable |
| Measuring under CPU contention misleads | resolved | clean before/after wall times taken on an idle box at implementation; call-count evidence is load-invariant |

**Explicitly out of scope (this investigation):** PostgreSQL, the server push, Numba (blocked: Py 3.14 +
PEP 668), and any change to `fast_engine` or the optimizer. Axis B is `engine.py` + its signal source only.

---

## 8. Recommendation & decision log

- **Recommended:** proceed **B1 first** (vectorized signal + equivalence test, no engine change), report,
  then seek approval for B2, then B3. Smallest blast radius, maximal redundancy — matches the standing
  mandate ("very strong stress testing, very careful, high precision, high redundancy, per-step approvals").
- **Expected end state:** fine-TF single backtests **−50 % to −70 %** (e.g. 15m ~44 s → ~15–20 s; 2m the
  largest absolute drop), **every step proven trade-for-trade byte-identical**, each with its own verbose
  `perf/UPDATE_step_B*.md` (before/after + revert) and one commit.
- **Decision recorded 2026-06-12:** user approved **B1 only**, then asked for this investigation document to
  be written **before** implementation. → This file is that document; implementation of B1 has **not**
  started and awaits the go-ahead to begin coding.

---

## 9. Reproduce / evidence pointers
- Profile tool: `/tmp/profile_axisB.py` (`python3 /tmp/profile_axisB.py 15m`).
- Clean per-TF baseline: `perf/bench_history.json` label `manual_bg` (+ `perf/logs/backtest_latest.log`).
- Engine: `engine.py:97` (`_stage1_candle_signal`), `engine.py:228` (`_walk_exit_for_4h`), `engine.py:320`
  (main loop). Signal: `optimize/signals.py:27`. Subset engine: `optimize/fast_engine.py:50`.
- Safety net: `optimize/test_parity.py`, `optimize/test_fast_parity.py`,
  `optimize/test_indicator_parity.py`, `perf/check_golden.py`, `perf/golden/`.
- Prior context: `perf/STATUS_optimization.md`, `perf/REPORT_optimization_roi_and_decision.md`,
  `optimize/REPORT_backtester_speed_optimization.md`.
