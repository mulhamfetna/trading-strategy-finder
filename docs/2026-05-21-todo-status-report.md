# TODO Status Report — 2026-05-21

> Comparison of `TODO.md` against actual work done in the Copilot session
> `185b7db7-31e5-4e8c-9121-8750b820ad5b` (2026-05-15 → 2026-05-21).
> Source transcript: `copilot-session-185b7db7-31e5-4e8c-9121-8750b820ad5b.md` (30,948 lines).

## Session timeline summary

The session had two distinct phases:

1. **Pre-TODO work (turns 1–20)** — debugging council reports, doc skeletons,
   interview prep, training-split dashboard runner (`run_dashboard_on_train.py`).
2. **TODO execution (turns 21–36)** — the user pasted `TODO.md` at line 14076 of
   the transcript, then 8 "proceed" turns walked through it one phase at a time
   until the session token expired mid-spec on TODO item 8.

All TODO-execution work landed across **two worktrees**, none of it pushed:

| Ref | HEAD | What lives here |
|---|---|---|
| `origin/master` | `d5dd641` | Pre-refactor baseline |
| local `master` | `fe82031` | One docs-spec commit ahead of origin |
| `phase1-core-engine` (worktree) | `41aaf79` | Template extraction + candlestick |
| `phase3-live-dashboard` (worktree) | `74aa367` | src/main move, Dash app, revisions log, master doc router, `output/dashboard/` |
| tag `v1.0-working` | `635d584` → `1890298` | Annotated freeze marker on the phase3 branch |
| Workspace (root) | `8f2d6ea` (detached) | src/main move + test imports only |

The two worktree branches **diverged** before the `src/main/` move, so the
candlestick/template work and the Dash/src-main work are not currently
integrated on any single branch.

---

## TODO-by-TODO status

Numbering follows the user's original list (preserving the duplicate "6").
Legend: ✅ done · ⚠️ partial · ❌ not started.

### 1. "Regrrate the data for the test data" — ✅ Done (re-run, no diff)

- Output regenerated during the session.
- The `run_dashboard_on_train.py` runner was added earlier in the session and
  is used for the train split too.
- Outputs were not committed because the regeneration produced an empty diff.

### 2. "Freeze the branch v1.0 working" — ✅ Done (local only)

- Branch `v1.0-working` + annotated tag `v1.0-working` at commit `1890298`
  (tag object `635d584`).
- **Not pushed to `origin`.**

### 3. "Add candle view, closing and opening price" — ✅ Done (iter 1, 2026-05-22)

- `src/main/ultimate_dashboard.py` now emits a Plotly candlestick trace
  (open/high/low/close) instead of a close-only line.
- A 4-card OHLC summary panel (Latest Open / Close / High / Low) sits above
  the chart in the rendered HTML.
- Test `test_generate_html_uses_candlestick_chart` locks in the candlestick
  trace + OHLC summary requirements.
- Implementation was replayed from `phase1-core-engine` (`41aaf79`) onto the
  current `src/main/ultimate_dashboard.py` path — the original branch was
  not rebased because it carried template/renderer changes that belong in
  iter 2.

### 4. "Separate HTML stuff into template" — ✅ Done (iter 2, 2026-05-22)

- New module `src/dashboard/template_renderer.py` — pure-function renderer.
  Placeholder syntax `{{NAME}}` (uppercase). Raises `KeyError` on missing
  values, `FileNotFoundError` on missing template, and does single-pass
  substitution so a replacement value cannot be re-substituted.
- New template `templates/ultimate_dashboard.html.tpl` (~650 lines) contains
  the full HTML shell with **19 named slots** (`{{TITLE}}`, `{{METRICS_BLOCK}}`,
  `{{OHLC_SUMMARY}}`, `{{TRADES_HTML}}`, `{{LOGS_HTML}}`, `{{CHART_JSON}}`,
  `{{PARAMS_BLOCK}}`, etc.).
- `src/main/ultimate_dashboard.py::generate_html` no longer inlines the HTML
  shell. It builds Python fragments (metrics grid, params table) and calls
  `render_template(...)`. File shrank from 1329 → 685 lines.
- 5 new renderer tests + 2 new template-separation tests (locks in: template
  file exists with all required slots; Python source no longer contains
  `<!DOCTYPE html>`).
- All previously-green tests still pass (15 dashboard tests + 12 supporting
  module tests).

### 5. "Organize the three Python files into src/main" — ✅ Done

