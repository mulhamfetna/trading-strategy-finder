# NQ 1-1-2 Scaling Strategy — Dashboard User Manual

## Table of Contents

1. [What This Dashboard Is](#1-what-this-dashboard-is)
2. [The NQ Futures Market — Context](#2-the-nq-futures-market--context)
3. [The 1-1-2 Scaling Strategy — Core Logic](#3-the-1-1-2-scaling-strategy--core-logic)
4. [Dashboard Layout](#4-dashboard-layout)
5. [Left Panel: Settings](#5-left-panel-settings)
6. [Running a Backtest](#6-running-a-backtest)
7. [The Progress Bar](#7-the-progress-bar)
8. [The Chart](#8-the-chart)
9. [Metrics Cards](#9-metrics-cards)
10. [Trade Log](#10-trade-log)
11. [Replay Mode](#11-replay-mode)
12. [Reading & Interpreting Results](#12-reading--interpreting-results)
13. [Parameter Tuning Guide](#13-parameter-tuning-guide)

---

## 1. What This Dashboard Is

This is a **strategy backtester** — a tool that simulates how the 1-1-2 scaling trading strategy would have performed on real historical NQ futures data, without risking any actual capital.

**What it does:**
- Loads historical 4-hour NQ (Nasdaq-100 E-mini futures) candlestick data
- Runs the 1-1-2 scaling strategy through every candle in the dataset
- Records every simulated trade (entry price, exit price, profit/loss, reason for exit)
- Displays a full performance report: chart, statistics, and trade-by-trade log

**What it does NOT do:**
- Execute real trades — this is purely a simulation
- Predict the future — past performance does not guarantee future results
- Account for slippage, real-world bid/ask spreads, or broker-specific execution

**The data:**
The default dataset is `NQ_4h.csv` — four-hour candlestick bars for the NQ futures from January 2025 onward. Each candle represents 4 hours of price action: one Open, High, Low, Close price and a Volume count.

---

## 2. The NQ Futures Market — Context

**NQ** is the ticker for Nasdaq-100 E-mini futures, traded on the CME exchange. It tracks the top 100 non-financial companies on the Nasdaq (Apple, Microsoft, Nvidia, etc.).

**Key numbers you need to know:**

| Term | Value | Meaning |
|------|-------|---------|
| Point value | $20/point | 1 full NQ point = $20 per contract |
| Tick | 0.25 points | Smallest price increment |
| Tick value | $5 | Cost of one tick per contract |
| Margin | ~$1,000–$2,000 | Typical intraday margin per contract |

> **Important:** This dashboard uses a simplified model: **$2 per point per contract** (not $20). This is intentional — the strategy uses micro-NQ contracts (MNQ), which are 1/10th the size of full NQ contracts. 1 MNQ point = $2. All P&L figures in this dashboard are in MNQ terms.

**What is a "point" in context?**
NQ typically trades between 18,000 and 22,000. A 100-point move is roughly 0.5% of price — common in a single trading session. A 400-point move in one candle is a major volatility event.

---

## 3. The 1-1-2 Scaling Strategy — Core Logic

This strategy is built around one core idea: **don't enter your full position at once — scale in as the market moves against you to get a better average price.**

### 3.1 The Three Entry Legs (1-1-2)

The strategy enters a position across 3 legs, not all at once:

```
Direction determined → LONG or SHORT
        │
        ▼
Leg 1: Enter 1 contract at the base level (current price)
        │
        ▼  (price moves against you)
Leg 2: Enter 1 more contract when price is 100 pts away from Leg 1
        │
        ▼  (price continues against you)
Leg 3: Enter 2 more contracts when price is 150 pts away from Leg 1
        │
        ▼
Total: 4 contracts, weighted average entry ≈ 75 pts from Leg 1
```

**Why this works in theory:**
If price moves 100–150 points against you before reversing, you've scaled in at better and better prices. Your average cost is more favorable than if you had entered everything at once. The 2-contract Leg 3 is the key — it pulls the average even further in your direction.

**Example (LONG trade):**
- Leg 1: Buy 1 contract @ 21,000
- Leg 2: Buy 1 contract @ 20,900 (100 pts lower)
- Leg 3: Buy 2 contracts @ 20,850 (150 pts lower)
- Weighted average: (21,000 + 20,900 + 20,850×2) / 4 = **20,900**

Your effective entry is 100 points below where you started — so you only need price to rally 100 points from average to hit +100 pts profit.

### 3.2 The Big Candle Exception (> 400 pts)

If the trigger candle is larger than 400 points (High − Low > 400), the market has extreme momentum. Scaling in would be dangerous — the pullbacks might never come.

**Big candle rule:**
- Skip the 3-leg scaling entirely
- Enter **all 4 contracts immediately** at the first level
- Trade in the **opposite direction** of the candle (fade the spike)
  - Green (bullish) big candle → enter SHORT
  - Red (bearish) big candle → enter LONG

The logic: extreme one-direction candles often mean the market is over-extended and will snap back.

### 3.3 Direction Logic

Each 4h candle determines whether the next potential trade is LONG or SHORT based on price direction:
- Current close > previous close → bullish candle → Leg 1 tries LONG
- Current close < previous close → bearish candle → Leg 1 tries SHORT

### 3.4 Take Profit (TP)

The take profit target is **+150 points from the average entry price** by default.

The algorithm also has a **trailing watch mechanism**:
- Once price reaches **+50 points** of profit (the "watch threshold"), the system starts monitoring closely
- If a candle **closes** beyond the +50-point level, the trade exits at that close (takes secured profit)
- This means the actual exit can be anywhere from +50 pts to +150 pts depending on candle behavior

**Exit reason shown as:** `TAKE PROFIT` or `TAKE PROFIT (TRAIL)`

### 3.5 Stop Loss — The Dual SL System (asymmetric fills)

Two stop losses protect every trade, with **different fill semantics** (user rule 2026-05-24):

| SL Type | Distance from avg | Confirmation timeframe | Where it fills | Realised loss |
|---|---|---|---|---|
| **Soft SL** | `sl_soft_points` (default 200) | 2-min candle CLOSE past the line | AT the confirming bar's CLOSE | ≥ `sl_soft_points` (depends on how far the close went past) |
| **Hard SL** | `sl_hard_points` (default 300) | 1-min candle CLOSE past the line | AT the line exactly | = `sl_hard_points` exactly |

**Why the asymmetry?** Hard SL models a stop-market order at the disaster line — the fill is the line. Soft SL is a slow-confirmation stop — by the time a 2-min candle has closed past it, the realised price is wherever that close happened, which is usually further from `avg` than the line itself.

**Dashboard invariants** (validated both backend Pydantic AND frontend computed; submit blocked while violated):

- `sl_hard_points > sl_soft_points` (hard farther out)
- `soft_sl_confirmation_timeframe_minutes > hard_sl_confirmation_timeframe_minutes` (soft confirms slower)

**Exit reason shown as:** `STOP LOSS (SOFT)` or `STOP LOSS (HARD)`

### 3.6 Re-Entry

After a profitable exit, if price pulls back to the original entry zone, the strategy can re-enter with the same 1-1-2 logic. Triggers ONLY when the previous exit was `TAKE PROFIT` (the hard target) — not on `TRAIL` or any `STOP LOSS`.

- **Re-entry enabled:** toggle on/off
- **Cooldown:** minimum number of 4h candles to wait before re-entering after an exit

### 3.7 Dual-Timeframe Engine (shipped 2026-05-24)

Entries are decided on the 4h frame; **SL/TP exits run on a 1-min companion frame**. The dashboard's Data section now requires three CSVs:

| File | Role |
|---|---|
| `NQ_4h.csv` | Entry signals (box traversals) |
| `NQ_1m.csv` | SL/TP exits — hard tier on 1-min closes, soft tier on 2-min aggregates |
| `NQ_full_data.csv` | Unified weekly + monthly box edges |

What that means in practice:

- **HARD SL / TP target** fire the moment the first 1-min close (or high/low for TP) breaches the line. Exit timestamp is the 1-min bar's time (e.g., `2025-01-03T15:47:00`).
- **SOFT SL / Trailing TP** fire on the first 2-min close past the threshold. Exit timestamp is the end-of-window 1-min bar.
- The first trigger in time wins. Hard before soft on the same minute.

**What used to be approximated** (15-sec entry confirmations, etc.) for the entry side remains documented-but-not-enforced — params live in the form but the 4h close is treated as already confirmed. The SL/TP side is now exact at 1-min/2-min resolution.

If you're comparing dashboard results to numbers from before 2026-05-24, expect dramatic shifts: 4 of the 7 January trades changed exit type (TP → TRAIL or HARD → SOFT) — see `docs/SYSTEM_BLUEPRINT.md` Part C for the side-by-side.

---

## 4. Dashboard Layout

The dashboard is split into two panels:

```
┌─────────────────────────────────────────────────────────────────────┐
│  HEADER: Title  │  [Replay]  [Run Backtest]                         │
├───────────────────────────┬─────────────────────────────────────────┤
│                           │  Progress Bar                           │
│   LEFT PANEL              │  ─────────────────────────────────────  │
│   Settings                │  Replay Bar (when active)               │
│   ──────────              │  ─────────────────────────────────────  │
│   • Data                  │  Chart                                  │
│   • Entry distribution    │    ├── Candlesticks + EMA overlays      │
│   • Big candle            │    ├── Volume panel                     │
│   • Take profit           │    └── RSI panel                       │
│   • Stop loss             │  ─────────────────────────────────────  │
│   • Re-entry              │  Metrics Cards                          │
│   • Indicators            │  ─────────────────────────────────────  │
│                           │  Trade Log                              │
└───────────────────────────┴─────────────────────────────────────────┘
```

---

## 5. Left Panel: Settings

### 5.1 Data Section

| Field | What It Does |
|-------|-------------|
| **CSV path** | The filename of the price data file. Default: `NQ_4h.csv`. Must exist in the project root directory |
| **Start date** | Filter the data to begin from this date. Click the calendar icon to pick. Leave empty to use the full dataset |
| **End date** | Filter the data to end at this date. Leave empty to run to the most recent bar |

**How to use dates:**
- To backtest just Q1 2025: Start = `2025-01-01`, End = `2025-03-31`
- To backtest the full dataset: leave both empty
- Narrowing the date range is useful for testing how the strategy behaves in specific market conditions (trending vs ranging, volatile vs quiet)

### 5.2 Entry Distribution & Sizing (1-1-2)

| Field | Default | Meaning |
|-------|---------|---------|
| **Total contracts** | 4 | Total contracts across all 3 legs. Should equal Leg1 + Leg2 + Leg3 |
| **Leg 1 contracts** | 1 | Contracts entered at the base level (first touch) |
| **Leg 2 contracts** | 1 | Contracts entered at the 100-pt pullback |
| **Leg 3 contracts** | 2 | Contracts entered at the 150-pt pullback |
| **Leg 2 pullback (pts)** | 100 | How far price must move against Leg 1 before Leg 2 fills |
| **Leg 3 pullback (pts)** | 150 | How far price must move against Leg 1 before Leg 3 fills |

**Experimenting:**
- Increase Leg 3 to 3 contracts (and reduce Leg 1 or Leg 2) to weight more heavily toward the deep pullback price
- Increase pullback distances (e.g., 150/200 instead of 100/150) if the strategy is getting stopped out before all legs fill

### 5.3 Big Candle Exception

| Field | Default | Meaning |
|-------|---------|---------|
| **Threshold (pts)** | 400 | A candle larger than this triggers the big candle rule |
| **Full size contracts** | 4 | Contracts to enter immediately under the big candle rule |
| **Reverse direction** | ✓ | Whether to fade (trade opposite) the big candle direction |

**Tuning notes:**
- Lower the threshold (e.g., 300) to trigger the big candle rule more often
- Uncheck "Reverse direction" to trade *with* big candles instead of fading them

### 5.4 Take Profit

| Field | Default | Meaning |
|-------|---------|---------|
| **Target (pts from avg)** | 150 | The full take-profit target, measured from the average entry price |
| **Watch threshold (pts)** | 50 | Once price reaches this profit level, the trailing exit activates |

**How the TP logic actually works:**
1. Trade opens, TP target is avg_entry ± 150 pts
2. When price first reaches avg_entry ± 50 pts (the watch threshold), the trailing logic arms
3. From that point, **if a candle closes** past the +50 level, the trade exits at that close
4. This can exit anywhere from +50 pts (minimal close-past) to +150 pts (if price gaps to target)

**Common adjustment:**
- Raise the watch threshold to 80–100 pts to only start trailing once profits are more secure
- Lower the target to 100 pts for quicker, more frequent wins

### 5.5 Stop Loss

| Field | Default | Meaning |
|-------|---------|---------|
| **Soft SL (pts from avg)** | 200 | Primary stop — requires a candle *close* to trigger |
| **Hard SL (pts from avg)** | 300 | Emergency stop — also requires a candle *close*, but much farther away |

**Risk per trade (at defaults):**
- Maximum loss with 1 contract: 300 pts × $2 = **$600**
- Maximum loss with 4 contracts (full load): 300 pts × 4 × $2 = **$2,400**
- More realistic loss (soft SL): 200 pts × avg contracts filled × $2

**Tuning notes:**
- Tighter SLs (e.g., 150/250) will reduce max loss but may cause more premature exits
- Wider SLs give the trade more room but increase risk per trade
- The ratio of TP:SL (150:200 = 0.75) means you need a **>57% win rate** to be profitable at defaults

### 5.6 Re-Entry

| Field | Default | Meaning |
|-------|---------|---------|
| **Enabled** | ✓ | Allow the strategy to re-enter after a profitable exit |
| **Cooldown (candles)** | 1 | Minimum 4h candles to wait after an exit before re-entering |

**When re-entry matters:**
In trending markets, after the strategy takes profit, price often continues in the same direction. Re-entry catches these continuation moves. In ranging markets, re-entry can cause over-trading.

### 5.7 Indicators

These control what you see on the chart — they do not affect the backtest results.

| Field | Default | Meaning |
|-------|---------|---------|
| **EMA fast period** | 20 | Period for the faster (orange) moving average |
| **EMA slow period** | 50 | Period for the slower (blue) moving average |
| **Show volume panel** | ✓ | Toggle the volume histogram below the main chart |
| **Show RSI panel** | ✓ | Toggle the RSI (Relative Strength Index) panel |
| **RSI period** | 14 | Number of candles used to calculate RSI |

---

## 6. Running a Backtest

### Step-by-step:

1. **Configure settings** in the left panel (or leave defaults)
2. **Optionally set a date range** using the calendar pickers in the Data section
3. **Click "Run Backtest"** in the top-right header
4. Watch the **Progress Bar** fill as the strategy processes each candle
5. Results appear automatically when complete:
   - Chart fills with candles and trade markers
   - Metrics Cards show summary statistics
   - Trade Log shows every individual trade
6. Scroll down to see Metrics and Trade Log if not immediately visible
7. Click **"Replay"** to walk through the backtest trade by trade

### What happens behind the scenes:

```
Browser sends settings → FastAPI backend
Backend loads NQ_4h.csv → applies date filter
Backend runs ScalingStrategy candle-by-candle → streams progress every ~21 candles
On completion → sends full result: metrics + trades + candles
Browser receives result → updates chart + metrics + trade log
```

The streaming means you see live progress (trades so far, running P&L, win rate) while the backtest is still running — not just a spinner.

---

## 7. The Progress Bar

The progress bar appears at the top of the right panel and stays visible throughout.

### During a backtest:

```
Running backtest...                               84.6%
████████████████████████████░░░░░░░░

Candle     Trades     PnL           Win rate
1833/2168  612        +$109,547     84.5%

Position    Legs filled
LONG        1 / 4
```

| Field | What it means |
|-------|--------------|
| **Candle X / Y** | Which 4h bar the engine is currently processing |
| **Trades** | How many completed trades (entries AND exits) so far |
| **PnL** | Running sum of all completed trade profits/losses in dollars |
| **Win rate** | Percentage of completed trades that were profitable |
| **Position** | Current open position: LONG, SHORT, or FLAT (no position) |
| **Legs filled** | How many of the 3 scaling legs have been executed (0–4 contracts) |

### After completion:

The bar shows **"Backtest complete (Nms)"** with the elapsed time. All status fields remain visible showing the final snapshot before the last candle.

---

## 8. The Chart

The chart has three vertically-stacked panels:

### 8.1 Main Panel — Candlesticks + EMA Overlays

**Reading candlesticks:**

```
     │ ← High (wick)
    ███ ← Body (green = close > open / bullish)
     │ ← Low (wick)

     │ ← High (wick)
    ███ ← Body (red = close < open / bearish)
     │ ← Low (wick)
```

Each candle = 4 hours of price action. The body shows where price opened and closed. The wicks show intraday extremes that didn't hold.

**EMA Overlays:**
- **Orange line** = EMA (Fast, default 20 periods = 80 hours ≈ 3.3 trading days)
- **Blue line** = EMA (Slow, default 50 periods = 200 hours ≈ 8.3 trading days)

An Exponential Moving Average (EMA) weights recent prices more heavily than older ones. When:
- Fast EMA crosses **above** Slow EMA → market trend turning bullish
- Fast EMA crosses **below** Slow EMA → market trend turning bearish
- Price is above both EMAs → uptrend context
- Price is below both EMAs → downtrend context

The EMA overlays help you visually understand the market regime when each trade occurred. They are for reading context only — they are not inputs to the 1-1-2 strategy.

**Trade markers:**
After a backtest, colored markers appear at entry and exit candles:

| Marker | Meaning |
|--------|---------|
| ▲ Green arrow (below bar) | Long trade entry (buy) |
| ▼ Red arrow (above bar) | Short trade entry (sell) |
| ■ Green square (above bar) | Profitable exit — shows +N points |
| ■ Red square (below bar) | Losing exit — shows −N points |

The number on the exit square is the **profit in points** for that trade. Positive = win, negative = loss.

### 8.2 Volume Panel

The volume histogram shows how many contracts traded in each 4h candle.

- **Green bars** — more buying volume (close ≥ open)
- **Red bars** — more selling volume (close < open)
- **Tall bars** — high activity, significant market participation
- **Short bars** — quiet, low-conviction moves

**What to look for:**
- Big price moves accompanied by high volume = conviction move, likely to continue
- Big price moves on low volume = suspect move, likely to reverse
- Volume spikes often coincide with news events, economic releases, or market opens

### 8.3 RSI Panel

The RSI (Relative Strength Index) is a momentum oscillator that measures the speed and magnitude of recent price changes. It ranges from 0 to 100.

```
100 ─────────────────────────────────────
 70 - - - - - - - - - - - - - - - - - - -  ← Overbought zone
    │           ╭──╮
    │      ╭────╯  ╰──╮
    │  ╭───╯          ╰─────
 30 - - - - - - - - - - - - - - - - - - -  ← Oversold zone
  0 ─────────────────────────────────────
```

| RSI Level | Interpretation |
|-----------|----------------|
| Above 70 | **Overbought** — market has risen fast, potential for pullback |
| 50–70 | Bullish momentum |
| 50 | Neutral |
| 30–50 | Bearish momentum |
| Below 30 | **Oversold** — market has fallen fast, potential for bounce |

**Default settings:** RSI 14 (calculated over 14 × 4h = 56 hours ≈ 2.3 trading days)

**Using RSI with this strategy:**
- Trades entered when RSI is extreme (>70 or <30) are higher risk — the market is already stretched
- Trades entered when RSI is near 50 are in the "neutral" zone — lower conviction
- The big candle exception often coincides with RSI spikes

### 8.4 Chart Navigation

- **Scroll wheel** — zoom in and out on the time axis
- **Click and drag** — pan left and right through history
- After clicking "Run Backtest", the chart auto-fits to show the full dataset

---

## 9. Metrics Cards

The metrics cards appear below the chart and summarize overall strategy performance.

| Card | Formula | What a Good Value Looks Like |
|------|---------|------------------------------|
| **Net Profit** | Sum of all trade P&L in $ | Positive. The larger the better |
| **Total Trades** | Count of completed trades | Enough to be statistically significant (>50 ideally) |
| **Win Rate** | Wins ÷ Total Trades × 100 | Depends on TP:SL ratio — see below |
| **Profit Factor** | Gross Profit ÷ Gross Loss | Above 1.5 is healthy. Above 2.0 is strong |
| **Sharpe** | Mean trade return ÷ Std deviation | Above 0.5 is acceptable. Above 1.0 is good |
| **Max DD** | Largest peak-to-trough equity drop in $ | Context-dependent. Should be tolerable relative to net profit |
| **Avg Win** | Average dollar profit on winning trades | Should be larger than Avg Loss for a healthy edge |
| **Avg Loss** | Average dollar loss on losing trades | Compare to Avg Win to understand the reward:risk ratio |

### Understanding Win Rate vs Profit Factor

A high win rate alone does NOT guarantee profitability. What matters is the combination:

```
Expectancy = (Win Rate × Avg Win) + ((1 - Win Rate) × Avg Loss)
```

For this strategy at defaults (~85% win rate, avg win ~$338, avg loss ~$690):
```
Expectancy = (0.847 × $338) + (0.153 × -$690)
           = $286 - $106
           = +$180 per trade  ← positive edge
```

**The minimum win rate needed to break even** at given TP:SL ratios:

| TP target | SL (soft) | Minimum win rate to break even |
|-----------|-----------|-------------------------------|
| 150 pts | 200 pts | 57% |
| 100 pts | 200 pts | 67% |
| 150 pts | 150 pts | 50% |

### What the Sharpe Ratio tells you

The Sharpe ratio here is calculated at the **trade level** (not annualized):
- **> 0** — strategy has positive expected return
- **0.3–0.5** — acceptable. Consistent returns relative to variability
- **> 1.0** — excellent consistency
- **< 0** — strategy loses money on average

### Maximum Drawdown

The max drawdown is the largest dollar loss from a peak to the subsequent trough in the equity curve. It answers: *"At the worst point, how much money had I lost from my high-water mark?"*

A max drawdown of $6,300 means that at some point during the backtest, the strategy was $6,300 below its best equity level before recovering.

**Rule of thumb:** Max drawdown should be less than 20–25% of net profit. If net profit is $116,000, a $6,300 drawdown is only 5.4% — very healthy.

---

## 10. Trade Log

The trade log shows every individual trade the strategy executed, sorted chronologically.

### Column reference:

| Column | What it shows | Source field |
|--------|--------------|---|
| **#** | Trade number (1 = first trade of the backtest) | row index |
| **Dir** | Direction — LONG or SHORT | `direction` |
| **Entry time** | 4h-bar timestamp where the signal fired | candle at `entry_idx` |
| **Exit time** | Sub-bar timestamp where the SL/TP confirmed (e.g. `2025-01-03 15:47`) | `exit_time` (ISO sub-bar) |
| **Entry px** | Close of the signal candle — always a real candle value | `entry_signal_price` |
| **Exit px** | Close of the bar that confirmed the exit — always a real candle value | `exit_close` |
| **Pts** | Profit/loss in NQ points (signed) — `(exit_price − avg)` for long, opposite for short | `profit_points` |
| **$** | Dollar P/L = `pts × contracts × point_value` | `profit_dollars` |
| **Reason** | Why the trade exited — see Exit Reasons below | `exit_reason` |
| **Box signal** | Which weekly/monthly level fired the entry + box start date | `box_signal.*` |

**Algorithm-effective prices on hover:** the displayed `Entry px` and `Exit px` are guaranteed to appear in the candle OHLC (so you can verify against the chart). The algorithm-effective prices used for PnL — `avg_entry_price` (weighted leg avg) and `exit_price` (SL/TP line for hard tiers) — surface in the cell tooltip when they differ from the displayed value. Cells with a divergence carry a dotted underline.

### Exit Reasons:

| Reason | Triggered by | Fill price (what `exit_price` records) |
|--------|---|---|
| `TAKE PROFIT` | 1-min high (long) / low (short) reached `avg + tp_target_points` | The target line (synthetic) |
| `TAKE PROFIT (TRAIL)` | 2-min close back through `tp_watch_line` (after the watch armed) | The 2-min close |
| `STOP LOSS (HARD)` | 1-min close past `sl_hard_line` | The hard line (synthetic) |
| `STOP LOSS (SOFT)` | 2-min close past `sl_soft_line` | The 2-min close |

### Reading the trade table:

**Example row** (real trade from January 2025, blueprint Part C Example 1):

```
# 1 │ LONG │ 2025-01-03 10:00 │ 2025-01-03 15:47 │ 21509.25 │ 21497.25 │ -12.0 │ -$24.00 │ STOP LOSS (SOFT) │ W-RL (W) since 2025-01-03
```

- LONG entered at the **2025-01-03 10:00** 4h candle's close (21509.25) — the bar where the weekly RL box traversal fired.
- 2 minutes 47 minutes later, a 2-min close at 21497.25 confirmed below `sl_soft_line` (21499.25) ⇒ SOFT SL fired.
- The `exit_price` (algorithm-effective) is also 21497.25 — SOFT tier fills at the bar close. No divergence ⇒ no dotted underline.
- Net: -12 pts × 1 contract × $2 = **-$24.00**.

In the pre-2026-05-24 4h-only engine, the same trade exited HARD at 21494.25 / -$30 — a check-order artifact. The dual-timeframe engine is the realistic backtest.

**A profitable trade:**
```
# 1  │ LONG   │ 21,269.00  │ 21,419.00  │ +150.0  │ +$300    │ TAKE PROFIT
```
- Trade #1 was a LONG
- Entered at 21,269, exited at 21,419
- Gained 150 points (full TP target hit)
- 1 contract × 150 pts × $2 = **+$300** (only 1 contract filled — legs 2 & 3 didn't trigger)

**Clicking a row** in the trade log immediately activates Replay mode and jumps the chart to that trade's entry candle, so you can visually examine exactly what happened.

---

## 11. Replay Mode

Replay lets you walk through the backtest as if watching it live — candle by candle, trade by trade.

### Activating Replay

After a backtest completes, click the **"Replay"** button that appears in the top header (next to "Run Backtest").

Alternatively, **click any row in the Trade Log** to jump directly to that specific trade.

### The Replay Bar

```
◀  [  Play  ]  ▶     Speed: [1×▼]     +$116,788.00     candle 47 / 2168     2025-01-10 11:00
───────────────────────────────────────────────────────────────────── ●
                                              ↑ scrubber (drag to seek)
```

| Control | Action |
|---------|--------|
| **◀** (Step back) | Go back one candle |
| **Play / Pause** | Auto-advance at the selected speed |
| **▶** (Step forward) | Advance one candle |
| **Speed** | How many candles to advance per 200ms tick (1×=1 candle, 25×=25 candles) |
| **Dollar amount** | Running P&L — cumulative dollars from completed trades up to the current candle |
| **Candle N / Total** | Current position in the dataset |
| **Timestamp** | Date and time of the current candle |
| **Scrubber** | Drag to any point in the timeline |
| **✕ Exit replay** | Return to full view |

### Keyboard Shortcuts (when Replay is active)

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `→` (Right arrow) | Step forward one candle |
| `←` (Left arrow) | Step back one candle |

> Note: Keyboard shortcuts do not activate when focus is inside a text input or dropdown.

### What changes in Replay mode

- **Chart** shows only candles up to the current replay position — future candles are hidden
- **Trade entry markers** (arrows) appear as the replay reaches each entry candle
- **Trade exit markers** (squares with P&L) appear only when the replay reaches the exit candle
- **Trade log rows** dim for trades that haven't happened yet; the currently open trade is highlighted with a blue ring
- **Running P&L** in the ReplayBar shows cumulative profit from completed trades only

### Using Replay effectively

1. **Quick overview:** Set speed to 25× and press Play. Watch the equity build up via the running P&L counter
2. **Study a losing trade:** Click the losing trade row in the Trade Log. The chart jumps to its entry. Step through candle by candle to see exactly why it stopped out
3. **Study a winning trade:** Same — find the biggest winning trade and watch the legs fill sequentially before the TP hit
4. **Find the drawdown period:** Seek the scrubber to where running P&L peaks, then step forward to find the losing streak

---

## 12. Reading & Interpreting Results

### What good backtest results look like

| Metric | Acceptable | Good | Excellent |
|--------|-----------|------|-----------|
| Win rate | > 57% | > 75% | > 85% |
| Profit factor | > 1.2 | > 1.5 | > 2.5 |
| Sharpe | > 0.2 | > 0.5 | > 1.0 |
| Max DD / Net Profit | < 30% | < 15% | < 8% |

**Default settings result (full 2025 dataset, 2168 candles):**

| Metric | Value |
|--------|-------|
| Net Profit | +$116,788 |
| Total Trades | 646 |
| Win Rate | 84.7% |
| Profit Factor | 2.71 |
| Sharpe | 0.34 |
| Max Drawdown | $6,300 |

### Common result patterns and what they mean

**High win rate but mediocre profit factor (<1.5):**
The strategy wins often but loses big when it loses. The losing trades are wiping out many winning trades. → Consider tightening the hard SL or widening the TP target.

**Low win rate (< 60%) but high profit factor (> 2.0):**
The strategy loses often but profits are large when it wins. This is actually viable, but psychologically difficult to trade live — you'd sit through many consecutive losses.

**High drawdown relative to profit:**
The strategy has one or more very bad periods. → Narrow the date range to identify when these occurred, then examine the chart in Replay mode to understand the market condition.

**Very few trades:**
The entry conditions are too strict, or the date range is too short. A robust backtest ideally has 100+ trades to be statistically meaningful.

### Beware of overfitting

If you tune parameters specifically to maximize results on the historical data, the strategy will look great in backtest but likely fail live. Signs of overfitting:
- You've changed many parameters to get "better" numbers
- The strategy performs dramatically differently on different date ranges
- Win rate is > 95% (too good to be real)

A robust strategy should show consistent (if not identical) performance across different sub-periods of the dataset.

---

## 13. Parameter Tuning Guide

### Where to start when results are disappointing

**Problem: Too many stop-loss hits**
→ The market is moving against positions more than 200 pts before reversing
- Try: Increase Leg 2 pullback to 120 pts, Leg 3 to 180 pts (enter later, better average price)
- Try: Widen soft SL to 250 pts
- Try: Reduce Leg 3 contracts to 1 (less exposure when fully loaded)

**Problem: TP targets never hit, trade exits on trail early**
→ The watch threshold (50 pts) is too sensitive
- Try: Raise watch threshold to 80–100 pts
- Try: Lower TP target to 100 pts (price gets there more often)

**Problem: Big candle trades consistently lose**
→ The market isn't reverting after big candles, or is continuing in the same direction
- Try: Uncheck "Reverse direction on big candle" (trade WITH momentum instead)
- Try: Raise the big candle threshold to 500 pts (only trigger on true outliers)

**Problem: Re-entry trades are losing**
→ The strategy re-enters but the trend has already exhausted
- Try: Disable re-entry
- Try: Increase cooldown to 3–5 candles

### Systematic approach to tuning

1. Run the default settings — establish your baseline
2. Change **one parameter at a time**
3. Compare the key metrics: Net Profit, Win Rate, Profit Factor, Max DD
4. Only keep the change if at least 3 of 4 metrics improve
5. Repeat with the next parameter

Changing multiple parameters at once makes it impossible to know which change drove the improvement (or caused a regression).

### Date range testing

Run the same settings on multiple sub-periods:
- Q1 2025 (Jan–Mar): trending market after post-election rally
- Q2 2025 (Apr–Jun): more volatile, tariff-driven swings
- Full year: combined performance

If the strategy works in both sub-periods, it's more likely to be robust. If it only works in one period, be cautious.

---

*This manual covers the dashboard as of Phase F. For technical architecture, see `CLAUDE.md`. For the original strategy playbook, see `Currunt_Strategy_Algo_for_Trading.md`.*
