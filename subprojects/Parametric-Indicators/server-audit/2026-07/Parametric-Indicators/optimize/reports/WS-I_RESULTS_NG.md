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
| 4h | 5389 | 4351 | 213 | $6,478 | $1,336 | 63 | $21,912 | 10% | 4 | 8 | cisd;ema_trend;keltner;macd;order_block;rsi;sma_trend;vwap |
| 2h | 5221 | 4257 | 354 | $5,471 | $1,456 | 53 | $21,782 | 9% | 3 | 6 | breaker;cci;keltner;rsi;sma_trend;vwap |
| 1h | 4924 | 2494 | 224 | $2,723 | $1,248 | 71 | $7,534 | 20% | 2 | 5 | bollinger;keltner;macd;rsi;vwap |
| 15m | 4199 | 2420 | 140 | $296 | $150 | 82 | $842 | 23% | 1 | 9 | bollinger;ema_trend;ifvg;keltner;mfi;order_block;sma_trend;stochastic;structure_trend |
| 5m | 5384 | 4175 | 324 | $7,518 | $262 | 32 | $38,079 | 1% | 1 | 6 | cisd;ema_trend;keltner;macd;obv;vwap |
| 2m | 5454 | 4726 | 457 | $6,158 | $575 | 49 | $30,179 | 2% | 1 | 6 | cisd;ema_trend;keltner;macd;obv;sma_trend |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $6,478  ·  worst DD $1,336  ·  win 63%  ·  full P/L $21,912 (10% DD)

- **Box / risk:** softSL `0.0197679300643` · hardSL `0.021086669492` · TP `0.0215009498406` · vol-gate `93.7980514034%` · dd-breaker `$0` · cooldown `1` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=352`, `slow=313` |
| **keltner** | confirm | `n=18`, `m=3.9` |
| **macd** | confirm | `fast=51`, `slow=160`, `signal=93` |
| **order_block** | both | `swing_l=20` |
| **rsi** | both | `n=55`, `lower=25`, `upper=69` |
| **sma_trend** | confirm | `fast=337`, `slow=258` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $5,471  ·  worst DD $1,456  ·  win 53%  ·  full P/L $21,782 (9% DD)

- **Box / risk:** softSL `0.0109627791392` · hardSL `0.0241207798867` · TP `0.0199857236306` · vol-gate `97.5201135014%` · dd-breaker `$1` · cooldown `1` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=15` |
| **cci** | both | `n=199`, `threshold=280` |
| **keltner** | confirm | `n=160`, `m=1.6` |
| **rsi** | both | `n=14`, `lower=29`, `upper=95` |
| **sma_trend** | confirm | `fast=128`, `slow=396` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $2,723  ·  worst DD $1,248  ·  win 71%  ·  full P/L $7,534 (20% DD)

- **Box / risk:** softSL `0.00826317992642` · hardSL `0.0170557156119` · TP `0.0069261396679` · vol-gate `67.8051512684%` · dd-breaker `$1` · cooldown `1` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=118`, `k=4.5` |
| **keltner** | confirm | `n=154`, `m=0.8` |
| **macd** | confirm | `fast=6`, `slow=149`, `signal=30` |
| **rsi** | both | `n=7`, `lower=15`, `upper=86` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $296  ·  worst DD $150  ·  win 82%  ·  full P/L $842 (23% DD)

- **Box / risk:** softSL `0.00326460174124` · hardSL `0.00782630640074` · TP `0.00284157741332` · vol-gate `75.74030873%` · dd-breaker `$0` · cooldown `2` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=9`, `k=5.0` |
| **ema_trend** | confirm | `fast=269`, `slow=64` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=65`, `m=3.8` |
| **mfi** | both | `n=41`, `lower=44`, `upper=88` |
| **order_block** | both | `swing_l=13` |
| **sma_trend** | confirm | `fast=232`, `slow=8` |
| **stochastic** | both | `n=67`, `d=46`, `lower=32`, `upper=82` |
| **structure_trend** | both | `swing_l=19` |

### 5m  —  median fold P/L $7,518  ·  worst DD $262  ·  win 32%  ·  full P/L $38,079 (1% DD)

- **Box / risk:** softSL `0.000809191240378` · hardSL `0.00101726377925` · TP `0.00392588155242` · vol-gate `98.8021066544%` · dd-breaker `$0` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=303`, `slow=125` |
| **keltner** | confirm | `n=4`, `m=1.0` |
| **macd** | confirm | `fast=16`, `slow=28`, `signal=25` |
| **obv** | confirm | `slope=183` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $6,158  ·  worst DD $575  ·  win 49%  ·  full P/L $30,179 (2% DD)

- **Box / risk:** softSL `0.00174300983321` · hardSL `0.00205447444533` · TP `0.00292889025795` · vol-gate `95.9254964029%` · dd-breaker `$0` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=304`, `slow=139` |
| **keltner** | confirm | `n=105`, `m=2.8` |
| **macd** | confirm | `fast=93`, `slow=56`, `signal=8` |
| **obv** | confirm | `slope=63` |
| **sma_trend** | confirm | `fast=47`, `slow=350` |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
