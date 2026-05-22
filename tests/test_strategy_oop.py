"""Iter 7 (TODO item 6b): tests for the hybrid OOP/FP refactor.

Refactor policy from
docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md:

- Stateful with lifecycle (Strategy config + prepare/train/apply,
  Backtester config + run) -> OOP
- Pure transforms (indicators, signals, metrics) -> stay FP
- Ties default to OOP

These tests cover the OOP wrappers. The underlying FP functions stay
covered by their existing tests in test_indicators / test_signals /
test_backtest.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.scalping_strategy import ScalpingStrategy
from src.strategy.backtester import Backtester


def _synth_15min_df(n_rows=200):
    """Build a synthetic 15-min OHLCV DataFrame large enough for the
    indicator + ML pipeline to run."""
    dates = pd.date_range(start='2025-09-01 09:30:00', periods=n_rows, freq='15min')
    close = 20000.0 + np.cumsum(np.random.default_rng(42).normal(0, 5, size=n_rows))
    df = pd.DataFrame({
        'Date':   dates.strftime('%Y-%m-%d'),
        'Time':   dates.strftime('%H:%M:%S'),
        'Open':   close - 1,
        'High':   close + 2,
        'Low':    close - 2,
        'Close':  close,
        'Volume': np.random.default_rng(7).integers(800, 1500, size=n_rows),
    })
    return df


def test_scalping_strategy_default_config_matches_v1():
    """Defaults match the v1.0.0 frozen parameters - keeping them as the
    safe starting point."""
    strat = ScalpingStrategy()
    assert strat.rsi_period == 5
    assert strat.ema_fast == 5
    assert strat.ema_slow == 15
    assert strat.vol_threshold == 2.0


def test_scalping_strategy_custom_config_overrides_defaults():
    """Construction kwargs are honored."""
    strat = ScalpingStrategy(rsi_period=7, ema_fast=8, ema_slow=21, vol_threshold=1.5)
    assert strat.rsi_period == 7
    assert strat.ema_fast == 8
    assert strat.ema_slow == 21
    assert strat.vol_threshold == 1.5


def test_scalping_strategy_prepare_adds_required_columns():
    """prepare() returns the df with indicator, signal, and ML-feature
    columns the rest of the pipeline expects."""
    df = _synth_15min_df(n_rows=200)
    strat = ScalpingStrategy()

    prepared = strat.prepare(df)

    # indicators
    assert 'rsi_5' in prepared.columns
    assert 'ema_5' in prepared.columns
    assert 'ema_15' in prepared.columns
    assert 'volume_spike' in prepared.columns
    # rule-based signal
    assert 'signal' in prepared.columns
    assert set(prepared['signal'].dropna().unique()).issubset({-1, 0, 1})


def test_scalping_strategy_prepare_does_not_mutate_input():
    """Copy-before-mutate convention - the input df is untouched."""
    df = _synth_15min_df(n_rows=120)
    orig_cols = set(df.columns)
    strat = ScalpingStrategy()
    _ = strat.prepare(df)
    assert set(df.columns) == orig_cols


def test_backtester_default_config_matches_v1_thresholds():
    """Default SL=0.6%, TP=1.8%, conservative resolution (iter 4)."""
    bt = Backtester()
    assert bt.stop_loss == 0.6
    assert bt.take_profit == 1.8
    assert bt.tp_sl_resolution == 'conservative'
    assert bt.initial_capital == 10000


def test_backtester_run_returns_trades_and_capital():
    """run(df) returns (trades_list, final_capital). Same shape as the FP
    engine."""
    # Synthetic candle where the trade entered at idx 0 will hit TP via
    # the intra-candle High at idx 1 (entry=100, TP=110).
    df = pd.DataFrame({
        'Date':  ['2025-09-01', '2025-09-02'],
        'Open':  [100.0, 100.0],
        'High':  [100.0, 115.0],  # hits TP
        'Low':   [100.0, 99.5],
        'Close': [100.0, 100.0],
        'signal': [1, 0],
    })
    bt = Backtester(stop_loss=1.0, take_profit=10.0, slippage_pct=0.0,
                    fee_per_trade=0.0)

    trades, capital = bt.run(df)

    assert isinstance(trades, list)
    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'TAKE PROFIT'
    assert capital > 10000


def test_backtester_passes_tp_sl_resolution_to_engine():
    """The resolution mode (iter 4) is wired through Backtester."""
    df = pd.DataFrame({
        'Date':  ['2025-09-01', '2025-09-02'],
        'Open':  [100.0, 100.0],
        'High':  [100.0, 120.0],  # both hit
        'Low':   [100.0, 85.0],
        'Close': [100.0, 100.0],
        'signal': [1, 0],
    })

    # Optimistic mode -> TP wins
    bt = Backtester(stop_loss=1.0, take_profit=10.0, slippage_pct=0.0,
                    fee_per_trade=0.0, tp_sl_resolution='optimistic')
    trades_opt, _ = bt.run(df)
    assert trades_opt[0]['exit_reason'] == 'TAKE PROFIT'

    # Conservative mode -> SL wins
    bt = Backtester(stop_loss=1.0, take_profit=10.0, slippage_pct=0.0,
                    fee_per_trade=0.0, tp_sl_resolution='conservative')
    trades_cons, _ = bt.run(df)
    assert trades_cons[0]['exit_reason'] == 'STOP LOSS'


def test_run_strategy_module_uses_strategy_and_backtester_classes():
    """src/main/run_strategy.py (iter 5) refactored to use the new
    classes - kill the inline _prepare_scalping helper."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] /
           'src' / 'main' / 'run_strategy.py').read_text(encoding='utf-8')
    assert 'from src.strategy.scalping_strategy import ScalpingStrategy' in src
    assert 'from src.strategy.backtester import Backtester' in src
    # The inline helper is gone (replaced by the class).
    assert 'def _prepare_scalping' not in src


def test_main_scalping_path_uses_strategy_and_backtester_classes():
    """src/main/main.py's scalping branch refactored to use the new
    classes - kill the inline pipeline duplication."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] /
           'src' / 'main' / 'main.py').read_text(encoding='utf-8')
    assert 'from src.strategy.scalping_strategy import ScalpingStrategy' in src
    assert 'from src.strategy.backtester import Backtester' in src
