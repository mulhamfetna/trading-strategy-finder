"""Backtester wrapper (iter 7, item 6b).

OOP configuration carrier for the FP run_backtest engine. The engine
itself stays FP (pure transform from DataFrame -> trades+capital); the
class adds two things:

  1. A single place to store the backtest configuration (capital, SL,
     TP, fees, slippage, daily limits, intra-candle TP/SL resolution
     mode from iter 4).
  2. A ``run(df)`` method so callers don't have to pass 8 keyword args
     every time.

Refactor policy: stateful with configuration lifecycle -> OOP. The
underlying transform stays FP.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from src.backtest.engine import run_backtest


class Backtester:
    """Backtest configuration + runner.

    Defaults match the v1.0.0 scalping configuration: SL=0.6%, TP=1.8%,
    $10 fee/trade, 0.05% slippage, conservative intra-candle resolution.

    Usage::

        bt = Backtester(stop_loss=0.6, take_profit=1.8,
                        tp_sl_resolution='conservative')
        trades, final_capital = bt.run(prepared_df)
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        stop_loss: float = 0.6,
        take_profit: float = 1.8,
        max_daily_trades: int = 10,
        fee_per_trade: float = 10.0,
        slippage_pct: float = 0.0005,
        tp_sl_resolution: str = 'conservative',
    ):
        self.initial_capital = initial_capital
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_daily_trades = max_daily_trades
        self.fee_per_trade = fee_per_trade
        self.slippage_pct = slippage_pct
        self.tp_sl_resolution = tp_sl_resolution

    def run(self, df: pd.DataFrame) -> Tuple[List[Dict], float]:
        """Run the backtest against the given prepared DataFrame.

        Returns ``(trades, final_capital)`` - exact same shape as the
        underlying FP ``run_backtest`` function.
        """
        return run_backtest(
            df,
            initial_capital=self.initial_capital,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            max_daily_trades=self.max_daily_trades,
            fee_per_trade=self.fee_per_trade,
            slippage_pct=self.slippage_pct,
            tp_sl_resolution=self.tp_sl_resolution,
        )
