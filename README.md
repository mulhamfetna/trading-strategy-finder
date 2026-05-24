# NQ Master Strategy Dashboard

FastAPI + Vue 3 application that backtests the **Master Strategy** — the 1-1-2 Scaling execution framework directed by the TradingView Box oracle — on historical NQ futures data.

The Master Strategy combines two layers:

- **Directional oracle** — `BoxStrategy` reads the unified weekly+monthly TradingView Box CSV and emits `long` / `short` / `hold` for each 4h candle close.
- **Execution framework** — `ScalingStrategy` handles 1-1-2 entries, dual stop-loss tiers, dual take-profit tiers, and the trailing-watch logic. Since 2026-05-24 the SL/TP exits run on a 1-min companion frame (HARD/TP-target on 1-min, SOFT/TRAIL on 2-min aggregates).

For the authoritative behaviour reference with real-data worked examples, see **`docs/SYSTEM_BLUEPRINT.md`**. For the strategy spec, see **`docs/MASTER_STRATEGY_GUIDE.md`**.

## Quick Start

```bash
# Backend
pip install -r requirements.txt
pytest tests/ -v                                                # all 96+ tests
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000     # serves on :8000

# Frontend
cd frontend && npm install
npm run dev                                                     # dev at :5173, proxies /api/*
npm test                                                        # vitest run
npm run build                                                   # type-check + production build
```

Open the dashboard at **`http://localhost:5173`**. Restart `uvicorn` whenever you change Python files (the `--reload` flag picks up most changes; if you don't see a new SSE field in the trade payload, that's the first thing to check).

## Required data files (gitignored)

Place these three CSVs at the repo root before running a backtest:

| File | Role | Format |
|---|---|---|
| `NQ_4h.csv` | Entry-signal timeframe | `datetime,open,high,low,close,volume` |
| `NQ_1m.csv` | SL/TP timeframe | same column shape as `NQ_4h.csv` |
| `NQ_full_data.csv` | Unified W+M box edges (v4) | `Date,Scraped_At,` + 48 level columns |

All three are **required** — the API rejects requests with missing or empty paths under the no-fallback rule (`docs/CODING_RULES.md`).

## Project structure

```
src/
  api/             FastAPI app, Pydantic schemas
  data/            CSV loader + date-range splitter
  strategy/        BoxStrategy + ScalingStrategy + BoxLookup
  optimization/    NSGA-II multi-objective optimiser (in progress)
  exceptions.py    Structured error types (no-fallback rule)
frontend/src/      Vue 3 + Pinia + Lightweight Charts dashboard
tests/             pytest (backend + blueprint regression locks)
docs/              Documentation — start at MASTER_DOCUMENTATION.md
```

## Documentation

| Doc | Read if you want to… |
|---|---|
| `docs/MASTER_DOCUMENTATION.md` | …know which doc to read for what |
| `docs/SYSTEM_BLUEPRINT.md` | …verify the system on real data, end to end |
| `docs/MASTER_STRATEGY_GUIDE.md` | …understand every numeric/boolean strategy decision |
| `docs/CODING_RULES.md` | …know the no-fallback rule + project-wide conventions |
| `CLAUDE.md` / `AGENTS.md` | …work on this repo as an agent |
| `docs/bug-checklist-revision-history.md` | …see past bugs + their fixes |

## License

MIT
