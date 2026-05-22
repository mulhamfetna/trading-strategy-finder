# Master Documentation Router

Single landing page for every documentation source in the repo. Updated
2026-05-22 as part of iter 6 (TODO item 12) of
`docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md`.

> **Trust executable code first.** Where this router links to long-form
> docs (`COMPLETE-DOCUMENTATION.md`, `PLAYBOOK.md`, `API.md`), check the
> referenced source files if anything looks off — those long-form docs
> haven't been kept in lock-step with the iter sequence.

## 1. Start here

| Doc | What it answers |
|---|---|
| `AGENTS.md` | How an automated agent should run / extend the repo. Canonical invocation paths, gotchas, branch/worktree layout. |
| `README.md` | Human entrypoint. Quickstart commands, project structure. |
| `docs/2026-05-21-todo-status-report.md` | Live status of every TODO item, per-iter completion notes. |
| `TODO.md` | The user's original task list (preserve typos). |

## 2. How it runs (code routing)

### Entry scripts (`src/main/`)

| File | Purpose | Run as |
|---|---|---|
| `src/main/main.py` | Multi-strategy comparison (scalping vs day vs intraday). | `python3 -m src.main.main` |
| `src/main/ultimate_dashboard.py` | 15-min ML-filtered scalping dashboard. Writes HTML + JSON to `output/dashboards/`. | `python3 -m src.main.ultimate_dashboard` |
| `src/main/fast_optimizer.py` | Parameter sweep over scalping config. Writes `output/configs/best_config.txt`. | `python3 -m src.main.fast_optimizer` |
| `src/main/live_dashboard.py` | Live simulation with HTML preview. Writes `output/dashboards/{live,equity}_*.html`. | `python3 -m src.main.live_dashboard` |
| `src/main/run_strategy.py` | **New (iter 5)** — date-range strategy runner. Generalises `filter_2025`. | `python3 -m src.main.run_strategy --data 1min.csv --start 2025-09-01 --end 2025-12-31 --strategy scalping` |
| `run_dashboard_on_train.py` (root) | Train-split runner for the ultimate dashboard. | `python3 run_dashboard_on_train.py` |

### Core modules

| Module | Role |
|---|---|
| `src/data/loader.py` | OHLCV CSV ingestion, column normalisation. |
| `src/data/splitter.py` | `filter_by_date_range` (iter 5), `filter_2025` (back-compat shim), `split_train_test`. |
| `src/data/resampler.py` | 1min → 5min / 15min OHLCV resampling. |
| `src/indicators/{scalping,day_trading,intraday}.py` | RSI / EMA / Volume / MACD / VWAP / Supertrend / ADX / Stochastic. |
| `src/signals/base_signals.py` | Rule-based signal generation (`-1` short, `0` hold, `1` long). |
| `src/signals/ml_filter.py` | Random Forest filter; trains on labelled candles, gates rule-based signals. |
| `src/backtest/engine.py` | Backtest with fees, slippage, **intra-candle TP/SL resolution** (iter 4: `conservative` / `optimistic` / `direction-proxy`). |
| `src/backtest/metrics.py` | Aggregate metrics (profit, win-rate, Sharpe, drawdown, EV, max losing streak). |
| `src/dashboard/template_renderer.py` | **New (iter 2)** — pure-function `{{NAME}}` template renderer. |
| `frontend/` | Vue 3 backtest dashboard (settings, progress, metrics, trades). |
| `src/dashboard/report.py`, `src/dashboard/visualizer.py` | Console / Plotly summary helpers. |

### Templates

| File | Role |
|---|---|
| `templates/ultimate_dashboard.html.tpl` | **New (iter 2)** — extracted HTML shell with 19 named slots. Replaces the inline 700-line f-string. |

## 3. Trading concepts (interview prep / academic notes)

All under `docs/Tutorials/`:

