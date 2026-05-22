#!/usr/bin/env python3
"""Date-range strategy runner (iter 5, TODO item 9 framework).

Lets you run a strategy over an ARBITRARY date range on an arbitrary
CSV. This is the framework piece of TODO item 9 - data acquisition for
Sep-Dec 2025 and Jan-Jun 2026 is deliberately out of scope.

Usage from repo root:

    python3 -m src.main.run_strategy \\
        --data 1min.csv \\
        --start 2025-09-01 --end 2025-12-31 \\
        --strategy scalping

Optional:
    --train-test-split DATE      train ML on <= DATE, backtest on > DATE
    --stop-loss FLOAT            default 0.6 (%)
    --take-profit FLOAT          default 1.8 (%)
    --tp-sl-resolution MODE      conservative | optimistic | direction-proxy
                                 (default: conservative; iter 4)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data.loader import load_data
from src.data.splitter import filter_by_date_range, split_train_test
from src.strategy.scalping_strategy import ScalpingStrategy
from src.strategy.backtester import Backtester
from src.backtest.metrics import calculate_metrics


_STRATEGIES = ('scalping',)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='run_strategy',
        description='Run a trading strategy over a custom date range.',
    )
    parser.add_argument('--data', required=True,
                        help='Path to the input CSV (1min or 15min OHLCV).')
    parser.add_argument('--start', required=True,
                        help='Inclusive start date (YYYY-MM-DD).')
    parser.add_argument('--end', required=True,
                        help='Inclusive end date (YYYY-MM-DD).')
    parser.add_argument('--strategy', default='scalping', choices=list(_STRATEGIES),
                        help='Which strategy to run (default: scalping).')
    parser.add_argument('--train-test-split', default=None,
                        help='If set, split the filtered range at this date '
                             'and train ML on the train half, backtest on test.')
    parser.add_argument('--stop-loss', type=float, default=0.6,
                        help='Stop loss percentage (default 0.6).')
    parser.add_argument('--take-profit', type=float, default=1.8,
                        help='Take profit percentage (default 1.8).')
    parser.add_argument('--tp-sl-resolution', default='conservative',
                        choices=['conservative', 'optimistic', 'direction-proxy'],
                        help='How to break ties when High>=TP AND Low<=SL '
                             '(iter 4 / TODO item 10). Default: conservative.')
    parser.add_argument('--initial-capital', type=float, default=10000.0)
    parser.add_argument('--fee-per-trade', type=float, default=10.0)
    return parser


def run_strategy(
    data_path: str,
    start: str,
    end: str,
    strategy: str = 'scalping',
    train_test_split: Optional[str] = None,
    stop_loss: float = 0.6,
    take_profit: float = 1.8,
    tp_sl_resolution: str = 'conservative',
    initial_capital: float = 10000.0,
    fee_per_trade: float = 10.0,
) -> Dict:
    """Load data, filter by date range, run strategy, return metrics.

    Iter 7 (TODO item 6b): pipeline is now driven by ScalpingStrategy +
    Backtester (OOP) - no more inline _prepare_scalping helper.
    """
    if strategy not in _STRATEGIES:
        raise ValueError(
            f"strategy must be one of {_STRATEGIES}, got {strategy!r}"
        )

    df = load_data(data_path)
    df = filter_by_date_range(df, start=start, end=end)

    if len(df) == 0:
        return calculate_metrics([], initial_capital)

    # 1min data loads newest-first; reverse to ascending for backtest.
    df = df.reset_index(drop=True)[::-1].reset_index(drop=True)

    strat = ScalpingStrategy()  # v1.0.0 defaults
    bt = Backtester(
        initial_capital=initial_capital,
        stop_loss=stop_loss,
        take_profit=take_profit,
        fee_per_trade=fee_per_trade,
        tp_sl_resolution=tp_sl_resolution,
    )

    if train_test_split:
        train_df, test_df = split_train_test(df, split_date=train_test_split)
        train_prepared = strat.prepare(train_df)
        ml_model = strat.train_ml(train_prepared)
        test_prepared = strat.prepare(test_df)
        backtest_df = strat.apply_ml(test_prepared, ml_model)
    else:
        # No split: use whole range, no ML filter (would leak future data).
        backtest_df = strat.prepare(df)

    trades, _ = bt.run(backtest_df)
    return calculate_metrics(trades, initial_capital)


def main():
    args = build_parser().parse_args()
    metrics = run_strategy(
        data_path=args.data,
        start=args.start,
        end=args.end,
        strategy=args.strategy,
        train_test_split=args.train_test_split,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        tp_sl_resolution=args.tp_sl_resolution,
        initial_capital=args.initial_capital,
        fee_per_trade=args.fee_per_trade,
    )

    print(f"=== Strategy: {args.strategy} | Range: {args.start} -> {args.end} ===")
    print(f"  Total Profit  : ${metrics['total_profit']:.2f}")
    print(f"  Win Rate      : {metrics['win_rate']:.1f}%")
    print(f"  Profit Factor : {metrics['profit_factor']:.2f}")
    print(f"  Sharpe        : {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown  : {metrics['max_drawdown']:.2f}%")
    print(f"  Total Trades  : {metrics['total_trades']}")


if __name__ == '__main__':
    main()
