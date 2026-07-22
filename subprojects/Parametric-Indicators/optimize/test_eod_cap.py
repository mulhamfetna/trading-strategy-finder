"""END_OF_DAY exit-cap behaviour in fast_backtest (synthetic; mirrors test_time_cap's 3-bar shape:
signal on decision bar 0, entry at bar 1)."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.fast_engine import fast_backtest


def test_eod_exits_at_session_target_bar():
    # 3 decision bars (sig read from idx-1 -> entry at idx=1, et=60 -> e=1); 10 one-minute bars.
    d_dates = np.array([0, 60, 120], dtype="int64").astype("datetime64[s]")
    d_close = np.array([100.0, 100.0, 100.0])
    sig = np.array([1, 0, 0], dtype=np.int64)
    m_dates = np.arange(0, 600, 60).astype("datetime64[s]")     # 10 bars
    m = np.full(10, 100.0)
    eod_target = np.full(10, 5, dtype=np.int64)                 # session EOD bar = global index 5
    session_last = np.full(10, 9, dtype=np.int64)
    tr = fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                       sl_soft=50, sl_hard=90, tp=90, flip=False,
                       cap_mode="eod", eod_target=eod_target, session_last=session_last, m_open=m)
    assert len(tr) == 1 and tr[0]["exit_reason"] == "END_OF_DAY"
    # entry e=1, target global 5 -> slice index 4 -> exit at m_dates[5]
    assert np.datetime64(tr[0]["exit_time"]) == m_dates[5]


def test_eod_off_by_default_no_exit():
    d_dates = np.array([0, 60, 120], dtype="int64").astype("datetime64[s]")
    sig = np.array([1, 0, 0], dtype=np.int64)
    m_dates = np.arange(0, 600, 60).astype("datetime64[s]")
    m = np.full(10, 100.0)
    tr = fast_backtest(d_dates, np.array([100.0, 100.0, 100.0]), sig, None, m_dates, m, m, m,
                       sl_soft=50, sl_hard=90, tp=90, flip=False, m_open=m)
    assert tr == []          # no cap, SL/TP never hit -> OPEN -> dropped
