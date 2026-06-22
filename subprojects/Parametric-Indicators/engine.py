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
    # Per-direction (split) SL/TP — OPTIONAL. Each None field falls back to the shared *_points above, so a
    # params object that sets none of these is byte-identical to before (golden-locked). When set, the value
    # applies to that FINAL (post-flip) entry direction. Added at the END so positional construction is
    # unaffected. See study_range_regime/ACTION_PLAN_range_regime_sltp.md (Phase E) + UPDATE_engine_split_sltp.md.
    long_sl_soft_points:  Optional[float] = None
    long_sl_hard_points:  Optional[float] = None
    long_tp_soft_points:  Optional[float] = None
    long_tp_hard_points:  Optional[float] = None
    short_sl_soft_points: Optional[float] = None
    short_sl_hard_points: Optional[float] = None
    short_tp_soft_points: Optional[float] = None
    short_tp_hard_points: Optional[float] = None


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
        # Resolve per-direction (split) SL/TP once. Each side's 4 points = its split field if set, else the
        # shared *_points (⇒ when NO split field is set, _long == _short == shared ⇒ byte-identical). Validate
        # ordering/positivity per side so a split can't sneak in a bad line.
        def _side(side: str):
            ss = getattr(params, f'{side}_sl_soft_points')
            sh = getattr(params, f'{side}_sl_hard_points')
            ts = getattr(params, f'{side}_tp_soft_points')
            th = getattr(params, f'{side}_tp_hard_points')
            ss = params.sl_soft_points if ss is None else float(ss)
            sh = params.sl_hard_points if sh is None else float(sh)
            ts = params.tp_soft_points if ts is None else float(ts)
            th = params.tp_hard_points if th is None else float(th)
            for nm, v in (('sl_soft', ss), ('sl_hard', sh), ('tp_soft', ts), ('tp_hard', th)):
                if v <= 0:
                    raise ValueError(f'{side}_{nm}_points must be > 0, got {v}')
            if sh < ss:
                raise ValueError(f'{side}_sl_hard_points ({sh}) must be >= {side}_sl_soft_points ({ss})')
            if th < ts:
                raise ValueError(f'{side}_tp_hard_points ({th}) must be >= {side}_tp_soft_points ({ts})')
            return (ss, sh, ts, th)
        self._long_pts = _side('long')    # (sl_soft, sl_hard, tp_soft, tp_hard) for FINAL dir == 'long'
        self._short_pts = _side('short')  # …for FINAL dir == 'short'

    def backtest(
        self,
        df_4h: pd.DataFrame,
        df_1min: pd.DataFrame,
        box_df_indexed: pd.DataFrame,
        sl_tp_mult: Optional[np.ndarray] = None,
        tp_mult: Optional[np.ndarray] = None,
        entry_gate: Optional[np.ndarray] = None,
        entry_resolver=None,
        veto_mask: Optional[np.ndarray] = None,
        blocked_log: Optional[List[Dict]] = None,
        veto_as_flip: bool = False,
        signals: Optional[np.ndarray] = None,
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

        # Axis-B (Step B2): optional precomputed per-decision-bar Stage-1 signal array (object dtype,
        # 'long'/'short'/'hold'), aligned 1:1 with df_4h. When supplied, the entry branch reads
        # signals[idx-1] instead of recomputing _stage1_candle_signal + box.loc per bar — proven
        # identical (optimize.signals.decision_signals + tests/test_axisB_signal_equiv.py).
        # None ⇒ ORIGINAL behaviour, byte-for-byte unchanged.
        if signals is not None and len(signals) != len(df_4h):
            raise ValueError(f'signals length {len(signals)} != df_4h length {len(df_4h)}')

        # Axis-B (Step B3a): pre-extract the decision-frame columns used in the loop as numpy arrays
        # ONCE, so the per-bar hot path indexes plain arrays instead of building a pandas Series via
        # df_4h.iloc[idx] (fast_xs) every bar. Date is tz-naive datetime64 (verified) so to_numpy is a
        # zero-copy view and pd.Timestamp(d4_dates[i]) == pd.Timestamp(df_4h['Date'].iloc[i]); Close
        # float matches float(row['Close']) bit-for-bit. (The signals=None path still builds the row
        # for _stage1_candle_signal — unchanged parity.)
        d4_dates = df_4h['Date'].to_numpy()
        d4_close = df_4h['Close'].to_numpy(dtype=float)

        if not df_1min.empty:
            ts_4h_arr = df_4h['Date'].to_numpy()
            ts_1m_arr = df_1min['Date'].to_numpy()
            start_1m = np.searchsorted(ts_1m_arr, ts_4h_arr, side='left')
            start_1m = np.append(start_1m, len(ts_1m_arr))
            # Axis-B (Step B3b): pre-extract the 1-min columns the exit walk reads as numpy arrays ONCE,
            # so _walk_exit_for_4h iterates by index instead of slicing df_1min.iloc[lo:hi] + itertuples
            # every window. Date tz-naive datetime64 (zero-copy view); High/Low/Close are float64. Per-bar
            # values are still wrapped in float()/pd.Timestamp() so trade dicts are bit-identical.
            md_arr = ts_1m_arr
            mh_arr = df_1min['High'].to_numpy(dtype=float)
            ml_arr = df_1min['Low'].to_numpy(dtype=float)
            mc_arr = df_1min['Close'].to_numpy(dtype=float)
        else:
            start_1m = None
            md_arr = mh_arr = ml_arr = mc_arr = None

        trades: List[Dict] = []
        open_trade: Optional[Dict] = None
        blocked_until: Optional[pd.Timestamp] = None
        soft_consec_count: int = 0   # consecutive 1-min closes past the active soft line
        armed: Optional[Dict] = None  # carry-mode (entry_resolver) armed-but-unfilled setup
        scope = self.params.direction_scope
        flip = self.params.flip_entry_direction
        # veto_as_flip: a vetoed (but otherwise eligible) signal ENTERS THE OPPOSITE direction
        # instead of being dropped. The caller passes a vol-only entry_gate in this mode (so vetoed
        # bars are not pre-filtered) plus the veto_mask used here to decide which entries to reverse.
        def _opp(d):
            return 'short' if d == 'long' else 'long'

        def _walk_exit_for_4h(idx: int) -> None:
            """Walk 1-min bars belonging to df_4h[idx] looking for an exit on the currently open
            trade. Single exit model regardless of `flip`: hard-SL > hard-TP > soft-SL on the
            ENTERED direction. `flip` only reverses entry direction (see entry logic below)."""
            nonlocal open_trade, blocked_until, soft_consec_count
            if open_trade is None or start_1m is None:
                return
            lo = int(start_1m[idx])
            hi = int(start_1m[idx + 1])
            d   = open_trade['direction']
            ss  = open_trade['sl_soft_line']
            sh  = open_trade['sl_hard_line']
            ts_ = open_trade['tp_soft_line']
            th  = open_trade['tp_hard_line']
            ep  = open_trade['entry_price']
            pv  = self.NQ_POINT_VALUE
            entry_time_np = np.datetime64(open_trade['entry_time'])   # for the no-look-ahead skip

            for t in range(lo, hi):
                if md_arr[t] < entry_time_np:                          # sub_ts < entry_time (skip pre-entry)
                    continue
                m_high  = float(mh_arr[t])
                m_low   = float(ml_arr[t])
                m_close = float(mc_arr[t])

                exit_reason: Optional[ExitReason] = None
                fill: Optional[float] = None
                resets_counter = True

                # Single exit model (flip or not): hard-SL > hard-TP > soft-SL on the ENTERED
                # direction. `flip` only reverses entry direction; it no longer swaps "soft" to the
                # TP side. (ts_ stays computed at entry but unused — soft-TP is inactive, as before.)
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

                if exit_reason is not None and fill is not None:
                    sub_ts = pd.Timestamp(md_arr[t])                   # materialise the exit timestamp
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
            ts_new_bar_start = pd.Timestamp(d4_dates[idx])

            # Exit walk for a carry-over trade (1-min bars in this new window).
            _walk_exit_for_4h(idx)

            # Entry decision: needs a just-closed predecessor bar (idx >= 1).
            if open_trade is None and idx >= 1:
                if blocked_until is not None and ts_new_bar_start <= blocked_until:
                    continue
                # Signal is computed from the JUST-CLOSED bar (idx-1), not
                # from the current bar. Box geometry is keyed off the
                # just-closed bar's timestamp.
                if signals is not None:
                    # Step B2: use the precomputed signal of the just-closed bar (idx-1).
                    signal = signals[idx - 1]
                else:
                    # ORIGINAL parity path: build the row only here (it feeds _stage1_candle_signal).
                    signal_candle = df_4h.iloc[idx - 1]
                    signal_ts = pd.Timestamp(d4_dates[idx - 1])
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

                # ADAPTIVE-CLONE: per-bar SL/TP multiplier (1.0 => original; scales ALL four lines).
                _m = 1.0
                if sl_tp_mult is not None and 0 <= idx < len(sl_tp_mult):
                    _mv = float(sl_tp_mult[idx])
                    if np.isfinite(_mv) and _mv > 0:
                        _m = _mv
                # per-bar TP-ONLY multiplier (1.0 => original; scales only the TP lines, SL untouched).
                # Lets the regime study move TP while pinning SL (Q3b). Default None ⇒ _tm=1 ⇒ identical.
                _tm = 1.0
                if tp_mult is not None and 0 <= idx < len(tp_mult):
                    _tv = float(tp_mult[idx])
                    if np.isfinite(_tv) and _tv > 0:
                        _tm = _tv

                # gate (vol etc.) matches the original: only blocks when set, in-range, and False.
                gated = (entry_gate is None) or not (0 <= idx < len(entry_gate)) or bool(entry_gate[idx])
                vetoed = (veto_mask is not None) and (0 <= idx < len(veto_mask)) and bool(veto_mask[idx])

                # DIAGNOSTIC ONLY (no effect on trades): record fresh in-scope directional signals
                # that the composite gate dropped, so the caller can LOG them instead of silently
                # discarding them. gate = vol ∧ ¬veto, so 'not gated' ⇒ veto (if vetoed) else vol-gate.
                if (blocked_log is not None and signal in ('long', 'short') and not gated
                        and not (scope == 'long_only' and signal != 'long')
                        and not (scope == 'short_only' and signal != 'short')):
                    blocked_log.append({'entry_idx': idx, 'signal_idx': idx - 1,
                                        'direction': signal,
                                        # in veto_as_flip mode a veto never blocks (it reverses),
                                        # so a dropped bar here is always the volatility gate.
                                        'reason': 'veto' if (vetoed and not veto_as_flip) else 'vol_gate'})

                if entry_resolver is None:
                    # ORIGINAL parity path (unchanged behaviour): immediate fill at the signal close.
                    if signal == 'hold':
                        continue
                    if scope == 'long_only' and signal != 'long':
                        continue
                    if scope == 'short_only' and signal != 'short':
                        continue
                    if not gated:
                        continue
                    entry_ts = ts_new_bar_start
                    entry_px = float(d4_close[idx - 1])
                    edir, sidx = signal, idx - 1
                    vflip = bool(veto_as_flip and vetoed)
                    if vflip:
                        edir = _opp(edir)              # veto reverses the entry direction
                else:
                    # CARRY MODE (live B1): (re)arm on a fresh gated, non-vetoed directional signal;
                    # carry an unfilled setup across HOLD bars; abort on a fresh veto; supersede on a
                    # new signal. The resolver reads votes LIVE at idx-1 and anchors levels to the
                    # ARMED signal's close.
                    in_scope = (signal in ('long', 'short')
                                and not (scope == 'long_only' and signal != 'long')
                                and not (scope == 'short_only' and signal != 'short'))
                    if in_scope and gated:
                        if vetoed and veto_as_flip:
                            # veto reverses: (re)arm the OPPOSITE direction instead of aborting.
                            armed = {'dir': _opp(signal), 'sidx': idx - 1,
                                     'sclose': float(d4_close[idx - 1]), 'vflip': True}
                        elif not vetoed:
                            armed = {'dir': signal, 'sidx': idx - 1,
                                     'sclose': float(d4_close[idx - 1]), 'vflip': False}
                    if armed is not None and vetoed and not veto_as_flip:
                        armed = None                      # live veto aborts the armed entry (Q4)
                    if armed is None or start_1m is None:
                        continue
                    sub_w = df_1min.iloc[int(start_1m[idx]):int(start_1m[idx + 1])]
                    res = entry_resolver(idx, armed['dir'], armed['sclose'], armed['sidx'],
                                         ts_new_bar_start, sub_w)
                    if res is None:
                        continue                          # keep armed → carry to the next bar
                    entry_ts = pd.Timestamp(res[0])
                    entry_px = float(res[1])
                    edir, sidx = armed['dir'], armed['sidx']
                    vflip = bool(armed.get('vflip'))
                    armed = None

                # per-direction (split) points; _long_pts/_short_pts == shared when no split set ⇒ identical
                if edir == 'long':
                    ss, sh, ts, th = self._long_pts
                    sl_soft_line = entry_px - ss * _m
                    sl_hard_line = entry_px - sh * _m
                    tp_soft_line = entry_px + ts * _m * _tm
                    tp_hard_line = entry_px + th * _m * _tm
                else:
                    ss, sh, ts, th = self._short_pts
                    sl_soft_line = entry_px + ss * _m
                    sl_hard_line = entry_px + sh * _m
                    tp_soft_line = entry_px - ts * _m * _tm
                    tp_hard_line = entry_px - th * _m * _tm

                open_trade = {
                    'entry_idx':    idx,                       # the new bar
                    'signal_idx':   sidx,                      # the (armed) signal's just-closed bar
                    'entry_time':   entry_ts,
                    'entry_price':  entry_px,
                    'direction':    edir,
                    'veto_flip':    bool(vflip),               # entered reversed because of a veto
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
