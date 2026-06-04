"""Simple backtest engine — Stage 1 entry + dual-SL/TP exit on 1-min bars.

Two coexisting modes selected by `flip_entry_direction`:

  NORMAL mode (flip_entry_direction=False, the default):
    - Entry direction = Stage 1 signal verbatim.
    - Exit lines: sl_soft, sl_hard, tp_hard.
    - Soft SL fires on 2 consecutive 1-min closes past sl_soft_line; fill at 2nd close.
    - Hard SL fires on bar EXTREME touching sl_hard_line; fill at line.
    - Hard TP fires on bar EXTREME touching tp_hard_line; fill at line.
    - Per-bar tie-break: hard SL > hard TP > soft SL (loss-first pessimism).

  FLIPPED mode (flip_entry_direction=True):
    - Entry direction = Stage 1 signal SWAPPED (long↔short); holds untouched.
    - Exit lines: tp_soft, tp_hard, sl_hard. (Soft SL is inactive.)
    - Soft TP fires on 2 consecutive 1-min closes past tp_soft_line; fill at 2nd close.
    - Hard SL fires on bar EXTREME touching sl_hard_line; fill at line.
    - Hard TP fires on bar EXTREME touching tp_hard_line; fill at line.
    - Per-bar tie-break: hard TP > hard SL > soft TP (symmetric flip — the whole
      logic flips, including the priority order).

  Entry signal at candle level (both modes):
        long  iff Stage 1 rule fires long
        short iff Stage 1 rule fires short
        hold  otherwise
    Collapsed: any-long → long, any-short → short, else hold.

  Position size = 1 contract. No ladder. NQ point value = $20.

  Line orientation (both modes — depends on the actual position direction,
  i.e. the post-flip direction in flipped mode):
    long position:  sl_soft_line, sl_hard_line below entry; tp_soft_line, tp_hard_line above
    short position: mirrored

  Re-entry gate (both modes): after exit at time T, next 4h candle is signal-
  eligible iff its `Date` (4h start) > T. Fresh Stage 1 evaluation; no SL/TP
  differentiation in the gate; no direction memory.

  All four soft/hard thresholds (sl_soft, sl_hard, tp_soft, tp_hard) are
  REQUIRED > 0. Constraints: sl_hard >= sl_soft, tp_hard >= tp_soft. The
  inactive soft threshold (sl_soft when flipped, tp_soft when normal) is
  validated but ignored at runtime in that mode.

Live reference: `docs/strategy/files/simple_strategy.md` (file overview) and
`docs/strategy/references/simple_engine_truth_table.md` (formal decision tables).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from box_lookup import BoxLookup, _MONTHLY_LEVELS, _WEEKLY_LEVELS


_LEVEL_PAIRS = _WEEKLY_LEVELS + _MONTHLY_LEVELS

DirectionScope = Literal['both', 'long_only', 'short_only']
Signal = Literal['long', 'short', 'hold']
ExitReason = Literal[
    'STOP_LOSS_HARD',
    'STOP_LOSS_SOFT',
    'TAKE_PROFIT_HARD',
    'TAKE_PROFIT_SOFT',
    'OPEN',
]


@dataclass
class SimpleStrategyParams:
    """All values REQUIRED (no-fallback rule).

    Constraints:
      - sl_hard_points >= sl_soft_points (the hard SL line is at or beyond
        the soft SL line)
      - tp_hard_points >= tp_soft_points (the hard TP line is at or beyond
        the soft TP line)

    All four soft/hard thresholds are validated > 0 regardless of mode;
    one of them is inactive at runtime (sl_soft_points when flipped,
    tp_soft_points when not flipped) but the value is preserved so the
    user can round-trip between modes without losing input.
    """
    sl_soft_points: float
    sl_hard_points: float
    tp_soft_points: float
    tp_hard_points: float
    data_path_4h:   str
    data_path_1min: str
    box_data_path:  str
    direction_scope:       DirectionScope = 'both'
    flip_entry_direction:  bool = False


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
        for fld in ('sl_soft_points', 'sl_hard_points', 'tp_soft_points', 'tp_hard_points'):
            v = getattr(params, fld)
            if v <= 0:
                raise ValueError(f'{fld} must be > 0, got {v}')
        if params.sl_hard_points < params.sl_soft_points:
            raise ValueError(
                f'sl_hard_points ({params.sl_hard_points}) must be >= '
                f'sl_soft_points ({params.sl_soft_points})'
            )
        if params.tp_hard_points < params.tp_soft_points:
            raise ValueError(
                f'tp_hard_points ({params.tp_hard_points}) must be >= '
                f'tp_soft_points ({params.tp_soft_points})'
            )
        if params.direction_scope not in ('both', 'long_only', 'short_only'):
            raise ValueError(f'direction_scope invalid: {params.direction_scope}')
        if not isinstance(params.flip_entry_direction, bool):
            raise ValueError(f'flip_entry_direction must be bool, got {type(params.flip_entry_direction)}')
        self.params = params

    def backtest(
        self,
        df_4h: pd.DataFrame,
        df_1min: pd.DataFrame,
        box_df_indexed: pd.DataFrame,
        sl_tp_mult: Optional[np.ndarray] = None,
        entry_gate: Optional[np.ndarray] = None,
        entry_resolver=None,
    ) -> Tuple[List[Dict], Dict]:
        """Run the simple engine.

        ADAPTIVE-CLONE additions (absent from the original src engine):
          - sl_tp_mult: optional per-4h-bar array; multiplies all four SL/TP
            distances at entry (scaling all four preserves ordering constraints).
            None or 1.0 => identical to the original.
          - entry_gate: optional per-4h-bar bool array; if entry_gate[idx] is
            False, no new trade opens on that bar. None => identical to original.
        When both are None the clone is behaviourally identical to the original
        (verified by tests/test_clone_parity.py).

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
        soft_consec_count: int = 0   # consecutive 1-min closes past the active soft line
        scope = self.params.direction_scope
        flip = self.params.flip_entry_direction

        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit
            on the currently open trade. Dispatches to the normal or
            flipped exit model based on `flip`."""
            nonlocal open_trade, blocked_until, soft_consec_count
            if open_trade is None or start_1m is None:
                return
            lo = int(start_1m[idx])
            hi = int(start_1m[idx + 1])
            sub_bars = df_1min.iloc[lo:hi]
            d   = open_trade['direction']
            ss  = open_trade['sl_soft_line']
            sh  = open_trade['sl_hard_line']
            ts_ = open_trade['tp_soft_line']
            th  = open_trade['tp_hard_line']
            ep  = open_trade['entry_price']
            pv  = self.NQ_POINT_VALUE

            for sub in sub_bars.itertuples(index=False):
                sub_ts = pd.Timestamp(getattr(sub, 'Date'))
                if sub_ts < open_trade['entry_time']:
                    continue
                m_high  = float(getattr(sub, 'High'))
                m_low   = float(getattr(sub, 'Low'))
                m_close = float(getattr(sub, 'Close'))

                exit_reason: Optional[ExitReason] = None
                fill: Optional[float] = None
                resets_counter = True

                if not flip:
                    # NORMAL mode: hard SL > hard TP > soft SL.
                    if d == 'long':
                        if m_low <= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_high >= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_close <= ss:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'STOP_LOSS_SOFT', m_close
                    else:  # short
                        if m_high >= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_low <= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_close >= ss:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'STOP_LOSS_SOFT', m_close
                else:
                    # FLIPPED mode: hard TP > hard SL > soft TP (Q-A: symmetric flip).
                    if d == 'long':
                        if m_high >= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_low <= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_close >= ts_:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'TAKE_PROFIT_SOFT', m_close
                    else:  # short
                        if m_low <= th:
                            exit_reason, fill = 'TAKE_PROFIT_HARD', th
                        elif m_high >= sh:
                            exit_reason, fill = 'STOP_LOSS_HARD', sh
                        elif m_close <= ts_:
                            soft_consec_count += 1
                            resets_counter = False
                            if soft_consec_count >= 2:
                                exit_reason, fill = 'TAKE_PROFIT_SOFT', m_close

                if exit_reason is not None and fill is not None:
                    _finalise(open_trade, sub_ts, fill, exit_reason, ep, d, pv)
                    trades.append(open_trade)
                    blocked_until = sub_ts
                    open_trade = None
                    soft_consec_count = 0
                    return
                if resets_counter:
                    soft_consec_count = 0

        # NO-LOOK-AHEAD TIMING (spec interpretation):
        # At iteration `idx`, the just-closed 4h bar is df_4h.iloc[idx-1].
        # The new 4h boundary just arrived at df_4h.iloc[idx].Date — that's
        # the entry moment. Entry price = the just-closed bar's close.
        # Walk 1-min bars in window `idx` for exits (all of which post-date
        # the signal). The first iteration (idx=0) has no predecessor and
        # cannot fire a signal — matches the spec's "first-candle warm-up".
        for idx in range(len(df_4h)):
            candle = df_4h.iloc[idx]
            ts_new_bar_start = pd.Timestamp(candle['Date'])

            # Exit walk for a carry-over trade (1-min bars in this new window).
            _walk_exit_for_4h(idx)

            # Entry decision: needs a just-closed predecessor bar (idx >= 1).
            if open_trade is None and idx >= 1:
                if blocked_until is not None and ts_new_bar_start <= blocked_until:
                    continue
                # Signal is computed from the JUST-CLOSED bar (idx-1), not
                # from the current bar. Box geometry is keyed off the
                # just-closed bar's timestamp.
                signal_candle = df_4h.iloc[idx - 1]
                signal_ts = pd.Timestamp(signal_candle['Date'])
                box_date = BoxLookup._candle_to_box_date(signal_ts)
                try:
                    box_row = box_df_indexed.loc[box_date]
                except KeyError:
                    box_row = None

                signal = _stage1_candle_signal(signal_candle, box_row)

                # Flip layer (Q-A symmetric flip): swap long↔short BEFORE
                # scope filtering. Holds stay holds.
                if flip and signal in ('long', 'short'):
                    signal = 'short' if signal == 'long' else 'long'

                if signal == 'hold':
                    continue
                # Scope filter applies to the POST-flip direction (Q-2: B).
                if scope == 'long_only' and signal != 'long':
                    continue
                if scope == 'short_only' and signal != 'short':
                    continue

                # ADAPTIVE-CLONE: regime gate. Skip entry on gated-out bars.
                if entry_gate is not None and 0 <= idx < len(entry_gate) and not bool(entry_gate[idx]):
                    continue

                # ADAPTIVE-CLONE: per-bar SL/TP multiplier (1.0 => original).
                _m = 1.0
                if sl_tp_mult is not None and 0 <= idx < len(sl_tp_mult):
                    _mv = float(sl_tp_mult[idx])
                    if np.isfinite(_mv) and _mv > 0:
                        _m = _mv

                # Entry price = the just-closed bar's close == the new bar's
                # open in continuous data. Trade opens at ts_new_bar_start.
                close = float(signal_candle['Close'])

                # ADAPTIVE-CLONE: optional entry resolver (retrace-fill). Given the signal, it may
                # return a (fill_time, fill_price) inside this 4h window, or None to abandon the
                # entry (armed-but-unfilled → superseded). None resolver ⇒ immediate fill at the
                # signal close (parity).
                entry_ts = ts_new_bar_start
                entry_px = close
                if entry_resolver is not None and start_1m is not None:
                    sub_w = df_1min.iloc[int(start_1m[idx]):int(start_1m[idx + 1])]
                    res = entry_resolver(idx, signal, close, ts_new_bar_start, sub_w)
                    if res is None:
                        continue
                    entry_ts = pd.Timestamp(res[0])
                    entry_px = float(res[1])

                if signal == 'long':
                    sl_soft_line = entry_px - self.params.sl_soft_points * _m
                    sl_hard_line = entry_px - self.params.sl_hard_points * _m
                    tp_soft_line = entry_px + self.params.tp_soft_points * _m
                    tp_hard_line = entry_px + self.params.tp_hard_points * _m
                else:
                    sl_soft_line = entry_px + self.params.sl_soft_points * _m
                    sl_hard_line = entry_px + self.params.sl_hard_points * _m
                    tp_soft_line = entry_px - self.params.tp_soft_points * _m
                    tp_hard_line = entry_px - self.params.tp_hard_points * _m

                open_trade = {
                    'entry_idx':    idx,                       # the new bar
                    'signal_idx':   idx - 1,                   # the just-closed bar
                    'entry_time':   entry_ts,
                    'entry_price':  entry_px,
                    'direction':    signal,
                    'sl_soft_line': sl_soft_line,
                    'sl_hard_line': sl_hard_line,
                    'tp_soft_line': tp_soft_line,
                    'tp_hard_line': tp_hard_line,
                    'flip':         flip,
                    'exit_time':    None,
                    'exit_price':   None,
                    'exit_reason':  None,
                    'pnl_points':   None,
                    'pnl_dollars':  None,
                }
                soft_consec_count = 0

                # Exit walk for the same new 4h window (its 1-min bars are
                # all chronologically AFTER the signal — no look-ahead).
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
