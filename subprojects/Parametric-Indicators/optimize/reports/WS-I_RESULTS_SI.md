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
| 2m | 4748 | 2679 | 412 | $7,005 | $3,308 | 46 | $32,642 | 9% | 1 | 5 | bollinger;breaker;keltner;order_block;structure_trend |
| 5m | 3136 | 1729 | 164 | $6,908 | $4,170 | 55 | $27,427 | 15% | 2 | 8 | bollinger;cci;fvg;mfi;obv;order_block;sma_trend;vwap |
| 15m | 1644 | 733 | 20 | $599 | $1,263 | 88 | $2,630 | 17% | 1 | 10 | adx;bollinger;cci;cisd;fvg;keltner;macd;obv;order_block;structure_trend |
| 1h | 1049 | 511 | 8 | $2,394 | $900 | 90 | $7,760 | 14% | 2 | 8 | bollinger;fvg;macd;obv;order_block;rsi;stochastic;vwap |
| 2h | 1167 | 783 | 25 | $5,779 | $6,343 | 70 | $31,428 | 20% | 2 | 7 | cci;cisd;ema_trend;mfi;order_block;rsi;vwap |
| 4h | 48 | 4 | 4 | $5,778 | $9,338 | 58 | $24,671 | 20% | 1 | 9 | breaker;cci;ifvg;mfi;obv;rsi;sma_trend;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $7,005  ·  worst DD $3,308  ·  win 46%  ·  full P/L $32,642 (9% DD)

- **Box / risk:** softSL `0.0` · hardSL `0.0` · TP `0.0` · vol-gate `97.1%` · dd-breaker `$7` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=145`, `k=2.0` |
| **breaker** | both | `swing_l=19` |
| **keltner** | confirm | `n=167`, `m=1.7` |
| **order_block** | both | `swing_l=7` |
| **structure_trend** | both | `swing_l=16` |

### 5m  —  median fold P/L $6,908  ·  worst DD $4,170  ·  win 55%  ·  full P/L $27,427 (15% DD)

- **Box / risk:** softSL `0.0` · hardSL `0.1` · TP `0.1` · vol-gate `92.7%` · dd-breaker `$3` · cooldown `0` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=135`, `k=2.5` |
| **cci** | both | `n=135`, `threshold=145` |
| **fvg** | both | `lookback=2` |
| **mfi** | both | `n=25`, `lower=40`, `upper=58` |
| **obv** | confirm | `slope=57` |
| **order_block** | both | `swing_l=15` |
| **sma_trend** | confirm | `fast=81`, `slow=8` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $599  ·  worst DD $1,263  ·  win 88%  ·  full P/L $2,630 (17% DD)

- **Box / risk:** softSL `0.0` · hardSL `0.1` · TP `0.0` · vol-gate `92.7%` · dd-breaker `$8` · cooldown `8` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=24`, `threshold=10` |
| **bollinger** | veto | `n=67`, `k=1.0` |
| **cci** | both | `n=164`, `threshold=160` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=37` |
| **keltner** | confirm | `n=58`, `m=1.5` |
| **macd** | confirm | `fast=31`, `slow=33`, `signal=36` |
| **obv** | confirm | `slope=12` |
| **order_block** | both | `swing_l=6` |
| **structure_trend** | both | `swing_l=12` |

### 1h  —  median fold P/L $2,394  ·  worst DD $900  ·  win 90%  ·  full P/L $7,760 (14% DD)

- **Box / risk:** softSL `0.0` · hardSL `0.2` · TP `0.0` · vol-gate `97.8%` · dd-breaker `$3` · cooldown `2` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=77`, `k=2.8` |
| **fvg** | both | `lookback=50` |
| **macd** | confirm | `fast=7`, `slow=161`, `signal=91` |
| **obv** | confirm | `slope=130` |
| **order_block** | both | `swing_l=20` |
| **rsi** | both | `n=81`, `lower=41`, `upper=53` |
| **stochastic** | both | `n=64`, `d=15`, `lower=42`, `upper=59` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $5,779  ·  worst DD $6,343  ·  win 70%  ·  full P/L $31,428 (20% DD)

- **Box / risk:** softSL `0.2` · hardSL `0.2` · TP `0.1` · vol-gate `97.0%` · dd-breaker `$3` · cooldown `1` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=35`, `threshold=145` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=283`, `slow=398` |
| **mfi** | both | `n=59`, `lower=21`, `upper=71` |
| **order_block** | both | `swing_l=8` |
| **rsi** | both | `n=26`, `lower=30`, `upper=83` |
| **vwap** | confirm | _(none)_ |

### 4h  —  median fold P/L $5,778  ·  worst DD $9,338  ·  win 58%  ·  full P/L $24,671 (20% DD)

- **Box / risk:** softSL `0.3` · hardSL `0.6` · TP `0.3` · vol-gate `97.9%` · dd-breaker `$4` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=18` |
| **cci** | both | `n=129`, `threshold=30` |
| **ifvg** | both | _(none)_ |
| **mfi** | both | `n=24`, `lower=16`, `upper=65` |
| **obv** | confirm | `slope=97` |
| **rsi** | both | `n=76`, `lower=45`, `upper=89` |
| **sma_trend** | confirm | `fast=177`, `slow=93` |
| **structure_trend** | both | `swing_l=5` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