- Commits:
  - `cf904c9 refactor(entry): move entry scripts into src/main/`
  - `8f2d6ea refactor(tests): update imports after moving entry scripts`
- All four entry scripts (`main.py`, `ultimate_dashboard.py`,
  `fast_optimizer.py`, `live_dashboard.py`) now live in `src/main/` on
  `phase3-live-dashboard`.
- Caveat: lives only on `phase3-live-dashboard` — not on `master` and not on
  `phase1-core-engine`.

### 6a. "Create a log of mistakes from revisions, lessons learned" — ✅ Done

- Commit: `1890298 docs(revisions): add mistakes log and lessons learned`
- Files:
  - `docs/revisions/REVISION_LOG.md` — 6 rounds of mistakes
  - `docs/revisions/LESSONS_LEARNED.md` — 7 lessons
- Lives on `phase3-live-dashboard` worktree.

### 6b. "Improve codebase to be OOP or FP, no replicated functions / messy code" — ✅ Done (iter 7, 2026-05-22)

Hybrid OOP/FP per the refactor policy in
`docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md`:

**New OOP package `src/strategy/`:**

- `ScalpingStrategy` — config (RSI period, EMA periods, vol threshold,
  ML toggle) + lifecycle (`prepare`, `train_ml`, `apply_ml`). Defaults
  match v1.0.0 frozen parameters.
- `Backtester` — config (capital, SL, TP, fees, slippage, max daily
  trades, **`tp_sl_resolution` from iter 4**) + `run(df)`.

**Kept FP (pure transforms):**

- `src/indicators/{scalping,day_trading,intraday}.py` — unchanged.
- `src/signals/base_signals.py`, `src/signals/ml_filter.py` —
  unchanged.
- `src/backtest/engine.py::run_backtest` and
  `_resolve_intra_candle_exit` — unchanged (the engine is FP; the
  `Backtester` class is a config carrier that delegates to it).
- `src/backtest/metrics.py` — unchanged.
- `src/dashboard/template_renderer.py` — unchanged (already FP).

**Duplication killed:**

- `src/main/run_strategy.py` (iter 5) — `_prepare_scalping` helper
  removed; pipeline now driven by `ScalpingStrategy` + `Backtester`.
- `src/main/main.py::run_scalping_strategy` — 8-step inline pipeline
  replaced with 4 calls into the new classes.

**Intentionally NOT refactored** (scope discipline):

- `src/main/ultimate_dashboard.py` — tightly coupled to its dashboard
  generation; refactor would be its own multi-day project, low payoff
  for the duplication-kill goal.
- `src/main/main.py::run_day_trading_strategy` / `run_intraday_strategy`
  — those pipelines diverge from scalping enough that a shared class
  would be over-engineering. Left for a future strategy-protocol pass
  if the day/intraday paths get used more.

9 new tests in `tests/test_strategy_oop.py` + 4 existing runner tests +
8 backtest tests + 4 signal tests + 37 other supporting tests all green.

### 7. "Live dashboard using Dash or Streamlit instead of HTML" — ✅ Done (iter 8, 2026-05-22, combined with item 8)

### 8. "Dashboard for data resolver + range options (train/test, start/end, timeframe)" — ✅ Done (iter 8, 2026-05-22)

Items 7 and 8 were the same goal (per the iter sequencing spec) and were
implemented together. `src/dashboard/dash_app.py` was rewritten from a
40-line iframe viewer into a 280-line native Dash app driven by the
iter 7 OOP classes:

**Controls (resolver pane):**

- Dataset radio: `train` / `test` (splits at `2025-06-30` by default).
- Start/end date inputs (free-form `YYYY-MM-DD`).
- Timeframe dropdown (`15min` only in v1; placeholder for future TFs).
- TP/SL resolution dropdown: `conservative` / `optimistic` /
  `direction-proxy` (wired through to `Backtester` from iter 4).
- Apply button.

**Outputs:**

- Native Plotly candlestick chart with entry/exit markers (no iframe).
- 6 metric cards (Net Profit, Win Rate, Profit Factor, Sharpe, Max DD,
  Total Trades).
- Trade list (top 50, scrollable).
- Error panel that surfaces invalid dates, empty ranges, missing CSV,
  pipeline failures.

**Architecture:**

- `build_app(data_path)` factory — no module-level state; tests can
  build apps without monkey-patching.
- `on_apply(...)` extracted as a pure function so callback logic is
  unit-testable without a Dash server.
- Pipeline: `load_data` → `filter_by_date_range` (iter 5) →
  `split_train_test` → `ScalpingStrategy.prepare` (iter 7) →
  `Backtester.run` (iter 7) → `calculate_metrics`.

