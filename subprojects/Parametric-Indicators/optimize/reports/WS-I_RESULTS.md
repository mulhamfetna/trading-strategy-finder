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
| 4h | 2292 | 1131 | 79 | $24,253 | $12,067 | 74 | $56,040 | 18% | 1 | 8 | ema_trend;macd;keltner;rsi;stochastic;mfi;adx;order_block |
| 2h | 2294 | 1248 | 96 | $15,132 | $10,835 | 90 | $55,836 | 17% | 1 | 7 | ema_trend;macd;vwap;obv;mfi;bollinger;order_block |
| 1h | 2048 | 942 | 65 | $12,284 | $4,418 | 71 | $33,280 | 24% | 2 | 9 | ema_trend;macd;vwap;obv;rsi;mfi;bollinger;adx;structure_trend |
| 15m | 2604 | 1778 | 159 | $10,538 | $3,223 | 67 | $33,676 | 24% | 1 | 7 | sma_trend;macd;vwap;keltner;cci;stochastic;structure_trend |
| 5m | 2716 | 1736 | 131 | $9,943 | $4,344 | 66 | $36,710 | 11% | 3 | 6 | ema_trend;macd;cci;mfi;structure_trend;order_block |
| 2m | 2594 | 1482 | 250 | $4,474 | $3,848 | 46 | $18,857 | 20% | 2 | 5 | ema_trend;obv;bollinger;adx;order_block |
| 1m | 2458 | 1684 | 343 | $1,876 | $1,167 | 80 | $7,681 | 15% | 1 | 8 | ema_trend;macd;vwap;obv;cci;stochastic;mfi;fvg |

## Notes / caveats
- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.
- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.
- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen combo on the **exact dashboard engine** (retrace/wait + carry apply there).
- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + trade counts before trusting them.
