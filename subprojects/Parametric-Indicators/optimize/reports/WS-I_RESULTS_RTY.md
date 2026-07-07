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
| 2m | 4776 | 2288 | 209 | $1,115 | $408 | 68 | $2,082 | 22% | 1 | 6 | breaker;cci;cisd;ema_trend;fvg;rsi |
| 5m | 5097 | 3539 | 206 | $1,147 | $385 | 67 | $2,150 | 18% | 3 | 10 | breaker;cisd;fvg;ifvg;keltner;macd;obv;rsi;sma_trend;stochastic |
| 15m | 4534 | 3046 | 189 | $1,852 | $620 | 86 | $3,980 | 15% | 1 | 11 | adx;bollinger;breaker;cci;ifvg;keltner;macd;mfi;obv;order_block;stochastic |
| 1h | 4567 | 1703 | 365 | $4,706 | $1,951 | 59 | $16,032 | 18% | 1 | 6 | bollinger;breaker;ifvg;macd;mfi;order_block |
| 2h | 4904 | 2970 | 44 | $5,582 | $1,290 | 86 | $18,846 | 10% | 3 | 8 | cisd;keltner;mfi;obv;order_block;sma_trend;structure_trend;vwap |
| 4h | 4319 | 3032 | 293 | $11,908 | $3,210 | 59 | $32,675 | 15% | 1 | 8 | adx;bollinger;cci;cisd;ema_trend;macd;rsi;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $1,115  ·  worst DD $408  ·  win 68%  ·  full P/L $2,082 (22% DD)

- **Box / risk:** softSL `1.2263` · hardSL `3.2276` · TP `1.4643` · vol-gate `40.34%` · dd-breaker `$361` · cooldown `25` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=1` |
| **cci** | both | `n=25`, `threshold=220` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=390`, `slow=383` |
| **fvg** | both | `lookback=15` |
| **rsi** | both | `n=32`, `lower=1`, `upper=69` |

### 5m  —  median fold P/L $1,147  ·  worst DD $385  ·  win 67%  ·  full P/L $2,150 (18% DD)

- **Box / risk:** softSL `1.6824` · hardSL `3.6907` · TP `1.899` · vol-gate `83.59%` · dd-breaker `$350` · cooldown `17` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=7` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=11` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=12`, `m=1.0` |
| **macd** | confirm | `fast=25`, `slow=7`, `signal=64` |
| **obv** | confirm | `slope=47` |
| **rsi** | both | `n=61`, `lower=7`, `upper=57` |
| **sma_trend** | confirm | `fast=82`, `slow=54` |
| **stochastic** | both | `n=99`, `d=35`, `lower=37`, `upper=78` |

### 15m  —  median fold P/L $1,852  ·  worst DD $620  ·  win 86%  ·  full P/L $3,980 (15% DD)

- **Box / risk:** softSL `3.7535` · hardSL `7.8095` · TP `2.2998` · vol-gate `80.88%` · dd-breaker `$349` · cooldown `10` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=25`, `threshold=15` |
| **bollinger** | veto | `n=27`, `k=2.0` |
| **breaker** | both | `swing_l=7` |
| **cci** | both | `n=142`, `threshold=145` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=59`, `m=3.9` |
| **macd** | confirm | `fast=27`, `slow=23`, `signal=6` |
| **mfi** | both | `n=85`, `lower=4`, `upper=84` |
| **obv** | confirm | `slope=103` |
| **order_block** | both | `swing_l=10` |
| **stochastic** | both | `n=35`, `d=9`, `lower=14`, `upper=85` |

### 1h  —  median fold P/L $4,706  ·  worst DD $1,951  ·  win 59%  ·  full P/L $16,032 (18% DD)

- **Box / risk:** softSL `6.8066` · hardSL `10.4993` · TP `10.0828` · vol-gate `97.92%` · dd-breaker `$176` · cooldown `2` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=26`, `k=2.8` |
| **breaker** | both | `swing_l=18` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=7`, `slow=49`, `signal=91` |
| **mfi** | both | `n=9`, `lower=44`, `upper=58` |
| **order_block** | both | `swing_l=11` |

### 2h  —  median fold P/L $5,582  ·  worst DD $1,290  ·  win 86%  ·  full P/L $18,846 (10% DD)

- **Box / risk:** softSL `8.6074` · hardSL `20.1741` · TP `3.1671` · vol-gate `88.91%` · dd-breaker `$402` · cooldown `1` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **keltner** | confirm | `n=193`, `m=1.7` |
| **mfi** | both | `n=39`, `lower=21`, `upper=94` |
| **obv** | confirm | `slope=170` |
| **order_block** | both | `swing_l=15` |
| **sma_trend** | confirm | `fast=277`, `slow=273` |
| **structure_trend** | both | `swing_l=12` |
| **vwap** | confirm | _(none)_ |

### 4h  —  median fold P/L $11,908  ·  worst DD $3,210  ·  win 59%  ·  full P/L $32,675 (15% DD)

- **Box / risk:** softSL `10.3952` · hardSL `26.5238` · TP `23.1537` · vol-gate `77.61%` · dd-breaker `$443` · cooldown `1` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=14`, `threshold=17` |
| **bollinger** | veto | `n=26`, `k=1.9` |
| **cci** | both | `n=28`, `threshold=115` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=176`, `slow=113` |
| **macd** | confirm | `fast=37`, `slow=132`, `signal=62` |
| **rsi** | both | `n=94`, `lower=36`, `upper=91` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
