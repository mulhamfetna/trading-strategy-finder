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
| 4h | 12022 | 8339 | 409 | $12,087 | $2,896 | 69 | $38,728 | 13% | 1 | 10 | adx;bollinger;cci;cisd;ifvg;keltner;mfi;order_block;sma_trend;vwap |
| 2h | 10538 | 7366 | 20 | $5,032 | $1,749 | 70 | $19,479 | 9% | 4 | 14 | adx;cci;cisd;fvg;keltner;macd;mfi;obv;order_block;rsi;sma_trend;stochastic;structure_trend;vwap |
| 1h | 11042 | 6056 | 303 | $14,161 | $4,226 | 41 | $52,167 | 9% | 5 | 7 | cci;cisd;ema_trend;mfi;order_block;structure_trend;vwap |
| 15m | 10999 | 5790 | 928 | $2,981 | $750 | 64 | $8,456 | 11% | 4 | 8 | bollinger;breaker;cci;cisd;ema_trend;fvg;structure_trend;vwap |
| 5m | 11015 | 5542 | 218 | $6,762 | $3,818 | 62 | $23,310 | 20% | 4 | 8 | adx;cci;ema_trend;macd;mfi;order_block;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $12,087  ·  worst DD $2,896  ·  win 69%  ·  full P/L $38,728 (13% DD)

- **Box / risk:** softSL `25.6` · hardSL `26.4` · TP `33.5` · vol-gate `84.5%` · dd-breaker `$462` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=36`, `threshold=10` |
| **bollinger** | veto | `n=198`, `k=4.0` |
| **cci** | both | `n=135`, `threshold=25` |
| **cisd** | both | _(none)_ |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=58`, `m=3.2` |
| **mfi** | both | `n=2`, `lower=38`, `upper=63` |
| **order_block** | both | `swing_l=12` |
| **sma_trend** | confirm | `fast=277`, `slow=214` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $5,032  ·  worst DD $1,749  ·  win 70%  ·  full P/L $19,479 (9% DD)

- **Box / risk:** softSL `25.6` · hardSL `27.7` · TP `30.9` · vol-gate `97.0%` · dd-breaker `$480` · cooldown `2` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=22`, `threshold=20` |
| **cci** | both | `n=142`, `threshold=270` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=9` |
| **keltner** | confirm | `n=93`, `m=1.1` |
| **macd** | confirm | `fast=19`, `slow=5`, `signal=6` |
| **mfi** | both | `n=85`, `lower=7`, `upper=87` |
| **obv** | confirm | `slope=195` |
| **order_block** | both | `swing_l=9` |
| **rsi** | both | `n=22`, `lower=16`, `upper=80` |
| **sma_trend** | confirm | `fast=396`, `slow=64` |
| **stochastic** | both | `n=49`, `d=29`, `lower=13`, `upper=92` |
| **structure_trend** | both | `swing_l=20` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $14,161  ·  worst DD $4,226  ·  win 41%  ·  full P/L $52,167 (9% DD)

- **Box / risk:** softSL `8.4` · hardSL `13.8` · TP `32.6` · vol-gate `79.9%` · dd-breaker `$612` · cooldown `1` · flip `True` · **K=`5`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=182`, `threshold=25` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=305`, `slow=323` |
| **mfi** | both | `n=91`, `lower=17`, `upper=84` |
| **order_block** | both | `swing_l=11` |
| **structure_trend** | both | `swing_l=16` |
| **vwap** | confirm | _(none)_ |

### 15m  —  median fold P/L $2,981  ·  worst DD $750  ·  win 64%  ·  full P/L $8,456 (11% DD)

- **Box / risk:** softSL `7.7` · hardSL `13.2` · TP `15.1` · vol-gate `40.3%` · dd-breaker `$661` · cooldown `5` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=66`, `k=2.9` |
| **breaker** | both | `swing_l=18` |
| **cci** | both | `n=198`, `threshold=150` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=324`, `slow=292` |
| **fvg** | both | `lookback=45` |
| **structure_trend** | both | `swing_l=9` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $6,762  ·  worst DD $3,818  ·  win 62%  ·  full P/L $23,310 (20% DD)

- **Box / risk:** softSL `6.1` · hardSL `13.3` · TP `7.5` · vol-gate `97.0%` · dd-breaker `$915` · cooldown `0` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=33`, `threshold=6` |
| **cci** | both | `n=135`, `threshold=150` |
| **ema_trend** | confirm | `fast=172`, `slow=89` |
| **macd** | confirm | `fast=35`, `slow=59`, `signal=9` |
| **mfi** | both | `n=57`, `lower=42`, `upper=57` |
| **order_block** | both | `swing_l=15` |
| **structure_trend** | both | `swing_l=1` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
