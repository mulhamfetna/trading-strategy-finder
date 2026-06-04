# The Indicators — full explanation (self-contained)

This document explains **every indicator** added in WS-I, from scratch, for someone studying **only
this folder**. It is the verbose companion to the frozen decisions in `INDICATOR_DECISIONS.md`
(approved 2026-06-04). For each indicator: **what it is · how it works · when & why you'd use it ·
the exact math · how it votes** in this system. No other part of the repo is required.

> **One-sentence mental model.** The **box** still decides *whether and which direction* to trade
> (see `STRATEGY.md`). Each indicator is a **judge** that, for that box signal, says **confirm**
> ("yes, take it"), **veto** ("no, skip it"), or **neutral** ("no opinion"). A trade happens only
> when **no active judge vetoes** and **at least K active judges confirm**. With every judge
> disabled the system is identical to today's box+vol-gate strategy.

---

## 0. How to read every "votes" rule
Each indicator below ends with a **Vote** block. The vote is always **relative to the box's
direction** for this signal (long or short):
- **confirm** = the indicator agrees the box direction is favourable *right now*.
- **veto** = the indicator says conditions are hostile to the box direction.
- **neutral** = no clear reading; the indicator abstains (counts as neither).

Whether an indicator is *allowed* to confirm, veto, or both is set by its **`mode`** parameter
(default per the table in §13). A `confirm`-mode indicator that would otherwise veto simply goes
neutral, and vice-versa.

---

## 1. The voting framework (shared by all indicators)
- **Two controls per indicator:** `value` (its setting/threshold) and `enabled` (default **OFF**).
- **Always computed, always logged.** Even a disabled indicator computes its opinion every bar and
  writes it to the log with an `active` flag (`0` disabled / `1` enabled). You can therefore *see*
  what an indicator *would* have said without it affecting the trade. Only **active** indicators
  (`active=1`) count toward the decision.
- **Decision rule (the "K rule"):** a box signal becomes a trade **iff**
  `(no active indicator vetoes)` **AND** `(# active indicators that confirm ≥ K)`.
- **K** is exposed on the dashboard, **default 1**, searchable in [1, N_active].
- **No silent fallback:** a missing/invalid indicator parameter raises `ParamError` to the UI.

## 2. Entry timing (per-indicator retrace + wait)
An indicator's confirm is not necessarily *immediate*. Each indicator carries **its own** two timing
controls (both default to "act now", which preserves parity):
- **`retrace`** — wait for price to pull back by `retrace_amount` (in `points` or `atr_mult`,
  default `atr_mult`, default amount **0**) from the signal candle's close before the confirm
  becomes live.
- **`wait_bars`** — wait this many decision bars after the signal (default **0**).

An indicator only counts as a **confirm** once **both** its own retrace and wait conditions are
satisfied. The entry fires on the first decision bar where the K rule is met. **There is no
expiry** — an armed (waiting) signal stays valid until it fills **or the next box signal supersedes
it** (logged `superseded, unfilled`). When an entry is taken the log records, **per indicator**: its
cause, settings, current values, met/not-met, and retrace+wait status — full attribution of what
caused the trade.

**`wait_bars`** is implemented as a confirm-debounce (`apply_wait`): a confirm only counts after it
has held `wait_bars`+1 consecutive bars; vetoes act immediately; `wait_bars=0` ⇒ parity.

**`retrace` changes the entry price (decided 2026-06-04).** It is a limit-style pullback, resolved on
the 1-minute series: as price pulls back from the signal close, each indicator's confirm goes live
when price reaches **its own** retrace level (long `signal_close − r`, short `+ r`). The trade fills
at the **K-th confirm's level** — the retrace amount of the indicator whose pullback completes the
K-rule. `retrace=0` ⇒ immediate fill at the signal close (parity). *Implemented as the `engine.py`
`entry_resolver` hook (default None ⇒ identity); verified-engine parity locks still pass. The
resolver algorithm is `indicators/timing.resolve_retrace_entry`.*

---

# GROUP A — Classic technical indicators

All Group A indicators are computed on the **decision/entry timeframe** (the same candle the box
signal is read on), from `open/high/low/close/volume`, using only **closed** bars (no look-ahead).
Periods below are defaults (search centers); all are tunable and dashboard-exposed.

