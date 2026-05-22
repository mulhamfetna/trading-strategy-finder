"""Backtest engine with intra-candle TP/SL resolution (iter 4, TODO item 10)."""

from typing import List, Tuple, Dict

import numpy as np
import pandas as pd


_RESOLUTION_MODES = ('conservative', 'optimistic', 'direction-proxy')


def _resolve_intra_candle_exit(
    direction: int,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    row: pd.Series,
    resolution: str,
) -> Tuple[bool, str, float]:
    """Decide whether this candle exits the trade and, if so, how.

    Args:
        direction: 1 for long, -1 for short.
        entry_price: Entry price (already slippage-adjusted).
        stop_loss: Stop-loss percentage (e.g. 1.0 for 1%).
        take_profit: Take-profit percentage (e.g. 2.0 for 2%).
        row: Candle row with Open/High/Low/Close.
        resolution: 'conservative', 'optimistic', or 'direction-proxy'.

    Returns:
        Tuple (triggered, exit_reason, exit_price). When triggered is False
        the other two values are unspecified.

    Logic:
        - For longs: TP is hit when High >= entry*(1+tp/100); SL when Low
          <= entry*(1-sl/100).
        - For shorts: TP when Low <= entry*(1-tp/100); SL when High
          >= entry*(1+sl/100).
        - If both are hit in the same candle, resolution mode breaks the
          tie. The trade exits at the chosen level's exact price.

    This function is FP (pure transform). Refactor policy in
    docs/superpowers/specs/2026-05-22-finish-todo-sequencing-design.md.
    """
    high = row['High']
    low = row['Low']
    open_ = row['Open']
    close = row['Close']

    if direction == 1:  # long
        tp_price = entry_price * (1 + take_profit / 100)
        sl_price = entry_price * (1 - stop_loss / 100)
        tp_hit = high >= tp_price
        sl_hit = low <= sl_price
    else:  # short
        tp_price = entry_price * (1 - take_profit / 100)
        sl_price = entry_price * (1 + stop_loss / 100)
        tp_hit = low <= tp_price
        sl_hit = high >= sl_price

    if not tp_hit and not sl_hit:
        return False, '', 0.0
    if tp_hit and not sl_hit:
        return True, 'TAKE PROFIT', tp_price
    if sl_hit and not tp_hit:
        return True, 'STOP LOSS', sl_price

    # Both hit in the same candle -> apply resolution mode.
    if resolution == 'optimistic':
        return True, 'TAKE PROFIT', tp_price
    if resolution == 'direction-proxy':
        # Green candle (closed up) -> assume price went up to TP first.
        # Red candle (closed down) -> assume it went down to SL first.
        # Doji (close == open) falls back to conservative.
        if close > open_:
            return True, 'TAKE PROFIT', tp_price
        if close < open_:
            return True, 'STOP LOSS', sl_price
    # Default / 'conservative' / doji: assume the bad side hit first.
    return True, 'STOP LOSS', sl_price


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 10000,
    stop_loss: float = 1.0,
    take_profit: float = 1.5,
    max_daily_trades: int = 10,
    fee_per_trade: float = 1.0,
    slippage_pct: float = 0.0005,
    tp_sl_resolution: str = 'conservative',
) -> Tuple[List[Dict], float]:
    """Run backtest simulation with fee, slippage, and intra-candle TP/SL.

    Args:
        df: DataFrame with Open/High/Low/Close prices and 'signal' column
            (-1 short, 0 hold, 1 long).
        initial_capital: Starting capital.
        stop_loss: Stop loss percentage (0.5 = 0.5%).
        take_profit: Take profit percentage (1.5 = 1.5%).
        max_daily_trades: Maximum trades per day.
        fee_per_trade: Fixed commission fee per trade.
        slippage_pct: Slippage on entry/exit (0.0005 = 0.05%).
        tp_sl_resolution: How to break ties when High >= TP AND Low <= SL
            in the same candle (iter 4, TODO item 10):
              - 'conservative' (default): assume SL hit first (worst case)
              - 'optimistic': assume TP hit first (best case)
              - 'direction-proxy': use candle Close vs Open as tiebreaker

    Returns:
        Tuple of (list of trades, final capital).
    """
    if tp_sl_resolution not in _RESOLUTION_MODES:
        raise ValueError(
            f"tp_sl_resolution must be one of {_RESOLUTION_MODES}, "
            f"got {tp_sl_resolution!r}"
        )

    trades: List[Dict] = []
    capital = initial_capital
    position = None
    entry_price = 0.0
    entry_idx = 0

    daily_trade_count = 0
    last_date = None

    date_col = 'Date' if 'Date' in df.columns else (
        'datetime' if 'datetime' in df.columns else None
    )

    for idx in range(len(df)):
        row = df.iloc[idx]
        current_date = row[date_col] if date_col else idx

        if last_date is not None and str(current_date) != str(last_date):
            daily_trade_count = 0
        last_date = current_date

        signal = row.get('signal', row.get('ml_signal', 0))

        if position is None and signal != 0 and daily_trade_count < max_daily_trades:
            position = signal
            entry_price = row['Close'] * (
                1 + slippage_pct if signal == 1 else 1 - slippage_pct
            )
            entry_idx = idx
            daily_trade_count += 1
            continue

        if position is not None:
            triggered, exit_reason, raw_exit_price = _resolve_intra_candle_exit(
                direction=position,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                row=row,
                resolution=tp_sl_resolution,
            )

            if not triggered:
                continue

            # Apply slippage to the chosen exit price.
            exit_price = raw_exit_price * (
                1 - slippage_pct if position == 1 else 1 + slippage_pct
            )

            if position == 1:
                profit_pct = (exit_price - entry_price) / entry_price * 100
            else:
                profit_pct = (entry_price - exit_price) / entry_price * 100

            profit = capital * (profit_pct / 100) - fee_per_trade
            capital += profit

            trades.append({
                'entry_idx': entry_idx,
                'exit_idx': idx,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'direction': 'long' if position == 1 else 'short',
                'profit_pct': profit_pct,
                'profit_dollars': profit,
                'capital_after': capital,
                'exit_reason': exit_reason,
                'fees_paid': fee_per_trade,
            })

            position = None

    return trades, capital


def calculate_max_drawdown(trades: List[Dict], initial_capital: float) -> float:
    """Calculate maximum drawdown from trades."""
    capital_curve = [initial_capital]
    for trade in trades:
        capital_curve.append(trade['capital_after'])

    peak = capital_curve[0]
    max_dd = 0.0

    for capital in capital_curve:
        if capital > peak:
            peak = capital
        dd = (peak - capital) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return max_dd
