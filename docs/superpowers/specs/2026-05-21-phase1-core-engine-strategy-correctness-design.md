# Phase 1 Design: Core Engine + Strategy Correctness

## Problem Statement

Phase 1 focuses on strategy correctness and reproducible backtest artifacts for the frozen v1.0 strategy. The target is to:

1. Regenerate test dashboard artifacts.
2. Evaluate old strategy performance on two requested windows (2025-09 to 2025-12, and 2026-01 to 2026-06).
3. Improve in-candle TP/SL handling for sampled candles using a conservative policy.
4. Standardize generated outputs under `output/`.

Scope excludes full UI migration to Streamlit/Dash, broad repository restructuring, and global documentation/router overhaul; those are deferred to later phases.

## Approved Strategy Baseline (Frozen v1.0)

- Indicators/signals: RSI(5), EMA(5/15), volume threshold 1.0.
- ML filter enabled (RandomForest).
- Risk parameters: stop loss 0.6%, take profit 2.4%.
- Contract economics: `point_value=2.0`, fee per trade `$10`.
- Reproducibility: `random_state=42`.

No behavioral changes are made to this strategy definition in Phase 1.

## Architecture

Introduce a reusable service layer for execution:

- New module: `src/main/backtest_runner.py`
  - Owns orchestration for data windowing, strategy execution, and artifact payload assembly.
  - Returns structured result object: trades, metrics, metadata, artifacts.
- `ultimate_dashboard.py`
  - Calls the runner instead of owning all execution details inline.
  - Remains an entrypoint for test dashboard generation.

This keeps strategy logic centralized and makes windowed runs and artifact generation consistent across commands.

## Data Flow

For each execution request:

1. Load source candles (`1min.csv`).
2. Filter to target date window(s).
3. Resample to 15-minute candles in chronological order.
4. Prepare indicators and base strategy signals.
5. Train/apply ML filter with frozen v1.0 configuration.
6. Apply RSI entry symmetry filter.
7. Run backtest with in-candle resolver.
8. Compute metrics and coverage diagnostics.
9. Write outputs to `output/` paths.

## In-Candle Exit Policy

When using sampled candles, high/low can indicate both TP and SL touched inside the same candle. Phase 1 policy:

- If both TP and SL are reachable inside one candle, **assume SL is hit first** (conservative).
- If only one threshold is touched, close on that threshold.
- If neither threshold is touched, keep position open.

This rule is explicit and deterministic for backtests on aggregated candles.

## Coverage and Missing Data Policy

Requested windows:

- 2025-09-01 to 2025-12-31
- 2026-01-01 to 2026-06-30

If local CSV coverage is incomplete:

- Run on available rows.
- Emit explicit coverage metadata (requested start/end, actual start/end, row counts, missing segments summary).
- Do not silently pretend full-range coverage.

## Output Contract (Phase 1)

Generated files move under `output/`:

- `output/dashboard/dashboard_data_test.json`
- `output/dashboard/ultimate_trading_dashboard_test.html`
- `output/backtests/old_strategy_2025-09_2025-12.json`
- `output/backtests/old_strategy_2026-01_2026-06.json`

Compatibility references may be retained at the old docs paths during transition to avoid immediate breakage.

## Error Handling

- Missing required files or required columns raises explicit, actionable errors.
- No broad silent fallbacks for critical data/logic failures.
- Runner returns/prints clear diagnostics for coverage limitations and runtime failures.

## Testing Plan

Add/update tests to cover:

1. In-candle TP/SL collision behavior (SL-first).
2. Date-window filtering and coverage metadata correctness.
3. Output path contract under `output/`.
4. Regression confidence for frozen v1.0 behavior where unchanged.

## Deliverables (Phase 1)

1. Regenerated test dashboard artifacts from frozen strategy.
2. Two windowed old-strategy performance reports.
3. In-candle conservative exit handling.
4. Output relocation to `output/` for newly generated artifacts.
5. Updated tests for correctness and regressions.

