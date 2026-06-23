"""TIME_CAP exit (max-1min-open-trade-streak-cap) — fast_engine behavioural tests."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.fast_engine import fast_backtest


def _frames():
    # 3 decision bars; long signal at idx0 (read at idx1) → enter at d_close[0]=100.
    d_dates = np.array([0, 60, 120], dtype="int64").astype("datetime64[s]")
    d_close = np.array([100.0, 100.0, 100.0])
    sig = np.array([1, 0, 0], dtype=np.int64)
    # 10 one-min bars from entry, flat at 100 (never hits SL 90 / TP 110 / soft 95)
    m_dates = np.arange(0, 600, 60).astype("datetime64[s]")
    m = np.full(10, 100.0)
    return d_dates, d_close, sig, m_dates, m


def test_time_cap_fires_at_nth_bar_close_long():
    d_dates, d_close, sig, m_dates, m = _frames()
    tr = fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                       sl_soft=5, sl_hard=10, tp=10, flip=False, cap_1min=4)
    assert len(tr) == 1
    t = tr[0]
    assert t["exit_reason"] == "TIME_CAP"
    assert t["exit_price"] == 100.0
    assert t["pnl_points"] == 0.0


def test_cap_zero_is_disabled():
    d_dates, d_close, sig, m_dates, m = _frames()
    tr = fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                       sl_soft=5, sl_hard=10, tp=10, flip=False, cap_1min=0)
    # no SL/TP/soft + no cap → never closes → OPEN dropped → no completed trade
    assert tr == []
