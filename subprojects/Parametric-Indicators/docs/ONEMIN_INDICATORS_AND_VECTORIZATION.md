---
name: onemin-indicators-and-vectorization
description: WS-I — moving the indicator layer to the 1-minute frame + vectorising the indicator
  compute to prepare for an on-server, parallel optimisation run. Full design, the exact code paths,
  the parity guarantees, the profiling/speedups, the remaining bottleneck, and the server-run plan.
type: reference
status: current
workstream: WS-I
---

# 1-minute indicators + vectorisation (preparing the parallel server optimisation)

This document records, verbosely, two linked changes and the state they leave the system in:

1. **Indicators now read the 1-minute frame** (dashboard backtester + optimiser, opt-in), instead of
   the decision-timeframe candles.
2. **The indicator compute was vectorised / memoised** so the system is fast enough to drive an
   on-server, parallel optimisation run with 1-minute indicators.

Everything below is parity-locked: with **no indicators enabled** the engine still reproduces the
verified box+volatility winner **byte-for-byte** ($7,735 / $3,670 / 66), and the decision-timeframe
indicator path (the optimiser's existing fast path + parity tests) is **unchanged**.

---

## 1. The full backtest pipeline (where indicators sit)

```
 raw OHLCV: decision-TF candles + 1-minute candles + weekly/monthly box levels
        │
        ▼
 HAR-RV volatility forecast per decision bar (from 1-minute squared returns)
        │
        ▼
 BOX Stage-1 signal per decision bar  → proposed direction (long / short / hold)   [decision TF]
        │
        ▼
 INDICATOR LAYER (optional, ≤15 indicators):  confirm / veto / neutral vote vs the box direction
        │      entry allowed ⇔ (no active veto) AND (#confirms ≥ K)
        │      ← THIS is what moved to the 1-minute frame (§2). Box trigger/cadence unchanged.
        ▼
 VOLATILITY GATE: skip bars whose HAR-RV forecast exceeds the gate percentile   [decision TF]
        │
        ▼
 ENGINE: open the trade; resolve soft/hard stop + take-profit on the 1-MINUTE frame (sub-bar fills)
        │
        ▼
 DRAWDOWN BREAKER: halt for `cooldown` trades after running drawdown ≥ dd_limit (global high-water mark)
        │
        ▼
 payload: summary + trades + equity + drawdown + per-event log
```

The decision timeframe is selectable (1m/2m/5m/15m/1h/2h/4h); exits always resolve on 1-minute.

---

## 2. Indicators on the 1-minute frame

### 2.1 What changed
Previously every indicator computed its reading on the **decision-timeframe** candles (e.g. 4-hour).
Now the indicator's direction is computed on the **1-minute** candles, and each decision bar reads
the value of its **last-closed 1-minute candle** (causal — no look-ahead). The box trigger, the
entry cadence (still one decision per decision bar) and the exits are **unchanged**; only the
indicators' *data source* moved.

### 2.2 Why it matters
- An indicator's look-back/warm-up now counts **1-minute candles**. A parameter like
  `ema_trend slow=373` means **373 minutes (~6 h)**, not 373×4h. So any parameter set tuned as a
  decision-TF look-back means something very different here — e.g. the 4h "champion" goes from
  ~$58k/$10.6k DD (decision-TF indicators) to **$18,091 / $21,671 DD / 59 trades** (1-minute
  indicators). That is expected, not a bug.

### 2.3 How it's implemented (exact code path)
In `indicators/runner.py`:
- `indicator_source_1min(df_dec, df1, bar_td) → (ctx_1min, j_idx)` builds a 1-minute `MarketContext`
  and `j_idx[i]` = the index of the **last 1-minute candle inside decision bar i's window**
  `[start_i, start_i + bar_td)` (the minute that "closes" that decision bar; `-1` if none).
- `_vote_from_1min(ind, ctx_1min, j_idx, box_dir)` computes the indicator's direction on the 1-minute
  context, applies its warm-up (now in 1-minute candles), **samples** the direction at `j_idx` for
  each decision bar, and compares to the decision-bar box direction — mirroring `base.Indicator.vote`
  exactly.
- `_ind_vote(ind, ctx, bdir, src)` routes to `ind.vote` (decision-TF) when `src is None`, else to
  `_vote_from_1min`. This single helper is used by `veto_mask`, `confirm_mask`, the entry resolver
  and the attribution, so all paths are consistent.

The dashboard (`strategy.build_payload`) always builds `src = runner.indicator_source_1min(...)` and
passes it through `build_layer`. The optimiser (`optimize/core.backtest_metrics`) builds the same
`src` **only when `params["ind_1min"]` is set** — default off ⇒ the optimiser's existing
decision-TF fast path and its parity locks are untouched.

### 2.4 Causality / no look-ahead (unchanged guarantee)
The engine enters at decision bar `idx` using the signal of the just-closed bar `idx-1`; the
indicator vote it reads is sampled at the **close of bar `idx-1`** (the last 1-minute candle of that
bar). The moving average at any 1-minute bar includes that closed minute but never the forming
decision bar's later minutes.

---

## 3. Vectorisation & memoisation (the speed work)

### 3.1 Why it was slow
Indicators recompute on the **full 1-minute history** (~487k bars for the full window). Profiling one
pass of the 4h-champion's 8 enabled indicators on 487k 1-minute bars:

| indicator | before | after | how |
|---|--:|--:|---|
| order_block | 13.3 s | 14.7 s | (unchanged — stateful SMC loop; the remaining bottleneck) |
| stochastic | 5.15 s | **2.98 s** | %D rolling mean via `sliding_window_view` (bitwise-exact) |
| adx | 2.67 s | 3.0 s | (unchanged — Wilder smoothing loop) |
| mfi | 1.83 s | **0.29 s** | rolling sums via `sliding_window_view` (bitwise-exact) |
| keltner / macd / rsi / ema_trend | <1 s each | <1 s | (EMA loop is already cheap) |

Worse, the dashboard backtest computed every indicator's vote **three times** (veto gate + confirm
resolver + attribution log) and even computed **disabled** indicators (for the greyed chips).

