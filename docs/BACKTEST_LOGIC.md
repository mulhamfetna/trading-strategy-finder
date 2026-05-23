# Backtest Logic — 1-1-2 Scaling Strategy

## 1. Data Pipeline

```
NQ_4h.csv  →  load_data()  →  filter_by_date_range()  →  reverse to ascending order  →  ScalingStrategy.backtest()
```

The CSV loads **newest-first** (that is how it is exported from the trading platform). The API reverses it to ascending order so candle index 0 is the oldest and index N-1 is the most recent. The strategy then walks through candles in forward time order, exactly as a live system would.

---

## 2. The Main Loop — One Candle at a Time

For every 4-hour candle the engine reads four values:
- `open`, `high`, `low`, `close` of the current candle
- `prev_close` — the close of the previous candle (or `open` if this is candle 0)

Each candle goes through four sequential phases:

```
1. EXIT CHECK     → if in a position, did this candle trigger an exit?
2. ENTRY / LEG-IN → if flat, should we open? if in a position, should we add legs?
3. ARM WATCH      → if in a position, should we start tracking the trailing TP?
4. PROGRESS       → emit a progress event to the frontend (SSE stream)
```

---

## 3. Entry: How a Trade Opens

### Standard trigger (every normal candle)

```
close > prev_close  →  LONG
close < prev_close  →  SHORT
close == prev_close →  no trade (flat candle, skip)
```

No RSI, no EMA, no volume filter. The direction is purely whether this 4-hour candle closed higher or lower than the previous one.

When a direction is confirmed, **Leg 1 fills immediately** at `prev_close` (called the *base level*) with 1 contract.

### Big-candle exception (|close − open| > 400 points)

A candle that moves more than 400 points in one bar is a volatility event — price is unlikely to retrace 100–150 points to allow scaling. The rules flip:

- Detect direction from the candle itself (`close > open` = green bar)
- **Reverse** that direction (green bar → enter SHORT; red bar → enter LONG) — fading the overextended move
- Enter all 4 contracts at once at the close
- Skip Legs 2 and 3 entirely

---

## 4. Scaling In: How Legs 2 and 3 Fill

After Leg 1 is open, the strategy watches the candle's intraday **Low** (for longs) or **High** (for shorts) on every subsequent candle. No new directional signal is required — filling is purely price-based.

**For a LONG position:**
```
Leg 1 fills at:  base_level                              (prev_close at entry)  —  1 contract
Leg 2 fills when: candle Low  ≤ base_level − 100 pts    —  adds 1 contract at that price
Leg 3 fills when: candle Low  ≤ base_level − 150 pts    —  adds 2 contracts at that price
```

**For a SHORT position (mirror image):**
```
Leg 2 fills when: candle High ≥ base_level + 100 pts
Leg 3 fills when: candle High ≥ base_level + 150 pts
```

Both legs can fill on the **same candle** if the candle's range is wide enough. Once all 3 legs are filled the position holds 4 contracts total.

### Average entry price

The weighted average across all filled legs:

```
avg = (leg1_price × 1 + leg2_price × 1 + leg3_price × 2) / 4
```

If all three legs fill at defaults (base, base−100, base−150), the average works out to `base − 75 pts` — already 75 points in-the-money from the first fill's perspective.

---

## 5. Exits: Four Ways a Trade Closes

All exit checks compare against `avg` — the weighted average entry price — not against any individual leg's price.

### Exit 1 — Hard Stop Loss (disaster protection)

```
LONG:  candle Close ≤ avg − 300 pts  →  exit at avg − 300
SHORT: candle Close ≥ avg + 300 pts  →  exit at avg + 300
```

Uses the 4h **close**, not a wick. Models the playbook's "5-second candle close beyond" rule.

### Exit 2 — Soft Stop Loss (normal risk management)

```
LONG:  candle Close ≤ avg − 200 pts  →  exit at avg − 200
SHORT: candle Close ≥ avg + 200 pts  →  exit at avg + 200
```

Also uses the close. Models the playbook's "2-minute candle close beyond" rule.

