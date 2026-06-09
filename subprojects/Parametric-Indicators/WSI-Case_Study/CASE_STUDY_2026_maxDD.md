---
name: wsi-case-study-2026-maxdd
description: Why the 4h champion's 2026-only backtest shows a HIGHER max-drawdown than the full
  backtest. Verdict + root cause (indicator warm-up, not a held trade or the breaker), proven
  from the three exported logs + a bar-level reproduction.
type: case-study
status: complete
workstream: WS-I
---

# Case study — 2026-only maxDD > full maxDD (4h champion)

## The claim under test

> "The 2026 backtest had a higher max-drawdown than the full backtest. We think a signal from
> 2025 participated in 2026 trades, which saved a little money and made the max-drawdown smaller —
> because in the full backtest, trades held for nearly two months at the beginning of 2026."

## Verdict

| Part of the claim | Verdict |
|---|---|
| 2026-only maxDD **>** full maxDD | ✅ **TRUE** — $13,802 vs $10,260 |
| 2025 "participated" in 2026 and lowered the full maxDD | ✅ **TRUE in effect** — but via **indicator look-back history**, not a held position and not the drawdown breaker |
| Trades were **held for ~2 months** at the start of 2026 | ❌ **FALSE** — no trade is held; the full run simply took **zero trades** from 2025-12-17 to 2026-02-09. The flat equity *looks* like a hold but is the **absence of trades** |

## The numbers (recomputed from the exported trade ledgers)

| Run | Trades | Total P/L | maxDD | maxDD trough |
|---|--:|--:|--:|---|
| **FULL** (2025+2026) | 50 | $56,043 | **$10,260** | 2025-02-05 (early **2025**) |
| **2025-only** | 34 | $30,804 | $10,260 | 2025-02-05 |
| **2026-only** | 26 | $15,102 | **$13,802** | 2026-01-12 (early **2026**) |

Two immediate tells:
1. **34 + 26 = 60 trades, but FULL has only 50.** The full run takes **10 fewer** trades — it is *not*
   the simple concatenation of the two windows.
2. The full-period maxDD trough sits in **early 2025**; the 2026-only trough sits in **early 2026**.
   The full run never experiences the 2026-01 drawdown at all.

## What actually happened at the boundary

- **No trade spans 2025→2026.** (Checked: zero trades enter in 2025 and exit in 2026.) The "held for
  two months" reading is incorrect.
- **FULL's first 2026 trade is 2026-02-09.** Its previous trade exited **2025-12-17**. So the full run
  is *flat — no trades at all — for ~8 weeks* across the new year ("nearly two months", matching what
  was seen on the chart).
- **2026-only trades all through January**: 9 trades from 2026-01-02 to 2026-01-12, mostly losers
  (−3062, −3062, +3664, −2925, −3062, −2895, +3664, −3062, −3062), summing to exactly **−$13,802** —
  which *is* the entire 2026-only max-drawdown.

So the full run **avoided the January-2026 losing streak**; the 2026-only run **took it**.

## Why did they diverge? (ruling out the obvious suspects)

| Candidate cause | Ruled out because |
|---|---|
| Volatility gate | Threshold is computed from `vf[:n2025]` (2025 reference) in **both** runs → identical 2026 gate (logs show "≤ 132" in both). |
| Drawdown breaker | `dd_limit=$1,305`, **cooldown=0** → every LOCK says "halt **0** trades"; **SKIP=0** in both logs. The breaker suppresses nothing. |
| A held position from 2025 | No trade spans the boundary (checked). |
| **Indicator look-back (warm-up)** | ✅ **This is it** — see below. |

## Root cause: indicator warm-up / history

The dashboard slices the decision frame to the chosen window **before** the indicator layer runs
(`strategy.build_payload`: `d4 = df4.iloc[lo:hi]` → `runner.build_layer(d4, …)`). So the **2026-only
run recomputes every indicator on a frame that starts 2026-01-02 with no 2025 history.**

The 4h champion uses long-lookback indicators — `ema_trend(fast=244, slow=373)`, `keltner(n=138)`,
`adx(n=81)`, `macd(143/81)`, `rsi(53)`, `mfi(39)`, `stochastic(39)`, `order_block(swing_l=18)`. With
no warm-up they spend the first weeks of January in their seeding region, where **vetoes cannot fire
and confirms behave differently**.

### Bar-level proof (125 January-2026 decision bars)

Computed the indicator entry-allow mask (`¬veto ∧ confirm ≥ K`) two ways:

| | January bars that ALLOW an entry | January vetoes |
|---|--:|--:|
| **WARMED** (indicators on full history, then sliced to 2026) | **0 / 125** | 60 |
| **COLD** (indicators recomputed on the 2026-only frame) | **16 / 125** | 39 |

- Warmed by 2025, the indicators **veto or decline every single January signal** → 0 entries → the
  full run has no January drawdown.
- Cold-started, they veto far less (39 vs 60) and confirm more easily → **16 bars become eligible** →
  the 9 January losing trades fire → −$13,802.

That is the precise sense in which "2025 participated in 2026 and saved money": **2025 supplies the
indicator look-back that, in the full run, filters out the bad January-2026 entries.** It is the
indicators' *history*, not a held trade and not the breaker.

## Implication (important)

**Windowed sub-backtests (2025 / 2026) are NOT faithful slices of the full backtest when indicators
are enabled** — the windowed run cold-starts its indicators and loses cross-boundary warm-up. The
**2026-only maxDD ($13,802) is a cold-start artifact**; the **full-period number ($10,260) is the
faithful one** for a strategy that has been running continuously.

### Recommended fix (optional)
When backtesting a sub-window, **warm the indicators on the preceding data**: compute the indicator
layer on the full frame and *then* slice to the window (or feed a look-back buffer of N prior bars,
N = max indicator lookback ≈ 400 4h-bars). Today the slice happens first, which is why 2025/2026
windows diverge from full. Worth doing if per-window numbers are to be trusted.

---

_Evidence: `WSI-4h-champion-{full,2025,2026}-backtest/` trade ledgers + event logs (exported from the
dashboard). Bar-level reproduction: `veto_mask`/`confirm_mask` warmed-vs-cold on the 2026 window._
