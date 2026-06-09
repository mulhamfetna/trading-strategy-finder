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
| 4h | 2292 | 1131 | 79 | $24,253 | $12,067 | 74 | $56,040 | 18% | 1 | 8 | adx;ema_trend;keltner;macd;mfi;order_block;rsi;stochastic |
| 2h | 2294 | 1248 | 96 | $15,132 | $10,835 | 90 | $55,836 | 17% | 1 | 7 | bollinger;ema_trend;macd;mfi;obv;order_block;vwap |
| 1h | 2048 | 942 | 65 | $12,284 | $4,418 | 71 | $33,280 | 24% | 2 | 9 | adx;bollinger;ema_trend;macd;mfi;obv;rsi;structure_trend;vwap |
| 15m | 2604 | 1778 | 159 | $10,538 | $3,223 | 67 | $33,676 | 24% | 1 | 7 | cci;keltner;macd;sma_trend;stochastic;structure_trend;vwap |
| 5m | 2716 | 1736 | 131 | $9,943 | $4,344 | 66 | $36,710 | 11% | 3 | 6 | cci;ema_trend;macd;mfi;order_block;structure_trend |
| 2m | 2594 | 1482 | 250 | $4,474 | $3,848 | 46 | $18,857 | 20% | 2 | 5 | adx;bollinger;ema_trend;obv;order_block |
| 1m | 2458 | 1684 | 343 | $1,876 | $1,167 | 80 | $7,681 | 15% | 1 | 8 | cci;ema_trend;fvg;macd;mfi;obv;stochastic;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $24,253  ·  worst DD $12,067  ·  win 74%  ·  full P/L $56,040 (18% DD)

- **Box / risk:** softSL `139.2` · hardSL `153.1` · TP `183.2` · vol-gate `83.6%` · dd-breaker `$1,305` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=81`, `threshold=8` |
| **ema_trend** | confirm | `fast=244`, `slow=373` |
| **keltner** | confirm | `n=138`, `m=3.5` |
| **macd** | confirm | `fast=14`, `slow=143`, `signal=81` |
| **mfi** | both | `n=39`, `lower=12`, `upper=57` |
| **order_block** | both | `swing_l=18` |
| **rsi** | both | `n=53`, `lower=40`, `upper=65` |
| **stochastic** | both | `n=39`, `d=35`, `lower=23`, `upper=52` |

### 2h  —  median fold P/L $15,132  ·  worst DD $10,835  ·  win 90%  ·  full P/L $55,836 (17% DD)

- **Box / risk:** softSL `82.6` · hardSL `153.7` · TP `36.5` · vol-gate `75.8%` · dd-breaker `$4,511` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=108`, `k=2.1` |
| **ema_trend** | confirm | `fast=92`, `slow=231` |
| **macd** | confirm | `fast=64`, `slow=85`, `signal=93` |
| **mfi** | both | `n=88`, `lower=22`, `upper=76` |
| **obv** | confirm | `slope=50` |
| **order_block** | both | `swing_l=12` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $12,284  ·  worst DD $4,418  ·  win 71%  ·  full P/L $33,280 (24% DD)

- **Box / risk:** softSL `13.0` · hardSL `101.8` · TP `84.5` · vol-gate `56.0%` · dd-breaker `$1,071` · cooldown `1` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=9`, `threshold=8` |
| **bollinger** | veto | `n=17`, `k=1.9` |
| **ema_trend** | confirm | `fast=65`, `slow=89` |
| **macd** | confirm | `fast=49`, `slow=19`, `signal=57` |
| **mfi** | both | `n=93`, `lower=10`, `upper=73` |
| **obv** | confirm | `slope=130` |
| **rsi** | both | `n=100`, `lower=22`, `upper=65` |
| **structure_trend** | both | `swing_l=11` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $10,538  ·  worst DD $3,223  ·  win 67%  ·  full P/L $33,676 (24% DD)

- **Box / risk:** softSL `32.2` · hardSL `36.5` · TP `31.3` · vol-gate `84.8%` · dd-breaker `$3,747` · cooldown `2` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=89`, `threshold=215` |
| **keltner** | confirm | `n=193`, `m=1.1` |
| **macd** | confirm | `fast=5`, `slow=26`, `signal=41` |
| **sma_trend** | confirm | `fast=279`, `slow=34` |
| **stochastic** | both | `n=29`, `d=7`, `lower=22`, `upper=81` |
| **structure_trend** | both | `swing_l=6` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $9,943  ·  worst DD $4,344  ·  win 66%  ·  full P/L $36,710 (11% DD)

- **Box / risk:** softSL `19.5` · hardSL `38.0` · TP `21.4` · vol-gate `91.9%` · dd-breaker `$4,015` · cooldown `23` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=104`, `threshold=20` |
| **ema_trend** | confirm | `fast=22`, `slow=95` |
| **macd** | confirm | `fast=64`, `slow=169`, `signal=7` |
| **mfi** | both | `n=39`, `lower=29`, `upper=71` |
| **order_block** | both | `swing_l=3` |
| **structure_trend** | both | `swing_l=6` |

### 2m  —  median fold P/L $4,474  ·  worst DD $3,848  ·  win 46%  ·  full P/L $18,857 (20% DD)

- **Box / risk:** softSL `12.7` · hardSL `13.8` · TP `21.9` · vol-gate `86.0%` · dd-breaker `$4,316` · cooldown `18` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=61`, `threshold=11` |
| **bollinger** | veto | `n=14`, `k=1.3` |
| **ema_trend** | confirm | `fast=143`, `slow=258` |
| **obv** | confirm | `slope=86` |
| **order_block** | both | `swing_l=14` |

### 1m  —  median fold P/L $1,876  ·  worst DD $1,167  ·  win 80%  ·  full P/L $7,681 (15% DD)

- **Box / risk:** softSL `9.9` · hardSL `23.7` · TP `5.4` · vol-gate `52.2%` · dd-breaker `$1,874` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=108`, `threshold=85` |
| **ema_trend** | confirm | `fast=3`, `slow=311` |
| **fvg** | both | `lookback=20` |
| **macd** | confirm | `fast=38`, `slow=59`, `signal=94` |
| **mfi** | both | `n=91`, `lower=20`, `upper=97` |
| **obv** | confirm | `slope=84` |
| **stochastic** | both | `n=5`, `d=29`, `lower=38`, `upper=91` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
