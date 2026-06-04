---
name: ws-i-indicator-decisions
description: WS-I Phase I.1 FROZEN spec — all indicator/confirmation/timing/SMC/optimizer decisions, approved by the team leader on 2026-06-04. This is the single source of truth that docs/INDICATORS.md (I.2) and the engine (I.3) are built from. Supersedes the awaiting-approval draft; the plain-language mirror lives in INDICATOR_DECISIONS_SIMPLE.md.
type: decision
status: FROZEN (approved 2026-06-04)
created: 2026-06-04
workstream: WS-I
---

# WS-I.1 — Frozen Decisions (approved 2026-06-04)

> **Invariant:** every indicator defaults **disabled** and neutral ⇒ the system reproduces today's
> box+vol-gate path exactly (`test_parity.py` / `test_fast_parity.py` keep passing). The box is
> always the primary trigger and direction; indicators only **confirm** or **veto**.

> **Architecture directive (applies everywhere).** Build each variant as **its own engine/entity**
> and select it by an explicit user/optimizer switch — do **not** stack hundreds of nested
> conditions. **OOP-first**, drop to functional where it's cleaner. (Drives the trend sub-engines,
> the two-phase run, and the indicator layer generally.)

---

## A. Confirmation / veto policy

**1. Per-indicator surface + voting** ✅
- Every indicator exposes **two controls**: `value` (its setting/threshold) and `enabled`
  (default **disabled**).
- **Every indicator always computes and logs its opinion**, tagged with `active` ∈ {0,1}. Disabled
  indicators (active=0) still show their vote in the logs but **do not** affect the decision.
- Decision rule: a trade is allowed **iff** `(no active indicator vetoes)` **AND**
  `(# active indicators that say "confirm" ≥ K)`.
- **K** is exposed on the dashboard, **default K = 1**, and is a search param ∈ [1, N_active].

**2. Confirm / veto class per indicator** ✅
Per-indicator `mode` ∈ {confirm, veto, both}, searchable. Starting defaults:
Trend MAs (EMA/SMA/MACD) → confirm · ADX/DMI → veto · Momentum (RSI/Stoch/CCI) → both ·
Volatility (ATR/BB/Keltner) → veto · Volume (OBV/VWAP/MFI) → confirm · SMC (all) → both.

---

## B. Entry timing (retrace / wait) — **per-indicator**

**3. Retrace** ✅ — **each indicator has its own** retrace picker. `retrace_unit` ∈ {points, atr_mult}
(default `atr_mult`), `retrace_amount` default **0 = immediate**. Measured from the signal candle's
close (mirror for short). FVG's retrace is intrinsic (price must pull back into the gap zone).

> **Retrace changes the ENTRY PRICE (decided 2026-06-04).** A retrace is a limit-style pullback: the
> trade fills at the pulled-back level, not the signal close. An indicator's confirm goes live once
> price reaches its own retrace level (favorable direction) — so as price pulls back, confirms
> activate one-by-one. **Fill rule = the K-th confirm's level:** the trade fills at the retrace level
> of the indicator whose pullback completes the K-rule (the one that opens the gate). Long fills at
> `signal_close − r`, short at `signal_close + r`, where `r` is that K-th indicator's retrace amount.
> retrace_amount = 0 ⇒ fills immediately at the signal close (parity). Level touches resolve on the
> 1-minute series (same precision as exits); within the armed window only (until superseded).
> Engine-level change (parity-locked); the all-off path is unaffected.

**4. Wait** ✅ — **each indicator has its own** wait picker. `wait_bars` in **decision bars**,
default **0**. **No expiry / no auto-drop** (the 3-bar cutoff was removed as a silent fallback).

**Armed-entry lifetime** ✅ — an armed (waiting) entry stays valid until its conditions fire
(→ enter, logged) **or the next box decision bar emits a new signal that supersedes it**
(→ logged `superseded, unfilled`). Never silently dropped.

**5. Combining timing across indicators** ✅ — there is no separate "wait for both" knob; timing
folds into the **K rule**: an indicator counts as a **confirm** only once **its own** retrace **and**
wait are satisfied. The entry fires at the first decision bar where `(no active veto)` AND
`(# fully-satisfied active confirms ≥ K)`.
- **Logging (mandatory, verbose):** when an entry is taken, log **how many indicators fired, and for
  each one**: its cause, its settings, its current values, met/not-met, retrace+wait status — i.e.
  full attribution of which indicators caused the decision.

---

## C. ICT / SMC structures  (all detectors **causal**)

