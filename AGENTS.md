# AGENTS.md — Trading Strategy Finder

Python-only repo. No build, no lint/typecheck/formatter, no CI. Stdlib + `pandas`, `numpy`, `scikit-learn`, `plotly`, `pytest` (`requirements.txt`).

## Run things

Entry scripts were moved into `src/main/` (commit `cf904c9`). README and `docs/V1-FROZEN.md` still reference the old root-level paths — ignore them. There is no `src/__init__.py` (implicit namespace packages), so invocation matters:

```bash
# From repo root only:
python3 -m src.main.main                 # multi-strategy comparison
python3 -m src.main.ultimate_dashboard   # writes docs/ultimate_trading_dashboard.html + docs/dashboard_data.json
python3 -m src.main.fast_optimizer       # parameter sweep -> best_config.txt
python3 -m src.main.live_dashboard       # live simulation
python3 run_dashboard_on_train.py        # same dashboard but on the TRAIN split -> docs/*_train.{html,json}

# Tests
pytest tests/ -v
pytest tests/test_ultimate_dashboard.py::test_run_backtest_15min_uses_nq_point_value_for_pnl -v
```

Do NOT use `python3 src/main/main.py` — the scripts contain `sys.path.insert(0, os.path.dirname(__file__))` that adds `src/main/`, which does not make `from src.data.loader` resolve. `-m` from repo root (or running a root-level script like `run_dashboard_on_train.py`) is what actually works.

Tests do `sys.path.insert(0, repo_root)` themselves and call `load_data('1min.csv')` / `load_data('NQ_15min_processed.csv')` with bare filenames — always run pytest from repo root.

## Data files (critical)

`1min.csv` (~135 MB) and `NQ_15min_processed.csv` (~8 MB) live at repo root and are referenced by bare relative paths everywhere. They are **gitignored** (`*.csv`) so they will be missing on a fresh clone — restore before running anything. `*.html` and `*.pdf` are also gitignored; never commit dashboard outputs.

## Architecture (one-line)

`src/data/loader.py` → `src/data/splitter.py` (+ `resampler.py`) → `src/indicators/{scalping,day_trading,intraday}.py` → `src/signals/base_signals.py` → `src/signals/ml_filter.py` → `src/backtest/{engine,metrics}.py` → `src/dashboard/{report,visualizer}.py`. Entry scripts in `src/main/` wire the pipeline together; `ultimate_dashboard.py` is its own near-complete pipeline that resamples 1min→15min internally.

## Conventions that bite

- Canonical column names: `Open/High/Low/Close/Volume`, plus `Date`/`Time` or `timestamps`. `loader.load_data()` normalizes case — always use it instead of `pd.read_csv` for new ingestion.
- Indicator/signal functions copy-before-mutate; they return new DataFrames.
- Signal contract: `-1` short, `0` hold, `1` long.
- Trade dict keys consumed by metrics/dashboard: `entry_idx, exit_idx, direction, entry_price, exit_price, profit_pct, profit_dollars, capital_after, exit_reason, fees_paid`.
- Scope is hardcoded to 2025 data with train/test split at `2025-06-30` (`filter_2025` + `split_train_test`).
- **1min CSV loads newest-first (descending).** Scalping path reverses it to ascending before backtest — see `src/main/main.py:42`. If you build any new pipeline off the 1min file, do the same or trades will exit before they enter.
- **NQ point-value PnL**, not pure %: backtest multiplies points moved by `point_value=2.0` (NQ futures). Test `test_run_backtest_15min_uses_nq_point_value_for_pnl` locks this in (1 contract × 500 pts × $2 = $1000, minus $10 fee = $990).
- ML filter: `apply_ml_filter` overwrites the active signal column; make sure the DataFrame you hand to `run_backtest` reflects the filtered signals, not the raw rule-based ones.
- `apply_rsi_entry_filters` in `ultimate_dashboard.py` zeroes out signals where RSI is on the wrong side of the band (longs require RSI ≤ oversold, shorts require RSI ≥ overbought). Tested behavior — don't relax it without updating the test.

## Output locations

Everything generated goes to `docs/`:
- `docs/ultimate_trading_dashboard.html` + `docs/dashboard_data.json` (test split)
- `docs/ultimate_trading_dashboard_train.html` + `docs/dashboard_data_train.json` (train split, via `run_dashboard_on_train.py`)
- `best_config.txt` at repo root (from `fast_optimizer`).

## Versioning / branches

- `v1.0.0` and `v1.0-working` tags are frozen; production reference is documented in `docs/V1-FROZEN.md`.
- `v1.1` tag: 15min timeframe + ML + RSI<25 + SL 0.6% / TP 2.4% (current default in `ultimate_dashboard.py`).
- Active development happens in git worktrees under `.worktrees/` (gitignored): currently `phase1-core-engine` and `live-dashboard`. Plans for those live in `docs/superpowers/plans/`, specs in `docs/superpowers/specs/`.
- Workspace HEAD is often detached on a documentation/review commit; check `git status` before assuming a branch.

## Documentation map

- `docs/Tutorials/` — current concept and interview-prep notes (RSI, EMA, Sharpe, Random Forest filter, OHLCV schema, etc.).
- `docs/COMPLETE-DOCUMENTATION.md`, `docs/PLAYBOOK.md`, `docs/API.md` — long-form references; trust executable code over these where they conflict.
- `docs/legacy/` — archived council reports, old `AGENTS.md`, old `copilot-instructions.md`. Useful for history, not for current behavior.
- `Project_Documentation/*.doc.md` — per-file skeletons that still reference the OLD root-level entrypoint paths (`ultimate_dashboard.py`, `main.py`, `fast_optimizer.py`, `live_dashboard.py`). Treat as stale until rewritten.
- `TODO.md` and `notes.md` are the user's running scratchpads (typos and all) — read them for intent, don't treat them as spec.
