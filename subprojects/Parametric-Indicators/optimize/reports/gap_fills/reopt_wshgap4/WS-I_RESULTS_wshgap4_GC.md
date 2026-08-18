---
name: ws-i-results-report
description: WS-I.10 results — per-TF NSGA-III indicator search (feasible Pareto fronts; DD≤25%·P/L constraint) + cross-TF champion combos.
type: report
status: complete
workstream: WS-I
---

> **PROVENANCE — rescued from the server 2026-07-31, not a fresh WS-I run.**
> This is the rendered report of the **`wshgap4`** gap-aware re-optimization campaign (GAP-04), regenerated
> on the server on 2026-07-30 and left only there. Its numbers match the already-rescued
> `wshgap4_champions_full*.json` in this folder byte for byte — the *data* was never at risk, only this
> human-readable rendering was un-synced.
>
> Two things in the generated boilerplate above are **stale template text, not facts about this run**:
> the header says "all 15 indicators" (this campaign searched the original **18** under `--only-indicators`),
> and the `workstream: WS-I` frontmatter is the template's, not this campaign's.
>
> Full-precision values (`13.274460944074837`, not `13.27`) are the expected output of the
> no-rounding change (`_sig` → `_exact`, cadc18e) — see the precision memo.

# WS-I.10 — All-timeframe indicator search: results

NSGA-III, 3 objectives (median fold P/L ↑, worst-fold maxDD ↓, median win-rate ↑), feasibility = full-period maxDD ≤ 25% of full-period P/L. Search = box params + all 15 indicators on/off + their params + K. Champion per TF = max median fold P/L among feasible.

## Per-timeframe champion (feasible)

| TF | complete | feasible | front | med P/L | worst DD | win% | full P/L | DD%·P/L | K | #ind | indicators |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 2m | 5304 | 2449 | 277 | $7,168 | $2,498 | 58 | $25,008 | 18% | 3 | 7 | cci;ema_trend;fvg;obv;rsi;stochastic;structure_trend |
| 5m | 4963 | 1909 | 1741 | $2,018 | $1,720 | 68 | $7,884 | 22% | 3 | 5 | breaker;cisd;ema_trend;fvg;mfi |
| 15m | 4662 | 2261 | 118 | $12,116 | $5,565 | 68 | $44,714 | 23% | 3 | 7 | cisd;ema_trend;keltner;macd;rsi;sma_trend;vwap |
| 1h | 4825 | 3503 | 112 | $26,243 | $9,465 | 46 | $88,632 | 14% | 4 | 6 | cisd;macd;obv;rsi;sma_trend;structure_trend |
| 2h | 5051 | 3748 | 238 | $30,944 | $17,350 | 60 | $134,191 | 11% | 1 | 6 | bollinger;cci;ema_trend;rsi;structure_trend;vwap |
| 4h | 4635 | 3689 | 800 | $33,704 | $11,622 | 86 | $121,292 | 10% | 2 | 8 | adx;ema_trend;keltner;order_block;rsi;sma_trend;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $7,168  ·  worst DD $2,498  ·  win 58%  ·  full P/L $25,008 (18% DD)

- **Box / risk:** softSL `2.24264241593` · hardSL `4.13975566383` · TP `3.72841581952` · vol-gate `94.7490063798%` · dd-breaker `$659` · cooldown `1` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=26`, `threshold=120` |
| **ema_trend** | confirm | `fast=44`, `slow=50` |
| **fvg** | both | `lookback=26` |
| **obv** | confirm | `slope=180` |
| **rsi** | both | `n=35`, `lower=49`, `upper=92` |
| **stochastic** | both | `n=100`, `d=34`, `lower=44`, `upper=97` |
| **structure_trend** | both | `swing_l=13` |

### 5m  —  median fold P/L $2,018  ·  worst DD $1,720  ·  win 68%  ·  full P/L $7,884 (22% DD)

- **Box / risk:** softSL `2.9376465215545675` · hardSL `4.229828795122374` · TP `2.984834679664288` · vol-gate `85.80467227304531%` · dd-breaker `$336` · cooldown `6` · flip `True` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=1` |
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=267`, `slow=223` |
| **fvg** | both | `lookback=14` |
| **mfi** | both | `n=16`, `lower=35`, `upper=79` |

### 15m  —  median fold P/L $12,116  ·  worst DD $5,565  ·  win 68%  ·  full P/L $44,714 (23% DD)

- **Box / risk:** softSL `5.57789576565` · hardSL `8.43643059794` · TP `4.16265905461` · vol-gate `98.8973456569%` · dd-breaker `$384` · cooldown `0` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **ema_trend** | confirm | `fast=151`, `slow=54` |
| **keltner** | confirm | `n=151`, `m=4.1` |
| **macd** | confirm | `fast=90`, `slow=95`, `signal=48` |
| **rsi** | both | `n=52`, `lower=43`, `upper=67` |
| **sma_trend** | confirm | `fast=344`, `slow=5` |
| **vwap** | confirm | _(none)_ |

### 1h  —  median fold P/L $26,243  ·  worst DD $9,465  ·  win 46%  ·  full P/L $88,632 (14% DD)

- **Box / risk:** softSL `7.324493512051806` · hardSL `17.38899521822895` · TP `18.84691540296266` · vol-gate `98.89734565685147%` · dd-breaker `$651` · cooldown `0` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **cisd** | both | _(none)_ |
| **macd** | confirm | `fast=39`, `slow=171`, `signal=80` |
| **obv** | confirm | `slope=54` |
| **rsi** | both | `n=35`, `lower=44`, `upper=96` |
| **sma_trend** | confirm | `fast=97`, `slow=206` |
| **structure_trend** | both | `swing_l=4` |

### 2h  —  median fold P/L $30,944  ·  worst DD $17,350  ·  win 60%  ·  full P/L $134,191 (11% DD)

- **Box / risk:** softSL `12.250928833350908` · hardSL `21.371281528290275` · TP `23.923609691961715` · vol-gate `92.81667114060964%` · dd-breaker `$598` · cooldown `0` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=37`, `k=2.9` |
| **cci** | both | `n=186`, `threshold=40` |
| **ema_trend** | confirm | `fast=124`, `slow=246` |
| **rsi** | both | `n=84`, `lower=48`, `upper=72` |
| **structure_trend** | both | `swing_l=12` |
| **vwap** | confirm | _(none)_ |

### 4h  —  median fold P/L $33,704  ·  worst DD $11,622  ·  win 86%  ·  full P/L $121,292 (10% DD)

- **Box / risk:** softSL `23.00259346947315` · hardSL `55.64732562844701` · TP `25.319512763741` · vol-gate `91.75379027229552%` · dd-breaker `$224` · cooldown `0` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=5`, `threshold=27` |
| **ema_trend** | confirm | `fast=357`, `slow=307` |
| **keltner** | confirm | `n=101`, `m=3.3` |
| **order_block** | both | `swing_l=20` |
| **rsi** | both | `n=12`, `lower=48`, `upper=99` |
| **sma_trend** | confirm | `fast=33`, `slow=269` |
| **structure_trend** | both | `swing_l=5` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
