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
| 4h | 4606 | 3138 | 112 | $11,491 | $3,926 | 53 | $35,047 | 11% | 3 | 5 | breaker;cisd;ema_trend;ifvg;mfi |
| 2h | 4702 | 2611 | 98 | $12,496 | $5,563 | 54 | $36,801 | 18% | 4 | 8 | bollinger;breaker;cci;cisd;keltner;macd;obv;vwap |
| 1h | 4897 | 2112 | 160 | $12,872 | $4,010 | 57 | $55,530 | 8% | 2 | 5 | adx;keltner;mfi;obv;structure_trend |
| 15m | 5537 | 3146 | 207 | $8,999 | $2,354 | 58 | $26,709 | 16% | 2 | 7 | bollinger;breaker;cci;cisd;ifvg;macd;obv |
| 5m | 5204 | 2679 | 230 | $5,554 | $2,616 | 45 | $14,900 | 18% | 4 | 7 | breaker;cisd;ema_trend;fvg;obv;order_block;structure_trend |
| 2m | 4984 | 3705 | 56 | $1,166 | $275 | 72 | $4,364 | 6% | 5 | 13 | adx;bollinger;breaker;cisd;fvg;ifvg;keltner;macd;obv;order_block;rsi;sma_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $11,491  ·  worst DD $3,926  ·  win 53%  ·  full P/L $35,047 (11% DD)

- **Box / risk:** softSL `87.5200851318` · hardSL `101.470343885` · TP `377.925954856` · vol-gate `94.5832156132%` · dd-breaker `$7,190` · cooldown `1` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=6` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=76`, `slow=393` |
| **ifvg** | both | _(none)_ |
| **mfi** | both | `n=95`, `lower=44`, `upper=93` |

### 2h  —  median fold P/L $12,496  ·  worst DD $5,563  ·  win 54%  ·  full P/L $36,801 (18% DD)

- **Box / risk:** softSL `158.92345487` · hardSL `188.225877079` · TP `281.240338107` · vol-gate `81.4321906575%` · dd-breaker `$3,472` · cooldown `1` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=195`, `k=3.4` |
| **breaker** | both | `swing_l=15` |
| **cci** | both | `n=21`, `threshold=30` |
| **cisd** | both | _(none)_ |
| **keltner** | confirm | `n=27`, `m=4.0` |
| **macd** | confirm | `fast=49`, `slow=63`, `signal=41` |
| **obv** | confirm | `slope=191` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $12,872  ·  worst DD $4,010  ·  win 57%  ·  full P/L $55,530 (8% DD)

- **Box / risk:** softSL `124.188338009` · hardSL `303.859129726` · TP `164.86389623` · vol-gate `97.5201135014%` · dd-breaker `$9,509` · cooldown `1` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=71`, `threshold=11` |
| **keltner** | confirm | `n=133`, `m=3.7` |
| **mfi** | both | `n=41`, `lower=24`, `upper=88` |
| **obv** | confirm | `slope=89` |
| **structure_trend** | both | `swing_l=9` |

### 15m  —  median fold P/L $8,999  ·  worst DD $2,354  ·  win 58%  ·  full P/L $26,709 (16% DD)

- **Box / risk:** softSL `44.868563754` · hardSL `80.2416471957` · TP `56.3900761665` · vol-gate `99.1634488256%` · dd-breaker `$2,702` · cooldown `3` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=195`, `k=4.1` |
| **breaker** | both | `swing_l=8` |
| **cci** | both | `n=162`, `threshold=195` |
| **cisd** | both | _(none)_ |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=16`, `slow=104`, `signal=30` |
| **obv** | confirm | `slope=61` |

### 5m  —  median fold P/L $5,554  ·  worst DD $2,616  ·  win 45%  ·  full P/L $14,900 (18% DD)

- **Box / risk:** softSL `14.900093084` · hardSL `57.9544708015` · TP `51.5117320916` · vol-gate `84.1898007827%` · dd-breaker `$9,308` · cooldown `15` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=4` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=29`, `slow=274` |
| **fvg** | both | `lookback=47` |
| **obv** | confirm | `slope=12` |
| **order_block** | both | `swing_l=10` |
| **structure_trend** | both | `swing_l=18` |

### 2m  —  median fold P/L $1,166  ·  worst DD $275  ·  win 72%  ·  full P/L $4,364 (6% DD)

- **Box / risk:** softSL `10.2459543287` · hardSL `28.3781960806` · TP `27.722595772` · vol-gate `42.3712083368%` · dd-breaker `$3,490` · cooldown `22` · flip `False` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=60`, `threshold=7` |
| **bollinger** | veto | `n=96`, `k=2.0` |
| **breaker** | both | `swing_l=18` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=13` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=3`, `m=4.0` |
| **macd** | confirm | `fast=69`, `slow=63`, `signal=41` |
| **obv** | confirm | `slope=31` |
| **order_block** | both | `swing_l=2` |
| **rsi** | both | `n=52`, `lower=41`, `upper=75` |
| **sma_trend** | confirm | `fast=7`, `slow=57` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
