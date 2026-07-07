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
| 2m | 4714 | 2890 | 189 | $8,587 | $4,695 | 66 | $30,064 | 14% | 3 | 9 | breaker;ema_trend;fvg;ifvg;macd;order_block;sma_trend;structure_trend;vwap |
| 5m | 4376 | 1593 | 72 | $4,702 | $1,630 | 75 | $15,146 | 22% | 2 | 10 | adx;breaker;cisd;ema_trend;fvg;ifvg;keltner;mfi;order_block;sma_trend |
| 15m | 4143 | 2339 | 114 | $2,808 | $939 | 73 | $10,292 | 18% | 5 | 7 | bollinger;cci;fvg;keltner;obv;stochastic;structure_trend |
| 1h | 4474 | 1969 | 422 | $7,370 | $2,870 | 32 | $39,139 | 8% | 5 | 9 | bollinger;breaker;cisd;ema_trend;ifvg;keltner;macd;sma_trend;vwap |
| 2h | 4413 | 2433 | 222 | $7,612 | $1,750 | 68 | $23,391 | 14% | 5 | 8 | bollinger;breaker;cisd;fvg;ifvg;keltner;mfi;vwap |
| 4h | 4649 | 2927 | 333 | $23,537 | $12,474 | 72 | $58,184 | 22% | 2 | 7 | bollinger;breaker;cci;fvg;keltner;rsi;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $8,587  ·  worst DD $4,695  ·  win 66%  ·  full P/L $30,064 (14% DD)

- **Box / risk:** softSL `1.5` · hardSL `4.1` · TP `2.2` · vol-gate `95.6%` · dd-breaker `$290` · cooldown `0` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=14` |
| **ema_trend** | confirm | `fast=50`, `slow=89` |
| **fvg** | both | `lookback=24` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=62`, `slow=176`, `signal=46` |
| **order_block** | both | `swing_l=9` |
| **sma_trend** | confirm | `fast=218`, `slow=116` |
| **structure_trend** | both | `swing_l=1` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $4,702  ·  worst DD $1,630  ·  win 75%  ·  full P/L $15,146 (22% DD)

- **Box / risk:** softSL `2.6` · hardSL `2.8` · TP `1.5` · vol-gate `90.4%` · dd-breaker `$84` · cooldown `0` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=68`, `threshold=9` |
| **breaker** | both | `swing_l=1` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=353`, `slow=237` |
| **fvg** | both | `lookback=47` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=126`, `m=1.7` |
| **mfi** | both | `n=36`, `lower=47`, `upper=96` |
| **order_block** | both | `swing_l=15` |
| **sma_trend** | confirm | `fast=317`, `slow=63` |

### 15m  —  median fold P/L $2,808  ·  worst DD $939  ·  win 73%  ·  full P/L $10,292 (18% DD)

- **Box / risk:** softSL `4.6` · hardSL `4.7` · TP `4.7` · vol-gate `73.0%` · dd-breaker `$623` · cooldown `6` · flip `True` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=103`, `k=1.2` |
| **cci** | both | `n=125`, `threshold=30` |
| **fvg** | both | `lookback=7` |
| **keltner** | confirm | `n=133`, `m=0.6` |
| **obv** | confirm | `slope=137` |
| **stochastic** | both | `n=65`, `d=1`, `lower=2`, `upper=84` |
| **structure_trend** | both | `swing_l=11` |

### 1h  —  median fold P/L $7,370  ·  worst DD $2,870  ·  win 32%  ·  full P/L $39,139 (8% DD)

- **Box / risk:** softSL `2.5` · hardSL `12.9` · TP `17.4` · vol-gate `90.4%` · dd-breaker `$493` · cooldown `0` · flip `True` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=187`, `k=1.8` |
| **breaker** | both | `swing_l=15` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=353`, `slow=189` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=126`, `m=5.0` |
| **macd** | confirm | `fast=27`, `slow=179`, `signal=59` |
| **sma_trend** | confirm | `fast=170`, `slow=85` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $7,612  ·  worst DD $1,750  ·  win 68%  ·  full P/L $23,391 (14% DD)

- **Box / risk:** softSL `7.1` · hardSL `15.1` · TP `16.5` · vol-gate `83.2%` · dd-breaker `$735` · cooldown `1` · flip `False` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=139`, `k=2.6` |
| **breaker** | both | `swing_l=20` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=9` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=102`, `m=2.6` |
| **mfi** | both | `n=14`, `lower=6`, `upper=74` |
| **vwap** | confirm | _(none)_ |

### 4h  —  median fold P/L $23,537  ·  worst DD $12,474  ·  win 72%  ·  full P/L $58,184 (22% DD)

- **Box / risk:** softSL `13.2` · hardSL `40.8` · TP `10.7` · vol-gate `88.9%` · dd-breaker `$276` · cooldown `0` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=114`, `k=2.8` |
| **breaker** | both | `swing_l=8` |
| **cci** | both | `n=129`, `threshold=20` |
| **fvg** | both | `lookback=3` |
| **keltner** | confirm | `n=70`, `m=3.8` |
| **rsi** | both | `n=40`, `lower=22`, `upper=90` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