## 3. SMA — Simple Moving Average
- **What:** the unweighted mean of the last *n* closes.
- **How / math:** `SMA_n[t] = (close[t] + … + close[t-n+1]) / n`. Default fast/slow = **50 / 200**.
- **When & why:** the most basic trend proxy — price above a rising SMA = uptrend bias. Slow to
  react (lags), but robust and noise-resistant. Used for regime/trend context.
- **Vote:** *confirm* a long when `close > SMA` (and SMA rising); *veto* a long when `close < SMA`
  (mirror for short). Neutral when price hugs the line (within a small band).

## 4. EMA — Exponential Moving Average
- **What:** a moving average that weights recent prices more (reacts faster than SMA).
- **How / math:** `EMA[t] = α·close[t] + (1-α)·EMA[t-1]`, `α = 2/(n+1)`. Default fast/slow = **20/50**.
- **When & why:** faster trend read than SMA; the standard building block for MACD and trend stacks.
  Use when you want responsiveness over smoothness.
- **Vote:** same logic as SMA but on the EMA; the **MA-trend sub-engine** (§19) uses an EMA stack
  (`fast > slow` ⇒ up).

## 5. RMA — Wilder's Moving Average (smoothing)
- **What:** Welles Wilder's smoothed average — an EMA with `α = 1/n`.
- **How / math:** `RMA[t] = (RMA[t-1]·(n-1) + x[t]) / n`. Default n = **14**.
- **When & why:** not usually a standalone signal — it's the **smoothing engine inside RSI, ATR and
  ADX**. Documented so those indicators are reproducible exactly.
- **Vote:** none standalone (support indicator).

## 6. MACD — Moving Average Convergence/Divergence
- **What:** momentum of the trend, built from two EMAs.
- **How / math:** `MACD = EMA_fast − EMA_slow` (default **12, 26**); `signal = EMA_9(MACD)`;
  `hist = MACD − signal`. 
- **When & why:** captures acceleration of trend and crossovers; classic momentum confirmation.
- **Vote:** *confirm* a long when `MACD > signal` (or `hist > 0`); *veto* when `MACD < signal`
  (mirror for short). Neutral near zero crossover.

## 7. RSI — Relative Strength Index
- **What:** a 0–100 oscillator measuring the ratio of recent gains to losses.
- **How / math:** `RS = RMA(gains)/RMA(losses)`, `RSI = 100 − 100/(1+RS)`. Default n = **14**;
  default bands 30/70.
- **When & why:** overbought/oversold and momentum. Above 50 = bullish momentum; extremes warn of
  exhaustion.
- **Vote (mode=both):** *confirm* a long when RSI > 50 (momentum aligned); *veto* a long when RSI is
  extreme-against (e.g. > 70, overbought into a long) — mirror for short. Bands are the `value`.

## 8. Stochastic Oscillator
- **What:** where the close sits within the recent high–low range (0–100), with a smoothed signal.
- **How / math:** `%K = 100·(close − lowest_low_n)/(highest_high_n − lowest_low_n)`, default n=**14**;
  `%D = SMA_3(%K)`, smooth 3.
- **When & why:** momentum/turning points in ranging markets; %K/%D crosses time entries.
- **Vote (both):** *confirm* a long when %K > %D and rising out of oversold; *veto* a long when in
  overbought against the trade (mirror short).

## 9. CCI — Commodity Channel Index
- **What:** how far price is from its average, in units of mean deviation (unbounded, ~±100 typical).
- **How / math:** `TP = (H+L+C)/3`; `CCI = (TP − SMA_n(TP)) / (0.015 · meanDev)`, default n = **20**.
- **When & why:** detects the start of new trends and overextension; ±100 are the classic triggers.
- **Vote (both):** *confirm* a long when CCI crosses above +100 (or > 0 for a looser setting);
  *veto* a long when CCI < −100 against the trade (mirror short).

## 10. ADX / DMI — Average Directional Index
- **What:** trend **strength** (0–100), direction-agnostic, with +DI/−DI for direction.
- **How / math:** from `+DM, −DM, TR` smoothed by RMA over n=**14**; `DX = 100·|+DI − −DI|/(+DI+−DI)`;
  `ADX = RMA_n(DX)`. Threshold default **20–25**.
- **When & why:** distinguishes trending from choppy markets. The single best "should I even be
  trading a directional signal now?" filter.
- **Vote (mode=veto by default):** *veto* the trade when `ADX < threshold` (no trend → box breakouts
  fail); optionally *confirm* when `ADX ≥ threshold` and `+DI > −DI` agrees with the box direction.

