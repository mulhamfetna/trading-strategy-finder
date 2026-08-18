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
| 4h | 5154 | 4161 | 154 | $19,204 | $6,752 | 63 | $61,704 | 10% | 3 | 7 | cisd;ema_trend;macd;mfi;obv;sma_trend;vwap |
| 2h | 4922 | 3730 | 199 | $4,401 | $1,598 | 58 | $13,738 | 11% | 1 | 11 | bollinger;ema_trend;ifvg;keltner;macd;obv;order_block;rsi;sma_trend;structure_trend;vwap |
| 1h | 4816 | 2765 | 192 | $4,363 | $2,220 | 64 | $15,954 | 14% | 4 | 8 | bollinger;cci;ifvg;keltner;order_block;rsi;stochastic;structure_trend |
| 15m | 4941 | 3345 | 427 | $2,375 | $620 | 65 | $6,022 | 25% | 1 | 9 | adx;cisd;ema_trend;ifvg;macd;obv;order_block;rsi;vwap |
| 5m | 4821 | 2548 | 145 | $1,573 | $376 | 45 | $5,308 | 7% | 1 | 10 | bollinger;breaker;cci;cisd;ema_trend;fvg;mfi;rsi;structure_trend;vwap |
| 2m | 5350 | 3028 | 270 | $4,607 | $1,205 | 56 | $18,128 | 6% | 1 | 5 | adx;cisd;macd;order_block;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 4h  —  median fold P/L $19,204  ·  worst DD $6,752  ·  win 63%  ·  full P/L $61,704 (10% DD)

- **Box / risk:** softSL `13.1062474293` · hardSL `29.5964952083` · TP `21.8337486885` · vol-gate `90.0783114707%` · dd-breaker `$346` · cooldown `0` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=177`, `slow=269` |
| **macd** | confirm | `fast=49`, `slow=105`, `signal=13` |
| **mfi** | both | `n=100`, `lower=30`, `upper=67` |
| **obv** | confirm | `slope=53` |
| **sma_trend** | confirm | `fast=373`, `slow=357` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $4,401  ·  worst DD $1,598  ·  win 58%  ·  full P/L $13,738 (11% DD)

- **Box / risk:** softSL `3.57836106323` · hardSL `5.11840772294` · TP `7.67032294801` · vol-gate `81.5721844492%` · dd-breaker `$40` · cooldown `1` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=22`, `k=1.6` |
| **ema_trend** | confirm | `fast=317`, `slow=301` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=133`, `m=1.8` |
| **macd** | confirm | `fast=16`, `slow=47`, `signal=85` |
| **obv** | confirm | `slope=85` |
| **order_block** | both | `swing_l=9` |
| **rsi** | both | `n=5`, `lower=44`, `upper=71` |
| **sma_trend** | confirm | `fast=173`, `slow=55` |
| **structure_trend** | both | `swing_l=10` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $4,363  ·  worst DD $2,220  ·  win 64%  ·  full P/L $15,954 (14% DD)

- **Box / risk:** softSL `6.51296938208` · hardSL `11.2051784792` · TP `7.94300342098` · vol-gate `98.6730238066%` · dd-breaker `$333` · cooldown `1` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=60`, `k=4.3` |
| **cci** | both | `n=49`, `threshold=170` |
| **ifvg** | both | _(none)_ |
| **keltner** | confirm | `n=130`, `m=4.5` |
| **order_block** | both | `swing_l=1` |
| **rsi** | both | `n=39`, `lower=17`, `upper=58` |
| **stochastic** | both | `n=45`, `d=14`, `lower=5`, `upper=94` |
| **structure_trend** | both | `swing_l=13` |

### 15m  —  median fold P/L $2,375  ·  worst DD $620  ·  win 65%  ·  full P/L $6,022 (25% DD)

- **Box / risk:** softSL `3.68060608873` · hardSL `3.68865032747` · TP `4.3120282781` · vol-gate `81.0611238076%` · dd-breaker `$435` · cooldown `2` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=27`, `threshold=19` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=317`, `slow=38` |
| **ifvg** | both | _(none)_ |
| **macd** | confirm | `fast=6`, `slow=190`, `signal=72` |
| **obv** | confirm | `slope=8` |
| **order_block** | both | `swing_l=1` |
| **rsi** | both | `n=33`, `lower=7`, `upper=71` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $1,573  ·  worst DD $376  ·  win 45%  ·  full P/L $5,308 (7% DD)

- **Box / risk:** softSL `1.19898400275` · hardSL `1.23117116432` · TP `3.5508761536` · vol-gate `62.0269304576%` · dd-breaker `$458` · cooldown `11` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=121`, `k=2.1` |
| **breaker** | both | `swing_l=17` |
| **cci** | both | `n=174`, `threshold=30` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=121`, `slow=364` |
| **fvg** | both | `lookback=28` |
| **mfi** | both | `n=71`, `lower=20`, `upper=60` |
| **rsi** | both | `n=25`, `lower=7`, `upper=58` |
| **structure_trend** | both | `swing_l=11` |
| **vwap** | confirm | _(none)_ |

### 2m  —  median fold P/L $4,607  ·  worst DD $1,205  ·  win 56%  ·  full P/L $18,128 (6% DD)

- **Box / risk:** softSL `1.2795510837` · hardSL `1.30100919142` · TP `1.29080528777` · vol-gate `81.4321906575%` · dd-breaker `$110` · cooldown `1` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=19`, `threshold=11` |
| **cisd** | both | _(none)_ |
| **macd** | confirm | `fast=80`, `slow=51`, `signal=67` |
| **order_block** | both | `swing_l=13` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
