---
name: ws-i-results-report
description: WS-I.10 results — per-TF NSGA-III indicator search (feasible Pareto fronts; DD≤25%·P/L constraint) + cross-TF champion combos.
type: report
status: complete
workstream: WS-I
---

# WS-I.10 — All-timeframe indicator search: results

NSGA-III, 3 objectives (median fold P/L ↑, worst-fold maxDD ↓, median win-rate ↑), feasibility = full-period maxDD ≤ 25% of full-period P/L. Search = box params + all 15 indicators on/off + their params + K. Champion per TF = max median fold P/L among feasible.

## Per-timeframe champion (feasible)

| TF | complete | feasible | front | med P/L | worst DD | win% | full P/L | DD%·P/L | K | #ind | indicators |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 4h | 5251 | 4246 | 297 | $33,592 | $13,925 | 71 | $142,229 | 10% | 1 | 8 | bollinger;cci;keltner;mfi;obv;order_block;sma_trend;structure_trend |
| 2h | 4476 | 2810 | 124 | $21,755 | $12,944 | 50 | $92,057 | 18% | 3 | 8 | bollinger;ema_trend;fvg;keltner;obv;rsi;sma_trend;structure_trend |
| 1h | 5017 | 2856 | 144 | $27,776 | $10,984 | 52 | $96,024 | 18% | 4 | 8 | adx;ema_trend;fvg;obv;order_block;rsi;structure_trend;vwap |
| 15m | 3294 | 1718 | 85 | $21,852 | $8,089 | 51 | $77,336 | 10% | 3 | 8 | bollinger;cci;ema_trend;keltner;obv;order_block;sma_trend;stochastic |
| 5m | 4565 | 2779 | 187 | $7,813 | $4,167 | 63 | $24,030 | 19% | 1 | 7 | adx;keltner;macd;mfi;obv;stochastic;vwap |
| 2m | 4037 | 2929 | 156 | $6,287 | $2,275 | 64 | $29,665 | 11% | 1 | 7 | bollinger;ema_trend;fvg;order_block;stochastic;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $33,592  ·  worst DD $13,925  ·  win 71%  ·  full P/L $142,229 (10% DD)

- **Box / risk:** softSL `149.8` · hardSL `167.1` · TP `120.2` · vol-gate `86.9%` · dd-breaker `$4,747` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=45`, `k=4.3` |
| **cci** | both | `n=138`, `threshold=35` |
| **keltner** | confirm | `n=40`, `m=5.0` |
| **mfi** | both | `n=39`, `lower=26`, `upper=87` |
| **obv** | confirm | `slope=18` |
| **order_block** | both | `swing_l=10` |
| **sma_trend** | confirm | `fast=346`, `slow=339` |
| **structure_trend** | both | `swing_l=6` |

### 2h  —  median fold P/L $21,755  ·  worst DD $12,944  ·  win 50%  ·  full P/L $92,057 (18% DD)

- **Box / risk:** softSL `78.5` · hardSL `123.7` · TP `127.0` · vol-gate `84.8%` · dd-breaker `$3,704` · cooldown `1` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=42`, `k=4.3` |
| **ema_trend** | confirm | `fast=22`, `slow=266` |
| **fvg** | both | `lookback=17` |
| **keltner** | confirm | `n=52`, `m=4.9` |
| **obv** | confirm | `slope=88` |
| **rsi** | both | `n=61`, `lower=36`, `upper=87` |
| **sma_trend** | confirm | `fast=362`, `slow=105` |
| **structure_trend** | both | `swing_l=6` |

### 1h  —  median fold P/L $27,776  ·  worst DD $10,984  ·  win 52%  ·  full P/L $96,024 (18% DD)

- **Box / risk:** softSL `49.6` · hardSL `63.3` · TP `93.5` · vol-gate `88.0%` · dd-breaker `$4,513` · cooldown `0` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=8`, `threshold=17` |
| **ema_trend** | confirm | `fast=201`, `slow=87` |
| **fvg** | both | `lookback=24` |
| **obv** | confirm | `slope=88` |
| **order_block** | both | `swing_l=10` |
| **rsi** | both | `n=100`, `lower=42`, `upper=87` |
| **structure_trend** | both | `swing_l=6` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $21,852  ·  worst DD $8,089  ·  win 51%  ·  full P/L $77,336 (10% DD)

- **Box / risk:** softSL `21.6` · hardSL `53.1` · TP `43.3` · vol-gate `92.4%` · dd-breaker `$3,595` · cooldown `0` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=38`, `k=4.5` |
| **cci** | both | `n=138`, `threshold=35` |
| **ema_trend** | confirm | `fast=353`, `slow=389` |
| **keltner** | confirm | `n=41`, `m=4.9` |
| **obv** | confirm | `slope=50` |
| **order_block** | both | `swing_l=3` |
| **sma_trend** | confirm | `fast=192`, `slow=11` |
| **stochastic** | both | `n=6`, `d=7`, `lower=13`, `upper=78` |

### 5m  —  median fold P/L $7,813  ·  worst DD $4,167  ·  win 63%  ·  full P/L $24,030 (19% DD)

- **Box / risk:** softSL `21.9` · hardSL `39.0` · TP `25.4` · vol-gate `75.8%` · dd-breaker `$4,260` · cooldown `20` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=8`, `threshold=15` |
| **keltner** | confirm | `n=44`, `m=3.3` |
| **macd** | confirm | `fast=53`, `slow=43`, `signal=35` |
| **mfi** | both | `n=39`, `lower=28`, `upper=98` |
| **obv** | confirm | `slope=130` |
| **stochastic** | both | `n=6`, `d=14`, `lower=35`, `upper=83` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $6,287  ·  worst DD $2,275  ·  win 64%  ·  full P/L $29,665 (11% DD)

- **Box / risk:** softSL `12.3` · hardSL `30.2` · TP `19.4` · vol-gate `92.8%` · dd-breaker `$4,377` · cooldown `26` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=42`, `k=1.6` |
| **ema_trend** | confirm | `fast=317`, `slow=389` |
| **fvg** | both | `lookback=12` |
| **order_block** | both | `swing_l=19` |
| **stochastic** | both | `n=18`, `d=31`, `lower=38`, `upper=55` |
| **structure_trend** | both | `swing_l=6` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
