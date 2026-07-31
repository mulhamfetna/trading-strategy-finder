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
| 2m | 5615 | 3812 | 263 | $9,181 | $4,936 | 48 | $25,608 | 19% | 3 | 7 | adx;cci;fvg;macd;rsi;sma_trend;vwap |
| 5m | 5359 | 3870 | 171 | $7,472 | $4,530 | 64 | $21,109 | 15% | 1 | 5 | breaker;keltner;mfi;obv;sma_trend |
| 15m | 5272 | 3882 | 278 | $7,640 | $1,672 | 48 | $29,835 | 6% | 1 | 9 | bollinger;cci;cisd;fvg;keltner;obv;rsi;sma_trend;stochastic |
| 1h | 5090 | 3675 | 103 | $21,476 | $6,306 | 68 | $75,245 | 10% | 4 | 9 | bollinger;cci;ema_trend;fvg;mfi;order_block;sma_trend;structure_trend;vwap |
| 2h | 5035 | 2164 | 235 | $29,925 | $16,024 | 59 | $97,898 | 16% | 2 | 5 | cci;ema_trend;keltner;macd;structure_trend |
| 4h | 5296 | 4259 | 284 | $25,373 | $9,186 | 63 | $90,054 | 13% | 1 | 8 | bollinger;keltner;macd;mfi;obv;order_block;structure_trend;vwap |

## Full champion recipe per timeframe

Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no internal params.)

### 2m  —  median fold P/L $9,181  ·  worst DD $4,936  ·  win 48%  ·  full P/L $25,608 (19% DD)

- **Box / risk:** softSL `13.274460944074837` · hardSL `13.290191774667566` · TP `20.71209515599036` · vol-gate `82.13720415432884%` · dd-breaker `$4,591` · cooldown `24` · flip `False` · **K=`3`**

| indicator | role | tuned internal params |
|---|---|---|
| **adx** | veto | `n=7`, `threshold=7` |
| **cci** | both | `n=8`, `threshold=245` |
| **fvg** | both | `lookback=24` |
| **macd** | confirm | `fast=92`, `slow=60`, `signal=70` |
| **rsi** | both | `n=69`, `lower=42`, `upper=78` |
| **sma_trend** | confirm | `fast=265`, `slow=135` |
| **vwap** | confirm | _(none)_ |

### 5m  —  median fold P/L $7,472  ·  worst DD $4,530  ·  win 64%  ·  full P/L $21,109 (15% DD)

- **Box / risk:** softSL `16.658992643449267` · hardSL `36.458084212366245` · TP `28.23198344323632` · vol-gate `41.646255617310814%` · dd-breaker `$3,834` · cooldown `16` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **breaker** | both | `swing_l=9` |
| **keltner** | confirm | `n=122`, `m=1.6` |
| **mfi** | both | `n=86`, `lower=40`, `upper=72` |
| **obv** | confirm | `slope=180` |
| **sma_trend** | confirm | `fast=89`, `slow=102` |

### 15m  —  median fold P/L $7,640  ·  worst DD $1,672  ·  win 48%  ·  full P/L $29,835 (6% DD)

- **Box / risk:** softSL `11.736343838746256` · hardSL `21.049220948625013` · TP `61.14601417999631` · vol-gate `69.5996510445494%` · dd-breaker `$4,719` · cooldown `3` · flip `True` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=89`, `k=4.0` |
| **cci** | both | `n=7`, `threshold=150` |
| **cisd** | both | _(none)_ |
| **fvg** | both | `lookback=44` |
| **keltner** | confirm | `n=21`, `m=2.9` |
| **obv** | confirm | `slope=99` |
| **rsi** | both | `n=4`, `lower=26`, `upper=65` |
| **sma_trend** | confirm | `fast=18`, `slow=152` |
| **stochastic** | both | `n=66`, `d=35`, `lower=24`, `upper=53` |

### 1h  —  median fold P/L $21,476  ·  worst DD $6,306  ·  win 68%  ·  full P/L $75,245 (10% DD)

- **Box / risk:** softSL `63.670615777194996` · hardSL `113.8948968544511` · TP `89.65125501747642` · vol-gate `88.45956925312461%` · dd-breaker `$3,065` · cooldown `2` · flip `False` · **K=`4`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=194`, `k=4.8` |
| **cci** | both | `n=143`, `threshold=85` |
| **ema_trend** | confirm | `fast=332`, `slow=154` |
| **fvg** | both | `lookback=8` |
| **mfi** | both | `n=8`, `lower=7`, `upper=81` |
| **order_block** | both | `swing_l=10` |
| **sma_trend** | confirm | `fast=7`, `slow=373` |
| **structure_trend** | both | `swing_l=13` |
| **vwap** | confirm | _(none)_ |

### 2h  —  median fold P/L $29,925  ·  worst DD $16,024  ·  win 59%  ·  full P/L $97,898 (16% DD)

- **Box / risk:** softSL `97.02586214940614` · hardSL `119.3804809231158` · TP `121.78839246367572` · vol-gate `94.41933496915841%` · dd-breaker `$4,539` · cooldown `2` · flip `False` · **K=`2`**

| indicator | role | tuned internal params |
|---|---|---|
| **cci** | both | `n=88`, `threshold=150` |
| **ema_trend** | confirm | `fast=195`, `slow=53` |
| **keltner** | confirm | `n=68`, `m=4.1` |
| **macd** | confirm | `fast=76`, `slow=167`, `signal=52` |
| **structure_trend** | both | `swing_l=1` |

### 4h  —  median fold P/L $25,373  ·  worst DD $9,186  ·  win 63%  ·  full P/L $90,054 (13% DD)

- **Box / risk:** softSL `128.577008338` · hardSL `151.442378696` · TP `125.561176619` · vol-gate `89.6628039906%` · dd-breaker `$4,119` · cooldown `1` · flip `False` · **K=`1`**

| indicator | role | tuned internal params |
|---|---|---|
| **bollinger** | veto | `n=132`, `k=4.4` |
| **keltner** | confirm | `n=84`, `m=2.7` |
| **macd** | confirm | `fast=58`, `slow=167`, `signal=30` |
| **mfi** | both | `n=64`, `lower=4`, `upper=92` |
| **obv** | confirm | `slope=120` |
| **order_block** | both | `swing_l=12` |
| **structure_trend** | both | `swing_l=6` |
| **vwap** | confirm | _(none)_ |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