## 11. ATR — Average True Range
- **What:** average size of a bar's true range — a pure **volatility** measure (not direction).
- **How / math:** `TR = max(H−L, |H−prevC|, |L−prevC|)`; `ATR = RMA_n(TR)`, default n = **14**.
- **When & why:** sizing stops, normalising other readings, and the **unit for per-indicator retrace**
  (`atr_mult`). Also the width source for Keltner channels.
- **Vote (veto):** *veto* when ATR is outside an allowed band (too dead or too wild) — complements
  the existing HAR-RV gate. Otherwise neutral. (ATR mostly serves as a *unit*, not a voter.)

## 12. Bollinger Bands
- **What:** a moving average with volatility envelopes.
- **How / math:** `mid = SMA_n` (default **20**); `upper/lower = mid ± k·σ_n` (default k = **2.0**).
- **When & why:** mean-reversion vs breakout context; band touches/squeezes flag extremes and
  volatility regime changes.
- **Vote (veto default):** *veto* a long that fires while price is stretched at/above the upper band
  (poor entry, likely mean-revert) — mirror short; optionally *confirm* breakouts on a band expansion.

## 13. Keltner Channels
- **What:** like Bollinger, but the envelope width is **ATR-based** (smoother than σ).
- **How / math:** `mid = EMA_n` (default **20**); `upper/lower = mid ± m·ATR` (default m = **2.0**).
- **When & why:** trend-following channel; price riding the upper band = strong uptrend. Pairs well
  with Bollinger for "squeeze" detection.
- **Vote:** *confirm* a long when price breaks/holds above the mid/upper in-trend; *veto* counter-band
  entries.

## 14. OBV — On-Balance Volume
- **What:** a running sum of volume signed by the day's direction — a volume/flow proxy.
- **How / math:** `OBV[t] = OBV[t-1] + sign(close[t]−close[t-1])·volume[t]`.
- **When & why:** confirms moves with participation; OBV making new highs with price = healthy trend;
  divergence warns. (Volume is present in the NQ CSVs.)
- **Vote (confirm):** *confirm* a long when OBV trend (its own SMA slope) agrees with the box
  direction; neutral/divergent otherwise.

## 15. VWAP — Volume-Weighted Average Price
- **What:** the average price weighted by volume, **anchored to the session** (daily reset).
- **How / math:** `VWAP = Σ(typical·vol)/Σ(vol)` cumulated from the session open; `typical=(H+L+C)/3`.
- **When & why:** the institutional "fair value" of the session; above VWAP = buyers in control.
  Strong intraday confirmation/veto.
- **Vote (confirm):** *confirm* a long when `close > VWAP`; *veto* a long when `close < VWAP`
  (mirror short).

## 16. MFI — Money Flow Index
- **What:** a volume-weighted RSI (0–100) — "RSI that knows about volume".
- **How / math:** money flow `= typical·volume`, split into positive/negative by typical-price
  change; `MFI = 100 − 100/(1 + posFlow/negFlow)` over n = **14**.
- **When & why:** overbought/oversold *with* volume confirmation; stronger than RSI when volume is
  meaningful.
- **Vote (both):** same shape as RSI (>50 confirm long; extreme-against veto), volume-aware.

---

# GROUP B — Entry-timing (not voters; they shape *when* a confirm goes live)

These are **not** judges — they are the per-indicator `retrace` and `wait_bars` controls from §2.
They were promoted to first-class concepts because the user's notes ("how much price / how much time
to wait before entering") make timing a core lever. Each indicator owns its own retrace + wait; an
indicator's confirm is withheld until both are met; entries are never silently dropped (armed until
filled or superseded). See §2 for the full rule and logging.

---

# GROUP C — ICT / Smart-Money-Concepts (SMC) structures

