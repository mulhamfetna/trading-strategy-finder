"""Dual-timeframe sub-bar exit walker (#118b).

Locks the asymmetric SL/TP contract per the user rule (2026-05-24):

  * HARD SL fires on the first 1-min CLOSE past sl_hard_line; fill AT THE LINE.
  * TP target fires on the first 1-min HIGH (long) / LOW (short) reaching the
    line; fill AT THE LINE.
  * SOFT SL fires on the first 2-min CLOSE past sl_soft_line; fill AT THE 2-min
    CLOSE.
  * TRAIL fires on a 2-min close back through tp_watch_line (after the watch
    armed via a 2-min close past avg + tp_watch_threshold_points); fill AT THE
    2-min CLOSE.

Each test builds a tiny synthetic 4h-bar (the entry bar plus one or two follow
bars) and a matching 1-min frame that's been hand-tuned to trigger exactly one
of the four exits at a known timestamp. The trade dict's `exit_time` must
point at the sub-bar timestamp; `exit_idx` is still the 4h-bar index containing
that sub-bar.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.scaling_strategy import ScalingStrategy
from tests._fixtures import scaling_params


# Two 4h bars: signal bar (long entry) and the bar in which the SL/TP fires.
_SIGNAL_BAR_TS = pd.Timestamp('2025-01-01 04:00:00')
_EXIT_BAR_TS   = pd.Timestamp('2025-01-01 08:00:00')


def _df_4h_entry_then_neutral():
    """4h frame that fires a LONG (close > prev_close on bar 1). The exit bar
    has neutral O/H/L/C — the 1-min frame is what actually drives the exit."""
    return pd.DataFrame({
        'Date':   [pd.Timestamp('2025-01-01 00:00:00'), _SIGNAL_BAR_TS, _EXIT_BAR_TS],
        'Open':   [20000.0, 20000.0, 20010.0],
        'High':   [20010.0, 20020.0, 20020.0],
        'Low':    [19990.0, 19995.0, 19995.0],
        'Close':  [20000.0, 20010.0, 20010.0],
        'Volume': [1000, 1000, 1000],
    })


def _df_1min_for_exit_bar(close_series, high_series=None, low_series=None):
    """Build a 1-min frame whose timestamps lie inside _EXIT_BAR_TS's 4h span
    (08:00..11:59 = 240 minutes). close_series is a list of exactly 240 closes
    for those minutes; high/low default to close ±1."""
    assert len(close_series) == 240
    if high_series is None:
        high_series = [c + 1 for c in close_series]
    if low_series is None:
        low_series  = [c - 1 for c in close_series]
    ts = pd.date_range(start=_EXIT_BAR_TS, periods=240, freq='1min')
    return pd.DataFrame({
        'Date':   ts,
        'Open':   close_series,
        'High':   high_series,
        'Low':    low_series,
        'Close':  close_series,
        'Volume': [10] * 240,
    })


# ---- HARD SL ----

def test_hard_sl_fires_on_1min_close_past_line():
    """Default params: sl_hard_points=300. avg=20000 ⇒ sl_hard_line=19700.
    Construct a 1-min frame where bar #5 closes at 19690 (past the line);
    earlier bars are neutral. HARD must fire on bar #5, fill at 19700."""
    df = _df_4h_entry_then_neutral()
    # 240 minutes, mostly flat at 20015. Bar at minute 5 dips to close=19690.
    closes = [20015.0] * 240
    closes[5] = 19690.0
    df_1min = _df_1min_for_exit_bar(closes)

    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df, df_1min=df_1min)

    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason']  == 'STOP LOSS (HARD)'
    assert t['exit_price']   == 19700.0                  # filled at the line
    assert t['exit_close']   == 19690.0                  # bar's actual close
    assert t['exit_time']    == '2025-01-01T08:05:00'    # 5 mins into the exit bar
    assert t['profit_points'] == -300.0


# ---- TP target ----

