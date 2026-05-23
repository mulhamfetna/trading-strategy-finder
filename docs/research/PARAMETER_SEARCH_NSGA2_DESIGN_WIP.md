# NSGA-II Optimisation Design — WIP Checkpoint

**Status:** Mid-brainstorm. Resumed on dev branch after a v3 traversal/HOLD-state intermezzo.
**Date originally suspended:** 2026-05-23
**Date refreshed for v3.1:** 2026-05-23
**Parent study:** `docs/research/PARAMETER_SEARCH_STUDY.md`
**Resume marker:** "Section 3 of 6 — The objective function" (sections 1 and 2 approved by user).

## How to resume

Say *"resume the NSGA-II brainstorm from section 3"* and I'll pick up where this checkpoint ends. All locked decisions below are settled — no need to re-litigate. Read the §"v3.1 changes that affect this design" block before answering Section 3's anchor question — a few edge cases moved.

---

## v3.1 changes that affect this design (added 2026-05-23 after the traversal/HOLD landing)

The post-pause work on the `v3-stable-dynamic-backtest-dashboard` branch (now also pinned at the same-named tag) changed several things in the engine that this design wraps. Locked decisions Q1-Q5 still hold; the impacts are concentrated in **Section 3 (objective function)** and **Section 6 (failure modes & testing)**.

### 1. BoxLookup is now stateful (per-(row, level) traversal state machine)

- `BoxLookup` carries two mutable dicts: `_state` (`'above' | 'below' | None`) and `_inside_seen` (bool), keyed by `(row_date, level_name)`.
- `BoxStrategy.backtest()` calls `self._box.reset_state()` at the start of every run, so a single BoxLookup instance can be re-used across N walk-forward folds *as long as we call `.backtest()` per fold* — which is exactly our pattern.
- **Walk-forward implication:** `walk_forward.py` can hold ONE `BoxLookup` for all folds (CSV load happens once). Each fold drives its own `BoxStrategy.backtest(df_fold)`; state isolation is automatic. **No code change required vs the original design** — confirmed by `tests/test_box_strategy_integration.py::test_back_to_back_backtest_resets_state`.

### 2. Traversal rule reduces signal frequency

- Old rule: a single bar with close past the edge fires LONG/SHORT.
- New rule (v3.1): the close must `'below' → 'inside' → 'above'` (or the reverse) — three-state traversal with an explicit gap-skip rejection.
- **Impact on the objective:** fewer trades per fold. The `total_trades < min_trades_per_fold` prune branch will fire more often. **Recommend bumping the default `min_trades_per_fold` floor downward** (e.g. from a notional 30 to 15) so realistic candidates aren't pruned, but make it a request param (no-fallback rule — see Q3 of Section 3).

### 3. New `'hold'` aggregate signal value

- BoxLookup's `signal` field is now `'long' | 'short' | 'hold' | None` (was `'long' | 'short' | None`).
- The optimiser doesn't read raw signals — only summary metrics — so this is invisible to NSGA-II. Worth noting only because any future test fixture that asserts on raw signals must expect `'hold'` instead of `None` for "active row, no traversal" bars.

### 4. Two new `ConfigurationError` codes the objective must handle

- `malformed-box-geometry` — raised by `BoxLookup._classify` when a box row has `upper <= lower`. Catastrophic data error; **prune trial**.
- `missing-candle-columns` — raised by `_candles_from_df` when the 4h CSV lacks Open/High/Low/Close/Volume. Catastrophic data error; **abort the entire study** (every fold of every trial will fail the same way). Section 3 should distinguish "single trial prune" vs "fast-fail the study".

### 5. New per-bar `_on_bar` hook in `ScalingStrategy.backtest`

- The parent backtest loop now calls `self._on_bar(idx, candle)` once per bar BEFORE exit/entry checks. Default no-op; `BoxStrategy` overrides it to drive the traversal state machine on every bar.
- **Implication for `walk_forward.py`:** if we ever want to capture per-bar diagnostics (e.g., signal counts per fold for diagnostics), the hook is the seam. Out of scope for v1 but easy to add later.

### 6. `big_candle_resolution` is a tunable enum now

