# API Documentation — DEPRECATED

> **This file documented the legacy Python pipeline (`src/main/`, `src/indicators/`, `src/signals/`, `src/backtest/`, `src/dashboard/`) which was erased on 2026-05-23 — see `docs/revisions/REVISION_LOG.md` round 9.**
>
> The current system is a FastAPI + Vue 3 stack. There is no longer a per-function "API reference" doc — the engine has only one production code path (BoxStrategy) and one HTTP entrypoint (`/api/backtest/box`). Both are documented inline.

## Where to look now

| For | Read |
|---|---|
| **HTTP endpoints** (`/api/backtest/box`, `/api/candles`, `/api/boxes`, `/api/optimize/*`) | `src/api/app.py` — endpoints are defined at the bottom of the file under their FastAPI decorators |
| **Request / response shapes** | `src/api/schemas.py` (Pydantic models). TypeScript mirror at `frontend/src/types.ts` |
| **Trade dict shape** | `docs/MASTER_STRATEGY_GUIDE.md` §7.3 + `docs/BACKTEST_LOGIC.md` §8 |
| **Engine internals** (per-bar lifecycle, sub-bar exit walker) | `docs/BACKTEST_LOGIC.md` |
| **End-to-end behaviour with real data** | `docs/SYSTEM_BLUEPRINT.md` |
| **Strategy parameters + dashboard mapping** | `docs/MASTER_STRATEGY_GUIDE.md` §6 + §8 |
| **No-fallback rule + error types** | `docs/CODING_RULES.md` §1 |

The HTTP endpoints emit Server-Sent Events for long-running backtests / optimisations. The SSE parser shape is locked by `frontend/tests/sse_parser.test.ts` and the backend tests under `tests/test_api_*.py`.
