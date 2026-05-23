# NSGA-II Multi-Objective Optimisation — Design Spec

**Date:** 2026-05-23
**Branch target:** `dev` (merges from / shares engine with `v3-stable-dynamic-backtest-dashboard`)
**Status:** Design approved across 6 sections. Ready for `writing-plans`.
**Parent docs:**
- Research survey: `docs/research/PARAMETER_SEARCH_STUDY.md`
- WIP brainstorm checkpoint (working notes): `docs/research/PARAMETER_SEARCH_NSGA2_DESIGN_WIP.md`

---

## 1. Goal

Add a dashboard-driven multi-objective parameter optimiser for `BoxStrategy`. The user picks search ranges and a budget; the optimiser explores the `(sl_soft_points, sl_hard_points, tp_target_points)` space and returns a **Pareto front** trading off profit factor against max drawdown. Selected points can be applied back to the regular backtest with one click.

The optimiser is built on Optuna's `NSGAIISampler` (industry-standard multi-objective evolutionary algorithm). A new SSE-streaming endpoint surfaces live progress, per-trial results, and the evolving Pareto front to a new `/optimize` route on the frontend.

---

## 2. Decision log (Q&A summary)

Every locked decision behind this spec:

| # | Question | Answer |
|---|---|---|
| Q1 | Objectives | **PF + Max Drawdown** — maximise `profit_factor` (median across folds), minimise `max_drawdown` (max across folds). |
| Q2 | Scoring strategy | **Walk-forward folds** — N equal-time-span folds; aggregate via median(PF) and max(MaxDD). |
| Q3 | Search space (v1) | **3 continuous params:** `sl_soft_points`, `sl_hard_points`, `tp_target_points`. Constraint `sl_hard ≥ sl_soft + 50` encoded via reparameterisation. |
| Q4 | Search budget | **Three presets:** Light (pop 40 × gen 15 × 3 folds = 600 trials, ~3 min), Standard (1,800 trials), Heavy (5,400 trials). Light is the default. |
| Q5 | Surface area | **New `/optimize` route** in the dashboard; live Pareto front via SSE. Apply-and-Backtest navigates back to `/`. |
| Library | NSGA-II implementation | **Optuna `NSGAIISampler`** with SQLite storage. |
| Q3.1 | PF undefined (zero losses) | **Prune the trial** via `optuna.TrialPruned`. |
| Q3.2 | `min_trades_per_fold` floor | **Default 15, exposed as a UI control** in OptimizePanel. |
| Q3.3 | Search `big_candle_resolution` as 4th param? | **No — freeze at baseline.** Keeps NSGA-II crossover/mutation working on a clean continuous space. |
| Q4.1 | Trial-event throttling | **Emit every trial** (~600 events over ~3 min ≈ 3.3 events/sec, fine for SSE). |
| Q4.2 | Cancellation policy | **Graceful by default** (`should_stop` flag polled between trials); `?abrupt=true` query param kills the worker thread. |
| Q5.1 | Panel placement | **New `/optimize` route** (not a sibling panel or modal). |
| Q6.1 | Study persistence | **SQLite + auto-resume on restart.** Incomplete studies surface in OptimizePanel as "Continue?" cards. |
| Q6.2 | Spec workflow | **Write spec → user review → writing-plans.** |

---

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                  Vue OptimizePanel (route /optimize)               │
│  param-range inputs · budget preset · live Pareto front scatter    │
│  three presets (Conservative / Balanced / Aggressive) · Apply+Run  │
│  "Continue?" cards for restored studies                            │
└────────────────────────────────────────────────────────────────────┘
                              ▲ SSE: progress / trial / generation / complete
                              │       error / warning
                              │