- `BoxStrategyParams.big_candle_resolution` ∈ `{'big_candle_wins', 'box_wins', 'skip'}` is a required field with no default. The dashboard exposes it.
- **Q for Section 3:** should we search this as a 4th param (categorical), or freeze it at the baseline value? Categorical params interact poorly with NSGA-II's crossover; freezing is the pragmatic v1 choice.

### 7. No-fallback rule extended to internal `.get(key, default)`

- Round 14b sweep closed 4 silent fallbacks (`trade['legs']`, `trade['entry_idx']`, `_LEVEL_COLORS[label]`, `df['Volume']` upfront validation).
- **Implication for the optimiser:** the objective MUST construct a complete `BoxStrategyParams` dict per trial — splicing only the searched fields into the baseline. No "we'll let the dataclass fill in the default" path exists. Already aligned with the locked Q2 / Q3 decisions; just reinforcing.

---

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
  - `total_trades < min_trades_per_fold` (insufficient sample) — prune. **v3.1 note:** traversal semantics produce fewer trades than the old edge-position rule, so the threshold should sit on the lower side (≈15 instead of ≈30 for a year of NQ_4h).
  - `BoxStrategy.backtest` raises `ConfigurationError(code='malformed-box-geometry')` (v3.1 new) — prune the trial; the box data is corrupt for this fold.
  - `_candles_from_df` raises `ConfigurationError(code='missing-candle-columns')` (v3.1 new) — fast-fail the entire STUDY; every fold will fail identically. Treat differently from per-trial prune.
  - Generic `ConfigurationError` (any other code) — prune trial, log code + system_status to the SSE `event: warning` stream so the user can see what's wrong.
- Constraint encoding: reparameterisation `sl_hard = sl_soft + δ` where `δ ∈ [50, 600 − sl_soft]`
- Per-fold backtest determinism check (same params → same metrics for a given fold) — **already verified** by `tests/test_box_strategy_integration.py::test_back_to_back_backtest_resets_state`.
- Whether to expose `min_trades_per_fold` as a request param or hardcode it (no-fallback rule says **expose**).
- v3.1 open question: search `big_candle_resolution` as a 4th categorical param, or freeze at the baseline value? (Categorical params hurt NSGA-II crossover efficiency — recommend freeze for v1.)

Anchor questions to user at start of Section 3 (v3.1-updated):
> Q3.1 — "Edge case: a candidate that has zero losses returns PF=None. How should NSGA-II treat it — prune (skip), or rank as 'best possible' so it dominates the Pareto front? Pruning is safer (None usually means insufficient data); 'best possible' might find genuine winners but more often masks tiny samples."
>
> Q3.2 (new) — "Under v3.1 traversal semantics the engine fires fewer trades. What `min_trades_per_fold` floor should the optimiser default to, and should this be a UI control or a baseline-spliced field? (No-fallback rule means it must be one or the other — no implicit default.)"
>
> Q3.3 (new) — "Search `big_candle_resolution` as a 4th categorical param, or freeze it at the user's baseline value to keep NSGA-II crossover focused on the three continuous fields?"

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
- ConfigurationError propagation from `BoxStrategy.backtest` / `_candles_from_df` to SSE error frame. Distinguish:
  - `malformed-box-geometry` → per-trial prune + warning event (v3.1 new)
  - `missing-candle-columns` → study-level abort with error event (v3.1 new)
  - `missing-parameter` / `missing-data-file` → study-level abort
  - any other ConfigurationError → per-trial prune
- Fold-split edge cases: too few candles per fold; weekend gaps; **partial box CSV coverage** (a fold's date range falls outside any active box row → BoxLookup returns `signal=None`, zero trades, → prune branch).
- Optuna study cancellation mid-trial.
- Resume across server restart (Optuna SQLite study persistence).
- **v3.1 state-machine isolation check:** add a `test_walk_forward_state_isolation.py` that runs two folds back-to-back on the same `BoxLookup` and asserts each fold's trade count matches a fresh-instance run. The integration test `test_back_to_back_backtest_resets_state` already covers this at the strategy layer; we need the optimiser-layer equivalent.
- Test plan:
  - `test_walk_forward_splits.py` — fold boundary correctness
  - `test_walk_forward_state_isolation.py` (v3.1 new) — back-to-back folds on shared BoxLookup
  - `test_objective_edge_cases.py` — PF=None, PF=0, insufficient trades, malformed-box-geometry, missing-candle-columns, generic ConfigurationError
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
