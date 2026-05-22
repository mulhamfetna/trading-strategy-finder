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

### 6b. "Improve codebase to be OOP or FP, no replicated functions / messy code" — ❌ Not done

- Never addressed.
- Code is still procedural with duplicated patterns across `main.py` /
  `ultimate_dashboard.py` / `live_dashboard.py`. No refactor was attempted.

### 7. "Live dashboard using Dash or Streamlit instead of HTML" — ⚠️ Skeleton only

- Commits:
  - `4bf5ab7 test(dash): add failing test for Dash app import and layout`
  - `6015350 feat(dashboard): add minimal Dash app embedding generated HTML dashboards`
  - `84e3495 docs(dashboard): add Dash live preview run guide`
- File: `src/dashboard/dash_app.py` (39 lines).
- **Issue:** the Dash app just **iframes the pre-generated static HTML**. It
  isn't a live or interactive dashboard. No callbacks, no live data, no
  controls. Effectively a viewer for the old HTML output.

### 8. "Dashboard for data resolver + range options (train/test, start/end, timeframe)" — ❌ Not done (design only)

- Spec was being drafted in chat at end of session:
  - User picked option **B (full native Dash, no iframe)**.
  - Approved Architecture / Data flow / Error handling / Testing strategy
    sections.
  - **Session token expired** before any code was written.
- No implementation, no tests, no plan file committed.

### 9. "Test the old strategy on 9→12 2025 data and 1→6 2026 data" — ❌ Not done

- Never touched.
- No CSVs for those windows.
- No backtest runs.
- No report.
- Note: data is currently hardcoded to 2025 with cutoff Sep 30 in
  `src/data/splitter.py::filter_2025`.

### 10. "Take care of in-candle TP/SL for sudden spikes" — ❌ Not done

- Never touched.
- `notes.md` records the design intent (SL-first conservative / TP-first
  optimistic / direction proxy) but no implementation exists.
- Backtest still resolves TP/SL on per-candle close, ignoring intra-candle
  path.

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

### 12. "Sort docs, master documentation router, update content" — ⚠️ Partial

- Commit: `a1d52ed docs(router): add master documentation index`
- File: `docs/MASTER_DOCUMENTATION.md` (52 lines).
- Earlier in the session: `Project_Documentation/` skeletons created,
  legacy files archived to `docs/legacy/`, interview prep moved into
  `docs/Tutorials/`.
- **Issues:**
  - The router is a thin 52-line index.
  - "Update content to match current codebase" was not done.
  - `Project_Documentation/*.doc.md` still references the OLD root-level paths
    (pre-`src/main/` move).
  - README still references the old paths.

---

## Score

- ✅ **Fully done: 7** — items 1, 2 (local only), 3, 4, 5, 6a, 11 (iter 3, 2026-05-22)
- ⚠️ **Partial / skeleton: 2** — items 7, 12
- ❌ **Not started: 4** — items 6b, 8, 9, 10

Approximately 58% solid, 17% partial, 33% untouched.

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
