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
| 2m | 4419 | 2133 | 187 | $1,997 | $831 | 80 | $8,476 | 10% | 3 | 6 | bollinger;ifvg;macd;mfi;order_block;sma_trend |
| 5m | 4975 | 2456 | 145 | $2,053 | $1,080 | 86 | $8,098 | 22% | 2 | 8 | adx;bollinger;breaker;cci;ema_trend;obv;order_block;stochastic |
| 15m | 4630 | 1698 | 1241 | $7,618 | $7,091 | 77 | $16,221 | 25% | 1 | 8 | bollinger;cci;cisd;fvg;keltner;macd;order_block;sma_trend |
| 1h | 3969 | 1946 | 46 | $19,216 | $5,318 | 53 | $57,242 | 10% | 3 | 8 | breaker;cci;cisd;keltner;macd;mfi;rsi;structure_trend |
| 2h | 4610 | 2959 | 61 | $10,175 | $2,482 | 93 | $26,519 | 16% | 2 | 10 | cci;cisd;ema_trend;fvg;keltner;macd;mfi;obv;sma_trend;structure_trend |
| 4h | 4476 | 3860 | 101 | $22,007 | $13,033 | 74 | $97,889 | 8% | 2 | 7 | bollinger;fvg;keltner;macd;order_block;rsi;structure_trend |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $1,997  ·  worst DD $831  ·  win 80%  ·  full P/L $8,476 (10% DD)

- **Box / risk:** softSL `2.0` · hardSL `4.3` · TP `2.2` · vol-gate `46.6%` · dd-breaker `$735` · cooldown `10` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=177`, `k=4.5` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=48`, `slow=23`, `signal=73` |
| **mfi** | both | `n=85`, `lower=4`, `upper=63` |
| **order_block** | both | `swing_l=5` |
| **sma_trend** | confirm | `fast=142`, `slow=41` |

### 5m  —  median fold P/L $2,053  ·  worst DD $1,080  ·  win 86%  ·  full P/L $8,098 (22% DD)

- **Box / risk:** softSL `3.6` · hardSL `6.2` · TP `1.4` · vol-gate `93.7%` · dd-breaker `$679` · cooldown `15` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=89`, `threshold=10` |
| **bollinger** | veto | `n=171`, `k=1.0` |
| **breaker** | both | `swing_l=19` |
| **cci** | both | `n=49`, `threshold=250` |
| **ema_trend** | confirm | `fast=219`, `slow=333` |
| **obv** | confirm | `slope=118` |
| **order_block** | both | `swing_l=6` |
| **stochastic** | both | `n=99`, `d=35`, `lower=14`, `upper=85` |

### 15m  —  median fold P/L $7,618  ·  worst DD $7,091  ·  win 77%  ·  full P/L $16,221 (25% DD)

- **Box / risk:** softSL `4.0` · hardSL `8.2` · TP `2.4` · vol-gate `93.7%` · dd-breaker `$679` · cooldown `5` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=58`, `k=3.0` |
| **cci** | both | `n=164`, `threshold=250` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=8` |
| **keltner** | confirm | `n=58`, `m=1.7` |
| **macd** | confirm | `fast=25`, `slow=126`, `signal=79` |
| **order_block** | both | `swing_l=20` |
| **sma_trend** | confirm | `fast=61`, `slow=362` |

### 1h  —  median fold P/L $19,216  ·  worst DD $5,318  ·  win 53%  ·  full P/L $57,242 (10% DD)

- **Box / risk:** softSL `7.6` · hardSL `19.6` · TP `19.5` · vol-gate `83.5%` · dd-breaker `$805` · cooldown `1` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=8` |
| **cci** | both | `n=183`, `threshold=210` |
| **cisd** | both | _(none)_ |
| **keltner** | confirm | `n=64`, `m=4.7` |
| **macd** | confirm | `fast=66`, `slow=123`, `signal=69` |
| **mfi** | both | `n=40`, `lower=2`, `upper=88` |
| **rsi** | both | `n=29`, `lower=3`, `upper=75` |
| **structure_trend** | both | `swing_l=20` |

### 2h  —  median fold P/L $10,175  ·  worst DD $2,482  ·  win 93%  ·  full P/L $26,519 (16% DD)

- **Box / risk:** softSL `15.0` · hardSL `34.5` · TP `3.5` · vol-gate `97.9%` · dd-breaker `$558` · cooldown `2` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=51`, `threshold=145` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=230`, `slow=231` |
| **fvg** | both | `lookback=11` |
| **keltner** | confirm | `n=15`, `m=1.3` |
| **macd** | confirm | `fast=27`, `slow=163`, `signal=72` |
| **mfi** | both | `n=56`, `lower=41`, `upper=78` |
| **obv** | confirm | `slope=149` |
| **sma_trend** | confirm | `fast=372`, `slow=326` |
| **structure_trend** | both | `swing_l=20` |

### 4h  —  median fold P/L $22,007  ·  worst DD $13,033  ·  win 74%  ·  full P/L $97,889 (8% DD)

- **Box / risk:** softSL `23.5` · hardSL `54.5` · TP `23.9` · vol-gate `88.9%` · dd-breaker `$129` · cooldown `1` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=72`, `k=2.8` |
| **fvg** | both | `lookback=45` |
| **keltner** | confirm | `n=118`, `m=2.0` |
| **macd** | confirm | `fast=81`, `slow=50`, `signal=53` |
| **order_block** | both | `swing_l=13` |
| **rsi** | both | `n=30`, `lower=13`, `upper=73` |
| **structure_trend** | both | `swing_l=15` |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