┌────────────────────────────────────────────────────────────────────┐
│  POST /api/optimize/box           → _opt_event_stream              │
│  POST /api/optimize/<id>/stop     [?abrupt=true]                   │
│  POST /api/optimize/<id>/resume                                    │
│  GET  /api/optimize/studies       → list resumable studies         │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                      src/optimization/                             │
│                                                                    │
│   study.py          — Optuna study lifecycle (NSGAIISampler        │
│                       + SQLite storage; resume-by-name)            │
│   objective.py      — evaluate(params, baseline, folds, ...)       │
│                       → (PF_median, MaxDD_max). Raises TrialPruned │
│                       on Q3.1 / Q3.2 / malformed-box-geometry      │
│                       conditions; re-raises study-fatal errors.    │
│   walk_forward.py   — N equal-time-span splits + aggregation       │
│   sse_bridge.py     — Optuna callback → queue.Queue → SSE          │
│   persistence.py    — list/scan/cleanup SQLite studies             │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
            ┌──────────────────────────────────────┐
            │  BoxStrategy.backtest(df_fold)       │ (existing v3.1)
            │  → trades[], metrics{PF, MaxDD, ...}│
            └──────────────────────────────────────┘
```

**Boundaries:**
- `src/optimization/` is a new package. Depends on `src/strategy/` and `src/data/`; nothing in `src/strategy/` or `src/api/` depends back on it.
- `objective.py::evaluate()` is the only seam Optuna sees.
- `sse_bridge.py` reuses the worker-thread + `queue.Queue` pattern from the existing `_box_event_stream`.

---

## 4. Data flow

### 4.1 Starting a fresh study

1. User opens `/optimize`. OptimizePanel.vue mounts.
2. On mount, frontend calls `GET /api/optimize/studies` — receives any incomplete studies (auto-resume candidates).
3. User picks search ranges + budget preset + min_trades_per_fold + max_duration_s.
4. User clicks **Run optimisation**. Frontend POSTs to `/api/optimize/box` with body:
   ```json
   {
     "baseline_params": { ...full BoxStrategyParams... },
     "search_space": {
       "sl_soft_points": [50.0, 300.0],
       "sl_hard_points_delta": [50.0, 600.0],
       "tp_target_points": [75.0, 250.0]
     },
     "budget": {"population_size": 40, "generations": 15},
     "folds": {"count": 3, "min_trades_per_fold": 15},
     "data_path": "NQ_4h.csv",
     "week_data_path": "NQ_week_data_shifted.csv",
     "month_data_path": "NQ_month_data_shifted.csv",
     "max_duration_s": 1800
   }
   ```
   No-fallback rule: every field is required.
5. Backend constructs Optuna study with SQLite storage (`optuna_studies.db`, study_name = generated UUID). Returns `study_id` in the first SSE event.
6. Worker thread runs the study, emitting SSE events.

### 4.2 Resuming after server restart

1. Frontend mounts OptimizePanel.
2. `GET /api/optimize/studies` returns incomplete studies with their last-known progress.
3. User clicks **Continue** on a "Continue?" card → `POST /api/optimize/<study_id>/resume`. Backend re-opens the SQLite study, continues `study.optimize()` from the next trial.

### 4.3 Per-trial flow (inside objective.evaluate)

```python
def evaluate(suggested_params, baseline_params, folds, min_trades_per_fold, box_lookup):
    fold_metrics = []
    for df_fold in folds:
        params_dict = {**asdict(baseline_params), **suggested_params}
        strat = BoxStrategy(BoxStrategyParams(**params_dict), box_lookup)
        try:
            trades, _state = strat.backtest(df_fold)   # reset_state() inside
        except ConfigurationError as e:
            if e.code in ('missing-candle-columns', 'missing-data-file', 'missing-parameter'):
                raise                                   # study-fatal — re-raise
            raise optuna.TrialPruned(f'trial-prune: {e.code}')

        if len(trades) < min_trades_per_fold:
            raise optuna.TrialPruned(f'insufficient trades: {len(trades)}')

        m = compute_metrics(trades)
        if m['profit_factor'] is None:
            raise optuna.TrialPruned('PF undefined (no losses)')

        fold_metrics.append(m)

    return (
        statistics.median(m['profit_factor'] for m in fold_metrics),
        max(m['max_drawdown'] for m in fold_metrics),
    )