def test_tp_target_fires_on_1min_high_reaching_line():
    """avg=20000 ⇒ tp_target_line=20150. Set the 1-min HIGH at minute 17 to
    20155 (reaches the line) while close stays at 20020. Fill at the line."""
    df = _df_4h_entry_then_neutral()
    closes = [20020.0] * 240
    highs  = [20025.0] * 240
    highs[17] = 20155.0
    lows   = [c - 1 for c in closes]
    df_1min = _df_1min_for_exit_bar(closes, high_series=highs, low_series=lows)

    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df, df_1min=df_1min)

    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason']  == 'TAKE PROFIT'
    assert t['exit_price']   == 20150.0                  # fill at line
    assert t['exit_close']   == 20020.0                  # bar's close (unchanged)
    assert t['exit_time']    == '2025-01-01T08:17:00'


# ---- SOFT SL ----

def test_soft_sl_fires_on_2min_close_past_line():
    """avg=20000 ⇒ sl_soft_line=19800. SOFT must fire on a 2-min CLOSE past
    the line. Construct 2 consecutive 1-min closes: minute 6 close=19805
    (above the line), minute 7 close=19795 (the 2-min window ends at 19795,
    past the soft line). Hard line is 19700, so HARD must NOT fire here."""
    df = _df_4h_entry_then_neutral()
    closes = [20015.0] * 240
    # Window [08:06, 08:07] closes at 19795 (the 2-min close).
    closes[6] = 19805.0
    closes[7] = 19795.0
    df_1min = _df_1min_for_exit_bar(closes)

    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df, df_1min=df_1min)

    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason']  == 'STOP LOSS (SOFT)'
    assert t['exit_price']   == 19795.0                  # fill at 2-min close
    assert t['exit_close']   == 19795.0
    assert t['exit_time']    == '2025-01-01T08:07:00'    # end of the 2-min window
    assert t['profit_points'] == -205.0                  # avg − close = 205


# ---- TRAIL ----

def test_trail_fires_after_watch_arms_on_2min_close():
    """avg=20000, watch_threshold=50 ⇒ arm when 2-min close ≥ 20050; trail when
    a later 2-min close < 20050. Sequence:
      08:00 close=20030 (below arm), 08:01 close=20055 (window end ≥ 20050 → ARM).
      08:02 close=20040, 08:03 close=20045 (window end 20045 < 20050 → TRAIL).
    All values stay below tp_target_line=20150 and above sl_hard_line=19700, so
    only the trail logic should fire."""
    df = _df_4h_entry_then_neutral()
    closes = [20020.0] * 240
    closes[0] = 20030.0
    closes[1] = 20055.0   # window 08:00-08:01 closes at 20055 → arm
    closes[2] = 20040.0
    closes[3] = 20045.0   # window 08:02-08:03 closes at 20045 < 20050 → trail
    df_1min = _df_1min_for_exit_bar(closes)

    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df, df_1min=df_1min)

    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason']  == 'TAKE PROFIT (TRAIL)'
    assert t['exit_price']   == 20045.0                  # 2-min close
    assert t['exit_close']   == 20045.0
    assert t['exit_time']    == '2025-01-01T08:03:00'    # end of the 2-min window
    assert t['profit_points'] == 45.0                    # close − avg = 45


# ---- Legacy 4h path remains intact ----

def test_legacy_4h_path_when_df_1min_is_none():
    """Without df_1min, the engine still uses the 4h close. Existing 4h
    semantics: HARD SL fills at line, SOFT SL fills at close, TP at line,
    TRAIL at close. Locked by test_trade_log_alignment + the rest of the
    legacy suite — this is just a sanity check that backtest(df, df_1min=None)
    behaves identically to backtest(df)."""
    df = pd.DataFrame({
        'Date':   [pd.Timestamp('2025-01-01 00:00:00'),
                   pd.Timestamp('2025-01-01 04:00:00'),
                   pd.Timestamp('2025-01-01 08:00:00')],
        'Open':   [20000.0, 20000.0, 20010.0],
        'High':   [20010.0, 20020.0, 20020.0],
        'Low':    [19990.0, 19995.0, 19000.0],
        'Close':  [20000.0, 20010.0, 19400.0],  # 4h close past hard line
        'Volume': [1000, 1000, 1000],
    })
    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df, df_1min=None)
    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason'] == 'STOP LOSS (HARD)'
    # 4h-only mode does NOT populate exit_time (frontend falls back to exit_idx
    # candle timestamp).
    assert t['exit_time'] is None
