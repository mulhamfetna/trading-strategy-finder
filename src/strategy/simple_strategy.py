"""Simple backtest engine — Stage 1 entry + dual-SL/TP exit on 1-min bars.

Replacement for the box/ladder/dual-anchor stack. Decision sheet:

  - Entry direction = Stage 1 truth table (per-candle, stateless).
        long  iff touched and color=green and close > box_upper
        short iff touched and color=red   and close < box_lower
        hold  otherwise
    Collapsed to candle level: any-long → long, any-short → short, else hold.

  - Position size = 1 contract. No ladder.

  - Exit model — three lines, two fire semantics, per-line fill price:

        Line     | Fire rule                                       | Fill price
        ---------+-------------------------------------------------+--------------
        Soft SL  | 2 consecutive 1-min CLOSES past the soft line   | the 2nd close
        Hard SL  | 1 single 1-min bar EXTREME touches the hard line | the hard line
        TP       | 1 single 1-min bar EXTREME touches the TP line   | the TP line

    For a long position:
        sl_soft_line = entry - sl_soft_points     (closer to entry, smaller pts)
        sl_hard_line = entry - sl_hard_points     (farther from entry, sl_hard >= sl_soft)
        tp_line      = entry + tp_points

      • Soft SL fires when the 1-min close ≤ sl_soft_line for two bars in a row.
        Fill price = the second close. The pnl is worse than -sl_soft_points
        because the close is past the line.
      • Hard SL fires when the 1-min low ≤ sl_hard_line. Fill = sl_hard_line.
        Pnl is exactly -sl_hard_points.
      • TP fires when the 1-min high ≥ tp_line. Fill = tp_line.
        Pnl is exactly +tp_points.

    For a short position the mirror applies (signs flipped).

  - Per-bar tie-break when multiple could fire: hard SL > TP > soft SL.
    Reasoning: hard SL and TP are intra-bar touch events; under the
    pessimistic ordering used here, the loss-side touch fires first.
    Soft SL fires at bar close, which is the last temporal event in the bar.

  - Re-entry gate: after an exit at time T, the next 4h candle is signal-
    eligible only if its `Date` (4h start) > T. The first eligible 4h is
    evaluated fresh against Stage 1's rule; if it says hold, we keep
    waiting; if long/short, we open immediately — regardless of the
    previous trade's direction or exit reason.

Spec: `backtest_updates.md` + `docs/superpowers/specs/2026-05-26-simple-backtest/notes.md`.
Plan: `docs/superpowers/plans/2026-05-26-simple-backtest.md`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from src.strategy.box_lookup import BoxLookup, _MONTHLY_LEVELS, _WEEKLY_LEVELS


_LEVEL_PAIRS = _WEEKLY_LEVELS + _MONTHLY_LEVELS

DirectionScope = Literal['both', 'long_only', 'short_only']
Signal = Literal['long', 'short', 'hold']
ExitReason = Literal['TAKE_PROFIT', 'STOP_LOSS_HARD', 'STOP_LOSS_SOFT', 'OPEN']


@dataclass
class SimpleStrategyParams:
    """All values REQUIRED (no-fallback rule).

    sl_hard_points must be >= sl_soft_points; the hard line sits at or
    beyond the soft line for safety semantics.
    """
    sl_soft_points: float
    sl_hard_points: float
    tp_points:      float
    data_path_4h:   str
    data_path_1min: str
    box_data_path:  str
    direction_scope: DirectionScope = 'both'


def _stage1_candle_signal(
    candle: pd.Series,
    box_row: Optional[pd.Series],
) -> Signal:
    """Evaluate Stage 1's truth table for one 4h candle against its mapped
    box-date row. Collapses across all active level pairs:
        any-long  → long
        any-short → short
        else      → hold
    """
    opn   = float(candle['Open'])
    high  = float(candle['High'])
    low   = float(candle['Low'])
    close = float(candle['Close'])

    if close > opn:
        color = 'green'
    elif close < opn:
        color = 'red'
    else:
        color = 'none'

    if box_row is None or color == 'none':
        return 'hold'

    has_long = False
    has_short = False
    for upper_col, lower_col, _label in _LEVEL_PAIRS:
        if upper_col not in box_row.index or lower_col not in box_row.index:
            continue
        u = box_row[upper_col]
        l = box_row[lower_col]
        if pd.isna(u) or pd.isna(l):
            continue
        b_upper = float(u)
        b_lower = float(l)
        touched = (low <= b_upper) and (high >= b_lower)
        if not touched:
            continue
        if color == 'green' and close > b_upper:
            has_long = True
        elif color == 'red' and close < b_lower:
            has_short = True

    if has_long:
        return 'long'
    if has_short:
        return 'short'
    return 'hold'


class SimpleStrategy:
    """Simple backtest engine — Stage 1 entry + dual-SL/TP exit.

    Decoupled from BoxStrategy / ScalingStrategy. Does not share state.
    Reads the same box CSV the old engine reads, but uses Stage 1's
    stateless per-candle rule for entry direction.
    """

    NQ_POINT_VALUE = 20.0  # NQ futures: $20 per point per contract.

    def __init__(self, params: SimpleStrategyParams) -> None:
        if params.sl_soft_points <= 0:
            raise ValueError(f'sl_soft_points must be > 0, got {params.sl_soft_points}')
        if params.sl_hard_points <= 0:
            raise ValueError(f'sl_hard_points must be > 0, got {params.sl_hard_points}')
        if params.sl_hard_points < params.sl_soft_points:
            raise ValueError(
                f'sl_hard_points ({params.sl_hard_points}) must be >= '
                f'sl_soft_points ({params.sl_soft_points})'
            )
        if params.tp_points <= 0:
            raise ValueError(f'tp_points must be > 0, got {params.tp_points}')
        if params.direction_scope not in ('both', 'long_only', 'short_only'):
            raise ValueError(f'direction_scope invalid: {params.direction_scope}')
        self.params = params

    def backtest(
        self,
        df_4h: pd.DataFrame,
        df_1min: pd.DataFrame,
        box_df_indexed: pd.DataFrame,
    ) -> Tuple[List[Dict], Dict]:
        """Run the simple engine.

        Returns (trades, final_state).
        """
        if df_4h.empty:
            return [], {'open_trade': None}

        if not df_1min.empty:
            ts_4h_arr = df_4h['Date'].to_numpy()
            ts_1m_arr = df_1min['Date'].to_numpy()
            start_1m = np.searchsorted(ts_1m_arr, ts_4h_arr, side='left')
            start_1m = np.append(start_1m, len(ts_1m_arr))
        else:
            start_1m = None

        trades: List[Dict] = []
        open_trade: Optional[Dict] = None
        blocked_until: Optional[pd.Timestamp] = None
        soft_consec_count: int = 0   # consecutive 1-min closes past soft SL
        scope = self.params.direction_scope

        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit
            on the currently open trade. Mutates the enclosing state via
            `nonlocal`."""
            nonlocal open_trade, blocked_until, soft_consec_count
            if open_trade is None or start_1m is None:
                return
            lo = int(start_1m[idx])
            hi = int(start_1m[idx + 1])
            sub_bars = df_1min.iloc[lo:hi]
            d  = open_trade['direction']
            ss = open_trade['sl_soft_line']
            sh = open_trade['sl_hard_line']
            tp = open_trade['tp_line']
            ep = open_trade['entry_price']
            for sub in sub_bars.itertuples(index=False):
                sub_ts = pd.Timestamp(getattr(sub, 'Date'))
                if sub_ts < open_trade['entry_time']:
                    continue
                m_high  = float(getattr(sub, 'High'))
                m_low   = float(getattr(sub, 'Low'))
                m_close = float(getattr(sub, 'Close'))

                # Priority within the bar: hard SL > TP > soft SL.
                if d == 'long':
                    if m_low <= sh:
                        _finalise(open_trade, sub_ts, sh, 'STOP_LOSS_HARD', ep, d, self.NQ_POINT_VALUE)
                        trades.append(open_trade)
                        blocked_until = sub_ts; open_trade = None; soft_consec_count = 0
                        return
                    if m_high >= tp:
                        _finalise(open_trade, sub_ts, tp, 'TAKE_PROFIT', ep, d, self.NQ_POINT_VALUE)
                        trades.append(open_trade)
                        blocked_until = sub_ts; open_trade = None; soft_consec_count = 0
                        return
                    if m_close <= ss:
                        soft_consec_count += 1
                        if soft_consec_count >= 2:
                            _finalise(open_trade, sub_ts, m_close, 'STOP_LOSS_SOFT', ep, d, self.NQ_POINT_VALUE)
                            trades.append(open_trade)
                            blocked_until = sub_ts; open_trade = None; soft_consec_count = 0
                            return
                    else:
                        soft_consec_count = 0
                else:  # short
                    if m_high >= sh:
                        _finalise(open_trade, sub_ts, sh, 'STOP_LOSS_HARD', ep, d, self.NQ_POINT_VALUE)
                        trades.append(open_trade)
                        blocked_until = sub_ts; open_trade = None; soft_consec_count = 0
                        return
                    if m_low <= tp:
                        _finalise(open_trade, sub_ts, tp, 'TAKE_PROFIT', ep, d, self.NQ_POINT_VALUE)
                        trades.append(open_trade)
                        blocked_until = sub_ts; open_trade = None; soft_consec_count = 0
                        return
                    if m_close >= ss:
                        soft_consec_count += 1
                        if soft_consec_count >= 2:
                            _finalise(open_trade, sub_ts, m_close, 'STOP_LOSS_SOFT', ep, d, self.NQ_POINT_VALUE)
                            trades.append(open_trade)
                            blocked_until = sub_ts; open_trade = None; soft_consec_count = 0
                            return
                    else:
                        soft_consec_count = 0

        for idx in range(len(df_4h)):
            candle = df_4h.iloc[idx]
            ts_4h = pd.Timestamp(candle['Date'])

            # Exit walk for a carry-over trade.
            _walk_exit_for_4h(idx)

            # Entry decision (only if flat and past the re-entry gate).
            if open_trade is None:
                if blocked_until is not None and ts_4h <= blocked_until:
                    continue
                box_date = BoxLookup._candle_to_box_date(ts_4h)
                try:
                    box_row = box_df_indexed.loc[box_date]
                except KeyError:
                    box_row = None

                signal = _stage1_candle_signal(candle, box_row)
                if signal == 'hold':
                    continue
                if scope == 'long_only' and signal != 'long':
                    continue
                if scope == 'short_only' and signal != 'short':
                    continue

                close = float(candle['Close'])
                if signal == 'long':
                    sl_soft_line = close - self.params.sl_soft_points
                    sl_hard_line = close - self.params.sl_hard_points
                    tp_line      = close + self.params.tp_points
                else:
                    sl_soft_line = close + self.params.sl_soft_points
                    sl_hard_line = close + self.params.sl_hard_points
                    tp_line      = close - self.params.tp_points

                open_trade = {
                    'entry_idx':    idx,
                    'entry_time':   ts_4h,
                    'entry_price':  close,
                    'direction':    signal,
                    'sl_soft_line': sl_soft_line,
                    'sl_hard_line': sl_hard_line,
                    'tp_line':      tp_line,
                    'exit_time':    None,
                    'exit_price':   None,
                    'exit_reason':  None,
                    'pnl_points':   None,
                    'pnl_dollars':  None,
                }
                soft_consec_count = 0

                # Exit walk for the same 4h that just fired the signal.
                _walk_exit_for_4h(idx)

        if open_trade is not None:
            open_trade['exit_reason'] = 'OPEN'
            trades.append(open_trade)

        final_state = {
            'open_trade': None if trades and trades[-1]['exit_reason'] != 'OPEN' else open_trade,
        }
        return trades, final_state


def _finalise(
    trade: Dict,
    exit_ts: pd.Timestamp,
    fill: float,
    reason: ExitReason,
    entry_price: float,
    direction: Signal,
    point_value: float,
) -> None:
    """Stamp the exit fields on a trade dict in place."""
    trade['exit_time']   = exit_ts
    trade['exit_price']  = fill
    trade['exit_reason'] = reason
    if direction == 'long':
        pnl = fill - entry_price
    else:
        pnl = entry_price - fill
    trade['pnl_points']  = pnl
    trade['pnl_dollars'] = pnl * point_value
