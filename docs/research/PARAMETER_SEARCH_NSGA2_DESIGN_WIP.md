# NSGA-II Optimisation Design — WIP Checkpoint

**Status:** Mid-brainstorm. Suspended to fix an unrelated bug.
**Date suspended:** 2026-05-23
**Parent study:** `docs/research/PARAMETER_SEARCH_STUDY.md`
**Resume marker:** "Section 3 of 6 — The objective function" (sections 1 and 2 approved by user).

## How to resume

When you're ready: paste this file's contents back to me, or just say *"resume the NSGA-II brainstorm from section 3"* and I'll pick up where this checkpoint ends. All locked decisions below are settled — no need to re-litigate.

---

## Locked decisions (Q&A)

| # | Decision | Choice |
|---|---|---|
| Q1 | Objectives | **PF + Max Drawdown** — maximise `profit_factor`, minimise `max_drawdown`. Clean 2D Pareto front. |
| Q2 | Scoring strategy | **Walk-forward folds** — N folds, median(PF) and max(MaxDD) across folds. |
| Q3 | Search space (v1) | **3 params:** `sl_soft_points`, `sl_hard_points`, `tp_target_points`. Constraint: `sl_hard ≥ sl_soft + 50`. |
| Q4 | Search budget | **Light:** population 40 × generations 15 × 3 folds = **1,800 backtests**. Iteration-friendly. |
| Q5 | Surface area | **Live in the dashboard** — new OptimizePanel.vue with SSE stream, Pareto front updates per generation. |
| Approach | Library | **Optuna `NSGAIISampler`** — industry default, FastAPI/SSE-friendly, scaling path to TPE/CMA-ES is one line. |

---

## Sections approved so far

### ✅ Section 1 — Architecture overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        Vue OptimizePanel                           │
│  param-range inputs · budget preset · live Pareto front scatter    │
└────────────────────────────────────────────────────────────────────┘
                              ▲ SSE: progress / generation / complete
                              │
┌────────────────────────────────────────────────────────────────────┐
│              POST /api/optimize/box  →  _opt_event_stream          │
│              POST /api/optimize/<id>/stop                          │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                      src/optimization/                             │
│                                                                    │
│   study.py          — Optuna study lifecycle (NSGAIISampler)       │
│   objective.py      — wraps walk_forward.evaluate → (PF, MaxDD)    │
│   walk_forward.py   — N-fold time-based CSV split + aggregation    │
│   sse_bridge.py     — Optuna callback → SSE event queue            │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
            ┌──────────────────────────────────────┐
            │  BoxStrategy.backtest(df_fold)       │  (existing)
            │  → metrics{PF, MaxDD, ...}           │
            └──────────────────────────────────────┘
