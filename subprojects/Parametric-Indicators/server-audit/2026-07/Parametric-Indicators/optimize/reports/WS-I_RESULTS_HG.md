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
| 4h | 4816 | 3845 | 169 | $7,277 | $2,225 | 71 | $23,970 | 9% | 5 | 8 | bollinger;breaker;ema_trend;ifvg;obv;rsi;stochastic;vwap |
| 2h | 5181 | 3427 | 381 | $11,073 | $4,280 | 34 | $34,405 | 15% | 2 | 6 | bollinger;cci;macd;order_block;rsi;stochastic |
| 1h | 4995 | 2892 | 186 | $5,351 | $2,146 | 68 | $28,475 | 8% | 4 | 10 | breaker;cci;cisd;ema_trend;fvg;macd;mfi;obv;rsi;vwap |
| 15m | 4888 | 2169 | 776 | $1,173 | $877 | 70 | $5,127 | 18% | 4 | 12 | bollinger;breaker;cci;cisd;ema_trend;fvg;keltner;mfi;obv;order_block;sma_trend;stochastic |
| 5m | 5090 | 3134 | 194 | $3,876 | $1,223 | 24 | $22,168 | 6% | 1 | 4 | cci;cisd;obv;sma_trend |
| 2m | 5115 | 2937 | 157 | $5,718 | $2,181 | 27 | $28,349 | 8% | 2 | 8 | bollinger;breaker;ema_trend;keltner;macd;obv;sma_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $7,277  ·  worst DD $2,225  ·  win 71%  ·  full P/L $23,970 (9% DD)

- **Box / risk:** softSL `0.0155494515674` · hardSL `0.0448103535487` · TP `0.0347187000857` · vol-gate `80.2419389875%` · dd-breaker `$0` · cooldown `0` · flip `False` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=86`, `k=3.9` |
| **breaker** | both | `swing_l=7` |
| **ema_trend** | confirm | `fast=335`, `slow=150` |
| **ifvg** | both | _(none)_ |
| **obv** | confirm | `slope=142` |
| **rsi** | both | `n=9`, `lower=11`, `upper=90` |
| **stochastic** | both | `n=36`, `d=43`, `lower=4`, `upper=91` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $11,073  ·  worst DD $4,280  ·  win 34%  ·  full P/L $34,405 (15% DD)

- **Box / risk:** softSL `0.00776857781784` · hardSL `0.00807178163358` · TP `0.0303254743127` · vol-gate `97.2870416517%` · dd-breaker `$1` · cooldown `0` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=32`, `k=3.8` |
| **cci** | both | `n=73`, `threshold=290` |
| **macd** | confirm | `fast=91`, `slow=94`, `signal=91` |
| **order_block** | both | `swing_l=9` |
| **rsi** | both | `n=94`, `lower=15`, `upper=82` |
| **stochastic** | both | `n=19`, `d=3`, `lower=2`, `upper=54` |

### 1h  —  median fold P/L $5,351  ·  worst DD $2,146  ·  win 68%  ·  full P/L $28,475 (8% DD)

- **Box / risk:** softSL `0.0118583907843` · hardSL `0.0141270182439` · TP `0.00979737240531` · vol-gate `97.2870416517%` · dd-breaker `$0` · cooldown `1` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=18` |
| **cci** | both | `n=22`, `threshold=155` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=251`, `slow=301` |
| **fvg** | both | `lookback=48` |
| **macd** | confirm | `fast=6`, `slow=152`, `signal=4` |
| **mfi** | both | `n=30`, `lower=17`, `upper=55` |
| **obv** | confirm | `slope=19` |
| **rsi** | both | `n=100`, `lower=25`, `upper=62` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $1,173  ·  worst DD $877  ·  win 70%  ·  full P/L $5,127 (18% DD)

- **Box / risk:** softSL `0.00711379004125` · hardSL `0.00927756896311` · TP `0.00471696505599` · vol-gate `79.120276351%` · dd-breaker `$0` · cooldown `1` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=9`, `k=2.3` |
| **breaker** | both | `swing_l=1` |
| **cci** | both | `n=23`, `threshold=105` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=252`, `slow=297` |
| **fvg** | both | `lookback=10` |
| **keltner** | confirm | `n=160`, `m=3.9` |
| **mfi** | both | `n=92`, `lower=1`, `upper=91` |
| **obv** | confirm | `slope=35` |
| **order_block** | both | `swing_l=7` |
| **sma_trend** | confirm | `fast=232`, `slow=138` |
| **stochastic** | both | `n=75`, `d=3`, `lower=8`, `upper=95` |

### 5m  —  median fold P/L $3,876  ·  worst DD $1,223  ·  win 24%  ·  full P/L $22,168 (6% DD)

- **Box / risk:** softSL `0.00148985961959` · hardSL `0.00163571231048` · TP `0.00746508334436` · vol-gate `62.7512294753%` · dd-breaker `$0` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=23`, `threshold=125` |
| **cisd** | both | _(none)_ |
| **obv** | confirm | `slope=144` |
| **sma_trend** | confirm | `fast=82`, `slow=138` |

### 2m  —  median fold P/L $5,718  ·  worst DD $2,181  ·  win 27%  ·  full P/L $28,349 (8% DD)

- **Box / risk:** softSL `0.00130224883087` · hardSL `0.00160384910873` · TP `0.00501585465694` · vol-gate `98.6730238066%` · dd-breaker `$0` · cooldown `0` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=10`, `k=1.8` |
| **breaker** | both | `swing_l=7` |
| **ema_trend** | confirm | `fast=77`, `slow=125` |
| **keltner** | confirm | `n=34`, `m=3.8` |
| **macd** | confirm | `fast=81`, `slow=15`, `signal=100` |
| **obv** | confirm | `slope=7` |
| **sma_trend** | confirm | `fast=118`, `slow=134` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
