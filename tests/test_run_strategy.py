"""Tests for src/main/run_strategy.py (iter 5, TODO item 9 framework).

The CLI lets you run the scalping strategy over an arbitrary date range
on an arbitrary CSV - the framework piece of item 9. Data acquisition
for Sep-Dec 2025 and Jan-Jun 2026 is deliberately NOT in scope here.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main.run_strategy import build_parser, run_strategy


def _write_synth_15min_csv(path, n_rows=200):
    """Write a synthetic 15min CSV that's just enough for the scalping
    pipeline to run (real data validates real behavior - this just
    validates the framework wiring)."""
    dates = pd.date_range(start='2025-09-01 09:30:00', periods=n_rows, freq='15min')
    df = pd.DataFrame({
        'Date': dates.strftime('%Y-%m-%d'),
        'Time': dates.strftime('%H:%M:%S'),
        'Open':   [20000.0 + i * 0.5 for i in range(n_rows)],
        'High':   [20002.0 + i * 0.5 for i in range(n_rows)],
        'Low':    [19998.0 + i * 0.5 for i in range(n_rows)],
        'Close':  [20001.0 + i * 0.5 for i in range(n_rows)],
        'Volume': [1000 + i for i in range(n_rows)],
    })
    df.to_csv(path, index=False)


def test_build_parser_requires_data_start_end():
    """CLI requires --data, --start, --end."""
    parser = build_parser()
    # All required args supplied -> no SystemExit
    args = parser.parse_args(['--data', 'x.csv', '--start', '2025-09-01', '--end', '2025-09-30'])
    assert args.data == 'x.csv'
    assert args.start == '2025-09-01'
    assert args.end == '2025-09-30'
    assert args.strategy == 'scalping'  # default


def test_build_parser_accepts_optional_flags():
    """Optional flags: --strategy, --train-test-split, --stop-loss,
    --take-profit, --tp-sl-resolution."""
    parser = build_parser()
    args = parser.parse_args([
        '--data', 'x.csv',
        '--start', '2025-09-01',
        '--end', '2025-12-31',
        '--strategy', 'scalping',
        '--train-test-split', '2025-10-15',
        '--stop-loss', '0.5',
        '--take-profit', '2.0',
        '--tp-sl-resolution', 'optimistic',
    ])
    assert args.train_test_split == '2025-10-15'
    assert args.stop_loss == 0.5
    assert args.take_profit == 2.0
    assert args.tp_sl_resolution == 'optimistic'


def test_run_strategy_returns_metrics_dict(tmp_path):
    """End-to-end smoke test: synthetic CSV -> run_strategy -> metrics dict.
    The framework runs; whether the synthetic data produces trades is not
    asserted (real data validates real behavior)."""
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    metrics = run_strategy(
        data_path=str(csv),
        start='2025-09-01',
        end='2025-12-31',
        strategy='scalping',
    )

    # Must return a metrics dict with the canonical keys.
    for key in ('total_profit', 'win_rate', 'profit_factor', 'total_trades'):
        assert key in metrics


def test_run_strategy_rejects_unknown_strategy(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    with pytest.raises(ValueError):
        run_strategy(
            data_path=str(csv),
            start='2025-09-01',
            end='2025-12-31',
            strategy='not-a-real-strategy',
        )
