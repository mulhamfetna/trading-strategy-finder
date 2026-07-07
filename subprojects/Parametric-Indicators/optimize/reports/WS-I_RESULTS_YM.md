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
| 2m | 5268 | 3293 | 237 | $6,095 | $1,979 | 46 | $19,406 | 10% | 1 | 6 | breaker;cci;cisd;ema_trend;structure_trend;vwap |
| 5m | 5335 | 4049 | 228 | $9,896 | $3,700 | 63 | $32,091 | 15% | 3 | 7 | breaker;cisd;fvg;macd;mfi;order_block;sma_trend |
| 15m | 5190 | 3931 | 310 | $5,021 | $1,200 | 60 | $12,762 | 8% | 2 | 7 | bollinger;cci;cisd;ema_trend;fvg;rsi;structure_trend |
| 1h | 4913 | 3479 | 174 | $9,987 | $4,045 | 69 | $28,096 | 14% | 5 | 8 | adx;cisd;fvg;macd;order_block;rsi;sma_trend;structure_trend |
| 2h | 5166 | 3744 | 286 | $9,940 | $2,977 | 67 | $27,718 | 14% | 1 | 7 | breaker;fvg;keltner;macd;order_block;sma_trend;stochastic |
| 4h | 4612 | 3485 | 111 | $10,596 | $2,265 | 77 | $41,542 | 9% | 5 | 10 | bollinger;ema_trend;keltner;macd;obv;rsi;sma_trend;stochastic;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $6,095  ·  worst DD $1,979  ·  win 46%  ·  full P/L $19,406 (10% DD)

- **Box / risk:** softSL `21.9518` · hardSL `29.0894` · TP `46.2427` · vol-gate `74.58%` · dd-breaker `$6,876` · cooldown `27` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=9` |
| **cci** | both | `n=40`, `threshold=260` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=248`, `slow=184` |
| **structure_trend** | both | `swing_l=17` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $9,896  ·  worst DD $3,700  ·  win 63%  ·  full P/L $32,091 (15% DD)

- **Box / risk:** softSL `42.3868` · hardSL `86.6282` · TP `45.9059` · vol-gate `99.61%` · dd-breaker `$6,536` · cooldown `22` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=6` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=39` |
| **macd** | confirm | `fast=85`, `slow=129`, `signal=51` |
| **mfi** | both | `n=39`, `lower=20`, `upper=77` |
| **order_block** | both | `swing_l=6` |
| **sma_trend** | confirm | `fast=111`, `slow=242` |

### 15m  —  median fold P/L $5,021  ·  worst DD $1,200  ·  win 60%  ·  full P/L $12,762 (8% DD)

- **Box / risk:** softSL `49.6112` · hardSL `142.9055` · TP `110.1363` · vol-gate `52.08%` · dd-breaker `$7,047` · cooldown `14` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=31`, `k=3.4` |
| **cci** | both | `n=151`, `threshold=235` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=58`, `slow=2` |
| **fvg** | both | `lookback=12` |
| **rsi** | both | `n=3`, `lower=13`, `upper=91` |
| **structure_trend** | both | `swing_l=17` |

### 1h  —  median fold P/L $9,987  ·  worst DD $4,045  ·  win 69%  ·  full P/L $28,096 (14% DD)

- **Box / risk:** softSL `117.2494` · hardSL `213.0482` · TP `179.0803` · vol-gate `82.34%` · dd-breaker `$5,290` · cooldown `5` · flip `True` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=17`, `threshold=15` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=6` |
| **macd** | confirm | `fast=3`, `slow=104`, `signal=6` |
| **order_block** | both | `swing_l=10` |
| **rsi** | both | `n=49`, `lower=2`, `upper=57` |
| **sma_trend** | confirm | `fast=44`, `slow=329` |
| **structure_trend** | both | `swing_l=18` |

### 2h  —  median fold P/L $9,940  ·  worst DD $2,977  ·  win 67%  ·  full P/L $27,718 (14% DD)

- **Box / risk:** softSL `188.1248` · hardSL `329.6387` · TP `246.5115` · vol-gate `62.7%` · dd-breaker `$6,667` · cooldown `4` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=4` |
| **fvg** | both | `lookback=24` |
| **keltner** | confirm | `n=75`, `m=1.0` |
| **macd** | confirm | `fast=27`, `slow=153`, `signal=43` |
| **order_block** | both | `swing_l=10` |
| **sma_trend** | confirm | `fast=218`, `slow=42` |
| **stochastic** | both | `n=35`, `d=23`, `lower=1`, `upper=94` |

### 4h  —  median fold P/L $10,596  ·  worst DD $2,265  ·  win 77%  ·  full P/L $41,542 (9% DD)

- **Box / risk:** softSL `276.1331` · hardSL `425.1374` · TP `367.1723` · vol-gate `78.63%` · dd-breaker `$6,667` · cooldown `2` · flip `True` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=114`, `k=4.4` |
| **ema_trend** | confirm | `fast=148`, `slow=292` |
| **keltner** | confirm | `n=12`, `m=1.0` |
| **macd** | confirm | `fast=33`, `slow=153`, `signal=6` |
| **obv** | confirm | `slope=22` |
| **rsi** | both | `n=61`, `lower=1`, `upper=53` |
| **sma_trend** | confirm | `fast=188`, `slow=352` |
| **stochastic** | both | `n=49`, `d=29`, `lower=17`, `upper=78` |
| **structure_trend** | both | `swing_l=10` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
