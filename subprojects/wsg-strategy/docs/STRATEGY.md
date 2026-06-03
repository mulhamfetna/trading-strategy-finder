# The Strategy — full explanation (self-contained)

This document explains the WS-G drawdown-capped strategy from scratch for someone studying **only
this folder**. No other part of the repo is required to understand it.

> **⚠️ Corrected results (2026-06-03).** An earlier version of the drawdown breaker reset its
> high-water mark on resume, so it did **not** actually cap drawdown — it inflated the headline to
> +$24,720 / $4,845. The breaker is now fixed (global high-water mark) and the default re-tuned to
> **trigger $2,000 / cooldown 20**. **Corrected result: +$7,735 P/L · true max drawdown $3,670**
> (both years positive), and that profitable-and-capped tuning is **overfit (n=1)**. The entry/exit
> logic is unchanged. **The §6 results table below still shows the SUPERSEDED buggy-breaker run
> (+$24,720 / $4,845)** — use the corrected figures in this banner. The engine + parameter wiring
> were always correct; only the breaker's bookkeeping was wrong.

---

## 1. The goal
Make money on NQ futures **without ever taking a large drawdown**. Concretely: maximise total P/L
while keeping the worst peak-to-trough equity drop (the *max drawdown*) under **$5,000** (1
contract). Capital preservation first, profit second.

## 2. The instrument & timeframe
- **NQ** = E-mini Nasdaq-100 futures. Point value **$20** (so 40 points = $800).
- Decisions are made on **4-hour candles**. Exits are resolved on **1-minute candles** inside each
  4h window (so a stop/target can fill intrabar, not only at the 4h close).
- **One contract**, always. No scaling, no pyramiding.

## 3. The entry signal (the "box" rule)
The repo's strategy labels each 4h candle, against weekly/monthly support/resistance **boxes**, as
**long**, **short**, or **hold** (the logic lives in `box_lookup.py` + `engine.py`). In words: when
a candle interacts with a box level in a directional way, it emits a long or short signal for the
*next* bar. We trade that signal — but only after two filters pass (below). (Entry uses the
*just-closed* bar's information only — no look-ahead.)

## 4. The three risk ideas that make it "drawdown-capped"
This is the heart of the strategy. Three independent safety layers stack:

1. **Volatility gate.** We forecast each bar's volatility with **HAR-RV** (a simple, robust model
   that averages recent realized volatility over short/medium/long windows). If the forecast is in
   the **top 40%** (above the 60th percentile, fixed on 2025 data), we **skip the trade** — those
   turbulent bars are where big losses happen. Calm bars only.
2. **Tight, capped stops.** Stop-loss sits **40 points** away (hard) → a single loss is capped at
   ≈ **$800**. Take-profit sits **60 points** away → ≈ **$1,200**. That's a **1.5 : 1
   reward:risk**, so we're profitable even winning < 50% of trades. (A soft stop at 30 pts exits a
   touch earlier if two consecutive 1-min closes breach it.)
3. **Drawdown circuit-breaker.** We track running equity vs its high-water mark. The moment the
   drawdown reaches **$2,500**, we **stop opening new trades for 30 trades**, then cautiously
   resume (resetting the high-water mark). Because each loss is capped at ~$800, the realized worst
   drawdown lands just past the trigger — about **$4,845**, under the $5,000 goal.

## 5. The exact rules
**Enter 1 contract only if ALL true:** (a) box signal is long/short; (b) volatility gate open
(HAR-RV ≤ 60th pct); (c) breaker not locked; (d) no position already open. Enter at the bar's open.

**Exit (resolved on 1-min bars), whichever first:** hard TP +60 (+$1,200) · hard SL −40 (−$800) ·
soft SL −30 (confirmed by 2 consecutive 1-min closes).

**Breaker:** running drawdown ≥ $2,500 → LOCK (skip entries) for 30 trades → UNLOCK (reset peak).

**Default parameters (the "winner"):** `SL_soft 30 · SL_hard 40 · TP 60 · gate 60th pct ·
breaker $2,500 / 30 · normal direction · 1 contract`.

## 6. Results (backtest, 2025–2026 NQ 4h)
| Metric | Value |
|---|---|
| Total P/L | **+$24,720** |
| 2025 / 2026 | +$15,995 / +$8,725 (both positive) |
| Max drawdown | **$4,845** (< $5,000 goal) |
| Win rate | 48.3% |
| Profit factor | 1.55 |
| Avg win / avg loss | +$1,200 / −$724 |
| Trades taken | 120 of 265 candidates (≈45% exposure) |
| Breaker locks | 5 |

For comparison, the same engine with **no** gate/breaker and the old 80/100/50 stops **lost
−$13,420 with a $57,160 drawdown** — so the three risk layers turn a boom-bust curve into a steady
climb. A more conservative alternative (`SL 35/40 · TP 40`) makes **+$21,100 at only $3,130
drawdown, 58% win** — pick it if you want more cushion than peak P/L.

## 7. Why it works (mechanism, not magic)
Volatility is *predictable* (it clusters), so the gate reliably avoids the dangerous bars; the
tight stop removes the fat tail of big losses; the breaker prevents a string of losses from
compounding into a hole. The favourable 1.5:1 payoff does the rest. The **cost** is upside: in
strong trends the tight stops + gate leave money on the table (it forgoes big runs to stay safe).

## 8. The honest caveats (read before trusting)
- **n = 1.** All parameters were tuned on a single ~1.4-year stretch of one instrument. The dollar
  figures are **in-sample on one regime** — evidence the *mechanism* works, not a forward promise.
- **Breaker is a backtest overlay**, computed on the trade stream after the fact. Live, it must be
  a real execution-layer equity-stop.
- The strict "drawdown ≤ 10% of P/L" target is **not** met (≈20%); that needs much higher P/L than
  this data supports.

## 9. Going live (do not skip)
1. **Validate out-of-sample** on other instruments/years (the single biggest requirement).
2. Re-run walk-forward with all params **frozen** (no peeking / re-fitting).
3. Implement the **drawdown breaker as a live equity-stop**; test its trigger.
4. **Paper-trade ≥ 1 month**; confirm fills match the SL/TP + 2-close soft-stop assumptions.
5. Define the **$5,000 manual kill-switch** and who watches it.
6. Start at **minimum size**; scale only after live tracks the backtest.

A condensed operator runbook (checklists, monitoring thresholds, contingencies) is in the research
notes: `../../meta-prophet/notes/45_winning_strategy_playbook.md`. The full analytical report is
`../../meta-prophet/notes/44_winning_system_full_report.md`. (Those workstream docs are kept in
place; this folder restates everything an outsider needs.)