```

**Approved boundaries:**
- New `src/optimization/` package; depends on `src/strategy/` but not vice-versa.
- `objective.py::evaluate(params: dict) → (PF, MaxDD)` is the only seam Optuna sees.
- `sse_bridge.py` reuses the existing SSE worker-thread + `queue.Queue` pattern from `_box_event_stream`.
- Frontend `OptimizePanel.vue` is a new component; coexists with `SettingsPanel.vue`. "Apply Selected Params" writes to settings store.

### ✅ Section 2 — Data flow

Full end-to-end flow approved. Key points:
1. **Baseline params travel in the request.** Frontend sends its entire current `BoxParams`; optimiser splices the 3 searched fields per trial.
2. **Constraint `sl_hard ≥ sl_soft + 50` encoded structurally:** Optuna suggests `sl_hard ∈ [sl_soft + 50, 600]` rather than rejecting violators.
3. **Fold aggregation:** `median([trial.PF])` and `max([trial.MaxDD])`. Median resists outlier folds; max-DD reports worst case.

SSE event timing:
- `event: trial` after each backtest (current trial's params + metrics)
- `event: generation` after every `population_size` trials (current Pareto front)
- `event: complete` when study finishes (final Pareto front + top-5 by PF + top-5 by lowest DD)

---

## Sections still to design

### ⏳ Section 3 — The objective function (next on resume)

To cover:
- Exact signature: `evaluate(suggested_params: dict, baseline_params: BoxStrategyParams, folds: list[pd.DataFrame]) → tuple[float, float]`
- Edge cases that must be handled, returning sentinel values that NSGA-II won't pick:
  - `profit_factor is None` (no losses) — return what? `+inf`? Skip with `optuna.TrialPruned`?
  - `profit_factor == 0.0` (no winners) — return `-inf` for the PF objective? Or treat as dominated?
  - `total_trades < threshold` (insufficient sample) — prune
  - `BoxStrategy.backtest` raises `ConfigurationError` — prune
- Constraint encoding: reparameterisation `sl_hard = sl_soft + δ` where `δ ∈ [50, 600 − sl_soft]`
- Per-fold backtest determinism check (same params → same metrics for a given fold)
- Whether to expose `min_trades_per_fold` as a request param or hardcode it (no-fallback rule says expose)

Anchor question to user at start of Section 3:
> "Edge case: a candidate that has zero losses returns PF=None. How should NSGA-II treat it — prune (skip), or rank as 'best possible' so it dominates the Pareto front? Pruning is safer (None usually means insufficient data); 'best possible' might find genuine winners but more often masks tiny samples."

### ⏳ Section 4 — SSE event protocol

To cover:
- Full JSON shape of each event type (`trial`, `generation`, `complete`, `error`, `warning`)
- Backwards compat with the existing box-backtest SSE shape (same `event: error` payload schema with `code` + `message` + `system_status`)
- How `event: trial` gets throttled (1,800 events would be noisy — only emit every Nth trial? Or send all and let frontend throttle render?)
- How the frontend builds the Pareto front incrementally from `event: trial` stream
- Cancellation: `POST /api/optimize/<study_id>/stop` — semantics (graceful: finish current generation; or abrupt: kill worker thread)

### ⏳ Section 5 — Pareto-point selection (UX)

To cover:
- Visualisation: scatter plot of PF vs MaxDD with Pareto-frontier curve highlighted
- Three preset selectors: **Conservative** (lowest MaxDD on the front), **Balanced** (knee point), **Aggressive** (highest PF on the front)
- Click-to-select interaction: user clicks a Pareto point, panel shows the `(sl_soft, sl_hard, tp_target)` for that point
- "Apply selected params" button → writes to settings store, marks `backtest.isDirty=true`
- "Save Pareto front as CSV" for offline analysis

Anchor question at start of Section 5:
> "Should clicking a Pareto point ONLY load the three searched params, or also re-run a single backtest with the full settings + selected params to refresh the metrics card / trade list?"

### ⏳ Section 6 — Failure modes & testing

To cover:
- ConfigurationError propagation from `BoxStrategy.backtest` to SSE error frame
- Fold-split edge cases: too few candles per fold; weekend gaps
- Optuna study cancellation mid-trial
- Resume across server restart (Optuna SQLite study persistence)
- Test plan:
  - `test_walk_forward_splits.py` — fold boundary correctness
  - `test_objective_edge_cases.py` — PF=None, PF=0, insufficient trades, ConfigurationError
  - `test_nsga2_study_runs.py` — small synthetic CSV; assert N trials run, Pareto front non-empty
  - `test_api_optimize_sse.py` — end-to-end SSE event stream
  - `test_optimize_panel.test.ts` — frontend SSE consumption + scatter render

---

## After Section 6 — Spec writing

Per the brainstorming skill flow, the next steps after section approval are:
1. Write `docs/superpowers/specs/2026-05-23-nsga2-optimization-design.md` (full validated spec)
2. Spec self-review (placeholders / consistency / scope / ambiguity)
3. User reviews spec file
4. Invoke `superpowers:writing-plans` to produce the implementation plan

**Do NOT skip straight to implementation on resume.** The brainstorming hard gate requires design approval first.

---

## Open task list (for resume)

The brainstorming skill set up tasks #62–#67. Current status:

| Task | Status |
|---|---|
| #62 Explore project context | ✅ completed |
| #63 Clarifying questions | ✅ completed (5 questions + library choice) |
| #64 Propose 2-3 approaches | ✅ completed (Approach A — Optuna) |
| #65 Present design in sections | 🔄 in_progress (2 of 6 sections approved) |
| #66 Write design spec doc | ⏳ pending |
| #67 User reviews spec + invoke writing-plans | ⏳ pending |

On resume, continue from Section 3.
