"""Simple backtest engine — Stage 1 entry + 1-min SL/TP exit.

Replacement for the box/ladder/dual-anchor stack. Decision sheet:

  - Entry direction = Stage 1 truth table (per-candle, stateless).
        long  iff touched and color=green and close > box_upper
        short iff touched and color=red   and close < box_lower
        hold  otherwise
    Collapsed to candle level: any-long → long, any-short → short, else hold.

  - Position size = 1 contract. No ladder. No anchor toggle.

  - Exit reasons = TAKE_PROFIT or STOP_LOSS only. Both fire on a 1-min
    `close` past the relevant line. No soft/hard split, no direction-flip,
    no trail, no big-candle override.

  - Re-entry gate: after an exit at time T, the next 4h candle is eligible
    only if its `Date` (4h start) > T. The first eligible 4h candle is
    evaluated fresh against Stage 1's rule; if it says hold, we keep
    waiting; if it says long/short, we open immediately — regardless of
    the previous trade's direction or exit reason.

  - Tie-break: a single 1-min close cannot satisfy both fire conditions
    under the close-past rule (SL_line < entry_price < TP_line; close
    can only be on one side). Documented for completeness.

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
ExitReason = Literal['TAKE_PROFIT', 'STOP_LOSS', 'OPEN']


@dataclass
class SimpleStrategyParams:
    """All values REQUIRED (no-fallback rule)."""
    sl_points: float
    tp_points: float
    data_path_4h: str
    data_path_1min: str
    box_data_path: str
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
        # Color/direction mismatch and close-on-edge both stay hold for
        # this level pair.

    # Stage 1's color rule guarantees a candle can't fire long AND short
    # simultaneously (green can only fire long, red can only fire short).
    if has_long:
        return 'long'
    if has_short:
        return 'short'
    return 'hold'


def _exit_check_close_past(
    direction: Signal,
    tp_line: float,
    sl_line: float,
    one_min_close: float,
) -> Optional[ExitReason]:
    """Return TAKE_PROFIT / STOP_LOSS / None for a single 1-min close.

    Close-past semantics for both lines. A single close cannot fire both
    (SL_line < entry < TP_line for long; opposite for short).
    """
    if direction == 'long':
        if one_min_close >= tp_line:
            return 'TAKE_PROFIT'
        if one_min_close <= sl_line:
            return 'STOP_LOSS'
    else:
        if one_min_close <= tp_line:
            return 'TAKE_PROFIT'
        if one_min_close >= sl_line:
            return 'STOP_LOSS'
    return None


class SimpleStrategy:
    """Simple backtest engine — Stage 1 entry + 1-min SL/TP exit.

    Decoupled from BoxStrategy / ScalingStrategy. Does not share state.
    Reads the same box CSV the old engine reads, but uses Stage 1's
    stateless per-candle rule for entry direction.
    """

    NQ_POINT_VALUE = 20.0  # NQ futures: $20 per point per contract.

    def __init__(self, params: SimpleStrategyParams) -> None:
        self.params = params
        if params.sl_points <= 0:
            raise ValueError(f'sl_points must be > 0, got {params.sl_points}')
        if params.tp_points <= 0:
            raise ValueError(f'tp_points must be > 0, got {params.tp_points}')
        if params.direction_scope not in ('both', 'long_only', 'short_only'):
            raise ValueError(f'direction_scope invalid: {params.direction_scope}')

    def backtest(
        self,
        df_4h: pd.DataFrame,
        df_1min: pd.DataFrame,
        box_df_indexed: pd.DataFrame,
    ) -> Tuple[List[Dict], Dict]:
        """Run the simple engine.

        Args:
            df_4h: 4h OHLCV with a 'Date' column (Timestamp); the bar's
                START time, e.g. 18:00 for the 18:00-22:00 bar.
            df_1min: 1-min OHLCV with a 'Date' column (Timestamp); also
                bar-start times.
            box_df_indexed: Box CSV indexed on `Date` (normalised).

        Returns:
            (trades, final_state). `trades` is a list of dicts (schema in
            plan §5). `final_state` summarises whether a trade was open
            at EOF.
        """
        if df_4h.empty:
            return [], {'open_trade': None}

        # Pre-index 1-min by 4h start for O(log N) windowing.
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
        scope = self.params.direction_scope

        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit
            on the currently open trade. Mutates `open_trade`, `trades`,
            and `blocked_until` (via nonlocal)."""
            nonlocal open_trade, blocked_until
            if open_trade is None or start_1m is None:
                return
            lo = int(start_1m[idx])
            hi = int(start_1m[idx + 1])
            sub_bars = df_1min.iloc[lo:hi]
            for sub in sub_bars.itertuples(index=False):
                sub_ts = pd.Timestamp(getattr(sub, 'Date'))
                if sub_ts < open_trade['entry_time']:
                    continue
                sub_close = float(getattr(sub, 'Close'))
                reason = _exit_check_close_past(
                    direction=open_trade['direction'],
                    tp_line=open_trade['tp_line'],
                    sl_line=open_trade['sl_line'],
                    one_min_close=sub_close,
                )
                if reason is not None:
                    open_trade['exit_time']   = sub_ts
                    open_trade['exit_price']  = sub_close
                    open_trade['exit_reason'] = reason
                    if open_trade['direction'] == 'long':
                        pnl = sub_close - open_trade['entry_price']
                    else:
                        pnl = open_trade['entry_price'] - sub_close
                    open_trade['pnl_points']  = pnl
                    open_trade['pnl_dollars'] = pnl * self.NQ_POINT_VALUE
                    trades.append(open_trade)
                    blocked_until = sub_ts
                    open_trade = None
                    return

        for idx in range(len(df_4h)):
            candle = df_4h.iloc[idx]
            ts_4h = pd.Timestamp(candle['Date'])

            # ---------------- Exit walk for CARRY-OVER trade ----------------
            # Walks 1-min bars in THIS 4h window for a trade that was already
            # open coming into this 4h.
            _walk_exit_for_4h(idx)

            # ---------------- Entry decision (only if flat and past gate) ----
            if open_trade is None:
                if blocked_until is not None and ts_4h <= blocked_until:
                    continue
                # Resolve the box row for this 4h candle's mapped date.
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
                    tp_line = close + self.params.tp_points
                    sl_line = close - self.params.sl_points
                else:
                    tp_line = close - self.params.tp_points
                    sl_line = close + self.params.sl_points

                open_trade = {
                    'entry_idx':   idx,
                    'entry_time':  ts_4h,
                    'entry_price': close,
                    'direction':   signal,
                    'tp_line':     tp_line,
                    'sl_line':     sl_line,
                    'exit_time':   None,
                    'exit_price':  None,
                    'exit_reason': None,
                    'pnl_points':  None,
                    'pnl_dollars': None,
                }
                # ---------- Exit walk for the SAME 4h that just fired ----
                # Walk 1-min bars in this 4h from entry_time forward; an SL
                # or TP can fire in the same window the trade opened.
                _walk_exit_for_4h(idx)

        # ---------------- EOF: emit any still-open trade as OPEN ----------
        if open_trade is not None:
            open_trade['exit_reason'] = 'OPEN'
            trades.append(open_trade)

        final_state = {'open_trade': None if trades and trades[-1]['exit_reason'] != 'OPEN' else open_trade}
        return trades, final_state
