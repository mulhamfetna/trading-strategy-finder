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
| 4h | 4743 | 3792 | 56 | $21,702 | $4,550 | 70 | $71,321 | 6% | 4 | 9 | bollinger;breaker;ema_trend;macd;mfi;obv;sma_trend;structure_trend;vwap |
| 2h | 4794 | 3140 | 302 | $17,214 | $11,225 | 53 | $68,109 | 13% | 3 | 7 | bollinger;breaker;ifvg;keltner;macd;obv;vwap |
| 1h | 4739 | 2690 | 142 | $19,295 | $4,989 | 52 | $61,507 | 15% | 2 | 8 | breaker;cci;cisd;ema_trend;fvg;keltner;rsi;vwap |
| 15m | 5114 | 3048 | 222 | $9,948 | $2,275 | 63 | $25,337 | 20% | 4 | 5 | breaker;ema_trend;macd;mfi;rsi |
| 5m | 4857 | 3842 | 103 | $2,536 | $716 | 92 | $9,093 | 9% | 4 | 11 | bollinger;breaker;cisd;ema_trend;fvg;keltner;macd;rsi;sma_trend;structure_trend;vwap |
| 2m | 4723 | 3054 | 127 | $1,767 | $433 | 72 | $5,967 | 7% | 4 | 10 | bollinger;breaker;cci;ema_trend;fvg;keltner;obv;stochastic;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $21,702  ·  worst DD $4,550  ·  win 70%  ·  full P/L $71,321 (6% DD)

- **Box / risk:** softSL `37.347425816` · hardSL `87.6009031524` · TP `49.7543855721` · vol-gate `77.4293306865%` · dd-breaker `$1,010` · cooldown `0` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=133`, `k=4.2` |
| **breaker** | both | `swing_l=2` |
| **ema_trend** | confirm | `fast=338`, `slow=109` |
| **macd** | confirm | `fast=80`, `slow=62`, `signal=19` |
| **mfi** | both | `n=61`, `lower=32`, `upper=90` |
| **obv** | confirm | `slope=25` |
| **sma_trend** | confirm | `fast=344`, `slow=328` |
| **structure_trend** | both | `swing_l=13` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $17,214  ·  worst DD $11,225  ·  win 53%  ·  full P/L $68,109 (13% DD)

- **Box / risk:** softSL `20.0259534184` · hardSL `21.6437498241` · TP `43.4358592994` · vol-gate `80.7060314547%` · dd-breaker `$1,242` · cooldown `0` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=68`, `k=3.1` |
| **breaker** | both | `swing_l=4` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=133`, `m=4.1` |
| **macd** | confirm | `fast=89`, `slow=147`, `signal=5` |
| **obv** | confirm | `slope=18` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $19,295  ·  worst DD $4,989  ·  win 52%  ·  full P/L $61,507 (15% DD)

- **Box / risk:** softSL `19.0419867417` · hardSL `19.6319082323` · TP `34.2504818898` · vol-gate `79.120276351%` · dd-breaker `$419` · cooldown `0` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=14` |
| **cci** | both | `n=156`, `threshold=125` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=317`, `slow=38` |
| **fvg** | both | `lookback=38` |
| **keltner** | confirm | `n=3`, `m=2.7` |
| **rsi** | both | `n=71`, `lower=44`, `upper=61` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $9,948  ·  worst DD $2,275  ·  win 63%  ·  full P/L $25,337 (20% DD)

- **Box / risk:** softSL `8.36114934211` · hardSL `19.0409546083` · TP `13.2984631149` · vol-gate `83.033185157%` · dd-breaker `$890` · cooldown `2` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=5` |
| **ema_trend** | confirm | `fast=271`, `slow=92` |
| **macd** | confirm | `fast=14`, `slow=132`, `signal=91` |
| **mfi** | both | `n=71`, `lower=28`, `upper=72` |
| **rsi** | both | `n=56`, `lower=6`, `upper=61` |

### 5m  —  median fold P/L $2,536  ·  worst DD $716  ·  win 92%  ·  full P/L $9,093 (9% DD)

- **Box / risk:** softSL `5.93773148666` · hardSL `7.16182303852` · TP `1.45272382741` · vol-gate `47.6752619967%` · dd-breaker `$1,043` · cooldown `7` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=183`, `k=3.4` |
| **breaker** | both | `swing_l=17` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=14`, `slow=316` |
| **fvg** | both | `lookback=7` |
| **keltner** | confirm | `n=46`, `m=0.7` |
| **macd** | confirm | `fast=9`, `slow=129`, `signal=4` |
| **rsi** | both | `n=95`, `lower=37`, `upper=72` |
| **sma_trend** | confirm | `fast=59`, `slow=131` |
| **structure_trend** | both | `swing_l=11` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $1,767  ·  worst DD $433  ·  win 72%  ·  full P/L $5,967 (7% DD)

- **Box / risk:** softSL `3.86275167464` · hardSL `4.32810645361` · TP `5.612072334` · vol-gate `43.2152993113%` · dd-breaker `$1,039` · cooldown `6` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=48`, `k=4.2` |
| **breaker** | both | `swing_l=9` |
| **cci** | both | `n=159`, `threshold=215` |
| **ema_trend** | confirm | `fast=310`, `slow=110` |
| **fvg** | both | `lookback=7` |
| **keltner** | confirm | `n=88`, `m=0.9` |
| **obv** | confirm | `slope=177` |
| **stochastic** | both | `n=86`, `d=14`, `lower=46`, `upper=75` |
| **structure_trend** | both | `swing_l=17` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
