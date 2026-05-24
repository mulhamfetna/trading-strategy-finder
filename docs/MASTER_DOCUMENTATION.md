# Master Documentation Router

Single landing page for every documentation source in the repo.

> **Trust executable code first.** Where this router links to long-form docs, check the referenced source files if anything looks off — the long-form docs aren't always in lock-step with the live engine.

---

## 1. Start here (active references)

| Doc | What it answers |
|---|---|
| `docs/SYSTEM_BLUEPRINT.md` | **Authoritative end-to-end behaviour reference.** Real-data worked examples + verification protocol. Locked by `tests/test_blueprint_examples.py`. |
| `docs/MASTER_STRATEGY_GUIDE.md` | Single source of truth for strategy rules: 1-1-2 sizing, dual-SL, dual-TP, dual-timeframe engine, Big-Candle vs Box conflict. |
| `docs/CODING_RULES.md` | Project-wide engineering rules. The no-fallback rule lives here. |
| `CLAUDE.md` | Codebase conventions, run commands, critical guardrails for agents working in this repo. |
| `AGENTS.md` | Agent-facing handoff notes (worktree layout, canonical commands, common pitfalls). |
| `README.md` | Human entrypoint: quickstart commands, project structure. |

---

## 2. Architecture (what the code actually does)

The system is a single FastAPI + Vue 3 stack.

### Backend modules

| Module | Role |
|---|---|
| `src/api/app.py` | FastAPI endpoints. `/api/backtest/box` (SSE), `/api/candles`, `/api/health`, `/api/boxes`, `/api/data-files`, `/api/upload-data-file`, plus the `/api/optimize/*` family (NSGA-II in progress). |
| `src/api/schemas.py` | Pydantic request/response models. `BoxParamsModel` enforces the SL ordering invariants (sl_hard > sl_soft, soft_tf > hard_tf). |
| `src/data/loader.py` | OHLCV CSV ingestion. Single `datetime` column → `Date` (pd.Timestamp). |
| `src/data/splitter.py` | `filter_by_date_range` for trimming candle frames. |
| `src/strategy/scaling_strategy.py` | 1-1-2 execution engine. `_check_exits_subbar` is the dual-timeframe SL/TP walker. |
| `src/strategy/box_strategy.py` | Production engine. Subclass of `ScalingStrategy` that consults `BoxLookup` for direction. |
| `src/strategy/box_lookup.py` | Directional oracle. Loads the unified box CSV; emits `'long'` / `'short'` / `'hold'` per 4h candle close. |
| `src/optimization/*` | NSGA-II multi-objective optimiser (in progress — see Phase H..N of the active plan). |
| `src/exceptions.py` | `ConfigurationError` / `MissingParameterError` / `MissingDataFileError` for the no-fallback error contract. |

### Frontend modules

| Module | Role |
|---|---|
| `frontend/src/components/SettingsPanel.vue` | The §1..§5b strategy-parameters form. Computes `errors.slOrder` and `errors.legOrder` live; blocks submit while invalid. |
| `frontend/src/components/ChartPane.vue` | Lightweight Charts wrapper. Candles + EMA + volume + RSI panes; trade markers anchored to bars. |
| `frontend/src/components/TradeList.vue` | The trade table. Renders `entry_signal_price` / `exit_close` (candle-grounded) by default; tooltip surfaces `avg_entry_price` / `exit_price` (algorithm-effective). |
| `frontend/src/stores/{backtest,candles,settings,replay}.ts` | Pinia stores. |
| `frontend/src/services/{api,sse}.ts` | REST + SSE plumbing. |
| `frontend/src/types.ts` | TypeScript mirror of `src/api/schemas.py`. |

---

## 3. Data files (gitignored)

| File | Role | Format |
|---|---|---|
| `NQ_4h.csv` | Entry-signal timeframe | `datetime,open,high,low,close,volume` |
| `NQ_1m.csv` | SL/TP timeframe (1-min hard, 2-min soft) | same shape as `NQ_4h.csv` |
| `NQ_full_data.csv` | Unified W+M box edges (v4 schema) | `Date,Scraped_At,` + 48 level columns (W*/M*/D*) — see `docs/Data_Shape_To_Do.md` |

