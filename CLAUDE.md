# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The codebase is a single FastAPI + Vue 3 stack. The legacy HTML-dashboard Python pipeline (`src/main/`, `src/dashboard/`, `src/indicators/`, `src/backtest/`, `src/signals/`, plus `scalping_strategy.py` / `backtester.py`) was erased on 2026-05-23 — see `docs/revisions/REVISION_LOG.md` round 9. Don't try to import or run those modules.

## Commands

### Python backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (always from repo root)
pytest tests/ -v

# Single test module / test
pytest tests/test_scaling_strategy.py -v
pytest tests/test_api_scaling_sse.py::test_scaling_backtest_streams_progress_and_complete_events -v

# FastAPI backend
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Vue 3 + Vite)

```bash
cd frontend

npm install
npm run dev          # dev server at :5173 (proxies /api/* to :8000)
npm run build        # type-check + Vite production build
npm test             # vitest run (happy-dom, tests in frontend/tests/)
npm run test:watch
```

## Architecture

Single stack: FastAPI backend + Vue 3 frontend, communicating over REST + SSE.

```
frontend/src/                              (Vue 3 + Pinia + Lightweight Charts + Tailwind)
  stores/{backtest,candles,settings,replay}.ts  ← state, calls api.ts / sse.ts
  services/api.ts                               ← axios REST calls
  services/sse.ts                               ← POST SSE fetch-based streaming
  components/...                                ← ChartPane, SettingsPanel, TradeList, MetricsCards, ProgressBar, ReplayBar

src/api/app.py                             (FastAPI)
  /api/strategy/config   GET   → StrategyConfig defaults
  /api/candles           GET   → load+filter+split → Candle[]
  /api/health            GET   → liveness probe
  /api/boxes             GET   → BoxRect[] for chart overlay
  /api/data-files        GET   → list available CSV files
  /api/upload-data-file  POST  → upload a CSV
  /api/backtest/scaling  POST  → ScalingStrategy → SSE stream (progress/complete/error)
  /api/backtest/box      POST  → BoxStrategy + ScalingStrategy → SSE stream

src/strategy/
  scaling_strategy.py    1-1-2 scaling algorithm (the core engine)
  box_strategy.py        TradingView box overlay + scaling engine
  box_lookup.py          Weekly/monthly box level lookup with signal logic
```

The Vite dev server proxies `/api/*` to `:8000`, so the frontend uses relative URLs in both dev and production.

### Scaling strategy (1-1-2)

`src/strategy/scaling_strategy.py` implements the algorithm from `Currunt_Strategy_Algo_for_Trading.md`:
- Scale into a position across 3 legs (1 contract, 1 contract, 2 contracts) at 0 / −100 / −150 point pullbacks
- Big-candle exception (>400 pts): enter full 4 contracts immediately, reverse direction
- TP at +150 pts; dual SL (soft + hard)
- Optional re-entry on pullback after a profitable exit

### Box strategy

`src/strategy/box_strategy.py` wraps the scaling engine with a TradingView-box filter:
- `box_lookup.py` loads the shifted weekly/monthly box CSVs and answers "is this candle inside a box level?"
- Signal fires as soon as price crosses ONE box level. Weekly takes priority over monthly when both are active.
- Box rectangles surface to the frontend as `BoxRect[]` for chart rendering.

### TypeScript / Pydantic contract

`frontend/src/types.ts` mirrors `src/api/schemas.py`. Keep both in sync when adding fields.

## Critical conventions

- **NQ point-value PnL**: scaling/box strategy emits `profit_dollars = profit_points × contracts × point_value` with `point_value=2.0`. Don't break this without updating the schema and the frontend tests.
- **Trade dict keys** (scaling strategy emits): `entry_idx, exit_idx, direction, avg_entry_price, exit_price, contracts, profit_points, profit_dollars, exit_reason, legs, exit_time, box_signal?`.
- **Signal contract** in `box_lookup.py`: `'long'`, `'short'`, or `None` (no numeric encoding).
- **Data files are gitignored** (`*.csv`, `*.html`). Active datasets:
  - `NQ_4h.csv` — single `datetime` column, ascending. Primary 4h backtest input.
  - `NQ_1m.csv` — single `datetime` column. Used for precise intra-bar exit timestamps in dual-timeframe mode.
  - `NQ_week_data_shifted.csv` / `NQ_month_data_shifted.csv` — box-level CSVs produced by `scripts/preprocess_boxes.py`.
- Run `pytest` from repo root.

## Documentation

- **`docs/CODING_RULES.md` — project-wide engineering rules.** Read this first. The no-fallback rule lives here: every missing value raises an explicit error with `code` + `message` + `system_status`. No silent defaults.
- **`docs/MASTER_STRATEGY_GUIDE.md` — single source of truth for strategy behaviour.** Read this second. Every numeric/boolean decision in the trading system is defined here and mapped to its `ScalingParams` / `BoxStrategyParams` field.
- `docs/STRATEGY_INTEGRATION_ANALYSIS.md` — deep analysis of how the 1-1-2 Scaling and Box playbooks integrate (the reasoning behind the master guide).
- `docs/MASTER_DOCUMENTATION.md` — top-level index to all docs.
- `docs/bug-checklist-revision-history.md` — bug bounty knowledge base.
- `docs/reviewer-playbook-segmented.md` — 6-lens review process.
- `docs/revisions/REVISION_LOG.md` — round-by-round revision history.
- `docs/revisions/swarm-2026-05-23/` — most recent multi-lens audit + action plan.

### Historical / frozen reference (do not edit; consult master guide instead)
- `Currunt_Strategy_Algo_for_Trading.md` — original 1-1-2 playbook.
- `BOXES_Strategy.md` — raw brainstorming dump for the Box system.
- `docs/BOX_STRATEGY.md` — structured Box spec; superseded by §2 of the master guide.
- `docs/V1-FROZEN.md` — v1.0.0 production reference.
- `docs/legacy/` — archived prior reports.
