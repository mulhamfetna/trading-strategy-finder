"""Regression lock: trade dict carries candle-grounded prices.

User-reported bug (2026-05-24): dashboard trade log shows entry/exit prices
that don't appear in the candle OHLC at the corresponding timestamp.

Root cause: `avg_entry_price` is a weighted blend across multiple legs (some
of which fill at synthetic pullback target prices), and `exit_price` for
SL/TP exits is the threshold LINE (avg ± offset), not the bar's close. Both
are mathematically correct for PnL but visually misleading on the chart.

Fix: every trade dict carries two additional fields that are guaranteed to
appear in the candle OHLC at the corresponding bar:

  - `entry_signal_price` = `legs[0].price` (the signal bar's close that
                                            triggered the entry)
  - `exit_close`         = the candle's close at `exit_idx`

The legacy `avg_entry_price` / `exit_price` fields are preserved unchanged
for PnL transparency (shown in tooltip on the UI).
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy
from src.strategy.scaling_strategy import ScalingStrategy
from tests._fixtures import box_strategy_params, scaling_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _unified_csv(path, dates=None, **levels):
    if dates is None:
        dates = ['2025-01-03']
    n = len(dates)
    row_data = {c: ([levels.get(c)] * n) for c in _W_COLS + _M_COLS}
    pd.DataFrame({'Date': dates, **row_data}).to_csv(path, index=False)


def _candles(rows):
    return pd.DataFrame(
        [dict(zip(['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], r + (1000,))) for r in rows]
    )


# ---- scaling strategy ----

def test_scaling_trade_carries_entry_signal_price_and_exit_close():
    """Force a 1-leg LONG that exits at SL HARD on the next bar. The
    trade dict must surface `entry_signal_price` = signal-bar close and
    `exit_close` = exit-bar close, distinct from `avg_entry_price` /
    `exit_price` (the SL line)."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20000, 20020, 19995, 20010),  # signal close = 20010, long
        ('2025-01-01 08:00', 20010, 20020, 19000, 19400),  # close 19400 < sl hard line (avg-300 = 19710)
    ])
    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df)

    assert len(trades) == 1
    t = trades[0]
    # Entry price recorded as the base-level / leg1 price (== the prev close
    # under the default trigger, == 20000 here).
    assert t['entry_signal_price'] == t['legs'][0]['price']
    # Exit close is the candle close at the exit bar — guaranteed to be in
    # the dataset (it IS a candle's close).
    assert t['exit_close'] == 19400
    # The legacy synthetic price is preserved for PnL transparency.
    assert t['exit_price'] != t['exit_close'], (
        'SL HARD must store the SL line as exit_price, NOT the bar close.'
    )


def test_scaling_trade_multi_leg_entry_signal_price_matches_leg1_only():
    """A multi-leg fill (leg 1 + leg 2 at pullback) must record
    entry_signal_price = leg1.price (a real candle's close), while
    avg_entry_price blends leg1 + leg2 prices."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        # signal bar: close > prev_close → LONG, leg1 at 20000 (prev close)
        ('2025-01-01 04:00', 20000, 20020, 19995, 20010),
        # leg2 fills here: low touches base_level - 100 = 19900
        ('2025-01-01 08:00', 20005, 20015, 19895, 19905),
        # SL HARD: close < avg - 300
        ('2025-01-01 12:00', 19905, 19910, 18000, 18000),
    ])
    strat = ScalingStrategy(params=scaling_params())
    trades, _ = strat.backtest(df)

    assert len(trades) == 1
    t = trades[0]
    # leg 1 at 20000 (signal-bar's base_level = prev_close), leg 2 at 19900
    assert t['legs'][0]['price'] == 20000
    assert t['legs'][1]['price'] == 19900
    # The new field tracks the signal-bar's price (always a candle value).
    assert t['entry_signal_price'] == 20000
    # The legacy avg blends both legs and is NOT any single candle's value.
    assert t['avg_entry_price'] == 19950


# ---- box strategy ----

def test_box_strategy_trade_carries_entry_signal_price_and_exit_close(tmp_path):
    """Box-strategy long that exits SL HARD: entry_signal_price = signal
    bar's close (matches MASTER_STRATEGY_GUIDE.md §3.1); exit_close =
    exit bar's close."""
    _unified_csv(tmp_path / 'u.csv', WRHU=20100.0, WRHD=20050.0)
    lookup = BoxLookup(unified_path=str(tmp_path / 'u.csv'), tick_threshold=0.75)

    # 3 bars on 2025-01-03 (single box date for the unified CSV row):
    #  bar 0: close 20040 (state = below WRH box)
    #  bar 1: close 20080 (state = inside the box; inside_seen=True)
    #  bar 2: close 20200 (traversed below→inside→above → LONG)
    #  bar 3: close 19800 (SL HARD: close < avg - sl_hard_points)
    df = _candles([
        ('2025-01-03 00:00', 20030, 20040, 20020, 20040),
        ('2025-01-03 04:00', 20040, 20090, 20030, 20080),
        ('2025-01-03 08:00', 20080, 20210, 20070, 20200),
        ('2025-01-03 12:00', 20200, 20200, 19790, 19800),
    ])
    params = box_strategy_params(
        sl_soft_points=50.0,
        sl_hard_points=100.0,
        tp_target_points=200.0,
        tp_watch_threshold_points=100.0,
    )
    strat = BoxStrategy(params=params, box_lookup=lookup)
    trades, _ = strat.backtest(df)

    assert len(trades) == 1
    t = trades[0]
    assert t['direction'] == 'long'
    # Per the box strategy, leg 1 fills at the SIGNAL BAR'S CLOSE.
    assert t['entry_signal_price'] == 20200
    # Exit close = candle's close at exit bar.
    assert t['exit_close'] == 19800
    # exit_price is the SL HARD line (synthetic), not the bar close.
    assert t['exit_price'] != t['exit_close']
