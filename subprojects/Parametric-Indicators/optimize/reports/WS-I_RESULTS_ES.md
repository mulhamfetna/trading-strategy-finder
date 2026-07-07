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
| 2m | 4679 | 2072 | 131 | $3,832 | $1,448 | 55 | $10,476 | 16% | 3 | 7 | adx;bollinger;breaker;cisd;ema_trend;fvg;obv |
| 5m | 4565 | 3859 | 93 | $1,989 | $560 | 62 | $7,855 | 10% | 3 | 9 | bollinger;breaker;cci;cisd;ema_trend;fvg;order_block;sma_trend;structure_trend |
| 15m | 5096 | 3762 | 361 | $2,892 | $761 | 94 | $11,215 | 7% | 3 | 9 | bollinger;cci;cisd;fvg;ifvg;keltner;macd;mfi;rsi |
| 1h | 5054 | 3614 | 185 | $16,520 | $8,449 | 58 | $61,638 | 14% | 4 | 8 | breaker;fvg;keltner;obv;order_block;rsi;sma_trend;vwap |
| 2h | 4746 | 3248 | 414 | $17,994 | $6,993 | 40 | $72,777 | 10% | 3 | 6 | bollinger;breaker;order_block;rsi;stochastic;vwap |
| 4h | 4513 | 2731 | 222 | $15,080 | $8,493 | 62 | $47,434 | 23% | 3 | 7 | breaker;cisd;ema_trend;keltner;macd;order_block;structure_trend |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $3,832  ·  worst DD $1,448  ·  win 55%  ·  full P/L $10,476 (16% DD)

- **Box / risk:** softSL `3.1` · hardSL `8.4` · TP `5.9` · vol-gate `74.2%` · dd-breaker `$966` · cooldown `19` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=2`, `threshold=32` |
| **bollinger** | veto | `n=91`, `k=1.4` |
| **breaker** | both | `swing_l=5` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=65`, `slow=292` |
| **fvg** | both | `lookback=9` |
| **obv** | confirm | `slope=18` |

### 5m  —  median fold P/L $1,989  ·  worst DD $560  ·  win 62%  ·  full P/L $7,855 (10% DD)

- **Box / risk:** softSL `2.3` · hardSL `4.2` · TP `9.6` · vol-gate `55.9%` · dd-breaker `$883` · cooldown `15` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=9`, `k=0.8` |
| **breaker** | both | `swing_l=20` |
| **cci** | both | `n=73`, `threshold=235` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=58`, `slow=292` |
| **fvg** | both | `lookback=12` |
| **order_block** | both | `swing_l=6` |
| **sma_trend** | confirm | `fast=355`, `slow=212` |
| **structure_trend** | both | `swing_l=8` |

### 15m  —  median fold P/L $2,892  ·  worst DD $761  ·  win 94%  ·  full P/L $11,215 (7% DD)

- **Box / risk:** softSL `9.2` · hardSL `15.2` · TP `2.6` · vol-gate `83.2%` · dd-breaker `$1,231` · cooldown `13` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=187`, `k=4.9` |
| **cci** | both | `n=122`, `threshold=25` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=9` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=114`, `m=2.6` |
| **macd** | confirm | `fast=84`, `slow=85`, `signal=43` |
| **mfi** | both | `n=56`, `lower=47`, `upper=52` |
| **rsi** | both | `n=50`, `lower=21`, `upper=57` |

### 1h  —  median fold P/L $16,520  ·  worst DD $8,449  ·  win 58%  ·  full P/L $61,638 (14% DD)

- **Box / risk:** softSL `15.9` · hardSL `18.5` · TP `30.6` · vol-gate `78.6%` · dd-breaker `$1,352` · cooldown `1` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=14` |
| **fvg** | both | `lookback=23` |
| **keltner** | confirm | `n=185`, `m=3.8` |
| **obv** | confirm | `slope=51` |
| **order_block** | both | `swing_l=19` |
| **rsi** | both | `n=88`, `lower=45`, `upper=80` |
| **sma_trend** | confirm | `fast=142`, `slow=329` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $17,994  ·  worst DD $6,993  ·  win 40%  ·  full P/L $72,777 (10% DD)

- **Box / risk:** softSL `12.4` · hardSL `18.3` · TP `40.0` · vol-gate `92.2%` · dd-breaker `$674` · cooldown `1` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=58`, `k=2.8` |
| **breaker** | both | `swing_l=11` |
| **order_block** | both | `swing_l=14` |
| **rsi** | both | `n=99`, `lower=28`, `upper=90` |
| **stochastic** | both | `n=75`, `d=50`, `lower=20`, `upper=91` |
| **vwap** | confirm | _(none)_ |

### 4h  —  median fold P/L $15,080  ·  worst DD $8,493  ·  win 62%  ·  full P/L $47,434 (23% DD)

- **Box / risk:** softSL `41.5` · hardSL `93.4` · TP `50.4` · vol-gate `79.3%` · dd-breaker `$937` · cooldown `1` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=7` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=377`, `slow=261` |
| **keltner** | confirm | `n=142`, `m=3.2` |
| **macd** | confirm | `fast=27`, `slow=153`, `signal=6` |
| **order_block** | both | `swing_l=18` |
| **structure_trend** | both | `swing_l=10` |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
