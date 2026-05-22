# Live Dashboard Migration — FastAPI + Vue 3 + Lightweight Charts

## Problem Statement

The Dash dashboard built in iter 8 of the prior plan is architecturally
wrong for a "live, heavily-dynamic" trading view. Every interaction
round-trips to the Python server, Plotly chokes past ~5–10k bars, and
WebSocket streaming is not first-class. The target is TradingView-style
UX: live tick stream, scrollable history over 100k+ bars, drawing
markers, multi-pane indicators.

## Decision

Migrate to a **Python backend + JavaScript frontend** split:

- **Backend (Python):** FastAPI on uvicorn. Reuses `ScalpingStrategy`
  and `Backtester` (iter 7) and `filter_by_date_range` (iter 5) as
  services. Exposes REST endpoints for batch operations and a
  WebSocket endpoint for live streaming.
- **Frontend (TypeScript / Vue 3):** Vue 3 Composition API with Vite,
  Pinia for state, Tailwind for styling. Charting via
  **TradingView Lightweight Charts** (free, MIT, canvas-based,
  handles millions of bars at 60fps).

Vue chosen over React on three grounds: smaller bundle, less
ceremony for a solo project, faster ramp-up. The architecture is
framework-agnostic; React would slot in identically if preferences
change.

## Architecture

```
┌─────────────────────────────┐         REST + WS         ┌──────────────────────────────┐
│  Vue 3 + Vite frontend      │ <───────────────────────> │  FastAPI / uvicorn backend   │
│                             │                           │                              │
│  - ChartPane (LWCharts)     │  GET  /api/candles        │  src/api/                    │
│  - ResolverControls         │  POST /api/backtest       │    routes/                   │
│  - MetricsCards             │  GET  /api/strategy/...   │      candles.py              │
│  - TradeList                │  WS   /ws/candles         │      backtest.py             │
│  - IndicatorPanel           │                           │      strategy.py             │
│  - ReplayControls           │                           │      ws_candles.py           │
│                             │                           │    services/                 │
│  Pinia stores:              │                           │      backtest_service.py     │
│    candles, backtest,       │                           │    schemas.py (Pydantic)     │
│    settings                 │                           │                              │
│                             │                           │  Reuses unchanged:           │
│                             │                           │    src/strategy/             │
│                             │                           │    src/backtest/             │
│                             │                           │    src/data/                 │
│                             │                           │    src/indicators/           │
│                             │                           │    src/signals/              │
└─────────────────────────────┘                           └──────────────────────────────┘
```

## Repo Layout

New folders:

- `src/api/` — FastAPI app and routes (Python).
- `frontend/` — Vue 3 project (TypeScript, Vite).
- `frontend/tests/` — Vitest tests for frontend.

Existing folders preserved:

- `src/strategy/`, `src/backtest/`, `src/data/`, `src/indicators/`,
  `src/signals/` — unchanged.
- `src/main/` — CLI runners kept for batch use.
- `tests/` — pytest backend tests stay here.

Deprecated (removed in phase C):

- `src/dashboard/dash_app.py` and its tests.
- `dash` dependency in `requirements.txt`.

## Phase Plan

Each phase ships working software and lives on the `dev` branch as
its own commit (or small commit cluster with TDD discipline).

| Phase | Goal | Deliverable |
|---|---|---|
| **A** | Backend API skeleton + 3 REST endpoints. No frontend. | `src/api/app.py` runnable with `uvicorn src.api.app:app --reload`. `curl` round-trips through `/api/candles`, `/api/backtest`, `/api/strategy/config`. Pytest covers each endpoint via `TestClient`. |
| **B** | Vue scaffold + historical candlestick chart. | `cd frontend && npm run dev` shows OHLC candles from `/api/candles` in TradingView Lightweight Charts. No interactivity yet beyond zoom/pan. |
| **C** | Resolver controls + backtest wiring. Feature-parity with Dash. | Date pickers, dataset toggle (train/test), timeframe, TP/SL resolution dropdown, Apply button. POST to `/api/backtest`. Trade markers on chart. Metric cards. Trade list. **Delete `dash_app.py`.** |
| **D** | Multi-pane indicators. | RSI subchart, Volume subchart, EMA overlays on price pane. Indicator toggle panel. |
| **E** | WebSocket streaming + replay. | `/ws/candles` endpoint. Replay mode (0.5x / 1x / 5x / 50x slider). Frontend appends bars in real time. |
| **F** | Polish & power features. | Crosshair tooltips with full trade context, jump-to-trade, custom hover, keyboard shortcuts, dark/light theme. |

**v1 = A + B + C.** Phases D–F ship incrementally afterward.

## API Contract (Phase A)

### `GET /api/strategy/config`

Returns the strategy defaults (RSI period, EMA periods, SL/TP, etc.).
Used by the frontend to populate control defaults.

```json
{
  "rsi_period": 5,
  "ema_fast": 5,
  "ema_slow": 15,
  "vol_threshold": 2.0,
  "stop_loss": 0.6,
  "take_profit": 1.8,
  "tp_sl_resolution": "conservative",
  "tp_sl_resolution_options": ["conservative", "optimistic", "direction-proxy"],
  "timeframe_options": ["15min"],
  "dataset_options": ["train", "test"]
}
```

### `GET /api/candles?start=...&end=...&dataset=...&data_path=...`

Returns OHLCV candles for the given date range and split.

```json
{
  "candles": [
    {"t": "2025-09-01T09:30:00", "o": 20000.0, "h": 20002.0, "l": 19998.0, "c": 20001.0, "v": 1000},
    ...
  ],
  "count": 200,
  "range": {"start": "2025-09-01", "end": "2025-12-31"}
}
```

### `POST /api/backtest`

Body:

```json
{
  "start": "2025-09-01",
  "end": "2025-12-31",
  "dataset": "test",
  "timeframe": "15min",
  "tp_sl_resolution": "conservative",
  "stop_loss": 0.6,
  "take_profit": 1.8,
  "data_path": "1min.csv"
}
```

Returns:

```json
{
  "metrics": {"total_profit": 633.65, "win_rate": 54.5, ...},
  "trades": [{"entry_idx": 12, "exit_idx": 30, "entry_price": ..., ...}],
  "candles": [...]
}
```

### `WS /ws/candles` (deferred to phase E)

Replay/live stream of candles. Out of scope for phase A.

## Testing Strategy

- **Backend:** FastAPI `TestClient` + pytest. Each endpoint gets at
  least: happy path, validation failure, missing data, edge case.
  Reuses synthetic CSV helper from `tests/test_run_strategy.py`.
- **Frontend (phase B+):** Vitest for component logic, Playwright
  (later) for end-to-end smoke tests.

## Non-Goals (Phase A)

- No frontend code.
- No WebSocket.
- No auth (single-user local app for now).
- No persistent storage (everything in-memory; the CSV is the source of truth).
- No multi-symbol support (still NQ-only, point value hardcoded to 2.0).

## Risks

1. **CSV load time.** `1min.csv` is 135 MB; `load_data()` takes ~1s on
   warm cache. For phase A this is fine; for phase E streaming we'll
   want pre-computed indexed slices or Redis cache.
2. **uvicorn reload + pandas import.** uvicorn `--reload` will reload
   the FastAPI app on every Python file save, which means re-importing
   pandas (~1s). Acceptable in dev.
3. **CORS in phase B.** Vue dev server runs on different port than
   uvicorn. Need to enable CORS in FastAPI for dev. Production builds
   serve both from one origin so this disappears.
