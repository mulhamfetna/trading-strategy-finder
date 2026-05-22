# NQ Futures Trading Strategy Finder

> **v1.0.0** is frozen (`git tag v1.0.0`). Current development continues on `master`.
> Active sequencing plan: `docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md`.
> Live status: `docs/2026-05-21-todo-status-report.md`.

A hybrid ML-powered trading algorithm that compares scalping, day trading,
and intraday strategies on historical NQ Futures data.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Restore the CSVs (gitignored, must live at repo root):
#   1min.csv                  (~135 MB, 1-minute OHLCV)
#   NQ_15min_processed.csv    (~8 MB,   15-minute OHLCV)

# Multi-strategy comparison
python3 -m src.main.main

# Generate the 15-min ML-filtered dashboard (writes to output/dashboards/)
python3 -m src.main.ultimate_dashboard

# Parameter sweep (writes output/configs/best_config.txt)
python3 -m src.main.fast_optimizer

# Live simulation dashboard
python3 -m src.main.live_dashboard

# Date-range runner (iter 5, no hardcoded 2025 cap)
python3 -m src.main.run_strategy \
    --data 1min.csv \
    --start 2025-09-01 --end 2025-12-31 \
    --strategy scalping

# Train-split dashboard variant
python3 run_dashboard_on_train.py

# Tests
pytest tests/ -v
```

Open the generated HTML:

```bash
open output/dashboards/ultimate_trading_dashboard.html
```

## v1.0.0 Results (Frozen)

| Metric | Value |
|--------|-------|
| Net Profit | $633.65 |
| Win Rate | 54.5% |
| Profit Factor | 2.62 |
| Return | 6.34% |

See `docs/V1-FROZEN.md` for the full v1.0.0 spec.

## Project Structure

```
├── src/
│   ├── main/                  # Entry scripts (moved here in commit cf904c9)
│   │   ├── main.py            #   multi-strategy comparison
│   │   ├── ultimate_dashboard.py
│   │   ├── fast_optimizer.py
│   │   ├── live_dashboard.py
│   │   └── run_strategy.py    #   date-range runner (iter 5)
│   ├── data/                  # loader, splitter (filter_by_date_range), resampler
│   ├── indicators/            # scalping / day_trading / intraday indicators
│   ├── signals/               # rule-based + ML signal generation
│   ├── backtest/              # engine (intra-candle TP/SL), metrics
│   └── dashboard/             # template_renderer (FP), dash_app, report, visualizer
├── templates/                 # ultimate_dashboard.html.tpl - 19 named slots
├── docs/                      # All documentation. Start at docs/MASTER_DOCUMENTATION.md.
├── output/                    # Generated artifacts (gitignored)
│   ├── dashboards/            #   HTML + JSON dashboards
│   └── configs/               #   best_config.txt from fast_optimizer
├── tests/                     # pytest
├── AGENTS.md                  # Instructions for automated agents
├── 1min.csv                   # gitignored - restore before running
└── NQ_15min_processed.csv     # gitignored - restore before running
```

## Documentation

Start at **`docs/MASTER_DOCUMENTATION.md`** — it routes to every other doc
(code, tutorials, design specs, revision logs, generated artifacts).

For agents and contributors: read **`AGENTS.md`** first (run commands,
data gotchas, conventions, branch/worktree layout).

## Versioning

| Version | Status | Tag |
|---------|--------|-----|
| v1.0.0  | **Frozen (Production Ready)** | `v1.0.0` |
| v1.0-working | Snapshot just before iter 1 | `v1.0-working` |
| v1.1   | 15min + ML + RSI<25 + SL 0.6% / TP 2.4% | `v1.1` |
| master | Active development | `HEAD` |

```bash
git tag -l                    # list tags
git checkout v1.0.0            # inspect a frozen version
git diff v1.0.0 master         # see what's changed
```

## License

MIT
