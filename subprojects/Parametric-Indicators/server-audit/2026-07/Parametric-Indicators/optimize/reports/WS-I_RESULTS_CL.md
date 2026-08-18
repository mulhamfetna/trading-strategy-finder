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
| 4h | 3778 | 2049 | 124 | $7,061 | $1,680 | 56 | $19,242 | 10% | 1 | 6 | bollinger;breaker;cci;cisd;order_block;vwap |
| 2h | 3927 | 2595 | 101 | $1,975 | $631 | 88 | $8,094 | 7% | 5 | 11 | bollinger;breaker;cci;fvg;keltner;macd;mfi;obv;order_block;structure_trend;vwap |
| 1h | 3829 | 2072 | 102 | $5,353 | $2,454 | 51 | $18,178 | 14% | 4 | 7 | breaker;cci;ema_trend;keltner;mfi;rsi;vwap |
| 15m | 4412 | 3224 | 295 | $3,982 | $615 | 51 | $14,001 | 6% | 2 | 7 | bollinger;ema_trend;keltner;macd;obv;order_block;vwap |
| 5m | 4781 | 3422 | 251 | $4,280 | $987 | 31 | $15,238 | 6% | 2 | 7 | bollinger;cci;cisd;macd;order_block;rsi;vwap |
| 2m | 4706 | 2967 | 296 | $3,848 | $563 | 37 | $15,050 | 5% | 2 | 8 | bollinger;cci;cisd;ema_trend;keltner;macd;rsi;sma_trend |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $7,061  ·  worst DD $1,680  ·  win 56%  ·  full P/L $19,242 (10% DD)

- **Box / risk:** softSL `0.233219610742` · hardSL `0.414649771445` · TP `0.374286030449` · vol-gate `96.0260734368%` · dd-breaker `$10` · cooldown `0` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=159`, `k=3.6` |
| **breaker** | both | `swing_l=13` |
| **cci** | both | `n=86`, `threshold=250` |
| **cisd** | both | _(none)_ |
| **order_block** | both | `swing_l=18` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $1,975  ·  worst DD $631  ·  win 88%  ·  full P/L $8,094 (7% DD)

- **Box / risk:** softSL `0.152622308669` · hardSL `0.232381942098` · TP `0.0693917940956` · vol-gate `97.4975443169%` · dd-breaker `$6` · cooldown `0` · flip `True` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=127`, `k=2.4` |
| **breaker** | both | `swing_l=5` |
| **cci** | both | `n=51`, `threshold=45` |
| **fvg** | both | `lookback=14` |
| **keltner** | confirm | `n=34`, `m=3.0` |
| **macd** | confirm | `fast=60`, `slow=177`, `signal=61` |
| **mfi** | both | `n=64`, `lower=19`, `upper=74` |
| **obv** | confirm | `slope=110` |
| **order_block** | both | `swing_l=18` |
| **structure_trend** | both | `swing_l=2` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $5,353  ·  worst DD $2,454  ·  win 51%  ·  full P/L $18,178 (14% DD)

- **Box / risk:** softSL `0.142130218925` · hardSL `0.38763914962` · TP `0.326739872946` · vol-gate `99.4300353312%` · dd-breaker `$9` · cooldown `1` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=8` |
| **cci** | both | `n=181`, `threshold=300` |
| **ema_trend** | confirm | `fast=330`, `slow=159` |
| **keltner** | confirm | `n=66`, `m=4.0` |
| **mfi** | both | `n=11`, `lower=19`, `upper=75` |
| **rsi** | both | `n=100`, `lower=40`, `upper=93` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $3,982  ·  worst DD $615  ·  win 51%  ·  full P/L $14,001 (6% DD)

- **Box / risk:** softSL `0.0406745279927` · hardSL `0.050005794501` · TP `0.0693049289855` · vol-gate `91.1142886446%` · dd-breaker `$2` · cooldown `0` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=122`, `k=2.7` |
| **ema_trend** | confirm | `fast=81`, `slow=161` |
| **keltner** | confirm | `n=66`, `m=4.0` |
| **macd** | confirm | `fast=16`, `slow=106`, `signal=6` |
| **obv** | confirm | `slope=20` |
| **order_block** | both | `swing_l=8` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $4,280  ·  worst DD $987  ·  win 31%  ·  full P/L $15,238 (6% DD)

- **Box / risk:** softSL `0.0188064459616` · hardSL `0.0311772571688` · TP `0.0985112306427` · vol-gate `97.2870416517%` · dd-breaker `$1` · cooldown `1` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=197`, `k=3.9` |
| **cci** | both | `n=7`, `threshold=45` |
| **cisd** | both | _(none)_ |
| **macd** | confirm | `fast=62`, `slow=99`, `signal=2` |
| **order_block** | both | `swing_l=16` |
| **rsi** | both | `n=63`, `lower=14`, `upper=81` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $3,848  ·  worst DD $563  ·  win 37%  ·  full P/L $15,050 (5% DD)

- **Box / risk:** softSL `0.0187814959051` · hardSL `0.0210972583637` · TP `0.0492371842358` · vol-gate `91.9560345627%` · dd-breaker `$6` · cooldown `1` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=118`, `k=3.9` |
| **cci** | both | `n=196`, `threshold=170` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=379`, `slow=49` |
| **keltner** | confirm | `n=5`, `m=4.6` |
| **macd** | confirm | `fast=28`, `slow=151`, `signal=84` |
| **rsi** | both | `n=14`, `lower=1`, `upper=97` |
| **sma_trend** | confirm | `fast=161`, `slow=146` |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
