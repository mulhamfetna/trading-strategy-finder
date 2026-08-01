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
| 4h | 1938 | 1501 | 96 | $14,879 | $6,525 | 62 | $61,524 | 14% | 5 | 9 | breaker;cci;cisd;fvg;keltner;macd;obv;order_block;vwap |
| 2h | 1931 | 1104 | 129 | $19,546 | $5,484 | 58 | $75,357 | 10% | 4 | 7 | breaker;cci;cisd;ema_trend;ifvg;keltner;obv |
| 1h | 2096 | 469 | 170 | $7,639 | $5,775 | 49 | $33,112 | 14% | 3 | 8 | bollinger;breaker;cci;cisd;keltner;macd;obv;stochastic |
| 15m | 2924 | 1168 | 191 | $13,133 | $5,107 | 55 | $59,586 | 8% | 1 | 7 | breaker;ema_trend;mfi;sma_trend;stochastic;structure_trend;vwap |
| 5m | 3806 | 1529 | 155 | $9,515 | $4,227 | 36 | $51,814 | 7% | 1 | 4 | cci;cisd;ema_trend;macd |
| 2m | 4043 | 2752 | 326 | $12,851 | $2,150 | 33 | $71,799 | 4% | 2 | 7 | cisd;ema_trend;keltner;macd;order_block;sma_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $14,879  ·  worst DD $6,525  ·  win 62%  ·  full P/L $61,524 (14% DD)

- **Box / risk:** softSL `0.294065528114` · hardSL `0.557572325593` · TP `0.332215322324` · vol-gate `98.5829989169%` · dd-breaker `$3` · cooldown `1` · flip `False` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=13` |
| **cci** | both | `n=20`, `threshold=50` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=34` |
| **keltner** | confirm | `n=46`, `m=1.3` |
| **macd** | confirm | `fast=11`, `slow=23`, `signal=18` |
| **obv** | confirm | `slope=184` |
| **order_block** | both | `swing_l=19` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $19,546  ·  worst DD $5,484  ·  win 58%  ·  full P/L $75,357 (10% DD)

- **Box / risk:** softSL `0.161513529966` · hardSL `0.201362595532` · TP `0.312732336343` · vol-gate `99.438101923%` · dd-breaker `$6` · cooldown `0` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=7` |
| **cci** | both | `n=166`, `threshold=130` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=157`, `slow=157` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=138`, `m=4.6` |
| **obv** | confirm | `slope=153` |

### 1h  —  median fold P/L $7,639  ·  worst DD $5,775  ·  win 49%  ·  full P/L $33,112 (14% DD)

- **Box / risk:** softSL `0.0778754270554` · hardSL `0.252117954799` · TP `0.163697896774` · vol-gate `97.8718439336%` · dd-breaker `$2` · cooldown `2` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=155`, `k=4.2` |
| **breaker** | both | `swing_l=20` |
| **cci** | both | `n=54`, `threshold=145` |
| **cisd** | both | _(none)_ |
| **keltner** | confirm | `n=113`, `m=3.0` |
| **macd** | confirm | `fast=2`, `slow=188`, `signal=61` |
| **obv** | confirm | `slope=13` |
| **stochastic** | both | `n=82`, `d=28`, `lower=8`, `upper=91` |

### 15m  —  median fold P/L $13,133  ·  worst DD $5,107  ·  win 55%  ·  full P/L $59,586 (8% DD)

- **Box / risk:** softSL `0.0521968852591` · hardSL `0.0677484983679` · TP `0.0848580040871` · vol-gate `99.4721826745%` · dd-breaker `$1` · cooldown `0` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=9` |
| **ema_trend** | confirm | `fast=84`, `slow=233` |
| **mfi** | both | `n=36`, `lower=11`, `upper=54` |
| **sma_trend** | confirm | `fast=253`, `slow=319` |
| **stochastic** | both | `n=97`, `d=43`, `lower=1`, `upper=75` |
| **structure_trend** | both | `swing_l=1` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $9,515  ·  worst DD $4,227  ·  win 36%  ·  full P/L $51,814 (7% DD)

- **Box / risk:** softSL `0.02022305295` · hardSL `0.0268783001306` · TP `0.0588432426995` · vol-gate `99.0806880326%` · dd-breaker `$8` · cooldown `2` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=88`, `threshold=135` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=23`, `slow=3` |
| **macd** | confirm | `fast=10`, `slow=60`, `signal=40` |

### 2m  —  median fold P/L $12,851  ·  worst DD $2,150  ·  win 33%  ·  full P/L $71,799 (4% DD)

- **Box / risk:** softSL `0.0124498981439` · hardSL `0.015176250339` · TP `0.0446940535848` · vol-gate `95.9534307468%` · dd-breaker `$1` · cooldown `0` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=205`, `slow=350` |
| **keltner** | confirm | `n=17`, `m=4.8` |
| **macd** | confirm | `fast=60`, `slow=127`, `signal=83` |
| **order_block** | both | `swing_l=4` |
| **sma_trend** | confirm | `fast=89`, `slow=222` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
