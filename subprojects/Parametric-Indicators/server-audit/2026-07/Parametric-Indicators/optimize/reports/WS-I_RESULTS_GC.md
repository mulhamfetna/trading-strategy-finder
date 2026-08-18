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
| 4h | 4842 | 3088 | 333 | $34,963 | $8,133 | 62 | $85,823 | 11% | 1 | 7 | adx;breaker;ema_trend;order_block;sma_trend;structure_trend;vwap |
| 2h | 5000 | 2860 | 275 | $19,863 | $13,728 | 54 | $62,386 | 23% | 2 | 8 | bollinger;ema_trend;fvg;obv;rsi;sma_trend;structure_trend;vwap |
| 1h | 4586 | 2040 | 154 | $26,714 | $13,592 | 50 | $68,013 | 24% | 2 | 6 | cci;cisd;fvg;keltner;sma_trend;structure_trend |
| 15m | 4590 | 1684 | 324 | $4,915 | $1,990 | 70 | $20,080 | 15% | 5 | 9 | bollinger;cci;ema_trend;fvg;keltner;macd;mfi;obv;vwap |
| 5m | 5320 | 3424 | 135 | $8,318 | $2,212 | 48 | $19,965 | 22% | 4 | 12 | bollinger;cci;cisd;ema_trend;fvg;ifvg;keltner;macd;mfi;rsi;sma_trend;vwap |
| 2m | 5195 | 4317 | 162 | $2,809 | $390 | 85 | $14,084 | 10% | 3 | 11 | bollinger;breaker;cisd;ema_trend;macd;mfi;order_block;rsi;sma_trend;stochastic;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $34,963  ·  worst DD $8,133  ·  win 62%  ·  full P/L $85,823 (11% DD)

- **Box / risk:** softSL `14.6536525647` · hardSL `34.3953371455` · TP `19.1547033831` · vol-gate `97.6394402895%` · dd-breaker `$707` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=2`, `threshold=50` |
| **breaker** | both | `swing_l=15` |
| **ema_trend** | confirm | `fast=238`, `slow=380` |
| **order_block** | both | `swing_l=5` |
| **sma_trend** | confirm | `fast=45`, `slow=9` |
| **structure_trend** | both | `swing_l=7` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $19,863  ·  worst DD $13,728  ·  win 54%  ·  full P/L $62,386 (23% DD)

- **Box / risk:** softSL `13.2717343001` · hardSL `29.6632588873` · TP `20.2178646129` · vol-gate `90.0783114707%` · dd-breaker `$247` · cooldown `0` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=35`, `k=2.1` |
| **ema_trend** | confirm | `fast=374`, `slow=34` |
| **fvg** | both | `lookback=8` |
| **obv** | confirm | `slope=30` |
| **rsi** | both | `n=58`, `lower=12`, `upper=64` |
| **sma_trend** | confirm | `fast=108`, `slow=120` |
| **structure_trend** | both | `swing_l=16` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $26,714  ·  worst DD $13,592  ·  win 50%  ·  full P/L $68,013 (24% DD)

- **Box / risk:** softSL `6.46845982106` · hardSL `16.6616089201` · TP `11.9612607804` · vol-gate `97.8168333695%` · dd-breaker `$630` · cooldown `1` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=152`, `threshold=255` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=46` |
| **keltner** | confirm | `n=17`, `m=4.6` |
| **sma_trend** | confirm | `fast=394`, `slow=190` |
| **structure_trend** | both | `swing_l=1` |

### 15m  —  median fold P/L $4,915  ·  worst DD $1,990  ·  win 70%  ·  full P/L $20,080 (15% DD)

- **Box / risk:** softSL `3.4428536933` · hardSL `4.06488999517` · TP `2.66245097505` · vol-gate `85.1859817041%` · dd-breaker `$144` · cooldown `2` · flip `False` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=15`, `k=2.8` |
| **cci** | both | `n=141`, `threshold=160` |
| **ema_trend** | confirm | `fast=205`, `slow=150` |
| **fvg** | both | `lookback=40` |
| **keltner** | confirm | `n=163`, `m=3.3` |
| **macd** | confirm | `fast=9`, `slow=21`, `signal=60` |
| **mfi** | both | `n=7`, `lower=12`, `upper=75` |
| **obv** | confirm | `slope=48` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $8,318  ·  worst DD $2,212  ·  win 48%  ·  full P/L $19,965 (22% DD)

- **Box / risk:** softSL `1.47823753296` · hardSL `5.47933442366` · TP `4.93846273016` · vol-gate `87.6441413802%` · dd-breaker `$380` · cooldown `1` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=19`, `k=4.9` |
| **cci** | both | `n=86`, `threshold=50` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=128`, `slow=223` |
| **fvg** | both | `lookback=45` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=59`, `m=3.8` |
| **macd** | confirm | `fast=52`, `slow=155`, `signal=94` |
| **mfi** | both | `n=10`, `lower=17`, `upper=56` |
| **rsi** | both | `n=17`, `lower=20`, `upper=72` |
| **sma_trend** | confirm | `fast=45`, `slow=222` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $2,809  ·  worst DD $390  ·  win 85%  ·  full P/L $14,084 (10% DD)

- **Box / risk:** softSL `2.43278844373` · hardSL `4.41685430455` · TP `3.89292758641` · vol-gate `54.6557088786%` · dd-breaker `$270` · cooldown `0` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=98`, `k=2.1` |
| **breaker** | both | `swing_l=20` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=305`, `slow=34` |
| **macd** | confirm | `fast=60`, `slow=60`, `signal=17` |
| **mfi** | both | `n=28`, `lower=29`, `upper=53` |
| **order_block** | both | `swing_l=7` |
| **rsi** | both | `n=52`, `lower=40`, `upper=85` |
| **sma_trend** | confirm | `fast=232`, `slow=116` |
| **stochastic** | both | `n=31`, `d=36`, `lower=36`, `upper=94` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
