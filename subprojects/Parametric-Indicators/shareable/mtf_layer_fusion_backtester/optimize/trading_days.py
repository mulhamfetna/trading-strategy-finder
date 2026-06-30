"""Trading-day calendar for the end-of-day exit cap. Sessions follow the box-date rule (hour>=18 ->
next day), matching the engine's day mapping. Pure; no engine state."""
from __future__ import annotations

import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd


def eod_targets(m_dates: np.ndarray, margin_min: int) -> tuple[np.ndarray, np.ndarray]:
    """(eod_target, session_last) per 1-min bar (global indices). Full day: last bar with
    time <= 17:00-margin. Partial (last bar < 16:00): the session's last bar. Abnormal: -1."""
    from optimize.signals import _box_dates_vec
    n = len(m_dates)
    if n == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)
    ts = pd.DatetimeIndex(m_dates)
    tod = (ts.hour * 60 + ts.minute).to_numpy()
    box = pd.DatetimeIndex(_box_dates_vec(ts)).asi8
    starts = np.concatenate(([0], np.flatnonzero(np.diff(box)) + 1))
    ends = np.concatenate((np.flatnonzero(np.diff(box)) + 1, [n]))
    eod_target = np.full(n, -1, dtype=np.int64)
    session_last = np.zeros(n, dtype=np.int64)
    cutoff_full = 17 * 60 - int(margin_min)
    for lo, hi in zip(starts, ends):
        last = hi - 1
        session_last[lo:hi] = last
        last_tod = tod[last]
        if 16 * 60 + 55 <= last_tod <= 17 * 60 + 5:          # full day
            seg = tod[lo:hi]
            ok = np.flatnonzero(seg <= cutoff_full)
            eod_target[lo:hi] = (lo + int(ok[-1])) if ok.size else last
        elif last_tod < 16 * 60:                              # partial / early close
            eod_target[lo:hi] = last
        else:                                                 # abnormal (truncated tail)
            eod_target[lo:hi] = -1
    return eod_target, session_last
