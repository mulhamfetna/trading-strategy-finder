# Finish-TODO Sequencing Design — 2026-05-22

## Problem Statement

`TODO.md` lists 12 items (with a duplicate "6" giving 13). After the Copilot
session ending 2026-05-21 and the master-branch consolidation on 2026-05-22,
the state is:

- ✅ Genuinely done: 1, 5, 6a
- 🔧 Done but not pushed: 2
- ⚠️ Partial / misleadingly done: 3, 4, 7, 11, 12
- ❌ Completely untouched: 6b, 8, 9, 10

This document specifies the **sequencing logic** for finishing the remaining
9 items as discrete iterations, each ending in TDD-validated, committed,
documented work. It does **not** specify per-task code — that lives in the
companion plan `2026-05-22-finish-todo-plan.md`.

Reference for current status: `docs/2026-05-21-todo-status-report.md`.

## Sequencing Logic

Order is chosen by **risk × dependency**, not by TODO-list number:

1. **Cheap structural wins first** to consolidate the surface (iters 1–3).
2. **Trading-correctness items next** (iters 4–5) — these have actual
   strategy implications, not just UI.
3. **Doc sync only after the surface is final** (iter 6) — updating docs
   before the code stops moving wastes effort.
4. **Big OOP/FP refactor late** (iter 7) — it refactors code already
   locked down by tests from earlier iterations.
5. **Native interactive dashboard last** (iter 8) — depends on the refactor
   so it reuses the new Strategy/Backtester classes.
6. **Publish (push to origin) only when everything is green** (iter 9).

## Iterations

| # | Iter | TODO item(s) | Effort | Definition of done |
|---|---|---|---|---|
| 1 | Integrate candlestick + OHLC | 3 | S | `phase1-core-engine` (41aaf79) rebased onto master at `src/main/ultimate_dashboard.py`; candlestick chart visible; OHLC summary present; new test for candlestick payload green; AGENTS.md / status report updated |
| 2 | Real template separation | 4 | M | `templates/ultimate_dashboard.html.tpl` contains real HTML shell with named slot placeholders (`{{TITLE}}`, `{{METRICS_GRID}}`, `{{TRADES_HTML}}`, `{{CHART_JSON}}`, …); Python builds only the inner fragments; renderer rejects unresolved placeholders; existing tests still green |
| 3 | Unified output directory | 11 | S | All entry scripts write to `output/` (subdirs `dashboards/`, `configs/`, `backtests/`). `docs/` no longer receives generated artifacts. `fast_optimizer.py` writes `output/configs/best_config.txt`. Path tests added. `.gitignore` updated. |
| 4 | In-candle TP/SL resolution | 10 | M | `run_backtest` accepts `tp_sl_resolution ∈ {"conservative","optimistic","direction-proxy"}`. Default `conservative` (SL-first). Tests with synthetic candles where both H ≥ TP and L ≤ SL for each mode. Existing behavior preserved when only one side is hit. |
| 5 | Date-range backtest framework | 9 | M | `filter_2025` deprecated; new `filter_by_date_range(df, start, end)` API. New entry point `python3 -m src.main.run_strategy --start 2025-09-01 --end 2025-12-31 --data 1min.csv --strategy scalping`. Tests cover date filtering for arbitrary ranges. **No data acquisition.** |
| 6 | Doc router + content sync | 12 | S | `Project_Documentation/*.doc.md` rewritten for `src/main/` paths. `docs/MASTER_DOCUMENTATION.md` expanded into a true router (sections for code, tutorials, revisions, design, output). README updated. Optional grep-test catches stale references to root-level entry-script paths. |
| 7 | Hybrid OOP/FP refactor | 6b | L | `src/strategy/{Strategy, Backtester, Reporter}.py` introduced as OOP. Indicators and pure metric functions stay FP. Three entry scripts reduced to ≤ 30-line orchestrators using the new classes. All previously-green tests still green. Refactor decisions logged in commit message. |
| 8 | Native Dash + resolver controls | 7 + 8 | L | `src/dashboard/dash_app.py` rewritten to use native Dash components (no iframe). Controls: dataset toggle (train/test), start/end datetime, timeframe (15min default in v1). On Apply: full pipeline runs in-memory via Strategy/Backtester from iter 7; chart + metrics + trades update. Validation: empty range, invalid dates, missing data. Callback tests. |
| 9 | Publish | 2 (push) | XS | `git push origin master` + `git push origin v1.0-working`. Confirm via `git ls-remote origin`. |

## Refactor Policy (applies inside iter 7, but informs all iterations)

For each unit, evaluate:

- **Pure transform, no state** (indicators, metrics calc, signal rules) → **FP**.
  The data shape is the contract; no class adds value.
- **Stateful with lifecycle** (Strategy config, Backtester run, Reporter
  output) → **OOP**.
- **Tie** → **OOP** (default).
- **Clear drawback for one style on a given unit** → switch that unit.
  Example drawback: OOP forces I/O into a constructor → switch that unit
  to FP.

Decisions are logged in the iter 7 commit message so the rationale is
traceable.

## Per-Iteration Discipline

Every iteration follows the same shape:

1. **Failing test** committed first (TDD).
2. **Minimal implementation** to turn the test green.
3. **Full local test suite** run (`pytest tests/ -v`) — must be green
   before the iteration ends.
4. **Doc update** — at minimum:
   - `docs/2026-05-21-todo-status-report.md` status row for the item
     flipped to ✅ done.
   - `AGENTS.md` updated only if invocation paths or conventions change.
5. **Single squashed commit** per iteration (or a small number of
   focused commits if TDD discipline makes that natural — never more
   than 4 commits per iteration).

## Non-Goals

- **No publishing** before iter 9.
- **No data acquisition** for item 9. Iter 5 stops at "tools ready".
- **No changes to the frozen `v1.0.0` tag.**
- **No new TODO items.** Anything discovered along the way that doesn't
  fit one of the 9 iterations gets recorded in `TODO.md` or a follow-up
  file and stays out of this sequence.

## Open Risks

1. **Iter 1 rebase may conflict.** `phase1-core-engine` modifies a file
   path that no longer exists on master. Mitigation: if rebase is messy,
   replay the changes manually (re-apply candlestick + template edits
   to `src/main/ultimate_dashboard.py`) instead of `git rebase`.
2. **Iter 7 OOP refactor may break the Dash iframe app** before iter 8
   rewrites it. Mitigation: iter 7 keeps `dash_app.py` as a deprecated
   thin wrapper around the new classes until iter 8 replaces it.
3. **Iter 8 may require additional Dash version pinning.** Mitigation:
   add a constrained version in `requirements.txt` during iter 8.

## Out of Scope (Possible Future Work)

- Real-time data ingestion (the system is sampling-time today; live data
  is a separate program).
- Multi-symbol support (currently NQ-only with hardcoded point value 2.0).
- Cloud deployment of the Dash app.
- ML model versioning / persistence.