```

### 4.4 Constraint encoding

`sl_hard ≥ sl_soft + 50` is encoded structurally — not as a post-hoc rejection:

```python
def suggest(trial):
    sl_soft = trial.suggest_float('sl_soft_points', 50.0, 300.0)
    delta   = trial.suggest_float('sl_hard_delta', 50.0, 600.0 - sl_soft)
    sl_hard = sl_soft + delta
    tp      = trial.suggest_float('tp_target_points', 75.0, 250.0)
    return {'sl_soft_points': sl_soft, 'sl_hard_points': sl_hard, 'tp_target_points': tp}
```

---

## 5. SSE event protocol

All events share the existing `event: <type>\ndata: <json>\n\n` shape from `/api/backtest/box`. Error and warning events reuse the `{code, message, system_status}` schema for frontend consistency.

```jsonc
event: study_started
data: {
  "study_id": "<uuid>",
  "trials_total": 600,
  "started_at": "2026-05-23T20:30:00Z",
  "resumed": false
}

event: progress
data: {
  "trials_done": 247,
  "trials_total": 600,
  "percent": 41.2,
  "current_generation": 7,
  "pareto_size": 12,
  "elapsed_ms": 84300
}

event: trial
data: {
  "trial_number": 247,
  "params": {"sl_soft_points": 180.0, "sl_hard_points": 280.0, "tp_target_points": 175.0},
  "values": [1.84, -2300.0],
  "state": "complete",
  "pruned_reason": null
}

event: generation
data: {
  "generation": 8,
  "pareto_front": [
    {"trial_number": 142, "params": {...}, "values": [1.92, -1850.0]},
    ...
  ]
}

event: complete
data: {
  "study_id": "<uuid>",
  "pareto_front": [...],
  "top_5_by_pf": [...],
  "top_5_by_min_dd": [...],
  "total_trials": 600,
  "pruned_count": 84,
  "elapsed_ms": 198400
}

event: error
data: {"code": "missing-candle-columns", "message": "...", "system_status": {...}}