**Run:**

```bash
python3 -m src.dashboard.dash_app
# Open http://localhost:8050
```

7 RED layout + 4 RED callback tests added (`tests/test_dash_resolver.py`).
Existing `test_dash_app.py` updated to require the new Apply button id
and forbid iframes. All 72 tests green.

### 9. "Test the old strategy on 9→12 2025 data and 1→6 2026 data" — ✅ Framework done (iter 5, 2026-05-22)

The framework piece is done. Data acquisition for those specific windows
is **explicitly deferred** (user does not have the CSVs yet).

Framework changes:

- `src/data/splitter.py::filter_by_date_range(df, start, end)` —
  generalized inclusive date-range filter that supersedes `filter_2025`.
  Works with `Date` or `timestamps` columns. Handles year-boundary ranges
  (e.g. 2025-09 → 2026-06).
- `filter_2025` is kept as a thin backwards-compat shim that delegates to
  `filter_by_date_range('2025-01-01', '2025-09-30')`.
- New entry point `src/main/run_strategy.py`:

  ```bash
  python3 -m src.main.run_strategy \\
      --data 1min.csv \\
      --start 2025-09-01 --end 2025-12-31 \\
      --strategy scalping \\
      --train-test-split 2025-10-15 \\
      --tp-sl-resolution conservative
  ```

  Loads CSV → filters by range → optionally splits train/test → runs
  scalping pipeline (RSI + EMA + Volume + ML filter) → backtest →
  prints metrics. Pluggable resolution mode from iter 4.

Once Sep-Dec 2025 / Jan-Jun 2026 CSVs are dropped at repo root, item 9
finishes by just running the CLI for those date ranges.

4 CLI tests + 5 new date-range tests + 1 backwards-compat test cover
the framework; all 32 supporting tests still green.

### 10. "Take care of in-candle TP/SL for sudden spikes" — ✅ Done (iter 4, 2026-05-22)

`src/backtest/engine.py` now uses High/Low (not just Close) for TP/SL
detection and exposes a `tp_sl_resolution` parameter for the tie-break case
where High >= TP **and** Low <= SL in the same candle:

- `'conservative'` (default) — assume SL hit first (worst case)
- `'optimistic'` — assume TP hit first (best case)
- `'direction-proxy'` — green candle (Close > Open) -> TP first; red -> SL
  first; doji -> falls back to conservative

The new pure-function `_resolve_intra_candle_exit` (FP per refactor policy)
encapsulates the resolution logic. Exits trigger on the chosen level's
exact price, then slippage is applied — this matches realistic execution
better than the previous close-only check.

5 new tests lock in: each mode's behavior, default = conservative, and
single-side hit (only TP or only SL) exits correctly regardless of mode.
`run_backtest_15min` in `src/main/ultimate_dashboard.py` is **not** covered
by this change — it's a separate function and would need its own pass
(follow-up).

### 11. "Move outputs to output/ directory" — ✅ Done (iter 3, 2026-05-22)

All entry scripts now write under `output/`:

- `src/main/ultimate_dashboard.py` → `output/dashboards/{ultimate_trading_dashboard.html,dashboard_data.json}`
- `src/main/live_dashboard.py` → `output/dashboards/{live_trading_dashboard,equity_curve_dashboard}.html`
  (was `output/dashboard/` singular - renamed to plural for consistency)
- `src/main/fast_optimizer.py` → `output/configs/best_config.txt` (was repo root)
- `run_dashboard_on_train.py` → `output/dashboards/{ultimate_trading_dashboard_train.html,dashboard_data_train.json}`
- `src/dashboard/dash_app.py` reads from `output/dashboards/` (with `docs/` fallback for legacy)

`.gitignore` adds `output/`. The six stale tracked artifacts in `docs/` were
removed (`docs/dashboard_data.json`, `docs/dashboard_data_train.json`,
`docs/equity_curve_dashboard.html`, `docs/live_trading_dashboard.html`,
`docs/trading_dashboard.html`, `docs/ultimate_trading_dashboard.html`).
`docs/legacy/index.html` is preserved as a historical archive.

4 new path-constant tests + 1 updated existing test pin the layout.

### 12. "Sort docs, master documentation router, update content" — ✅ Done (iter 6, 2026-05-22)

