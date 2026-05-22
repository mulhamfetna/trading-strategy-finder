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


@dataclass
class ScalingParams:
    """Every parameter the strategy exposes to the settings UI."""

    # Entry distribution & sizing -------------------------------------------
    total_contracts: int = 4
    leg1_contracts: int = 1
    leg2_contracts: int = 1
    leg3_contracts: int = 2
    leg2_pullback_points: float = 100.0
    leg3_pullback_points: float = 150.0

    # Big candle exception --------------------------------------------------
    big_candle_threshold_points: float = 400.0
    big_candle_full_contracts: int = 4
    big_candle_reverses_dir: bool = True

    # Take profit -----------------------------------------------------------
    tp_target_points: float = 150.0
    tp_watch_threshold_points: float = 50.0

    # Stop loss (the playbook is vague on distances; conservative defaults)
    sl_soft_points: float = 200.0
    sl_hard_points: float = 300.0

    # Re-entry --------------------------------------------------------------
    reentry_enabled: bool = True
    reentry_cooldown_candles: int = 1


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
    """Stateful simulator of the 1-1-2 scaling strategy."""

    def __init__(self, params: Optional[ScalingParams] = None):
        self.params = params or ScalingParams()
        self.last_state: Dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def backtest(
        self,
        df: pd.DataFrame,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ) -> Tuple[List[Dict], Dict]:
        """Run the simulation over ``df`` (one row per candle).

        Args:
            df: OHLCV DataFrame with at least Open/High/Low/Close columns.
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

            exit_event: Optional[Dict] = None

            # ----- EXIT CHECKS (if position open) -----
            if position.is_open:
                exit_event = self._check_exits(position, idx, high, low, close)
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

            # Hard SL: candle closes below the hard line.
            if close <= sl_hard_line:
                return {'exit_reason': 'STOP LOSS (HARD)', 'exit_price': sl_hard_line}
            # Soft SL: candle closes below the soft line.
            if close <= sl_soft_line:
                return {'exit_reason': 'STOP LOSS (SOFT)', 'exit_price': sl_soft_line}
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
            return {'exit_reason': 'STOP LOSS (SOFT)', 'exit_price': sl_soft_line}
        if low <= tp_target_line:
            return {'exit_reason': 'TAKE PROFIT', 'exit_price': tp_target_line}
        if position.watch_armed and close > tp_watch_line:
            return {'exit_reason': 'TAKE PROFIT (TRAIL)', 'exit_price': close}
        return None

    def _maybe_arm_watch(self, position: _Position, close: float):
        """Arm the trailing-TP watch when the candle CLOSE sustains above
        (long) or below (short) the watch threshold from avg. We use
        close - not the intra-candle high/low - to avoid arming on a
        wick within the entry candle itself."""
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
        # NQ futures: $2 per point per contract (matches the rest of the codebase).
        nq_point_value = 2.0
        profit_dollars = profit_points * contracts * nq_point_value
        return {
            'entry_idx': position.opened_at_idx,
            'exit_idx': exit_idx,
            'direction': position.direction,
            'avg_entry_price': avg,
            'exit_price': exit_price,
            'contracts': contracts,
            'profit_points': profit_points,
            'profit_dollars': profit_dollars,
            'exit_reason': exit_event['exit_reason'],
            'legs': [
                {'contracts': leg.contracts, 'price': leg.price, 'candle_idx': leg.candle_idx}
                for leg in position.legs
            ],
        }


__all__ = ['ScalingStrategy', 'ScalingParams']