**6. FVG (Fair Value Gap)** ✅ — 3-candle imbalance, **wick-based geometry**. Bullish: `low[t] >
high[t-2]` (zone `[high[t-2], low[t]]`); bearish: `high[t] < low[t-2]`. Trigger = price **retraces
into the zone** in the trade direction (per the standard fill strategy). "Filled/mitigated" once a
later candle trades back through it.

**7. "Burned into" (IFVG / breaker invalidation)** ✅ — counts only on a **close** beyond the zone
(not a wick) — "all closes, not highs/lows." A closed-through FVG flips to an IFVG (continuation in
the new direction).

**8. Order block → breaker** ✅ — bottom (bullish) OB = last down-close candle before an up-move that
**closes** above a prior swing high; top (bearish) OB = last up-close candle before a down-move that
**closes** below a prior swing low. Zone = candle body (default; `ob_zone` ∈ {body, wick}). Once
price **closes beyond** an OB it converts to a **breaker** and is usable only as a breaker thereafter
(state tracked causally).

**9. CISD / golf candle** ✅ — golf candle = body `|close−open|` greater than the max body of the
prior **`golf_n`** candles; **`golf_n` is user/dashboard-exposed and tunable** (default 3, not fixed).
Breaker confirmation stack `breaker_confirm` ∈ {golf_only, golf+fvg, all_three}, default `all_three`.

**10. Market structure (LL/HL/HH/LH)** ✅ — close-based swings, fractal lookback `swing_L`
(default 2, tunable), confirmed L bars after forming (no look-ahead).

**11. Boxes / key levels — TWO classes, generated NOT inferred on a hidden path** ✅
- **External key-level boxes (weekly + monthly):** come from the existing offline pipeline
  (`NQ_full_data.csv`; `box_lookup.py` already uses weekly+monthly and **ignores daily**). Not
  derivable from OHLC → stay precomputed/imported. **Daily boxes remain ignored.**
- **OHLC-derived SMC structures (FVG, OB, breaker, structure, golf/CISD):** produced by an explicit
  **generation stage**, never silently inline:
  - **Manual mode (dashboard):** the user sets the generation params; pressing **Backtest** runs a
    **two-phase** flow in the same dashboard — **(1) generate structures → (2) run backtest** — each
    phase with **its own report + logs** (a generation report and a backtest report).
  - **Optimizer mode:** the generation params (`golf_n`, `swing_L`, FVG lookback, …) are **part of
    the tunable search space** — each trial generates structures for its param set, then backtests.
  - *Engineering note (for I.7):* generation must be vectorized and **memoized by gen-param
    signature** so the optimizer doesn't regenerate identical structures across trials.

**12. Trend — two independent sub-engines** ✅ — implement **MA-trend** and **structure-trend** as
**separate engine entities**, chosen by a dashboard switch via a simple if (per the OOP directive),
not nested branches. **Default = moving-average**, switchable to structure.

---

## D. Optimizer

**13. Win-rate objective (guarded)** ✅ — 3rd objective credited only when a fold has ≥
`min_trades_fold` = 10 trades; thin folds score 0 and flag low-support. (Kills the win-rate
cherry-pick mirage.)

**14. NSGA-III budget** ✅ — population 100, ~1500 trials/TF, 5-fold walk-forward, overfit auto-flags
kept. Big all-TF run still gated on explicit go (I.10).

---

## E. Parameters & dashboard
- **Every indicator parameter** (periods, thresholds, `golf_n`, `swing_L`, retrace/wait, mode, K,
  generation params) is **tunable by the optimizer AND exposed in the dashboard** for manual tuning
  in the manual-backtest stage (before the optimizer).
- Period defaults (search centers): RSI 14 · MACD 12/26/9 · ATR 14 · ADX 14 (thr 20–25) ·
  EMA 20/50 · SMA 50/200 · Bollinger 20/2.0σ · Keltner 20 EMA/2.0×ATR · Stochastic 14/3/3 ·
  CCI 20 · MFI 14 · VWAP daily-anchored · OBV cumulative · RMA Wilder.
- **No silent fallbacks anywhere** — bad/missing params raise `ParamError` to the UI.

## F. Structural confirmations
- Indicators compute on the **decision/entry timeframe**; **exits stay 1-minute** (WS-H rule).
- All-off ⇒ box parity (the invariant at the top).

---

**Status: FROZEN.** Next: I.2 — write `docs/INDICATORS.md` (verbose per-indicator spec) from this,
then I.3 engine. No engine code until I.2 is reviewed.
