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
| 4h | 4984 | 2714 | 277 | $24,808 | $3,820 | 66 | $70,496 | 10% | 1 | 10 | breaker;fvg;ifvg;macd;mfi;order_block;rsi;sma_trend;stochastic;vwap |
| 2h | 5185 | 3358 | 129 | $21,683 | $7,616 | 66 | $82,752 | 11% | 5 | 10 | bollinger;cci;ema_trend;fvg;keltner;mfi;obv;order_block;rsi;vwap |
| 1h | 4987 | 3280 | 170 | $21,771 | $7,825 | 54 | $78,823 | 11% | 1 | 10 | bollinger;breaker;cci;cisd;fvg;order_block;rsi;sma_trend;structure_trend;vwap |
| 15m | 4935 | 2121 | 134 | $19,914 | $7,968 | 56 | $35,176 | 21% | 1 | 8 | bollinger;breaker;fvg;keltner;macd;mfi;rsi;structure_trend |
| 5m | 5032 | 3952 | 202 | $5,680 | $1,521 | 75 | $15,216 | 11% | 2 | 9 | cci;cisd;ema_trend;ifvg;macd;obv;order_block;sma_trend;vwap |
| 2m | 5111 | 3476 | 187 | $10,594 | $3,209 | 54 | $31,740 | 12% | 2 | 7 | breaker;cisd;ifvg;mfi;order_block;sma_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $24,808  ·  worst DD $3,820  ·  win 66%  ·  full P/L $70,496 (10% DD)

- **Box / risk:** softSL `65.1485180394` · hardSL `172.921776188` · TP `187.449564024` · vol-gate `89.0517235224%` · dd-breaker `$2,000` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=16` |
| **fvg** | both | `lookback=2` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=18`, `slow=91`, `signal=36` |
| **mfi** | both | `n=47`, `lower=16`, `upper=61` |
| **order_block** | both | `swing_l=15` |
| **rsi** | both | `n=64`, `lower=36`, `upper=99` |
| **sma_trend** | confirm | `fast=12`, `slow=90` |
| **stochastic** | both | `n=87`, `d=30`, `lower=14`, `upper=92` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $21,683  ·  worst DD $7,616  ·  win 66%  ·  full P/L $82,752 (11% DD)

- **Box / risk:** softSL `83.6760646471` · hardSL `182.284425066` · TP `97.0777723889` · vol-gate `85.1859817041%` · dd-breaker `$2,334` · cooldown `1` · flip `False` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=128`, `k=3.4` |
| **cci** | both | `n=8`, `threshold=160` |
| **ema_trend** | confirm | `fast=150`, `slow=150` |
| **fvg** | both | `lookback=19` |
| **keltner** | confirm | `n=48`, `m=3.8` |
| **mfi** | both | `n=46`, `lower=28`, `upper=75` |
| **obv** | confirm | `slope=68` |
| **order_block** | both | `swing_l=2` |
| **rsi** | both | `n=12`, `lower=24`, `upper=71` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $21,771  ·  worst DD $7,825  ·  win 54%  ·  full P/L $78,823 (11% DD)

- **Box / risk:** softSL `59.6962700398` · hardSL `109.737848341` · TP `124.993620625` · vol-gate `79.794730824%` · dd-breaker `$4,726` · cooldown `4` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=133`, `k=3.4` |
| **breaker** | both | `swing_l=3` |
| **cci** | both | `n=125`, `threshold=195` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=14` |
| **order_block** | both | `swing_l=9` |
| **rsi** | both | `n=95`, `lower=17`, `upper=68` |
| **sma_trend** | confirm | `fast=146`, `slow=101` |
| **structure_trend** | both | `swing_l=15` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $19,914  ·  worst DD $7,968  ·  win 56%  ·  full P/L $35,176 (21% DD)

- **Box / risk:** softSL `33.9232848642` · hardSL `69.781123063` · TP `60.0354781994` · vol-gate `99.4309621818%` · dd-breaker `$104` · cooldown `3` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=138`, `k=2.6` |
| **breaker** | both | `swing_l=20` |
| **fvg** | both | `lookback=44` |
| **keltner** | confirm | `n=186`, `m=1.2` |
| **macd** | confirm | `fast=64`, `slow=165`, `signal=39` |
| **mfi** | both | `n=54`, `lower=38`, `upper=72` |
| **rsi** | both | `n=77`, `lower=43`, `upper=85` |
| **structure_trend** | both | `swing_l=6` |

### 5m  —  median fold P/L $5,680  ·  worst DD $1,521  ·  win 75%  ·  full P/L $15,216 (11% DD)

- **Box / risk:** softSL `21.3712196233` · hardSL `26.6433916436` · TP `25.724761594` · vol-gate `30.3758434152%` · dd-breaker `$2,608` · cooldown `19` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=93`, `threshold=35` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=201`, `slow=205` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=18`, `slow=198`, `signal=50` |
| **obv** | confirm | `slope=49` |
| **order_block** | both | `swing_l=8` |
| **sma_trend** | confirm | `fast=88`, `slow=226` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $10,594  ·  worst DD $3,209  ·  win 54%  ·  full P/L $31,740 (12% DD)

- **Box / risk:** softSL `13.2499763856` · hardSL `14.6211989155` · TP `20.1541403219` · vol-gate `76.4624050328%` · dd-breaker `$4,305` · cooldown `9` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=5` |
| **cisd** | both | _(none)_ |
| **ifvg** | both | _(none)_ |
| **mfi** | both | `n=68`, `lower=28`, `upper=69` |
| **order_block** | both | `swing_l=4` |
| **sma_trend** | confirm | `fast=190`, `slow=131` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