These are **generated**, not silently inferred (decision #11). Two classes:
- **External key-level boxes** (weekly + monthly) come from the existing offline pipeline
  (`NQ_full_data.csv`; daily ignored) — they cannot be derived from OHLC.
- **OHLC-derived structures** (FVG, order blocks, breakers, market structure, golf/CISD) are produced
  by an explicit **generation stage**: in **manual mode** the dashboard generates them (user-set
  params) then backtests, each with its own report/log; in **optimizer mode** their generation
  params are tunable search parameters. All detectors are **causal** (only closed bars).

## 17. FVG — Fair Value Gap (a.k.a. imbalance)
- **What:** a 3-candle price gap left by an impulsive move — an "untraded" zone the market tends to
  revisit.
- **How / math (wick-based geometry):** over candles `(t-2, t-1, t)`:
  - **Bullish FVG:** `low[t] > high[t-2]` → zone `[high[t-2], low[t]]` (a buy-side imbalance).
  - **Bearish FVG:** `high[t] < low[t-2]` → zone `[high[t], low[t-2]]`.
- **When & why:** price acts like a magnet and **retraces to fill the gap** before continuing.
  Standard play: wait for the pull-back **into** the zone, then enter in the impulse direction.
  Considered most reliable on higher timeframes.
- **Lifecycle:** a gap is **mitigated/filled** once a later candle trades back through it; the
  "burned into" / inverse transition (§18) is judged on a **close** through the far side.
- **Vote (both):** *confirm* the box direction when an **unmitigated** FVG of the same direction sits
  within `fvg_lookback` bars **and price has retraced into the zone**; *veto* a trade firing straight
  into an opposing unmitigated FVG.

## 18. IFVG — Inverse Fair Value Gap
- **What:** an FVG that price **closed through** — it flips polarity and becomes a continuation
  signal in the new direction (same idea as a breaker, for gaps).
- **How:** a bullish FVG whose far side is broken by a **close below** becomes a bearish IFVG (and
  vice-versa). Wicks don't count — only closes (decision #7).
- **When & why:** a failed/filled gap that price rejects is strong evidence of the new direction.
- **Vote (both):** *confirm* the box direction when an IFVG points the same way; *veto* when opposed.

## 19. Order Block (OB)
- **What:** the last opposite-direction candle before an impulsive, structure-breaking move — a proxy
  for where institutions loaded a position.
- **How (close-based structure break):**
  - **Bottom (bullish) OB** = the last **down-close** candle before an up-move that **closes above** a
    prior swing high.
  - **Top (bearish) OB** = the last **up-close** candle before a down-move that **closes below** a
    prior swing low.
  - Zone = the OB candle's **body** by default (`ob_zone ∈ {body, wick}`).
- **When & why:** price often **returns to** an order block and reacts; a high-probability entry zone
  in the trend direction.
- **State machine:** an OB stays valid until price **closes beyond** it; then it **converts to a
  breaker** (§20) and can only be used as a breaker thereafter. Tracked causally per block.
- **Vote (both):** *confirm* the box direction when price is reacting from a same-direction OB; *veto*
  a trade firing into an opposing live OB.

## 20. Breaker Block
- **What:** an order block that has been **broken** (closed beyond) — now it acts as support/
  resistance from the **opposite** side (the burned-OB concept, same family as the IFVG).
- **How:** produced by the OB state machine (§19) once an OB is closed through. Confirmation to
  *trade* a breaker uses the stack below.
- **Breaker confirmation stack (`breaker_confirm`):**
  - `golf_only` — just a CISD/golf candle (§21),
  - `golf+fvg` — golf candle **and** a fresh FVG,
  - `all_three` (**default**) — golf candle **and** FVG **and** a market-structure break — per the
    user's "all three for confirmation to take the breaker box."
- **Vote (both):** *confirm* when a same-direction breaker is confirmed by the chosen stack; *veto*
  against an opposing confirmed breaker.

## 21. CISD — Change In State of Delivery (the "golf candle")
- **What:** the moment momentum decisively flips — marked by an outsized candle ("golf candle") that
  closes beyond the prior consolidation.
- **How / math:** a **golf candle** has body `|close − open|` greater than the **maximum body of the
  prior `golf_n` candles** (`golf_n` user-exposed & tunable, **default 3**). A **CISD** is a golf
  candle that closes beyond the prior range in the new direction.
- **When & why:** the primary trigger that "delivery" (who's in control) has changed — the key
  confirmation for taking breakers/order blocks.
- **Vote (both):** *confirm* the box direction when a same-direction CISD prints; part of the breaker
  stack (§20).

## 22. Market structure — HH / HL / LH / LL
- **What:** the sequence of swing highs/lows that defines trend and breaks of structure (BOS).
- **How (close-based swings):** a swing high = a close higher than the `swing_L` closes on each side
  (default **L = 2**, tunable); mirror for swing low. Confirmed only **L bars after** it forms (no
  look-ahead). Labels: higher-high/higher-low = uptrend; lower-high/lower-low = downtrend.
- **When & why:** the backbone of SMC — defines the structure-trend sub-engine and the
  "structure-break" leg of the breaker stack and OB detection.
- **Vote (both):** *confirm* a box long while structure prints HH/HL; *veto* a long into a confirmed
  LH/LL downtrend (mirror short).

## 23. Trend — two independent sub-engines (pick one)
Per decision #12 + the OOP directive, trend is **two separate engines**, selected by a dashboard
switch (no nested branches):
- **MA-trend sub-engine (default):** trend = EMA/SMA stack (e.g. `close > EMA_fast > EMA_slow` ⇒ up).
- **Structure-trend sub-engine:** trend = the HH/HL vs LH/LL sequence from §22.
- **Vote (both):** *confirm* in-trend box signals; *veto* counter-trend ones (subject to its `mode`).

## 24. Key levels (external weekly/monthly boxes)
- **What:** horizontal levels from the offline box pipeline — weekly & monthly opens and
  inducement/retracement highs/lows (`wOpen/mOpen`, `W*`/`M*` columns). **Daily (`D*`) ignored.**
- **How:** loaded from `NQ_full_data.csv` via `box_lookup.py` (already weekly+monthly). Not generated
  on the fly — they depend on external/scraped structure.
- **When & why:** major decision levels where price reacts; trading **into** a strong opposing level
  is low-quality.
- **Vote (veto-led, start minimal):** *veto* a box entry firing **into** an opposing active level
  within `level_buffer` (default **0.5·ATR**); *confirm* entries firing **off** a level in-direction.
  Start with opens only; other level columns available but off until selected.

## 25. Gap — no-trade interval
- **What:** any interval with no trades (session breaks, the NQ 17:00–18:00 close, weekends).
- **How:** detected from missing/zero-volume bars and the session calendar.
- **When & why:** gaps create FVG-like imbalances and unreliable readings; useful as context and to
  avoid stale signals across a gap.
- **Vote (veto):** optionally *veto* entries immediately across a large gap; otherwise contextual.

---

## 26. Causality & parity guarantees (every indicator)
- **No look-ahead:** every reading uses only **closed** bars up to the signal bar; swings/OBs are
  confirmed `L` bars late; generation runs on data available at that point in time.
- **Decision TF in, 1-min exits:** indicators are evaluated on the entry/decision timeframe; **exits
  still resolve on 1-minute** (the WS-H rule) — indicators never touch the exit path.
- **All-off ⇒ parity:** with every indicator disabled and retrace/wait = 0, the composite gate
  collapses to today's vol-gate-only path; `test_parity.py` / `test_fast_parity.py` keep passing.
- **No silent fallback:** invalid/missing params raise `ParamError`; disabled indicators still log
  their opinion with `active=0`.

## 27. Parameter index (defaults; all tunable + dashboard-exposed)
| Indicator | Key params (default) | Default mode |
|---|---|---|
| SMA | n_fast 50 / n_slow 200 | confirm |
| EMA | n_fast 20 / n_slow 50 | confirm |
| RMA | n 14 (support) | — |
| MACD | 12 / 26 / 9 | confirm |
| RSI | n 14, bands 30/70 | both |
| Stochastic | 14 / 3 / 3 | both |
| CCI | n 20, ±100 | both |
| ADX/DMI | n 14, thr 20–25 | veto |
| ATR | n 14 (also retrace unit) | veto |
| Bollinger | n 20, k 2.0σ | veto |
| Keltner | EMA 20, m 2.0×ATR | confirm |
| OBV | slope window | confirm |
| VWAP | daily-anchored | confirm |
| MFI | n 14 | both |
| FVG | fvg_lookback (bars) | both |
| IFVG | close-through | both |
| Order Block | ob_zone body/wick | both |
| Breaker | breaker_confirm all_three | both |
| CISD/golf | golf_n 3 | both |
| Structure | swing_L 2 | both |
| Trend | mode MA(default)/structure | both |
| Key levels | level_buffer 0.5·ATR, weekly+monthly | veto |
| Gap | gap size | veto |
| **Global** | **K 1**, per-indicator retrace 0 / wait_bars 0 | — |

---

*Next (I.3): implement these as `indicators/{classic,smc,timing,confirm}.py` + the two-phase
generation, each variant its own engine selected by switch (OOP), off-by-default. No engine code
until this spec is reviewed.*
