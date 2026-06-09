---
name: server-run-readiness
description: Detailed explanation of WHY the 1-minute-indicator optimisation is not yet ready to run
  on the server — the two wiring gaps, the measured per-trial cost problem, what would happen if you
  launched as-is, and the exact changes + options to make it ready. Numbers are measured, not estimated.
type: reference
status: blocker-analysis
workstream: WS-I
---

# Is the 1-minute-indicator optimisation ready to run on the server? — detailed analysis

**Verdict: not yet.** A *decision-timeframe* sweep is ready (that's the proven WS-I.10 path), but a
**1-minute-indicator** sweep needs three things fixed first. Two are one-line/one-command wiring; the
third is a real performance problem with measured numbers. This document explains each in depth.

---

## 0. Quick summary

| # | Issue | Type | Effect if ignored |
|---|---|---|---|
| 1 | The optimiser never sets `ind_1min` in its trial params | wiring (1 line) | The server would silently optimise **decision-TF** indicators — i.e. redo WS-I.10, **not** a 1-minute search |
| 2 | The server scratch holds the **pre-change** code | sync (1 command) | The new 1-minute / vectorisation code wouldn't even be present |
| 3 | **30.4 s per trial** with 1-minute indicators (measured) | performance | A full 21,000-trial sweep ≈ **~6 hours**; `order_block` alone is ~2/3 of that |

---

## 1. Issue 1 — the optimiser does not turn 1-minute indicators on

### What the code does today
The backtest core was wired to *support* 1-minute indicators:
```python
# optimize/core.py — backtest_metrics(...)
src = runner.indicator_source_1min(d, d1, bar_duration) if params.get("ind_1min") else None
```
It reads the flag from the per-trial `params` dict. **But the optimiser never puts that flag there.**
The per-trial params are assembled in `optimize/optimizer.py`:
```python
params = dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
              dd_limit=dd_limit, cooldown=cooldown, flip=flip, window="full",
              indicators=specs, k=k_rule)            # ← no ind_1min key
```
`grep ind_1min optimize/optimizer.py optimize/folds.py` → **no matches.**

### Consequence
`params.get("ind_1min")` is `None` → `src=None` → every trial computes indicators on the
**decision-timeframe** candles, exactly like the original WS-I.10 sweep. So if you launched the
server run right now, it would burn hours re-deriving the **4-hour-indicator** champions you already
have — **not** the 1-minute search you intend.

### Fix
Add `ind_1min=True` to that `params` dict (one line). That single key flips the whole search to
1-minute indicators (the core, folds and full-period feasibility check all read it).

---

## 2. Issue 2 — the server is running stale code

`optimize/server/remote_wsi.sh` rsyncs the local `Parametric-Indicators/` tree to the server scratch
(`/home/dev/Mulham/wsg-i`). That scratch was last synced **before** any of this work:
the 1-minute source (`indicator_source_1min`, `_vote_from_1min`), the vectorised
stochastic/MFI, the memoised votes, and the `ind_1min` hook in `core.py` are **not on the server.**

### Fix
`bash optimize/server/remote_wsi.sh push` (then `parity` to sanity-check env/data). One command —
but it must happen *after* Issue 1 is fixed, or you'd push code that still can't run 1-minute.

---

## 3. Issue 3 — the real problem: per-trial cost

This is the substantive blocker, and it is **measured**, not guessed.

### 3.1 How one trial is scored
For each trial the optimiser runs the strategy **multiple times** (walk-forward + a feasibility
check), via `score_walkforward` + one full-period `backtest_metrics`:
- the history is split into **5 equal-time folds**; folds 1–4 are scored (fold 0 is the causal
  gate warm-up) → **4 backtests**;
- plus **1 full-period backtest** for the "max-drawdown ≤ 25 % of P/L" feasibility gate.
- = **5 backtests per trial**, and with 1-minute indicators **each backtest recomputes the indicator
  series over its slice of the ~487 k-bar 1-minute history.**

### 3.2 Measured cost (4h champion, full 2025–26 data, this machine)
| | walk-forward (4 folds) | full-period | **per trial** |
|---|--:|--:|--:|
| decision-TF indicators (today's proven path) | 0.6 s | 0.8 s | **1.4 s** |
| **1-minute indicators** | 10.7 s | 19.7 s | **30.4 s** |

That is a **~22× slowdown per trial.** The cost is the indicator compute over the 1-minute frame,
**not** the trade simulation — and within it, the stateful Smart-Money-Concept `order_block`
(~15 s/pass) is the single biggest piece (≈ 2/3 of the time).

### 3.3 What that means for a full sweep
A WS-I.10-style sweep = **3,000 trials × 7 timeframes = 21,000 trials**, on the 30-worker AMD server:

| configuration | per trial | 21,000 trials ÷ 30 workers |
|---|--:|--:|
| decision-TF (proven) | ~1.4 s | **~15 min** |
| 1-minute, WITH SMC (`order_block`/structure/fvg) | ~30 s | **~5.9 hours** |
| 1-minute, WITHOUT the stateful SMC indicators | ~10 s | **~2 hours** |

(The per-trial cost is roughly TF-independent: the 1-minute indicator series spans the whole 1-minute
history regardless of the decision timeframe, so finer TFs don't make it dramatically worse.)

### 3.4 Why `order_block` (and structure/fvg) are slow
They are **stateful per-bar state machines** (track live order-block zones, convert them to breakers,
walk swing pivots). Unlike the moving-average / oscillator indicators, they can't be expressed as a
vectorised window op without re-deriving their exact zone-lifecycle semantics — so they still run a
Python loop over all ~487 k 1-minute bars. The cheap indicators (EMA, MACD, Keltner, RSI) and the two
that were vectorised this round (Stochastic %D, MFI) are already fast.

---

## 4. What "ready" requires (the exact changes)

1. **Turn on 1-minute in the search** — add `ind_1min=True` to the params dict in
   `optimize/optimizer.py:objective`. (1 line.)
2. **Decide the indicator search space** (this is the lever on the 6 h vs 2 h cost):
   - *Fast first pass (recommended):* drop `order_block`, `structure_trend`, `fvg` from
     `_suggest_indicators` so the search only tunes the 12 vectorised/cheap indicators (trend,
     momentum, mean-reversion, volume). ~2 h.
   - *Full search:* keep all 15 and accept ~6 h (or vectorise the SMC machines first — a dedicated
     follow-up task).
3. **Push + launch** — `remote_wsi.sh push → parity → run 3000 → status/counts → pull`.

Nothing about the math, parity or correctness blocks this — it is purely the two wiring steps plus
the cost trade-off decision. Everything is verified:
- no-indicator parity unchanged (**$7,735 / $3,670 / 66**);
- decision-TF indicator + fast-engine parity locks **pass**;
- the 1-minute path is **identical** between the dashboard and the optimiser ($18,091 / $21,671 / 59);
- Stochastic %D and MFI vectorisations are **bitwise-equal** to the old loops;
- **88 tests pass.**

---

## 5. Recommendation
Run the **fast first pass** (1-minute indicators, SMC excluded, ~2 h): it covers 12 of the 15
indicators, finishes in one short session, and tells you whether 1-minute indicators help at all
before committing to the ~6 h full search or a SMC-vectorisation project. Say the word and I'll make
the two edits, push, and launch it.
