"""1-1-2 scaling strategy simulator.

Implements [[strategy-master]] §3, §4, §5:

* Entry distribution & position sizing (1-1-2 scaling, 4 contracts total).
* Big-candle exception (>400 points -> enter full, reverse direction).
* Fixed take profit at `+tp_target_points` (no trail, no +50 watch).
* Dual stop loss (soft = 2-min close confirmation; hard = 1-min close).
* `anchor_mode` toggle — SL/TP/Trail lines computed from `base_level`
  (default) or running `avg_price`. See [[strategy-master]] §5.

The strategy is OOP per the hybrid refactor policy: it has configuration
(`ScalingParams`) and a stateful lifecycle (legs filling, exit checks).
Per-candle decisions delegate to small pure functions for testability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from src.exceptions import MissingParameterError


@dataclass
class ScalingParams:
    """Every parameter the strategy exposes to the settings UI.

    Per the no-fallback rule every field is REQUIRED — there are no
    dataclass defaults. The frontend supplies all of them at the API
    boundary; tests should use a fixture helper instead of relying on
    field defaults.
    """

    # §1 Entry distribution & sizing
    total_contracts: int
    leg1_contracts: int
    leg2_contracts: int
    leg3_contracts: int
    leg2_pullback_points: float
    leg3_pullback_points: float

    # §2 Big candle exception
    big_candle_threshold_points: float
    big_candle_full_contracts: int
    big_candle_reverses_dir: bool

    # §3 Entry trigger (15-second confirmation; not enforced in 4h-only mode)
    entry_confirmation_timeframe_seconds: int
    entry1_confirmation_candles: int
    entry23_confirmation_candles: int

    # §4 Stop loss
    # Dashboard invariants (validated at the API boundary in BoxParamsModel):
    #   - sl_hard_points  >  sl_soft_points              (hard farther out)
    #   - soft_sl_confirmation_timeframe_minutes  >
    #     hard_sl_confirmation_timeframe_minutes         (soft confirms slower)
    sl_soft_points: float
    sl_hard_points: float
    soft_sl_confirmation_timeframe_minutes: int
    hard_sl_confirmation_timeframe_minutes: int

    # §5 Take profit (fixed; no trail per spec)
    tp_target_points: float

    # Re-entry
    reentry_enabled: bool
    reentry_cooldown_candles: int

    # Instrument: $/point/contract. NQ=2.0, ES=50.0, MES=5.0.
    point_value: float

    # Anchoring mode for SL/TP lines.
    #   'base'    — lines fixed at `base_level ± thresholds` for trade lifetime.
    #   'average' — lines re-anchor on every leg fill to the running avg.
    # See [[strategy-master]] §5.
    anchor_mode: str


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
    base_level: float = 0.0   # the original entry-1 level (used for pullback math + base-anchored exit lines)
    legs: List[_Leg] = field(default_factory=list)
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
        if params.anchor_mode not in ('base', 'average'):
            raise MissingParameterError(
                'anchor_mode',
                where='ScalingStrategy.__init__',
                system_status={
                    'received_value': params.anchor_mode,
                    'allowed_values': ['base', 'average'],
                },
            )
        self.params = params
        self.last_state: Dict = {}

    # ------------------------------------------------------------------
    # Anchor selection (§5 of master strategy)
    # ------------------------------------------------------------------

    def _anchor(self, position: _Position) -> float:
        """Return the reference price for SL/TP line computation.

        `base`    — fixed at the original entry-1 price (default).
        `average` — running weighted-average entry across filled legs.
        """
        if self.params.anchor_mode == 'base':
            return position.base_level
        return position.avg_price

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
                the first 1-min close past the line; soft SL triggers on a
                2-min close. When ``None``, all tiers collapse to the 4h
                close (legacy mode used by unit tests with synthetic candles).
            on_progress: Optional callback invoked once per candle with a
                progress dict.

        Returns:
            ``(trades, final_state)``. ``trades`` is a list of closed-trade
            dicts (one per round trip). ``final_state`` snapshots the
            in-flight position (if any) at the end of the data.
        """
        total = len(df)
        if total == 0:
            self.last_state = _Position().to_dict()
            return [], self.last_state

        # Pre-index the 1-min frame for O(log N) per-4h-bar slicing.
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

        for idx in range(total):
            candle = df.iloc[idx]
            opn = float(candle['Open'])
            high = float(candle['High'])
            low = float(candle['Low'])
            close = float(candle['Close'])

            prev_close = float(df.iloc[idx - 1]['Close']) if idx > 0 else opn

            # Per-bar observation hook for subclasses (BoxStrategy's
            # traversal state machine). Default no-op.
            self._on_bar(idx, candle)

            exit_event: Optional[Dict] = None

            # ----- EXIT CHECKS (if position open) -----
            if position.is_open:
                if start_1m is not None:
                    lo = int(start_1m[idx])
                    hi = int(start_1m[idx + 1]) if idx + 1 < total else len(df_1min)
                    sub_bars = df_1min.iloc[lo:hi]
                    exit_event = self._check_exits_subbar(position, sub_bars)
                else:
                    exit_event = self._check_exits(position, idx, high, low, close)
                    if exit_event is not None:
                        exit_event['exit_close'] = close

                if exit_event is not None:
                    trades.append(self._build_trade(position, idx, exit_event))
                    cooldown_counter = max(cooldown_counter, self.params.reentry_cooldown_candles)
                    position = _Position()

            # ----- ENTRY OR SCALE-IN -----
            if position.is_open:
                self._maybe_fill_legs(position, idx, low, high)
            else:
                if cooldown_counter > 0:
                    cooldown_counter -= 1
                else:
                    new_position = self._maybe_open_position(idx, opn, high, low, close, prev_close)
                    if new_position is not None:
                        position = new_position

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

        self.last_state = position.to_dict()
        return trades, self.last_state

    # ------------------------------------------------------------------
    # Per-candle decision helpers
    # ------------------------------------------------------------------

    def _on_bar(self, idx: int, candle: pd.Series) -> None:
        """Hook called once per bar from `backtest`, BEFORE exits/entries."""
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

        if close > prev_close:
            direction = 'long'
        elif close < prev_close:
            direction = 'short'
        else:
            return None

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
        """Fill leg 2 / leg 3 if this candle's range reaches the pullback price.

        Pullback distances are measured from `base_level` (the original
        entry-1 price), independent of `anchor_mode` — the ladder shape is
        spec-locked.
        """
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
        """Return an exit event dict if this candle exits the position.

        Lines computed from `_anchor(position)` per `anchor_mode` (§5).
        TP is a fixed line — no trail.
        """
        p = self.params
        anchor = self._anchor(position)
        if position.direction == 'long':
            sl_soft_line = anchor - p.sl_soft_points
            sl_hard_line = anchor - p.sl_hard_points
            tp_target_line = anchor + p.tp_target_points

            # Hard SL: candle closes below the hard line. Fill AT THE LINE.
            if close <= sl_hard_line:
                return {'exit_reason': 'STOP LOSS (HARD)', 'exit_price': sl_hard_line}
            # Soft SL: candle closes below the soft line. Fill AT THE BAR CLOSE.
            if close <= sl_soft_line:
                return {'exit_reason': 'STOP LOSS (SOFT)', 'exit_price': close}
            # Hard TP: high reaches the target.
            if high >= tp_target_line:
                return {'exit_reason': 'TAKE PROFIT', 'exit_price': tp_target_line}
            return None

        # short
        sl_soft_line = anchor + p.sl_soft_points
        sl_hard_line = anchor + p.sl_hard_points
        tp_target_line = anchor - p.tp_target_points

        if close >= sl_hard_line:
            return {'exit_reason': 'STOP LOSS (HARD)', 'exit_price': sl_hard_line}
        if close >= sl_soft_line:
            return {'exit_reason': 'STOP LOSS (SOFT)', 'exit_price': close}
        if low <= tp_target_line:
            return {'exit_reason': 'TAKE PROFIT', 'exit_price': tp_target_line}
        return None

    # ------------------------------------------------------------------
    # Dual-timeframe sub-bar exit walker
    # ------------------------------------------------------------------

    def _check_exits_subbar(
        self,
        position: _Position,
        sub_bars: pd.DataFrame,
    ) -> Optional[Dict]:
        """Walk a contiguous slice of 1-min OHLCV bars searching for the
        first SL/TP trigger that closes the position.

        Trigger contract (master strategy §4):

          * HARD SL: 1-min close past `sl_hard_line` → fill AT the line.
          * TP target: 1-min high (long) / low (short) reaches `tp_target_line`
                       → fill AT the line.
          * SOFT SL: 2-min close past `sl_soft_line` → fill AT the 2-min close.

        No trail mechanism. The 2-min window is wall-clock anchored
        (`ts.floor('2min')`).

        Lines computed from `_anchor(position)` per `anchor_mode` (§5).
        """
        if sub_bars.empty:
            return None

        p = self.params
        anchor = self._anchor(position)
        if position.direction == 'long':
            sl_hard_line   = anchor - p.sl_hard_points
            sl_soft_line   = anchor - p.sl_soft_points
            tp_target_line = anchor + p.tp_target_points
        else:
            sl_hard_line   = anchor + p.sl_hard_points
            sl_soft_line   = anchor + p.sl_soft_points
            tp_target_line = anchor - p.tp_target_points

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

            # ---- 2-min aggregator (for SOFT SL only) ----
            window_start = ts_1m.floor('2min')
            if position.cur_2m_start != window_start:
                position.cur_2m_start = window_start
                position.cur_2m_high = h_1m
                position.cur_2m_low = l_1m
            else:
                position.cur_2m_high = max(position.cur_2m_high, h_1m)
                position.cur_2m_low  = min(position.cur_2m_low,  l_1m)

            is_window_end = ((ts_1m - window_start) == pd.Timedelta('1min'))

            if is_window_end:
                c_2m = c_1m

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
            'entry_signal_price': position.legs[0].price,
            'exit_close': exit_event['exit_close'],
            'avg_entry_price': avg,
            'exit_price': exit_price,
            'contracts': contracts,
            'profit_points': profit_points,
            'profit_dollars': profit_dollars,
            'exit_reason': exit_event['exit_reason'],
            'exit_time': exit_event.get('exit_time'),
            'legs': [
                {'contracts': leg.contracts, 'price': leg.price, 'candle_idx': leg.candle_idx}
                for leg in position.legs
            ],
        }


__all__ = ['ScalingStrategy', 'ScalingParams']
