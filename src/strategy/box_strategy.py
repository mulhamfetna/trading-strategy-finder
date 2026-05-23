"""Box Strategy — TradingView box-based entry signal.

Subclasses ScalingStrategy and replaces only the entry-signal logic.
All 1-1-2 scaling mechanics, leg fills, SL/TP, and re-entry are inherited
from the playbook (Currunt_Strategy_Algo_for_Trading.md).

Entry signal:
  - BoxLookup checks the 4h candle close against weekly/monthly box edges.
  - Single-box rule (weekly priority): the FIRST side to fire wins.
  - 3-tick margin (default 0.75 points) required before triggering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from src.exceptions import MissingParameterError
from src.strategy.box_lookup import BoxLookup
from src.strategy.scaling_strategy import ScalingParams, ScalingStrategy, _Leg, _Position


@dataclass
class BoxStrategyParams(ScalingParams):
    """ScalingParams + box-specific decisions and data file paths.

    Per the no-fallback rule, every field is REQUIRED — no defaults.
    """
    # Data files
    week_data_path:  str
    month_data_path: str

    # §Box-rule decisions
    box_tick_threshold: float
    weekly_window_days: int
    monthly_window_days: int

    # Big-Candle vs Box conflict resolution. See MASTER_STRATEGY_GUIDE.md §5.
    # 'big_candle_wins' | 'box_wins' | 'skip'
    big_candle_resolution: str


class BoxStrategy(ScalingStrategy):
    """ScalingStrategy with box-based entry signals.

    Construction modes:
      - Pass `BoxStrategyParams` to wire BoxLookup automatically using the
        params' paths + thresholds.
      - Pass `params` + an explicit `box_lookup` to reuse a pre-built BoxLookup
        (the FastAPI endpoint does this so it can validate file existence
        and emit `event: warning` SSE frames before instantiating).
    """

    def __init__(
        self,
        params: BoxStrategyParams,
        box_lookup: BoxLookup,
    ) -> None:
        """Both arguments REQUIRED (no-fallback rule).

        The FastAPI endpoint owns BoxLookup construction so it can
        validate file existence + raise MissingDataFileError before
        spinning up the worker thread.

        Re-entry note (C2): under traversal semantics, re-entry after a
        profitable exit naturally requires a NEW traversal to fire — the
        state machine doesn't grant a "free" re-entry on the same side,
        because doing so would contradict the user's spec ("stayed inside
        the box in both situations is considered hold"). The
        `reentry_cooldown_candles` parameter still gates how soon after an
        exit a new entry can fire; the traversal itself decides which
        direction.
        """
        if params is None:
            raise MissingParameterError(
                'params',
                where='BoxStrategy.__init__',
                system_status={'hint': 'pass a fully-populated BoxStrategyParams'},
            )
        if box_lookup is None:
            raise MissingParameterError(
                'box_lookup',
                where='BoxStrategy.__init__',
                system_status={'hint': 'construct BoxLookup explicitly and pass it'},
            )
        super().__init__(params)
        self._box = box_lookup
        self._df4h: Optional[pd.DataFrame] = None
        self._signal_details: Dict[int, Dict] = {}

    # ------------------------------------------------------------------
    # Override backtest to store df reference + attach box signal detail
    # ------------------------------------------------------------------

    def backtest(
        self,
        df: pd.DataFrame,
        on_progress: Optional[Callable[[Dict], None]] = None,
    ) -> Tuple[List[Dict], Dict]:
        self._df4h = df
        self._signal_details = {}
        # Traversal state machine is per-run. Reset so a fresh backtest does
        # not inherit observations from a prior run (matters for re-using
        # the same BoxLookup across walk-forward folds).
        self._box.reset_state()
        trades, state = super().backtest(df, on_progress=on_progress)
        # Post-process: attach box_signal to each trade. `_on_bar` recorded
        # the box detail at the bar's idx; entry_idx is that same idx.
        # Direct access on `entry_idx` — every trade the engine emits carries
        # it (no silent -1 fallback). `_signal_details.get` may legitimately
        # return None for that idx if no box was active that bar.
        for trade in trades:
            detail = self._signal_details.get(trade['entry_idx'])
            if detail:
                trade['box_signal'] = detail
        return trades, state

    # ------------------------------------------------------------------
    # Per-bar observation hook — drive the traversal state machine on
    # EVERY bar, regardless of position/cooldown state. This is the C1
    # fix: without it, bars during an open trade or cooldown were invisible
    # to the state machine and stale state could fire spurious signals
    # after exit.
    # ------------------------------------------------------------------

    def _on_bar(self, idx: int, candle: pd.Series) -> None:
        ts = self._get_ts(idx)
        if ts is None:
            return
        close = float(candle['Close'])
        # get_signal_detail mutates the state machine — calling it once
        # per bar here means _maybe_open_position MUST NOT call it again.
        self._signal_details[idx] = self._box.get_signal_detail(close, ts)

    # ------------------------------------------------------------------
    # Override entry — box-based instead of close > prev_close
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
        is_big_candle = candle_size > p.big_candle_threshold_points

        # Read the per-bar box signal recorded by `_on_bar`. Do NOT call
        # `get_signal_detail` here — it would double-advance the state.
        box_detail: Optional[Dict] = self._signal_details.get(idx)
        box_signal: Optional[str] = box_detail.get('signal') if box_detail else None

        # 'hold' and None both mean "box did not fire a directional signal".
        # Treat them as equivalent in the conflict-resolution logic below.
        box_directional = box_signal if box_signal in ('long', 'short') else None

        if is_big_candle:
            # Compute the Big-Candle direction (with the §2 reversal rule
            # applied per `big_candle_reverses_dir`).
            bc_dir = 'long' if close > opn else 'short'
            if p.big_candle_reverses_dir:
                bc_dir = 'short' if bc_dir == 'long' else 'long'

            # Resolve the conflict per MASTER_STRATEGY_GUIDE.md §5.
            # No fallback: `p.big_candle_resolution` MUST exist (the
            # BoxStrategyParams dataclass enforces it). Unknown values
            # raise instead of silently using the legacy behaviour.
            policy = p.big_candle_resolution
            if box_directional is None or box_directional == bc_dir:
                chosen = bc_dir
            elif policy == 'big_candle_wins':
                chosen = bc_dir
            elif policy == 'box_wins':
                chosen = box_directional
            elif policy == 'skip':
                return None
            else:
                raise MissingParameterError(
                    'big_candle_resolution',
                    where=f'BoxStrategy._maybe_open_position (idx={idx})',
                    system_status={
                        'received_value': policy,
                        'allowed_values': ['big_candle_wins', 'box_wins', 'skip'],
                    },
                )

            # Attach the box detail so the trade log can show how the
            # conflict was resolved.
            if box_detail and box_directional is not None:
                self._signal_details[idx] = box_detail

            pos = _Position(direction=chosen, base_level=close, opened_at_idx=idx)
            pos.legs.append(_Leg(p.big_candle_full_contracts, close, idx))
            return pos

        # Normal (non-big-candle) box-driven entry — only a traversal fires.
        if box_directional is None:
            return None
        self._signal_details[idx] = box_detail or {}

        pos = _Position(direction=box_directional, base_level=close, opened_at_idx=idx)
        pos.legs.append(_Leg(p.leg1_contracts, close, idx))
        return pos

    # ------------------------------------------------------------------

    def _get_ts(self, idx: int) -> Optional[pd.Timestamp]:
        if self._df4h is None:
            return None
        row = self._df4h.iloc[idx]
        date_val = row.get('Date') if hasattr(row, 'get') else row['Date']
        try:
            return pd.Timestamp(date_val)
        except Exception:
            return None


__all__ = ['BoxStrategy', 'BoxStrategyParams']