| Topic | File |
|---|---|
| OHLCV schema | `docs/Tutorials/OHLCV_schema.md` |
| RSI | `docs/Tutorials/RSI.md` |
| EMA / SMA | `docs/Tutorials/Moving_Avarage_SMA-EMA.md` |
| VWAP & MACD | `docs/Tutorials/VWAP_and_MACD.md` |
| Supertrend, ADX, Stochastic | `docs/Tutorials/Supertrend_ADX_Stochastic.md` |
| Volume spike + max losing streak | `docs/Tutorials/Volume_Spike_and_Max_Losing_Streak.md` |
| Random Forest filter | `docs/Tutorials/Random_Forest_Filter.md` |
| TP / SL / Profit-Loss | `docs/Tutorials/PL_TP_SL.md` |
| P/L vs EV per trade | `docs/Tutorials/P-L_vs_EV-Trade.md` |
| Expected value per trade | `docs/Tutorials/Expected_Value_per_Trade-EV-Trade.md` |
| Sharpe ratio | `docs/Tutorials/Sharpe_Ratio.md` |
| Max drawdown | `docs/Tutorials/Maximum_Drawdown.md` |
| Stock vs contract backtest definitions | `docs/Tutorials/Stock_Contract_Backtest_Definition.md` |
| Parameter rationale | `docs/Tutorials/Parameter_Rationale.md` |
| Technical spec walkthrough | `docs/Tutorials/Technical_Spec_Walkthrough.md` |
| Interview playbook | `docs/Tutorials/Interview_Playbook.md` |
| R | `docs/Tutorials/R.md` |
| Curated YouTube videos | `docs/Tutorials/Youtube_videos.md` |

## 4. Design specs and plans (active work)

- `docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md` — **active**: the 9-iteration plan currently being executed.
- `docs/superpowers/specs/2026-05-21-dashboard-template-candlestick-design.md` — completed in iters 1–2.
- `docs/superpowers/plans/2026-05-21-live-dashboard.md` — completed in the phase3-live-dashboard worktree.
- `docs/superpowers/plans/2026-05-21-phase1-core-engine-strategy-correctness.md` — superseded; phase1 work integrated piecemeal.

## 5. Revision history & lessons

- `docs/revisions/REVISION_LOG.md` — mistakes by revision round and fixes applied.
- `docs/revisions/LESSONS_LEARNED.md` — process / quality lessons.
- `docs/bug-checklist-revision-history.md` — pre-iter-sequence checklist.
- `docs/fixes-needed-report-2026-05-21.md` — snapshot list of issues identified pre-iter-1.
- `docs/ultimate_trading_dashboard_review_v3.md` — original v1.0.0 council review.
- `docs/reviewer-playbook-segmented.md` — review process notes.

## 6. Per-file deep docs

`Project_Documentation/*.doc.md` — one file per source module. Updated
in iter 6 to reflect the `src/main/` move and current invocation paths.
These are short skeletons; for deep behavior read the source.

## 7. Frozen versions

- `docs/V1-FROZEN.md` — v1.0.0 production reference (still tagged `v1.0.0`).
- Git tag `v1.0-working` — local snapshot of state just before iter 1.

## 8. Long-form references (kept but lagging)

- `docs/COMPLETE-DOCUMENTATION.md` — pre-iter consolidated tech doc.
- `docs/PLAYBOOK.md` — strategy playbook.
- `docs/API.md` — function reference (pre-`src/main/` move).

> These three were written before the iter sequence and still describe
> the older layout in places. Trust the executable code in `src/` when
> they conflict.

## 9. Generated output (gitignored)

Everything generated goes to `output/`:

- `output/dashboards/ultimate_trading_dashboard.html` + `dashboard_data.json` (test split).
- `output/dashboards/ultimate_trading_dashboard_train.html` + `dashboard_data_train.json` (train split, via `run_dashboard_on_train.py`).
- `output/dashboards/live_trading_dashboard.html`, `output/dashboards/equity_curve_dashboard.html` (live simulation).
- `output/configs/best_config.txt` (from `src/main/fast_optimizer.py`).

`docs/legacy/index.html` is the one HTML file kept in `docs/` — preserved as a historical archive of the v1.0.0 dashboard.

## 10. Legacy archive

`docs/legacy/` holds:

- Old `AGENTS.md`, `copilot-instructions.md`, council reports.
- Pre-`src/main/` Project_Documentation skeletons (in `docs/legacy/Project_Documentation/`).
- Original `parameter_optimizer.py` (predecessor to `fast_optimizer.py`).
- The original v1.0.0 dashboard `docs/legacy/index.html`.

Useful for history; do not treat as current.
