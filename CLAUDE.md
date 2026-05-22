# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (always from repo root)
pytest tests/ -v

# Run a single test module or a single test
pytest tests/test_scaling_strategy.py -v
pytest tests/test_ultimate_dashboard.py::test_run_backtest_15min_uses_nq_point_value_for_pnl -v

# Entry scripts — must be run as modules from repo root (NOT python3 src/main/main.py)
python3 -m src.main.main                 # multi-strategy comparison
python3 -m src.main.ultimate_dashboard   # 15min ML-filtered dashboard -> output/dashboards/
python3 -m src.main.fast_optimizer       # parameter sweep -> output/configs/best_config.txt
python3 -m src.main.live_dashboard       # live simulation
python3 -m src.main.run_strategy --data 1min.csv --start 2025-09-01 --end 2025-12-31 --strategy scalping

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

### Two parallel stacks

**Legacy pipeline** — pure Python, generates standalone HTML dashboards:

```
src/data/loader.py
  → src/data/splitter.py + src/data/resampler.py
    → src/indicators/{scalping,day_trading,intraday}.py
      → src/signals/base_signals.py → src/signals/ml_filter.py
        → src/backtest/{engine.py, metrics.py}
          → src/dashboard/{report,visualizer,template_renderer}.py
```

Entry scripts in `src/main/` wire the pipeline. `ultimate_dashboard.py` resamples 1-min → 15-min internally and is its own near-complete pipeline.

**FastAPI + Vue stack** (active development, "phase C"):

```
frontend/src/                           (Vue 3 + Pinia + Lightweight Charts + Tailwind)
  stores/{backtest,candles,settings}.ts  ← state, calls api.ts / sse.ts
  services/api.ts                        ← axios REST calls
  services/sse.ts                        ← POST SSE fetch-based streaming
  components/...                         ← ChartPane, SettingsPanel, TradeList, etc.

src/api/app.py                           (FastAPI)
  /api/candles         GET   → load+filter+split → Candle[]
  /api/backtest        POST  → ScalpingStrategy → trades/metrics
  /api/backtest/scaling POST → ScalingStrategy  → SSE stream (progress/complete/error)
  /api/strategy/config GET   → StrategyConfig defaults
```

The Vite dev server proxies `/api/*` to `:8000`, so the frontend uses relative URLs in both dev and production.

### Scaling strategy (1-1-2)

`src/strategy/scaling_strategy.py` implements the core algorithm from `Currunt_Strategy_Algo_for_Trading.md`:
- Scale into a position across 3 legs (1 contract, 1 contract, 2 contracts) at 0 / −100 / −150 point pullbacks
- Big-candle exception (>400 pts): enter full 4 contracts immediately, reverse direction
- TP at +150 pts; dual SL (soft + hard)
- Optional re-entry on pullback after a profitable exit

`src/strategy/backtester.py` is the OOP wrapper used by the FastAPI endpoints. The older functional pipeline in `src/backtest/engine.py` is used by legacy entry scripts.

### TypeScript / Pydantic contract

`frontend/src/types.ts` mirrors `src/api/schemas.py` exactly. Keep both in sync when adding fields.

## Critical conventions

- **Always use `python3 -m src.main.<script>`** from repo root. `sys.path` inside the scripts does not resolve `src.*` imports when run directly.
- **1min.csv loads newest-first (descending).** Any new pipeline off the 1-min file must reverse to ascending before backtesting — same as `src/main/main.py:42`.
- **NQ point-value PnL**: backtest multiplies points × `point_value=2.0` (1 contract × N pts × $2). Test `test_run_backtest_15min_uses_nq_point_value_for_pnl` is the canonical lock.
- **Signal contract**: `-1` short, `0` hold, `1` long throughout all modules.
- **Trade dict keys** consumed by metrics and dashboard: `entry_idx, exit_idx, direction, entry_price, exit_price, profit_pct, profit_dollars, capital_after, exit_reason, fees_paid`. Scaling trades use a different shape (`avg_entry_price`, `contracts`, `profit_points`, `legs`).
- **Indicator/signal functions copy-before-mutate**; they return new DataFrames.
- **ML filter**: `apply_ml_filter` overwrites the active signal column — pass the filtered DataFrame to `run_backtest`, not the pre-filter one.
- **Data files are gitignored** (`*.csv`, `*.html`): `1min.csv` (~135 MB) and `NQ_15min_processed.csv` (~8 MB) must be restored at repo root before running anything.
- **Train/test split** is hardcoded to 2025 data, split at `2025-06-30`.
- Run `pytest` from repo root — tests use relative bare filenames for the CSV paths.

## Output locations

- `output/dashboards/ultimate_trading_dashboard.html` + `dashboard_data.json` (gitignored)
- `output/configs/best_config.txt` (from `fast_optimizer`)

## Documentation

- `docs/MASTER_DOCUMENTATION.md` — top-level index to all docs
- `AGENTS.md` — authoritative run-commands and data-gotchas reference (read first for agents)
- `Currunt_Strategy_Algo_for_Trading.md` — plain-English strategy playbook
- `docs/V1-FROZEN.md` — v1.0.0 production reference
- `docs/legacy/` — archived, treat as historical only
- `Project_Documentation/*.doc.md` — stale (reference old root-level paths), ignore for current paths
