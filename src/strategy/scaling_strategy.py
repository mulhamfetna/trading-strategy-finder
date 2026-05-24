"""1-1-2 scaling strategy simulator (phase C1).

Implements the strategy documented in
``Currunt_Strategy_Algo_for_Trading.md``:

* Entry distribution & position sizing (1-1-2 scaling, 4 contracts total).
* Big-candle exception (>400 points -> enter full, reverse direction).
* Take profit at +150 points with a watch threshold at +50.
* Dual stop loss (soft + hard) - close beyond the line, not just a wick.
* Optional re-entry on pullback after a profitable exit.

The strategy is OOP per the hybrid refactor policy: it has
configuration (`ScalingParams`) and a stateful lifecycle (legs filling,
watching for TP, exit, cooldown, re-entry). The per-candle decisions
delegate to small pure functions for testability.

**Approximations on 4h data**
The playbook prescribes multi-timeframe confirmations (15-second
entry confirmation, 2-minute SL1 close, 5-second SL2 close). With 4h
bars these are impossible to model directly. We approximate by:

* treating each 4h close as already passing the 15-sec confirmation,
* treating each 4h close beyond an SL line as the "candle close beyond"
  event (both SL1 and SL2 collapse to the same trigger granularity),
* checking pullbacks via the 4h candle's Low/High (long/short).

These approximations are conservative: they may exit earlier than the
real system would. All thresholds are exposed in ``ScalingParams`` so
the UI can tune them.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from src.exceptions import MissingParameterError


@dataclass
class ScalingParams:
    """Every parameter the strategy exposes to the settings UI.

    Every value below is a *decision* the playbook makes
    (Currunt_Strategy_Algo_for_Trading.md). Per the no-fallback rule
    (see docs/CODING_RULES.md) every field is REQUIRED — there are no
    dataclass defaults. The frontend supplies all of them at the API
    boundary; tests should use a fixture helper instead of relying on
    field defaults.
    """

    # §1 Entry distribution & sizing ----------------------------------------
    total_contracts: int
    leg1_contracts: int
    leg2_contracts: int
    leg3_contracts: int
    leg2_pullback_points: float
    leg3_pullback_points: float

    # §2 Big candle exception -----------------------------------------------
    big_candle_threshold_points: float
    big_candle_full_contracts: int
    big_candle_reverses_dir: bool

    # §3 Entry trigger (15-second confirmation; not enforced in 4h-only mode)
    entry_confirmation_timeframe_seconds: int
    entry1_confirmation_candles: int
    entry23_confirmation_candles: int

    # §4 Stop loss ----------------------------------------------------------
    # Dashboard invariants (validated at the API boundary in BoxParamsModel):
    #   - sl_hard_points  >  sl_soft_points              (hard farther out)
    #   - soft_sl_confirmation_timeframe_minutes  >
    #     hard_sl_confirmation_timeframe_minutes         (soft confirms slower)
    sl_soft_points: float
    sl_hard_points: float
    soft_sl_confirmation_timeframe_minutes: int
    hard_sl_confirmation_timeframe_minutes: int

    # §5 Take profit --------------------------------------------------------
    tp_target_points: float
    tp_watch_threshold_points: float
    tp_confirmation_timeframe_minutes: int

    # Re-entry --------------------------------------------------------------
    reentry_enabled: bool
    reentry_cooldown_candles: int

    # Instrument: $/point/contract. NQ=2.0, ES=50.0, MES=5.0.
    point_value: float


@dataclass
class _Leg:
    """One scaling leg (record of a fill)."""
    contracts: int
    price: float
    candle_idx: int


@dataclass
class _Position:
    """Open position state during the simulation."""
    direction: str = 'flat'   # 'long' | 'short' | 'flat'
    base_level: float = 0.0   # the original entry-1 level (used for pullback math)
    legs: List[_Leg] = field(default_factory=list)
    watch_armed: bool = False  # has price ever exceeded avg + tp_watch_threshold?
    opened_at_idx: int = -1
    # Dual-timeframe sub-bar walker state. Used only when df_1min is
    # supplied to backtest(); persists across 4h-bar boundaries within a
    # single position's lifetime. cur_2m_start is the wall-clock-floored
    # 2-min window start; cur_2m_high / _low aggregate the in-progress
    # window's high/low. Reset on each new 2-min window.
    cur_2m_start: Optional[pd.Timestamp] = None
    cur_2m_high: Optional[float] = None
    cur_2m_low: Optional[float] = None

    @property
    def is_open(self) -> bool:
        return self.direction != 'flat'

    @property
    def contracts_filled(self) -> int:
        return sum(leg.contracts for leg in self.legs)

    @property
    def avg_price(self) -> float:
        if not self.legs:
            return 0.0
        total_contracts = sum(leg.contracts for leg in self.legs)
        weighted = sum(leg.price * leg.contracts for leg in self.legs)
        return weighted / total_contracts

    def to_dict(self) -> Dict:
        return {
            'direction': self.direction,
            'base_level': self.base_level,
            'legs': [{'contracts': l.contracts, 'price': l.price, 'candle_idx': l.candle_idx} for l in self.legs],
            'contracts_filled': self.contracts_filled,
            'avg_price': self.avg_price,
            'watch_armed': self.watch_armed,
            'opened_at_idx': self.opened_at_idx,
        }


class ScalingStrategy:
    """Stateful simulator of the 1-1-2 scaling strategy.

    Per the no-fallback rule, the `params` argument is REQUIRED. The
    caller (FastAPI endpoint or a test fixture) must construct a fully-
    populated ScalingParams and pass it explicitly.
    """

    def __init__(self, params: ScalingParams) -> None:
        if params is None:
            raise MissingParameterError(
                'params',
                where='ScalingStrategy.__init__',
                system_status={'hint': 'pass a fully-populated ScalingParams'},
            )
        self.params = params
        self.last_state: Dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def backtest(
        self,
        df: pd.DataFrame,
        df_1min: Optional[pd.DataFrame] = None,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ) -> Tuple[List[Dict], Dict]:
        """Run the simulation over ``df`` (one row per candle).

        Args:
            df: 4h OHLCV DataFrame with at least Open/High/Low/Close columns.
            df_1min: Optional 1-min OHLCV frame covering the same wall-clock
                span as ``df``. When supplied, hard SL & TP-target trigger on
                the first 1-min close past the line; soft SL & TP-trail trigger
                on 2-min aggregates of the same frame. When ``None``, both
                tiers collapse to the 4h close (legacy mode used by unit tests
                with synthetic candles).
            on_progress: Optional callback invoked once per candle with a
                progress dict. Used by the SSE endpoint in phase C2.

        Returns:
            ``(trades, final_state)``. ``trades`` is a list of closed-trade
            dicts (one per round trip). ``final_state`` snapshots the
            in-flight position (if any) at the end of the data.
        """
        total = len(df)
        if total == 0:
            self.last_state = _Position().to_dict()
            return [], self.last_state

        # Pre-index the 1-min frame for O(log N) per-4h-bar slicing. Each
        # 4h-bar idx i uses 1-min bars in [start_1m[i], start_1m[i+1]).
        if df_1min is not None and len(df_1min) > 0:
            import numpy as np
            ts_4h_arr = df['Date'].to_numpy()
            ts_1m_arr = df_1min['Date'].to_numpy()
            start_1m = np.searchsorted(ts_1m_arr, ts_4h_arr, side='left')
            start_1m = np.append(start_1m, len(ts_1m_arr))
        else:
            start_1m = None

        trades: List[Dict] = []
        position = _Position()
        cooldown_counter = 0
        # 'cooldown_direction' lets the re-entry rule re-enter the same way
        # after a profitable exit when price pulls back to the original
        # base level.
        cooldown_direction: Optional[str] = None
        cooldown_base_level: Optional[float] = None

        for idx in range(total):
            candle = df.iloc[idx]
            opn = float(candle['Open'])
            high = float(candle['High'])
            low = float(candle['Low'])
            close = float(candle['Close'])

            prev_close = float(df.iloc[idx - 1]['Close']) if idx > 0 else opn

            # Per-bar observation hook for subclasses that need to see EVERY
            # bar (e.g., BoxStrategy's traversal state machine). Default no-op.
            self._on_bar(idx, candle)

            exit_event: Optional[Dict] = None

            # ----- EXIT CHECKS (if position open) -----
            if position.is_open:
                if start_1m is not None:
                    # Dual-timeframe: walk 1-min bars within this 4h bar.
                    # The 4h-bar's timespan is [df.Date[idx], df.Date[idx+1]).
                    lo = int(start_1m[idx])
                    hi = int(start_1m[idx + 1]) if idx + 1 < total else len(df_1min)
                    sub_bars = df_1min.iloc[lo:hi]
                    exit_event = self._check_exits_subbar(position, sub_bars)
                else:
                    # Legacy 4h-only path: collapse both SL tiers and TP target
                    # to the 4h close.
                    exit_event = self._check_exits(position, idx, high, low, close)
                    if exit_event is not None:
                        exit_event['exit_close'] = close

                if exit_event is not None:
                    trades.append(self._build_trade(position, idx, exit_event))
                    # Decide if we should arm a re-entry watch.
                    if (
                        self.params.reentry_enabled
                        and exit_event['exit_reason'] == 'TAKE PROFIT'
                    ):
                        cooldown_direction = position.direction
                        cooldown_base_level = position.base_level
                        cooldown_counter = self.params.reentry_cooldown_candles
                    else:
                        cooldown_direction = None
                        cooldown_base_level = None
                        cooldown_counter = max(cooldown_counter, self.params.reentry_cooldown_candles)
                    position = _Position()

            # ----- ENTRY OR SCALE-IN -----
            if position.is_open:
                # Already in a position; check pullback legs (no new entry).
                self._maybe_fill_legs(position, idx, low, high)
            else:
                # Possible new entry (subject to cooldown).
                if cooldown_counter > 0:
                    cooldown_counter -= 1
                else:
                    new_position = self._maybe_open_position(idx, opn, high, low, close, prev_close)
                    if new_position is not None:
                        position = new_position

            # ----- ARM WATCH (TP trailing) -----
            if position.is_open:
                self._maybe_arm_watch(position, close)

            # ----- PROGRESS CALLBACK -----
            if on_progress is not None:
                trades_so_far = len(trades)
                pnl_so_far = sum(t['profit_dollars'] for t in trades)
                win_count = sum(1 for t in trades if t['profit_dollars'] > 0)
                win_rate = (win_count / trades_so_far * 100.0) if trades_so_far else 0.0
                on_progress({
                    'current_idx': idx,
                    'total': total,
                    'percent': (idx + 1) / total * 100.0,
                    'phase': 'running',
                    'trades_so_far': trades_so_far,
                    'pnl_so_far': pnl_so_far,
                    'win_rate_so_far': win_rate,
                    'current_position': position.direction,
                    'current_legs_filled': position.contracts_filled,
                })

        # ----- FINALIZE -----
        self.last_state = position.to_dict()
        return trades, self.last_state

    # ------------------------------------------------------------------
    # Per-candle decision helpers (pure functions on `position` state)
    # ------------------------------------------------------------------

    def _on_bar(self, idx: int, candle: pd.Series) -> None:
        """Hook called once per bar from `backtest`, BEFORE exits/entries.

        Default no-op. BoxStrategy overrides this to drive its traversal
        state machine on every bar regardless of position/cooldown state."""
        pass

    def _maybe_open_position(
        self,
        idx: int,
        opn: float,
        high: float,
        low: float,
        close: float,
        prev_close: float,
    ) -> Optional[_Position]:
        p = self.params
        candle_size = abs(close - opn)
        base_level = prev_close

        if candle_size > p.big_candle_threshold_points:
            # Big candle exception: enter full size, optionally reversed.
            base_direction = 'long' if close > opn else 'short'
            if p.big_candle_reverses_dir:
                base_direction = 'short' if base_direction == 'long' else 'long'
            position = _Position(
                direction=base_direction,
                base_level=close,
                opened_at_idx=idx,
            )
            position.legs.append(_Leg(
                contracts=p.big_candle_full_contracts,
                price=close,
                candle_idx=idx,
            ))
            return position

        # Standard trigger: trade in the direction of the close vs prev close.
        if close > prev_close:
            direction = 'long'
        elif close < prev_close:
            direction = 'short'
        else:
            return None  # doji-ish, no trigger

        position = _Position(
            direction=direction,
            base_level=base_level,
            opened_at_idx=idx,
        )
        position.legs.append(_Leg(
            contracts=p.leg1_contracts,
            price=base_level,
            candle_idx=idx,
        ))
        return position

    def _maybe_fill_legs(self, position: _Position, idx: int, low: float, high: float):
        """Fill leg 2 / leg 3 if this candle's range reaches the pullback price."""
        p = self.params

        if position.direction == 'long':
            if len(position.legs) == 1:
                leg2_price = position.base_level - p.leg2_pullback_points
                if low <= leg2_price:
                    position.legs.append(_Leg(p.leg2_contracts, leg2_price, idx))
            if len(position.legs) == 2:
                leg3_price = position.base_level - p.leg3_pullback_points
                if low <= leg3_price:
                    position.legs.append(_Leg(p.leg3_contracts, leg3_price, idx))
        else:  # short
            if len(position.legs) == 1:
                leg2_price = position.base_level + p.leg2_pullback_points
                if high >= leg2_price:
                    position.legs.append(_Leg(p.leg2_contracts, leg2_price, idx))
            if len(position.legs) == 2:
                leg3_price = position.base_level + p.leg3_pullback_points
                if high >= leg3_price:
                    position.legs.append(_Leg(p.leg3_contracts, leg3_price, idx))

    def _check_exits(
        self,
        position: _Position,
        idx: int,
        high: float,
        low: float,
        close: float,
    ) -> Optional[Dict]:
        """Return an exit event dict if this candle exits the position."""
        p = self.params
        avg = position.avg_price
        if position.direction == 'long':
            sl_soft_line = avg - p.sl_soft_points
            sl_hard_line = avg - p.sl_hard_points
            tp_target_line = avg + p.tp_target_points
            tp_watch_line = avg + p.tp_watch_threshold_points

            # Hard SL: candle closes below the hard line. Fill AT THE LINE
            # (loss = exactly sl_hard_points — the disaster-stop contract).
            if close <= sl_hard_line:
                return {'exit_reason': 'STOP LOSS (HARD)', 'exit_price': sl_hard_line}
            # Soft SL: candle closes below the soft line. Fill AT THE BAR
            # CLOSE — the slow-confirmation stop accepts whatever close
            # confirmed past the line, so realised loss ≥ sl_soft_points
            # (user rule, 2026-05-24).
            if close <= sl_soft_line:
                return {'exit_reason': 'STOP LOSS (SOFT)', 'exit_price': close}
            # Hard TP: high reaches the target.
            if high >= tp_target_line:
                return {'exit_reason': 'TAKE PROFIT', 'exit_price': tp_target_line}
            # Trailing TP (watch mode): once armed, exit if close falls back
            # below the watch threshold.
            if position.watch_armed and close < tp_watch_line:
                return {'exit_reason': 'TAKE PROFIT (TRAIL)', 'exit_price': close}
            return None

        # short
        sl_soft_line = avg + p.sl_soft_points
        sl_hard_line = avg + p.sl_hard_points
        tp_target_line = avg - p.tp_target_points
        tp_watch_line = avg - p.tp_watch_threshold_points

        if close >= sl_hard_line:
            return {'exit_reason': 'STOP LOSS (HARD)', 'exit_price': sl_hard_line}
        if close >= sl_soft_line:
            return {'exit_reason': 'STOP LOSS (SOFT)', 'exit_price': close}
        if low <= tp_target_line:
            return {'exit_reason': 'TAKE PROFIT', 'exit_price': tp_target_line}
        if position.watch_armed and close > tp_watch_line:
            return {'exit_reason': 'TAKE PROFIT (TRAIL)', 'exit_price': close}
        return None

    def _maybe_arm_watch(self, position: _Position, close: float):
        """Arm the trailing-TP watch when the candle CLOSE sustains above
        (long) or below (short) the watch threshold from avg. We use
        close - not the intra-candle high/low - to avoid arming on a
        wick within the entry candle itself.

        4h-only path. In dual-timeframe mode, arming happens inside
        `_check_exits_subbar` on a 2-min close.
        """
        if position.watch_armed:
            return
        p = self.params
        avg = position.avg_price
        if position.direction == 'long':
            if close >= avg + p.tp_watch_threshold_points:
                position.watch_armed = True
        else:
            if close <= avg - p.tp_watch_threshold_points:
                position.watch_armed = True

    # ------------------------------------------------------------------
    # Dual-timeframe sub-bar exit walker (#118b)
    # ------------------------------------------------------------------

    def _check_exits_subbar(
        self,
        position: _Position,
        sub_bars: pd.DataFrame,
    ) -> Optional[Dict]:
        """Walk a contiguous slice of 1-min OHLCV bars searching for the
        first SL/TP trigger that closes the position.

        Trigger contract (user rule 2026-05-24, MASTER_STRATEGY_GUIDE §4-5):

          * HARD SL: 1-min close past `sl_hard_line` → fill AT the line
                    (loss = exactly sl_hard_points).
          * TP target: 1-min high (long) / low (short) reaches `tp_target_line`
                    → fill AT the line.
          * SOFT SL: 2-min close past `sl_soft_line` → fill AT the 2-min close
                    (loss can exceed sl_soft_points).
          * TP trail: once watch is armed (2-min close moved +tp_watch_threshold
                    in favour), a later 2-min close back through `tp_watch_line`
                    → fill AT that 2-min close.

        The 2-min window is wall-clock anchored (`ts.floor('2min')`). The
        accumulator state (cur_2m_*) persists on the `_Position` instance so
        consecutive calls (each handling one 4h-bar's slice) keep their place
        across the position's lifetime.

        Returns the first exit_event dict that fires, with `exit_price`,
        `exit_close`, `exit_time`, `exit_reason` keys. Returns None when no
        trigger fires inside this slice.
        """
        if sub_bars.empty:
            return None

        p = self.params
        avg = position.avg_price
        if position.direction == 'long':
            sl_hard_line   = avg - p.sl_hard_points
            sl_soft_line   = avg - p.sl_soft_points
            tp_target_line = avg + p.tp_target_points
            tp_watch_line  = avg + p.tp_watch_threshold_points
        else:
            sl_hard_line   = avg + p.sl_hard_points
            sl_soft_line   = avg + p.sl_soft_points
            tp_target_line = avg - p.tp_target_points
            tp_watch_line  = avg - p.tp_watch_threshold_points

        watch_arm_threshold = p.tp_watch_threshold_points

        for sub in sub_bars.itertuples(index=False):
            ts_1m = sub.Date if isinstance(sub.Date, pd.Timestamp) else pd.Timestamp(sub.Date)
            h_1m = float(sub.High)
            l_1m = float(sub.Low)
            c_1m = float(sub.Close)

            # ---- 1-min HARD SL ----
            if position.direction == 'long':
                if c_1m <= sl_hard_line:
                    return {
                        'exit_reason': 'STOP LOSS (HARD)',
                        'exit_price': sl_hard_line,
                        'exit_close': c_1m,
                        'exit_time': ts_1m.isoformat(),
                    }
            else:
                if c_1m >= sl_hard_line:
                    return {
                        'exit_reason': 'STOP LOSS (HARD)',
                        'exit_price': sl_hard_line,
                        'exit_close': c_1m,
                        'exit_time': ts_1m.isoformat(),
                    }

            # ---- 1-min TP target (intra-bar high/low touches the line) ----
            if position.direction == 'long':
                if h_1m >= tp_target_line:
                    return {
                        'exit_reason': 'TAKE PROFIT',
                        'exit_price': tp_target_line,
                        'exit_close': c_1m,
                        'exit_time': ts_1m.isoformat(),
                    }
            else:
                if l_1m <= tp_target_line:
                    return {
                        'exit_reason': 'TAKE PROFIT',
                        'exit_price': tp_target_line,
                        'exit_close': c_1m,
                        'exit_time': ts_1m.isoformat(),
                    }

            # ---- 2-min aggregator ----
            window_start = ts_1m.floor('2min')
            if position.cur_2m_start != window_start:
                position.cur_2m_start = window_start
                position.cur_2m_high = h_1m
                position.cur_2m_low = l_1m
            else:
                position.cur_2m_high = max(position.cur_2m_high, h_1m)
                position.cur_2m_low  = min(position.cur_2m_low,  l_1m)

            # 2-min window completes when the SECOND minute lands. ts_1m's
            # minute relative to window_start: 0 = first minute, 1 = second.
            is_window_end = ((ts_1m - window_start) == pd.Timedelta('1min'))

            if is_window_end:
                c_2m = c_1m   # close of the 2nd minute = close of the 2-min window

                # ---- 2-min watch arming (one-way) ----
                if not position.watch_armed:
                    if position.direction == 'long' and c_2m >= avg + watch_arm_threshold:
                        position.watch_armed = True
                    elif position.direction == 'short' and c_2m <= avg - watch_arm_threshold:
                        position.watch_armed = True

                # ---- 2-min SOFT SL ----
                if position.direction == 'long':
                    if c_2m <= sl_soft_line:
                        return {
                            'exit_reason': 'STOP LOSS (SOFT)',
                            'exit_price': c_2m,
                            'exit_close': c_2m,
                            'exit_time': ts_1m.isoformat(),
                        }
                else:
                    if c_2m >= sl_soft_line:
                        return {
                            'exit_reason': 'STOP LOSS (SOFT)',
                            'exit_price': c_2m,
                            'exit_close': c_2m,
                            'exit_time': ts_1m.isoformat(),
                        }

                # ---- 2-min TRAIL (only after arm) ----
                if position.watch_armed:
                    if position.direction == 'long' and c_2m < tp_watch_line:
                        return {
                            'exit_reason': 'TAKE PROFIT (TRAIL)',
                            'exit_price': c_2m,
                            'exit_close': c_2m,
                            'exit_time': ts_1m.isoformat(),
                        }
                    if position.direction == 'short' and c_2m > tp_watch_line:
                        return {
                            'exit_reason': 'TAKE PROFIT (TRAIL)',
                            'exit_price': c_2m,
                            'exit_close': c_2m,
                            'exit_time': ts_1m.isoformat(),
                        }

        return None

    def _build_trade(
        self,
        position: _Position,
        exit_idx: int,
        exit_event: Dict,
    ) -> Dict:
        avg = position.avg_price
        exit_price = exit_event['exit_price']
        contracts = position.contracts_filled
        if position.direction == 'long':
            profit_points = exit_price - avg
        else:
            profit_points = avg - exit_price
        profit_dollars = profit_points * contracts * self.params.point_value
        return {
            'entry_idx': position.opened_at_idx,
            'exit_idx': exit_idx,
            'direction': position.direction,
            # `entry_signal_price` and `exit_close` are the candle-grounded
            # prices for the dashboard / trade-log display — guaranteed to
            # appear in the OHLC of the corresponding bar. `avg_entry_price`
            # and `exit_price` remain the algorithm-effective fill prices
            # used for PnL math (weighted leg avg / SL-TP threshold line).
            'entry_signal_price': position.legs[0].price,
            'exit_close': exit_event['exit_close'],
            'avg_entry_price': avg,
            'exit_price': exit_price,
            'contracts': contracts,
            'profit_points': profit_points,
            'profit_dollars': profit_dollars,
            'exit_reason': exit_event['exit_reason'],
            # Sub-bar timestamp ISO string when the dual-timeframe engine
            # fired the exit; absent (None) in 4h-only legacy mode (the
            # frontend falls back to the 4h bar's timestamp via exit_idx).
            'exit_time': exit_event.get('exit_time'),
            'legs': [
                {'contracts': leg.contracts, 'price': leg.price, 'candle_idx': leg.candle_idx}
                for leg in position.legs
            ],
        }


__all__ = ['ScalingStrategy', 'ScalingParams']
