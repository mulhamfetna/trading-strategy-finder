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
| 2m | 5351 | 3646 | 110 | $2,988 | $1,090 | 83 | $9,710 | 12% | 4 | 10 | bollinger;cci;cisd;ema_trend;macd;mfi;order_block;rsi;sma_trend;stochastic |
| 5m | 5181 | 4404 | 38 | $2,680 | $549 | 89 | $11,241 | 4% | 1 | 9 | bollinger;cci;cisd;ema_trend;macd;mfi;sma_trend;stochastic;structure_trend |
| 15m | 4904 | 3302 | 169 | $4,996 | $1,009 | 56 | $17,666 | 6% | 3 | 8 | cisd;fvg;macd;mfi;order_block;sma_trend;structure_trend;vwap |
| 1h | 4296 | 2131 | 364 | $7,520 | $4,694 | 75 | $33,112 | 9% | 1 | 5 | bollinger;cci;ema_trend;keltner;stochastic |
| 2h | 4431 | 3177 | 207 | $4,601 | $562 | 96 | $11,069 | 5% | 1 | 10 | bollinger;breaker;cci;cisd;ema_trend;keltner;mfi;rsi;stochastic;vwap |
| 4h | 4772 | 2943 | 330 | $21,565 | $5,888 | 66 | $58,418 | 11% | 1 | 7 | adx;ema_trend;ifvg;macd;obv;order_block;sma_trend |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $2,988  ·  worst DD $1,090  ·  win 83%  ·  full P/L $9,710 (12% DD)

- **Box / risk:** softSL `4.1` · hardSL `6.3` · TP `2.2` · vol-gate `75.1%` · dd-breaker `$919` · cooldown `14` · flip `True` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=79`, `k=4.0` |
| **cci** | both | `n=132`, `threshold=220` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=154`, `slow=282` |
| **macd** | confirm | `fast=2`, `slow=168`, `signal=51` |
| **mfi** | both | `n=39`, `lower=31`, `upper=71` |
| **order_block** | both | `swing_l=13` |
| **rsi** | both | `n=98`, `lower=47`, `upper=70` |
| **sma_trend** | confirm | `fast=121`, `slow=242` |
| **stochastic** | both | `n=24`, `d=29`, `lower=48`, `upper=86` |

### 5m  —  median fold P/L $2,680  ·  worst DD $549  ·  win 89%  ·  full P/L $11,241 (4% DD)

- **Box / risk:** softSL `6.2` · hardSL `12.1` · TP `2.3` · vol-gate `67.2%` · dd-breaker `$1,274` · cooldown `19` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=9`, `k=2.5` |
| **cci** | both | `n=151`, `threshold=65` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=8`, `slow=324` |
| **macd** | confirm | `fast=48`, `slow=84`, `signal=62` |
| **mfi** | both | `n=21`, `lower=29`, `upper=87` |
| **sma_trend** | confirm | `fast=189`, `slow=45` |
| **stochastic** | both | `n=66`, `d=49`, `lower=48`, `upper=94` |
| **structure_trend** | both | `swing_l=17` |

### 15m  —  median fold P/L $4,996  ·  worst DD $1,009  ·  win 56%  ·  full P/L $17,666 (6% DD)

- **Box / risk:** softSL `3.6` · hardSL `7.7` · TP `15.9` · vol-gate `88.1%` · dd-breaker `$998` · cooldown `4` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=14` |
| **macd** | confirm | `fast=43`, `slow=130`, `signal=62` |
| **mfi** | both | `n=2`, `lower=4`, `upper=74` |
| **order_block** | both | `swing_l=14` |
| **sma_trend** | confirm | `fast=371`, `slow=117` |
| **structure_trend** | both | `swing_l=11` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $7,520  ·  worst DD $4,694  ·  win 75%  ·  full P/L $33,112 (9% DD)

- **Box / risk:** softSL `18.2` · hardSL `20.3` · TP `11.2` · vol-gate `73.0%` · dd-breaker `$1,205` · cooldown `4` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=32`, `k=4.0` |
| **cci** | both | `n=139`, `threshold=300` |
| **ema_trend** | confirm | `fast=317`, `slow=121` |
| **keltner** | confirm | `n=184`, `m=1.8` |
| **stochastic** | both | `n=89`, `d=45`, `lower=7`, `upper=51` |

### 2h  —  median fold P/L $4,601  ·  worst DD $562  ·  win 96%  ·  full P/L $11,069 (5% DD)

- **Box / risk:** softSL `24.6` · hardSL `43.8` · TP `5.9` · vol-gate `83.2%` · dd-breaker `$1,138` · cooldown `3` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=132`, `k=1.8` |
| **breaker** | both | `swing_l=19` |
| **cci** | both | `n=104`, `threshold=160` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=259`, `slow=338` |
| **keltner** | confirm | `n=149`, `m=2.5` |
| **mfi** | both | `n=89`, `lower=42`, `upper=98` |
| **rsi** | both | `n=7`, `lower=24`, `upper=59` |
| **stochastic** | both | `n=95`, `d=27`, `lower=14`, `upper=98` |
| **vwap** | confirm | _(none)_ |

### 4h  —  median fold P/L $21,565  ·  worst DD $5,888  ·  win 66%  ·  full P/L $58,418 (11% DD)

- **Box / risk:** softSL `32.5` · hardSL `74.8` · TP `48.1` · vol-gate `72.6%` · dd-breaker `$126` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=57`, `threshold=6` |
| **ema_trend** | confirm | `fast=338`, `slow=50` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=42`, `slow=82`, `signal=91` |
| **obv** | confirm | `slope=115` |
| **order_block** | both | `swing_l=5` |
| **sma_trend** | confirm | `fast=47`, `slow=32` |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
