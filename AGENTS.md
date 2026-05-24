# AGENTS.md — NQ Master Strategy Dashboard

Two-process app: a FastAPI backend (Python) serving SSE backtests and a Vue 3 frontend (Vite). Mirror of the engineering surface in `CLAUDE.md`; this file is the agent-facing handoff.

> **Single source of truth for strategy rules:** `docs/MASTER_STRATEGY_GUIDE.md`.
> **End-to-end verification reference:** `docs/SYSTEM_BLUEPRINT.md`.
> **No-fallback rule:** `docs/CODING_RULES.md`.

## Run things

```bash
# ---- Backend ----
pip install -r requirements.txt
pytest tests/ -v                                                  # all tests, from repo root
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000       # SSE backend on :8000

# ---- Frontend ----
cd frontend
npm install
npm run dev                                                       # :5173, proxies /api/* → :8000
npm test -- --run                                                 # vitest single-run
npm run build                                                     # vue-tsc --noEmit + Vite production build
```

Dashboard URL: **`http://localhost:5173`**.

**Restart `uvicorn` after Python edits.** The `--reload` flag picks up most file changes, but if the SSE payload is missing a field you just added, the backend is the first thing to suspect — restart and retry. The 12:01 saved dashboard snapshot in this repo's history is exactly this scenario: frontend rebuilt against the new SettingsPanel + 1-min picker, backend still serving the pre-dual-timeframe code → trade rows rendered with `NaN` for Entry px / Exit px.

## Architecture (one-line)

```
data CSVs (NQ_4h, NQ_1m, NQ_full_data)
   ↓
src/data/loader.py  →  src/data/splitter.py
   ↓
src/strategy/box_lookup.py  →  src/strategy/box_strategy.py  →  src/strategy/scaling_strategy.py
   ↓                                            ↓
   directional oracle                  1-1-2 execution + dual-timeframe SL/TP walker
   ↓
src/api/app.py  (POST /api/backtest/box → SSE: progress, complete)
   ↓
frontend/src/stores/backtest.ts → ChartPane / TradeList / MetricsCards
```

`src/optimization/` is the NSGA-II multi-objective optimiser (in progress, see Phase H..N of `docs/superpowers/plans/2026-05-23-nsga2-optimization-implementation.md`).

## Conventions that bite

- **No silent fallbacks.** Every dataclass field, Pydantic field, function arg is required. Use the helpers in `tests/_fixtures.py` (`scaling_params`, `box_strategy_params`, `box_params_dict`) for tests. `docs/CODING_RULES.md` §1 has the full contract.
- **Trade dict shape** — backend emits all of:
  - `entry_idx`, `exit_idx` (4h-bar indices)
  - `entry_signal_price` (= `legs[0].price`, always in candle OHLC)
  - `exit_close` (sub-bar / 4h-bar close at exit, always in candle OHLC)
  - `avg_entry_price`, `exit_price` (algorithm-effective; used for PnL math)
  - `contracts`, `profit_points`, `profit_dollars`, `exit_reason`
  - `exit_time` (ISO sub-bar timestamp in dual-timeframe mode; `None` in 4h-only legacy mode)
  - `legs[]`, `box_signal`
- **Asymmetric exit fill** (user rule 2026-05-24):
  - HARD SL & hard TP fill AT the line (loss/gain = exactly the configured points)
  - SOFT SL & trailing TP fill AT the confirming bar's close (loss/gain depends on the actual close)
- **Dual-timeframe SL/TP** (since 2026-05-24): hard SL & TP target scan 1-min closes; soft SL & trail scan 2-min aggregates. `BoxBacktestRequest.data_path_1min` is required at the API boundary. The engine still accepts `df_1min=None` for unit tests with synthetic candles (collapses to 4h close).
- **Signal contract** in `box_lookup.py`: `'long'`, `'short'`, or `None`. No numeric encoding.
- **NQ point-value PnL**: `profit_dollars = profit_points × contracts × point_value` with `point_value=2.0`.
- **Box-date mapping** (NQ session cycle): a candle with hour ≥ 18 belongs to box_date + 1 day; hour < 18 stays on the same day. The CSV `Date` field is the box's CLOSING day (17:00). See `notes2.md:79` and `src/strategy/box_lookup.py:13-20`.
- **Dashboard validators** (strict `>`, both ends enforced):
  - `sl_hard_points > sl_soft_points`
  - `soft_sl_confirmation_timeframe_minutes > hard_sl_confirmation_timeframe_minutes`
  Backend (`BoxParamsModel._sl_ordering`) returns 422 on violation; frontend (`SettingsPanel.errors.slOrder`) blocks submit and shows inline error.

## Data files (gitignored, must live at repo root)

| File | Role | Format |
|---|---|---|
| `NQ_4h.csv` | Entry-signal timeframe (4h OHLCV) | `datetime,open,high,low,close,volume` |
| `NQ_1m.csv` | SL/TP timeframe | same shape |
| `NQ_full_data.csv` | Unified W+M box edges (v4) | `Date,Scraped_At,` + 48 level columns |

The deprecated `NQ_week_data_shifted.csv` / `NQ_month_data_shifted.csv` pair was replaced by `NQ_full_data.csv` on 2026-05-23 (v4 migration).

## Branches and worktrees

- `dev` — active branch (current).
- `master` — stable.
- Tags: `v1.0.0`, `v1.0-working`, `v1.1` — frozen historical references (legacy Python pipeline, no longer runs).
- Git worktrees live under `.worktrees/` (gitignored).

## Documentation map

| Doc | When to read |
|---|---|
| `docs/SYSTEM_BLUEPRINT.md` | Verifying engine output against real data |
| `docs/MASTER_STRATEGY_GUIDE.md` | Looking up any strategy parameter |
| `docs/CODING_RULES.md` | Adding/modifying a Pydantic field or dataclass |
| `docs/MASTER_DOCUMENTATION.md` | "Which doc do I read for…?" |
| `docs/bug-checklist-revision-history.md` | Auditing past bugs / adding a new bug row |
| `docs/superpowers/plans/2026-05-23-nsga2-PROGRESS.md` | NSGA-II execution state |
| `notes2.md` / `docs/Data_Shape_To_Do.md` | User's narrative spec for the v4 unified box CSV + NQ session cycle |

## Frozen reference (do not edit)

- `Currunt_Strategy_Algo_for_Trading.md` — original 1-1-2 playbook (pre-Box).
- `BOXES_Strategy.md` — raw brainstorming for the Box system.
- `docs/BOX_STRATEGY.md` — structured Box spec (superseded by §2 of the master guide).
- `docs/V1-FROZEN.md` — v1.0.0 production reference.
- `docs/legacy/` — archived historical material.

The legacy Python pipeline (`src/main/`, `src/indicators/`, `src/dashboard/`, `src/backtest/`, `src/signals/`, plus `scalping_strategy.py` / `backtester.py`) was erased on 2026-05-23. Do not try to import or run those modules.