`docs/MASTER_DOCUMENTATION.md` rewritten as a real 10-section router:
start-here · code routing · trading concepts · design specs ·
revision history · per-file docs · frozen versions · long-form refs ·
generated output · legacy archive. Each section points to current
paths only (no more stale `docs/interview_preparation/` or
`docs/ultimate_trading_dashboard.html` references).

`README.md` rewritten for the post-iter codebase: shows
`python3 -m src.main.X` invocation pattern, lists all 5 entry
scripts (including `run_strategy.py` from iter 5), points at
`output/dashboards/` for artifacts, references the iter sequencing
spec and live status report.

4 of the `Project_Documentation/*.doc.md` files (the entry-script
ones) rewritten to reflect `src/main/` paths, current outputs in
`output/`, and the gotchas from iters 1-5. The other `.doc.md`
files (core modules, data files, tests) describe stable code and
remain accurate; deferred until they actually drift.

`AGENTS.md` reference to the removed `docs/interview_preparation/`
directory cleaned up.

6 doc-consistency tests pin: tutorials path, output paths,
iter artifacts mentioned, README invocation pattern, entry-script
doc paths, no stale `interview_preparation/` in current docs.

---

## Score

- ✅ **Fully done: 13** — items 1, 2 (local only), 3, 4, 5, 6a, 6b, 7 (iter 8), 8 (iter 8), 9 (framework), 10, 11, 12
- ⚠️ **Partial / skeleton: 0**
- ❌ **Not started: 0**

All 12 numbered TODO items addressed (with item 9 framework-done pending
data). Item 2 is the only one not pushed to origin yet — that's iter 9's
job.

---

## Biggest open risks

1. **Branch fragmentation.** Items 3+4 live on `phase1-core-engine`,
   items 5+7+11 live on `phase3-live-dashboard`. They were developed in
   parallel from before the `src/main/` move. Merging them is non-trivial
   because `phase1-core-engine` still uses root-level `ultimate_dashboard.py`
   while `phase3-live-dashboard` uses `src/main/ultimate_dashboard.py`. The
   candlestick/template change needs to be re-applied on top of the moved
   file.

2. **Nothing is pushed.** `origin/master` is still at `d5dd641`. The freeze
   tag `v1.0-working`, the Dash app, the candlestick chart, the `src/main/`
   move — all local.

3. **Item 4 is misleadingly marked done.** The committed template is literally
   `{{BODY}}` — the giant HTML string is still inside Python; only the
   outermost wrapper was externalized.

4. **Item 7 is also misleadingly done.** It's an iframe viewer, not a live
   dashboard. Item 8 was meant to fix this with native Dash components but
   never got past the design Q&A.

5. **Items 9 and 10 are completely untouched.** These are the only TODO items
   with real *trading-correctness* implications (out-of-sample validation on
   a new period, and intra-candle TP/SL spike handling). Both are pure no-ops
   in the current code.

6. **The local `master` branch is one commit ahead of `origin/master` with
   only a spec doc** (`fe82031`) — it does not contain any of the TODO work.
   If pushed as-is, none of the TODO work goes with it.

---

## Suggested next moves

1. Merge `phase3-live-dashboard` into `master`, then rebase
   `phase1-core-engine` (candlestick/template) on top so the candlestick code
   uses the moved `src/main/ultimate_dashboard.py`.
2. Push `master` + the `v1.0-working` tag.
3. Finish item 4 properly (real template, not a single `{{BODY}}` slot).
4. Either implement item 8 (native Dash controls) or stop calling item 7
   "done" — they're the same goal.
5. Plan items 9, 10, 6b explicitly — they are real engineering work that
   hasn't been touched.

---

## Commit reference (chronological, TODO-related only)

```
74aa367 refactor(outputs): write live dashboards to output/dashboard      # item 11
a1d52ed docs(router): add master documentation index                       # item 12
1890298 docs(revisions): add mistakes log and lessons learned              # item 6a (= v1.0-working)
84e3495 docs(dashboard): add Dash live preview run guide                   # item 7
6015350 feat(dashboard): add minimal Dash app embedding generated HTML dashboards  # item 7
4bf5ab7 test(dash): add failing test for Dash app import and layout        # item 7
8f2d6ea refactor(tests): update imports after moving entry scripts         # item 5
cf904c9 refactor(entry): move entry scripts into src/main/                 # item 5
41aaf79 refactor(dashboard): extract template and candlestick chart        # items 3, 4
1d7ffd9 docs(plan): add dashboard template candlestick plan                # planning
c6df110 docs(spec): add dashboard template candlestick design              # planning
3b13f42 feat(backtest): add phase1 runner and outputs                      # phase1 setup
```
