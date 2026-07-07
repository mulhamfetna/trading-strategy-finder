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
| 2m | 3329 | 2260 | 376 | $424 | $2,176 | 66 | $3,172 | 21% | 1 | 7 | bollinger;breaker;fvg;keltner;order_block;structure_trend;vwap |
| 5m | 2892 | 1229 | 202 | $4,615 | $5,403 | 42 | $28,400 | 12% | 2 | 9 | bollinger;breaker;cci;fvg;macd;obv;rsi;sma_trend;vwap |
| 15m | 2395 | 1371 | 814 | $2,131 | $1,863 | 45 | $14,571 | 19% | 1 | 8 | bollinger;breaker;cci;fvg;macd;obv;sma_trend;stochastic |
| 1h | 474 | 38 | 8 | $1,803 | $7,336 | 78 | $13,744 | 22% | 1 | 5 | adx;breaker;cci;ifvg;mfi |
| 2h | 1400 | 500 | 82 | $11,511 | $11,944 | 68 | $45,420 | 24% | 4 | 6 | bollinger;cisd;fvg;ifvg;obv;rsi |
| 4h | 40 | 0 | 0 | — | — | — | — | — | — | — | (no feasible) |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $424  ·  worst DD $2,176  ·  win 66%  ·  full P/L $3,172 (21% DD)

- **Box / risk:** softSL `0.0225` · hardSL `0.0551` · TP `0.0279` · vol-gate `92.24%` · dd-breaker `$9` · cooldown `17` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=145`, `k=2.6` |
| **breaker** | both | `swing_l=11` |
| **fvg** | both | `lookback=8` |
| **keltner** | confirm | `n=70`, `m=3.8` |
| **order_block** | both | `swing_l=19` |
| **structure_trend** | both | `swing_l=13` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $4,615  ·  worst DD $5,403  ·  win 42%  ·  full P/L $28,400 (12% DD)

- **Box / risk:** softSL `0.0218` · hardSL `0.0408` · TP `0.0644` · vol-gate `91.97%` · dd-breaker `$1` · cooldown `1` · flip `True` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=168`, `k=3.8` |
| **breaker** | both | `swing_l=2` |
| **cci** | both | `n=15`, `threshold=300` |
| **fvg** | both | `lookback=43` |
| **macd** | confirm | `fast=28`, `slow=177`, `signal=32` |
| **obv** | confirm | `slope=133` |
| **rsi** | both | `n=31`, `lower=4`, `upper=55` |
| **sma_trend** | confirm | `fast=353`, `slow=30` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $2,131  ·  worst DD $1,863  ·  win 45%  ·  full P/L $14,571 (19% DD)

- **Box / risk:** softSL `0.0255` · hardSL `0.0479` · TP `0.0773` · vol-gate `94.05%` · dd-breaker `$3` · cooldown `2` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=155`, `k=3.1` |
| **breaker** | both | `swing_l=11` |
| **cci** | both | `n=194`, `threshold=265` |
| **fvg** | both | `lookback=25` |
| **macd** | confirm | `fast=36`, `slow=12`, `signal=98` |
| **obv** | confirm | `slope=12` |
| **sma_trend** | confirm | `fast=194`, `slow=325` |
| **stochastic** | both | `n=93`, `d=6`, `lower=12`, `upper=64` |

### 1h  —  median fold P/L $1,803  ·  worst DD $7,336  ·  win 78%  ·  full P/L $13,744 (22% DD)

- **Box / risk:** softSL `0.1204` · hardSL `0.2316` · TP `0.0649` · vol-gate `97.29%` · dd-breaker `$3` · cooldown `1` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=67`, `threshold=15` |
| **breaker** | both | `swing_l=17` |
| **cci** | both | `n=75`, `threshold=145` |
| **ifvg** | both | _(none)_ |
| **mfi** | both | `n=25`, `lower=21`, `upper=87` |

### 2h  —  median fold P/L $11,511  ·  worst DD $11,944  ·  win 68%  ·  full P/L $45,420 (24% DD)

- **Box / risk:** softSL `0.1856` · hardSL `0.2497` · TP `0.247` · vol-gate `98.58%` · dd-breaker `$9` · cooldown `0` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=18`, `k=3.0` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=35` |
| **ifvg** | both | _(none)_ |
| **obv** | confirm | `slope=190` |
| **rsi** | both | `n=64`, `lower=25`, `upper=95` |

### 4h — (no feasible champion)

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