### 3.2 What was done (all parity-preserving)
1. **Compute each ENABLED indicator's vote once** (`runner.compute_votes`) and share it across the
   veto gate, the confirm resolver and the attribution. **Disabled indicators are skipped entirely**
   (they don't trade; computing a disabled `order_block` on 1-minute was pure waste). This alone took
   the full-history 4h-champion dashboard backtest **72.8 s → 28.2 s** with an **identical** result.
2. **Vectorised the two cheap hot loops** — Stochastic `%D` and Money-Flow-Index rolling sums — with
   `numpy.lib.stride_tricks.sliding_window_view`, which sums each window with the **same float ops**
   as the old per-bar loop ⇒ **bitwise-identical** output (verified element-by-element on the real
   1-minute data). Net dashboard backtest ≈ **25 s**.
3. **Memoised the optimiser path** too: `core.backtest_metrics` now computes the vote dict once and
   feeds both `veto_mask` and `confirm_mask` (previously 2× recompute).

### 3.3 Parity evidence
- `optimize/test_parity.py` (no indicators): **+$7,735 / $3,670 / 66** — unchanged.
- `optimize/test_indicator_parity.py` + `optimize/test_fast_parity.py`: **pass** (decision-TF, no
  `src` ⇒ untouched).
- Stochastic `%D` and Money-Flow-Index: **bitwise-equal** to the pre-vectorisation loops on the full
  1-minute frame.
- Full suite: **88 passed**.
- The 1-minute champion result is **identical** across the dashboard and the optimiser
  (`ind_1min=True`): $18,091 / $21,671 DD / 59 trades.

### 3.4 The remaining bottleneck
`order_block` (and the other stateful Smart-Money-Concept detectors `structure_trend`, `fvg`) run a
**per-bar Python state machine** that is hard to vectorise without risking the exact zone-lifecycle
semantics. On 487k 1-minute bars `order_block` alone is ~15 s, which dominates a 1-minute backtest
(~19 s/trial when it's enabled). The EMA/Wilder loops (ema, rma→adx) are individually cheap and were
left as-is.

---

## 4. Preparing the on-server parallel optimisation run

### 4.1 What is ready
- The optimiser (`optimize/optimizer.py` → `core.backtest_metrics`) accepts **`ind_1min`** in the
  trial params; set it to run the search with **1-minute indicators**. Default off keeps the proven
  decision-TF behaviour.
- Vote memoisation is in the optimiser path, so each trial computes each enabled indicator's
  1-minute series once.
- The existing server harness `optimize/server/remote_wsi.sh` (push / parity / run / status / counts
  / pull) and the per-TF study layout are unchanged and reusable.

### 4.2 Feasibility (the honest cost)
Per-trial cost with 1-minute indicators is dominated by the indicator compute over the full 1-minute
history, **not** the trade simulation:

| configuration | ≈ per trial | 21,000 trials (7 TF × 3,000) on 30 cores |
|---|--:|--:|
| with SMC indicators (incl. `order_block`) | ~15–19 s | **~3–3.5 hours** |
| WITHOUT the stateful SMC indicators | ~4–5 s | **~45–60 minutes** |
| decision-TF indicators (today's proven path) | <1 s | minutes |

So a 1-minute-indicator sweep is feasible on the AMD server overnight, but **`order_block` /
structure / fvg are the cost driver**. Two ways forward:
- **(recommended first pass)** run the 1-minute search with the **stateful SMC indicators excluded**
  from the search space (the other 12 indicators cover trend / momentum / mean-reversion / volume) —
  ~1 hour, then add SMC only if a candidate looks worth it; or
- vectorise the SMC state machines (a dedicated follow-up) before including them.

### 4.3 How to launch (when you choose to)
1. Decide whether `ind_1min` is wired into the per-trial params the optimiser emits (a one-line
   addition in `optimizer.py`'s param assembly) and whether to drop SMC keys from `_suggest_indicators`
   for the fast first pass.
2. `bash optimize/server/remote_wsi.sh push` → `parity` → `run 3000` (weighted workers across the 7
   timeframes) → `status`/`counts` → `pull`, exactly as the WS-I.10 sweep.

This document + the parity locks are the green light; the actual launch is a deliberate next step.

---

## 5. File-change summary
- `indicators/runner.py` — `indicator_source_1min`, `_decbar_1min_index`, `_vote_from_1min`,
  `_ind_vote`, `compute_votes`; optional `src=` and `votes=` on `veto_mask` / `confirm_mask` /
  `build_entry_resolver` / `build_layer`.
- `indicators/classic.py` — Stochastic `%D` and Money-Flow-Index vectorised (bitwise-exact).
- `strategy.py` — dashboard builds the 1-minute source, computes votes once, reuses for the gate +
  resolver + attribution; warm-up log counts 1-minute candles.
- `optimize/core.py` — optional `ind_1min` 1-minute source + memoised votes in `backtest_metrics`.