Hard SL is checked before soft SL — if both fire on the same candle, hard SL wins.

### Exit 3 — Hard Take Profit

```
LONG:  candle High ≥ avg + 150 pts  →  exit at avg + 150
SHORT: candle Low  ≤ avg − 150 pts  →  exit at avg − 150
```

Uses the intraday **high/low** (not the close) because TP is a limit order that fills the moment price touches it.

### Exit 4 — Trailing Take Profit (watch mode)

A two-step mechanism:

1. **Arm**: once the candle **close** (not a wick) moves 50 pts past avg in the right direction, `watch_armed = True`
2. **Fire**: once armed, if the close then **pulls back** below the +50 threshold, exit at the current close

```
LONG example:
  candle close ≥ avg + 50  →  watch_armed = True
  next candle: close < avg + 50  →  TAKE PROFIT (TRAIL) at close
```

This exits earlier than +150 but still profitably. Models the playbook's "2-minute candle close beyond +50" rule.

### Priority order within a candle

```
Hard SL  →  Soft SL  →  Hard TP  →  Trailing TP
```

Only one exit fires per candle.

---

## 6. Re-Entry After a Profitable Exit

Only triggers when:
- `reentry_enabled = True`, AND
- The exit reason was `TAKE PROFIT` or `TAKE PROFIT (TRAIL)` (not a stop loss)

When those conditions are met:
1. The strategy saves `cooldown_direction` and `cooldown_base_level` from the closed trade
2. A cooldown of 1 candle (configurable) starts — no new entries during cooldown
3. After cooldown expires, the normal `close > prev_close` / `close < prev_close` trigger resumes

The re-entry is a completely fresh position with the same leg structure, meant to catch a second wave of the same trend after a temporary pullback. If the exit was a **stop loss**, no re-entry is armed.

---

## 7. P&L Calculation

```
profit_points  =  exit_price − avg_entry_price    (LONG)
profit_points  =  avg_entry_price − exit_price    (SHORT)

profit_dollars =  profit_points × contracts × $2.00
```

`$2.00` is the NQ Micro futures point value (MNQ = $2 per point per contract). A full 4-contract position winning 150 points earns `150 × 4 × $2 = $1,200`.

---

## 8. What the Settings Panel Controls

| Setting | Destination | Effect |
|---|---|---|
| Leg 1 / 2 / 3 contracts | `ScalingParams` → backend | Contracts filled at each level |
| Leg 2 / 3 pullback pts | `ScalingParams` → backend | How deep a retrace before adding |
| Big candle threshold | `ScalingParams` → backend | When the reversal exception fires |
| TP target / watch threshold | `ScalingParams` → backend | Where hard TP and trailing TP arm / fire |
| Soft / Hard SL | `ScalingParams` → backend | Where the two stop lines sit |
| Re-entry / cooldown | `ScalingParams` → backend | Whether and how fast to re-enter |
| Start / end date | CSV filter | Which candles are included |
| EMA, RSI, Volume toggles | Frontend display only | Chart overlays — no effect on trades |

---

## 9. Known Gaps vs the Live System

| Live rule | Backtest approximation |
|---|---|
| 15-second confirmation for Entry 1 (3 candles) | Every 4h close is treated as already confirmed |
| 1-second confirmation for Legs 2 & 3 | Leg fills the moment the candle's range touches the pullback price |
| 2-minute soft SL close | 4h candle close beyond the soft line |
| 5-second hard SL close | 4h candle close beyond the hard line |
| Sequential leg fills within a bar | Both legs 2 and 3 can fill on the same 4h candle |
| Slippage and commissions | Not modelled in the scaling engine |

---

## 10. Source Files

| File | Role |
|---|---|
| `src/strategy/scaling_strategy.py` | Core simulation loop, all entry/exit/leg logic |
| `src/api/app.py` | FastAPI endpoint wiring data load → strategy → SSE stream |
| `src/api/schemas.py` | Pydantic contracts between frontend and backend |
| `Currunt_Strategy_Algo_for_Trading.md` | Original plain-English strategy playbook |
