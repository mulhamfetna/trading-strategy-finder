# NQ Futures Trading Strategy Finder

> **📦 v1.0.0 (Stable)** - Frozen and tagged. See [docs/V1-FROZEN.md](docs/V1-FROZEN.md)

A hybrid ML-powered trading algorithm that compares scalping, day trading, and intraday strategies using historical NQ Futures data.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate dashboard
python3 ultimate_dashboard.py

# Open in browser
open output/dashboard/ultimate_trading_dashboard_test.html
```

## v1.0.0 Results (Frozen)

| Metric | Value |
|--------|-------|
| Net Profit | $633.65 |
| Win Rate | 54.5% |
| Profit Factor | 2.62 |
| Return | 6.34% |

## Versioning

This project uses Git tags for version management:

| Version | Status | Tag |
|---------|--------|-----|
| v1.0.0 | **Frozen (Production Ready)** | `v1.0.0` |
| develop | Active Development | `HEAD` |

### Working with Versions

```bash
# View available tags
git tag -l

# Checkout frozen version
git checkout v1.0.0

# Create new development branch from v1.0.0
git checkout -b develop-v2 v1.0.0

# Compare versions
git diff v1.0.0 master
```

## Documentation

- [Complete Documentation](docs/COMPLETE-DOCUMENTATION.md)
- [Trading Playbook](docs/PLAYBOOK.md)
- [v1.0.0 Frozen Details](docs/V1-FROZEN.md)
- [Final Review (v3)](docs/ultimate_trading_dashboard_review_v3.md)

## Phase 1 Outputs

- `output/dashboard/dashboard_data_test.json`
- `output/dashboard/ultimate_trading_dashboard_test.html`
- `output/backtests/old_strategy_2025-09_2025-12.json`
- `output/backtests/old_strategy_2026-01_2026-06.json`

## Project Structure

```
├── src/
│   ├── backtest/          # Backtesting engine
│   ├── data/               # Data loading/splitting
│   ├── indicators/         # Technical indicators
│   ├── signals/            # Signal generation + ML
│   └── dashboard/          # Reports and visualization
├── docs/                   # Documentation & dashboards
├── tests/                  # Unit tests
└── scripts/               # Utilities
```

## License

MIT