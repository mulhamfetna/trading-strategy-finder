# Trading Strategy Playbook — DEPRECATED

> **This file documented the deleted "scalping vs day trading vs intraday" comparison pipeline** (`src/main/main.py`, `src/main/ultimate_dashboard.py`, etc.) which was erased on 2026-05-23 — see `docs/revisions/REVISION_LOG.md` round 9.
>
> The current system runs **one master strategy only**: 1-1-2 Scaling execution + TradingView Box directional oracle, with a dual-timeframe SL/TP engine.

## Where the strategy lives now

| Topic | Read |
|---|---|
| **Strategy rules** (1-1-2 sizing, dual SL, dual TP, big-candle exception, Box oracle, conflict resolution) | `docs/MASTER_STRATEGY_GUIDE.md` |
| **Per-bar lifecycle, leg fills, exit walker** | `docs/BACKTEST_LOGIC.md` |
| **End-to-end behaviour with real-data worked examples** | `docs/SYSTEM_BLUEPRINT.md` |
| **Dashboard user manual** | `docs/USER_MANUAL.md` |
| **Original 1-1-2 playbook (pre-Box integration)** | `Currunt_Strategy_Algo_for_Trading.md` (frozen) |
| **Original Box system spec** | `BOXES_Strategy.md` + `docs/BOX_STRATEGY.md` (frozen) |

There is no longer a "compare three strategies" workflow — the dashboard runs the master strategy and only the master strategy. Parameter exploration is handled by the NSGA-II optimiser (`src/optimization/`, in progress).