event: warning
data: {"trial_number": 247, "code": "malformed-box-geometry", "message": "...", "system_status": {...}}
```

**Throttling:** Emit every trial (Q4.1). Frontend can RAF-batch render at 30 FPS if needed.

**Cancellation:** `POST /api/optimize/<study_id>/stop` flips a `should_stop` flag the trial loop polls between trials. Default is graceful (finish current trial → emit `complete` with the partial Pareto front). `?abrupt=true` kills the worker thread immediately.

---

## 6. Frontend (OptimizePanel.vue)

### 6.1 Layout

```
┌────────────────────────────────────────────────────────────────────┐
│  Optimize        (search ranges + budget preset + max duration)   │
├────────────────────────────────────────────────────────────────────┤
│   sl_soft   [  50 ── 300 ]   sl_hard_delta [  50 ── 600 ]         │
│   tp_target [  75 ── 250 ]   min trades/fold [ 15 ]               │
│   Budget: ○ Light  ○ Standard  ○ Heavy                            │
│   Max duration: [ 30 min ]                                        │
│   [ Run optimisation ]   [ Stop ]                                 │
│                                                                    │
│   Continue? incomplete studies from earlier sessions:             │
│   [ #abc123 — 247/600 done, 84 pruned, started 18:42  Continue ]  │
├────────────────────────────────────────────────────────────────────┤
│   Pareto front (PF vs Max Drawdown)        |  Selected trial:    │
│   (scatter; frontier highlighted)          |  #247               │
│      PF                                    |  PF: 1.84           │
│   2.0│  ●     ★ Pareto                     |  MaxDD: -$2,300     │
│      │   ●        ★                        |  sl_soft: 180       │
│   1.5│       ●        ★                    |  sl_hard: 280       │
│      │             ●     ★                 |  tp_target: 175     │
│   1.0│   ●  ●  ●  ●  (dominated)          |                     │
│      └────────────────────────── MaxDD     |  [ Apply + Backtest ]│
│   Presets: [ Conservative ] [ Balanced ] [ Aggressive ]           │
│   [ Save Pareto CSV ]                                             │
└────────────────────────────────────────────────────────────────────┘
```

### 6.2 Chart library

**Chart.js** (`scatter` type). Already-small bundle; Pareto-frontier line drawn as a second dataset (`showLine: true`, dashed). Lightweight Charts is unsuited (time-series-only).

### 6.3 Preset selectors

| Preset | Algorithm |
|---|---|
| Conservative | `argmin(MaxDD)` on the Pareto front |
| Balanced | Knee point: `argmin(L2 distance to utopia corner)` after normalising both axes to [0,1] across the front |
| Aggressive | `argmax(PF)` on the front |

### 6.4 Apply + Backtest

Click "Apply + Backtest" → splice the 3 fields into the settings store, navigate to `/`, immediately trigger `/api/backtest/box` so the dashboard's metrics/trade-list/chart reflect the chosen point. Single click, fully consistent UI state.

### 6.5 Save Pareto CSV

Pure-frontend: serialise the current Pareto front to a 6-column CSV (`trial_number, sl_soft, sl_hard, tp_target, pf_median, max_dd_max`) and trigger a download.

---

## 7. Failure modes

| Failure | Direction | Reason |
|---|---|---|
| `missing-candle-columns` | Re-raise → SSE `event: error` → study aborts | Every fold/trial fails identically |
| `missing-data-file` / `missing-parameter` | Re-raise → SSE `event: error` → study aborts | Config error, not per-trial |
| `malformed-box-geometry` | `TrialPruned` + SSE `event: warning` | Box CSV bug; other folds may still succeed |
| Any other `ConfigurationError` | `TrialPruned` + SSE `event: warning` | Surface without killing the study |
| `total_trades < min_trades_per_fold` | `TrialPruned` | Insufficient sample (Q3.2) |
| `profit_factor is None` | `TrialPruned` | Q3.1 |
| `profit_factor == 0.0` (no winners) | Return `(0.0, max_dd)` — let NSGA-II dominate it normally | Real data point |
| Fold has zero box rows | `TrialPruned` + warning | Date window outside all box rows |
| Insufficient data window (<90 days) | Request-validation error 422 | Reject upfront |
| Hung trial | Worker thread sets `should_stop` if `elapsed > max_duration_s` | Wall-clock guard |
| Server restart mid-study | Optuna SQLite persists; OptimizePanel offers "Continue?" cards on next load (Q6.1) | Auto-recovery |

---

## 8. Test plan

### Backend (Python / pytest)

| File | Coverage |
|---|---|
| `tests/test_walk_forward_splits.py` | N=3 and N=5 fold split correctness: every bar lands in exactly one fold; union == full range; equal time spans. |
| `tests/test_walk_forward_state_isolation.py` | Two folds back-to-back on the same `BoxLookup`; assert each fold's trades match a fresh-instance run. Locks the determinism claim in Section 4.3. |
| `tests/test_objective_edge_cases.py` | PF=None → `TrialPruned`; PF=0 → returns `(0.0, dd)`; `total_trades < min` → `TrialPruned`; `malformed-box-geometry` → `TrialPruned`; `missing-candle-columns` → re-raises (study abort). |
| `tests/test_nsga2_study_runs.py` | End-to-end on a tiny synthetic CSV (~200 bars + minimal box CSV); pop=4 × gen=2 × folds=2 = 16 trials; assert Pareto front non-empty + all values numeric. |
| `tests/test_api_optimize_sse.py` | POST `/api/optimize/box`; assert at least one each of `study_started`, `progress`, `trial`, `generation`, `complete`. Cancellation: `POST stop` produces a `complete` frame with partial Pareto front. |
| `tests/test_optimize_persistence.py` | Create study → kill mid-run → `GET /api/optimize/studies` lists it as incomplete → resume → study completes from where it stopped. |

### Frontend (TypeScript / vitest)

| File | Coverage |
|---|---|
| `frontend/tests/optimize_panel.test.ts` | Component renders empty state; consumes a mocked SSE event sequence; scatter plot updates; click-to-select updates the right-hand detail panel; Apply+Backtest navigates and writes to settings store. |
| `frontend/tests/optimize_presets.test.ts` | Three preset algorithms (conservative / balanced / aggressive) on a known Pareto front; assert each picks the expected trial. |

---

## 9. File-level deliverables

### Backend

```
src/optimization/__init__.py
src/optimization/study.py            — Optuna study lifecycle, SQLite storage
src/optimization/objective.py        — evaluate() function (Section 4.3)
src/optimization/walk_forward.py     — fold-split helper
src/optimization/sse_bridge.py       — Optuna callback → queue.Queue → SSE
src/optimization/persistence.py      — list/scan/cleanup studies
src/api/app.py                        — 4 new endpoints (POST /optimize/box,
                                        POST /optimize/<id>/stop, POST /optimize/<id>/resume,
                                        GET /optimize/studies)
src/api/schemas.py                    — OptimizeRequest, OptimizeResponse,
                                        TrialResult, StudySummary
```

### Frontend

```
frontend/src/components/OptimizePanel.vue       — main panel
frontend/src/components/ParetoScatter.vue       — Chart.js wrapper
frontend/src/components/StudyContinueCard.vue   — restored-study card
frontend/src/stores/optimize.ts                  — SSE-driven Pinia store
frontend/src/services/optimize_sse.ts            — fetch-based SSE consumer
frontend/src/types.ts                            — OptimizeRequest, TrialResult, ParetoPoint types
frontend/src/router.ts                           — add /optimize route
```

### Dependencies

- Python: add `optuna` to `requirements.txt` (pulls SQLAlchemy + alembic transitively for SQLite storage).
- Frontend: add `chart.js` (and `vue-chartjs` for Vue integration) to `package.json`.

### Data / runtime

- `optuna_studies.db` lives at the repo root, **gitignored**.

---

## 10. Out of scope (future work)

- Adaptive sampler switching (TPE if PF is multi-modal; CMA-ES if continuous and smooth). v1 is NSGA-II only.
- Distributed multi-machine search (Optuna supports it via shared DB, but adds operational complexity).
- Custom acquisition functions or hand-rolled hypervolume tracking. NSGA-II's intrinsic dominance + crowding is fine for v1.
- Searching more than 3 params at once. Future v2 may add `tp_watch_threshold_points` or `leg2_pullback_points`.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Optuna SQLite contention if two studies share the file | Use one DB file per study (study_name = file path). Drawback: cleanup logic gets complex. Alt: serialise study runs in a per-server lock. v1 picks single DB + serialised runs. |
| `_box_event_stream` worker pattern doesn't scale to long-running studies | The pattern already handles a 200-bar backtest with thousands of events. 600 events over 3 minutes is well within budget. |
| Pareto fronts with <3 points are uninteractive in the UI | Render an explanatory message: "Optimisation didn't find enough non-dominated trials. Try widening the search space or relaxing min_trades_per_fold." |
| Chart.js bundle bloat | Tree-shake to scatter + line types only. Should add <30 KB gzipped. If too much, fall back to native SVG via Vue templates. |

---

## 12. Approval signature

All locked decisions Q1–Q6.2 in Section 2 above were approved by the user across six brainstorm sections on 2026-05-23. Sections 3–6 were each individually approved before this spec was written.

**Next step:** user reviews this spec (see §13 below). After approval, invoke `superpowers:writing-plans` to produce the step-by-step implementation plan.

---

## 13. User review checklist

- [ ] Architecture (§3) — boundaries and file layout look right
- [ ] Data flow (§4) — request body, per-trial flow, constraint encoding
- [ ] SSE event protocol (§5) — payload shapes work for the frontend renderer you'd build
- [ ] UX (§6) — `/optimize` route layout, preset semantics, Apply+Backtest behaviour
- [ ] Failure modes (§7) — every failure has the right destination (abort vs prune)
- [ ] Test plan (§8) — coverage feels appropriate for v1
- [ ] Deliverables (§9) — file structure aligns with project conventions
- [ ] Risks (§11) — mitigation sounds sufficient

Open questions to flag:
- Anything you'd add to §10 "out of scope"?
- Anything in §11 "risks" that should escalate to §7 "failure modes"?