Legacy `NQ_week_data_shifted.csv` + `NQ_month_data_shifted.csv` have been replaced by the single unified `NQ_full_data.csv` (v4 migration, 2026-05-23).

---

## 4. Run commands

```bash
# Python
pip install -r requirements.txt
pytest tests/ -v                                                    # full suite (from repo root)
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000         # backend

# Frontend (cd frontend)
npm install
npm run dev                                                          # :5173, proxies /api/* → :8000
npm run build                                                        # type-check + Vite build
npm test                                                             # vitest run
```

> **Restart the backend after Python code changes.** `--reload` watches Python files; if you don't see your new fields in the SSE payload, that's the first thing to check.

---

## 5. Design specs and plans (active work)

- `docs/superpowers/specs/2026-05-23-nsga2-optimization-design.md` — NSGA-II design.
- `docs/superpowers/plans/2026-05-23-nsga2-optimization-implementation.md` — 22-task plan.
- `docs/superpowers/plans/2026-05-23-nsga2-PROGRESS.md` — live execution state (paused at H.1 done; dashboard certification path took priority).

---

## 6. Frozen reference (do not edit; consult `MASTER_STRATEGY_GUIDE.md` instead)

- `Currunt_Strategy_Algo_for_Trading.md` — original 1-1-2 playbook (pre-Box integration).
- `BOXES_Strategy.md` — raw brainstorming dump of the Box system.
- `docs/BOX_STRATEGY.md` — structured/confirmed Box spec.
- `docs/STRATEGY_INTEGRATION_ANALYSIS.md` — deep analysis of how the two playbooks integrate.
- `docs/V1-FROZEN.md` — v1.0.0 production reference.
- `notes.md` / `notes2.md` — user's running notes; `notes2.md` lines 95-101 carry the NQ session-cycle rule that pins the box-date mapping.
- `docs/Data_Shape_To_Do.md` — user's narrative description of the v4 unified box CSV semantics.

The legacy Python pipeline (`src/main/`, `src/indicators/`, `src/dashboard/`, `src/backtest/`, `src/signals/`, plus the standalone `scalping_strategy.py` / `backtester.py`) was erased on 2026-05-23; the `Tutorials/` and `Project_Documentation/` directories under `docs/` document that vanished pipeline and are kept only as historical reading.

---

## 7. Bug tracking and revisions

- `docs/bug-checklist-revision-history.md` — bug bounty knowledge base. Add a row per non-trivial fix.
- `docs/revisions/REVISION_LOG.md` — round-by-round summary.
- `docs/revisions/swarm-2026-05-23/` — most recent multi-lens audit + action plan.
- `docs/revisions/hardcoded-scan-2026-05-23-v3/HARDCODED_VALUES_REPORT_V3.md` — latest hardcoded-values scan output.

---

## 8. Recent material changes (chronological, newest first)

| Date | What | Reference |
|---|---|---|
| 2026-05-24 | Dual-timeframe SL/TP engine: 1-min hard SL & TP target, 2-min soft SL & trail. `data_path_1min` required at API. | Blueprint Part G, commits `86fb9d0` `f7ac6e3` `b36aef5` |
| 2026-05-24 | SL ordering validators (strict `>`) + `hard_sl_confirmation_timeframe_seconds` → `_minutes` rename. | Commit `a83ef21` |
| 2026-05-24 | Soft SL fills at confirming bar's close (not the line); hard SL keeps line fill. | Commit `6b9ba4d` |
| 2026-05-24 | Trade dict carries candle-grounded `entry_signal_price` + `exit_close` alongside algorithm-effective fields. | Commit `8cc5afb` |
| 2026-05-24 | `SYSTEM_BLUEPRINT.md` — end-to-end verification reference. | Commit `c838c27` |
| 2026-05-23 | v4 unified box CSV (`NQ_full_data.csv`); legacy pipeline erased. | `docs/revisions/DATA_FORMAT_V4_UNIFIED_BOX.md` |
