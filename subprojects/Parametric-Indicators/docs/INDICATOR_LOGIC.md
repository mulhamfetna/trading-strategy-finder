---
name: indicator-logic
description: WS-I full indicator logic reference — the vote model (confirm/veto/neutral vs box direction) and the exact per-bar rule for each of the 15 indicators + the golf engulfing structure. Grounded in indicators/{library,votes,classic,smc}.py.
type: reference
status: current
created: 2026-06-08
workstream: WS-I
---

# Indicator Logic — the 15 judges (+ golf)

Every indicator is a **judge** over the box's per-bar direction. It never sets direction; it only
**confirms**, **vetoes**, or stays **neutral**. This doc gives the exact rule for each.

## 1. The vote model (shared by all)
```
                 box direction d ∈ {LONG +1, SHORT −1, HOLD 0}   (from the box, just-closed bar)
                              │
 indicator.directions(ctx) ──┼──►  cdir[bar] ∈ {+1,−1,0, BOTH}   "which side I'd confirm"
        (per-bar, causal)     └──►  vdir[bar] ∈ {+1,−1,0, BOTH}   "which side I'd veto"
                              │
        vote() maps them vs d and the indicator's MODE ∈ {confirm, veto, both}:
            would_confirm = (cdir == d) or (cdir == BOTH)      ; only on a non-HOLD bar
            would_veto    = (vdir == d) or (vdir == BOTH)
            mode confirm → CONFIRM if would_confirm
            mode veto    → VETO    if would_veto
            mode both    → CONFIRM, then VETO overrides on the same bar
                              ▼
            vote[bar] ∈ {CONFIRM +1, VETO −1, NEUTRAL 0}    (raw per decision bar)
```
- `BOTH` (sentinel) = direction-agnostic: matches whatever the box direction is (e.g. ADX "no trend"
  vetoes a long *or* a short).
- Votes are **raw per decision bar** (no smoothing). The global *wait* is a 1-min entry delay, not a
  vote debounce (see `ENTRY_TIMING_CHANGES.md`).
- **Stance helper** (`votes.stance_directions`): a bullish/bearish stance `s∈{+1,−1,0}` →
  `cdir = s`, `vdir = −s` (confirm that side, veto the other).
- **Zone helper** (`votes.rsi_directions`, used by RSI/Stochastic/MFI): `long_zone → (cdir +1, vdir −1)`,
  `short_zone → (cdir −1, vdir +1)`.

K-rule at the gate: **entry allowed ⇔ (no active veto) AND (#active confirms ≥ K)**.

---

## 2. Trend / moving-average family (stance: confirm the side, veto the other)
| Indicator | key | params | Bullish stance (+1) when | Bearish (−1) when |
|---|---|---|---|---|
| **EMA trend** | `ema_trend` | fast=20, slow=50 | `close > EMA_fast > EMA_slow` | `close < EMA_fast < EMA_slow` |
| **SMA trend** | `sma_trend` | fast=50, slow=200 | `close > SMA_fast > SMA_slow` | `close < SMA_fast < SMA_slow` |
| **MACD** | `macd` | fast=12, slow=26, signal=9 | histogram > 0 | histogram < 0 |
| **VWAP** | `vwap` | (session) | `close > VWAP` | `close < VWAP` |
| **Keltner** | `keltner` | n=20, m=2.0 | `close > Keltner mid (EMA)` | `close < mid` |
| **OBV** | `obv` | slope=20 | `OBV > SMA(OBV, slope)` | `OBV < SMA(OBV, slope)` |
Each maps via the stance helper → confirm its side, veto the opposite.

## 3. Momentum mean-reversion zones (RSI / Stochastic / MFI)
`rsi_directions(value, lower, upper)` — used by all three (Stoch on %K, MFI on money-flow):
```
 value ≥ upper           → SHORT zone   (cdir −1, vdir +1)   "overbought → fade"
 value ≤ lower           → LONG  zone   (cdir +1, vdir −1)   "oversold → bounce"
 50 < value < upper      → LONG  zone   (bullish momentum)
 lower < value < 50      → SHORT zone   (bearish momentum)
 value == 50 or NaN      → NEUTRAL
```
| Indicator | key | params |
|---|---|---|
| **RSI** | `rsi` | n=14, lower=30, upper=70 |
| **Stochastic** | `stochastic` | n=14, d=3, lower=20, upper=80 (votes on %K) |
| **MFI** | `mfi` | n=14, lower=20, upper=80 |

## 4. Breakout / strength
- **CCI breakout** (`cci`, n=20, threshold=100): `CCI ≥ +thr → +1` (confirm long), `CCI ≤ −thr → −1`
  (confirm short), else neutral. Stance helper (confirm side / veto other).

## 5. Veto-only family
- **Bollinger veto** (`bollinger`, n=20, k=2.0): pure veto on band-stretch —
  `close ≥ upper band → vdir +1` (veto a long), `close ≤ lower band → vdir −1` (veto a short);
  `cdir` always 0 (never confirms).
- **ADX veto** (`adx`, n=14, threshold=25): regime filter using ADX + ±DI —
  ```
  ADX <  thr (no trend)        → vdir = BOTH      (veto EITHER side)
  ADX ≥ thr and +DI > −DI      → cdir = +1        (trend up → confirm long)
  ADX ≥ thr and −DI > +DI      → cdir = −1        (trend down → confirm short)
  ```
  So ADX both vetoes (when choppy) and can confirm (when trending) depending on `mode`.

## 6. SMC family (Smart-Money-Concepts; stance helper)
- **Structure trend** (`structure_trend`, swing_l=2): swing-based market structure —
  higher-highs/higher-lows ⇒ +1 (uptrend), lower-highs/lower-lows ⇒ −1 (downtrend). (`smc.structure_trend`.)
- **Order block → breaker** (`order_block`, swing_l=2): an order-block / breaker **state machine**
  on (open,high,low,close) → +1 bullish OB regime / −1 bearish. (`smc.order_blocks`.)
- **FVG confirm** (`fvg`, lookback=3): active fair-value-gap direction — an unfilled bullish gap
  in the lookback ⇒ +1, bearish gap ⇒ −1. (`smc.fvg_active_direction`.)

## 7. Golf — N-candle engulfing (generation-only, not a vote)
Golf is a **generated structure** surfaced in the Phase-1 report (`n_golf`/`n_golf_bull`/
`n_golf_bear`), not a confirm/veto judge. For bar `t`, `N = golf_n`:
1. opposite colour to **all** N prior candles (bullish: current green, all prior red; bearish: mirror);
2. range engulf incl. wicks: `high[t] ≥ max(high[t−N:t])` and `low[t] ≤ min(low[t−N:t])`;
3. body filter: `|close−open| ≥ 0.70 × (prior combined high−low)`.
→ +1 bullish / −1 bearish / 0. Full spec: [[golf-engulfing]].

---

## 8. Defaults & parity
Every indicator defaults **disabled**; the registry is in `indicators/library.py` (`REGISTRY`), UI
metadata + param bounds in `SCHEMA`. With nothing enabled the gate == the vol gate exactly (box
parity). Primitives (SMA/EMA/RMA/RSI/ATR/MACD/Stochastic/CCI/Bollinger/Keltner/VWAP/MFI/OBV/ADX) are
hand-verified causal implementations in `indicators/classic.py` (no TA-Lib). See [[indicators-spec]]
(`INDICATORS.md`) for the verbose per-indicator narrative and `INDICATOR_DECISIONS.md` for the frozen
rules.
