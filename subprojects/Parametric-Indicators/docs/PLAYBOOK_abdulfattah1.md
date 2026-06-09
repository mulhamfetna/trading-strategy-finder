---
name: playbook-abdulfattah1-profile
description: Strategy playbook for the saved profile "abdulfattah1" — its exact knobs, what each
  indicator does + its tuned values, the warm-up timeline, performance per window (warm-up-aware
  engine), and how to operate/validate it. Reconstructed from the dashboard run logs (4h champion
  config); regenerate if the saved profile differs.
type: playbook
status: current
profile: abdulfattah1
workstream: WS-I
---

# Playbook — profile **abdulfattah1**

> Reconstructed from the parameters in the dashboard run logs (they match the **WS-I 4h champion**
> config). If your saved `abdulfattah1` differs, paste its JSON / re-run it once and I'll regenerate.
> Stats below are from the **current engine with per-indicator warm-up active**.

## 1. What this profile is, in one line
A **4-hour** box strategy that only trades when a trend/momentum stack agrees and a no-trend filter
isn't blocking — patient, wide stops, take-profit bigger than the stop, and a tight intraday
drawdown breaker.

## 2. The exact knobs

| Knob | Value | Meaning |
|---|---|---|
| Timeframe | **4h** | decision candle |
| Soft SL | **139.2** pts | first stop (2 closes beyond confirm) |
| Hard SL | **153.11** pts | hard stop (touch); caps loss ≈ $3,062 |
| Take-profit | **183.22** pts | target ≈ +$3,664 |
| Vol gate | **83.59%** | skip the wildest ~16% of bars (HAR-RV) |
| Breaker | **$1,305** | halt after drawdown hits this… |
| Cooldown | **0** | …but releases immediately (breaker barely bites) |
| Flip | **False** | trade the box direction as-is |
| **K** | **1** | need **≥1** confirming indicator, and **no** veto |
| retrace / wait | 0 / 0 | no entry-timing delay (immediate fill at signal close) |

Risk per contract: hard stop ≈ **$3,062**, target ≈ **$3,664** (≈ 1.2 : 1 reward:risk), NQ @ $20/pt.

## 3. The indicator stack (8 of 15 on)

| Indicator | Role | Tuned settings | What it checks |
|---|---|---|---|
| **ema_trend** | confirm | fast 244 / slow 373 | long-term trend direction |
| **macd** | confirm | 14 / 143 / 81 | momentum building/fading |
| **keltner** | confirm | n 138, m 3.5 | price above/below a slow band |
| **rsi** | both | 53 (40/65) | overbought/oversold (asymmetric) |
| **stochastic** | both | 39, d 35 (23/52) | overbought/oversold |
| **mfi** | both | 39 (12/57) | overbought/oversold w/ volume |
| **adx** | veto | 81, thr 8 | **blocks trades when there's no real trend** |
| **order_block** | both | swing_l 18 | big-player reaction zones |

Entry rule: **box gives a direction → allowed iff (no veto fires) AND (≥1 of the confirmers agrees).**
`adx` is the gatekeeper — in a no-trend regime it vetoes everything.

## 4. Performance (current engine, warm-up active)

| Window | Trades | P/L | max DD | Win % | Profit factor |
|---|--:|--:|--:|--:|--:|
| **full (25–26)** | 45 | **$58,001** | $10,635 | 64% | 2.2 |
| 2025 | 29 | $32,762 | $10,635 | 62% | 2.0 |
| 2026 | 19 | $22,780 | **$3,062** | 63% | 2.1 |

Note: these differ from the optimizer's original champion numbers ($56,040 / $10,260) because the
**warm-up rule is now applied** — indicators stay neutral until their look-back fills, so a few early
trades are no longer taken. This is the more honest read.

## 5. Warm-up timeline (when this profile actually starts trading)

Each indicator waits out its look-back before it can vote. On 4h (~4.9 bars/day):

| Indicator | warm-up | ≈ days | waits for |
|---|--:|--:|---|
| **ema_trend** | 373 bars | ~76 | EMA(244) & EMA(373) |
| adx (veto) | 161 | ~33 | ATR(81)+DX, then ADX over 81 |
| macd | 224 | ~46 | EMA line + signal EMA(81) |
| keltner | 138 | ~28 | EMA(138) mid + ATR(138) |
| stochastic | 73 | ~15 | %K(39)+%D(35) |
| rsi | 53 | ~11 | 53-bar look-back |
| mfi | 39 | ~8 | 39-bar look-back |
| order_block | 18 | ~4 | confirmed swings (l=18) |

**Practical consequence:** the profile is effectively *idle for its first ~76 trading days* (until
`ema_trend` warms) on any fresh data window — the event log will show `WARMING UP` lines and the
first `WARMED` around then. **Do not run this on a window shorter than ~80 trading days of 4h data**
or `ema_trend` "NEVER warms up" and the confirm stack is crippled.

## 6. How to run it
1. `python3 server.py --port 8200` → open http://localhost:8200/
2. **Strategy** dropdown → **My saved profiles → abdulfattah1** (fills every field + runs).
3. Use **window = full** for the trustworthy read (single-year windows cold-start the indicators).
4. Read the **event log**: `WARMING UP/WARMED` (which indicator is live), `ENTRY` (with `K: x confirm
   / y veto`), `NOENTRY` (a signal blocked — `vetoed by adx…` or `volatility gate`).
5. **⬇ CSV** on either log to export the run.

## 7. Operating notes & cautions
- **adx(thr=8) is a loose trend filter** — threshold 8 is low, so it rarely vetoes; the trade gate is
  mostly "≥1 confirm". Watch how often `NOENTRY … vetoed by adx` appears.
- **Cooldown 0** means the $1,305 breaker locks and instantly unlocks — it provides almost no
  protection here. If you want real circuit-breaking, raise cooldown.
- **R:R ≈ 1.2:1** with a 64% win-rate is the edge; a drop in win-rate hurts fast at this R:R.
- **n = 1 history** (2025→2026) — candidate, not proof. Re-validate before real use.
- Reward:risk and all stats assume **1 contract**, NQ $20/pt.

---

_Generated for the saved profile `abdulfattah1`. Companion: `docs/PLAYBOOK_ABDULFATTAH_1.md` (general
operator guide). If the live profile's knobs differ from §2, send me its JSON and I'll regenerate this._
