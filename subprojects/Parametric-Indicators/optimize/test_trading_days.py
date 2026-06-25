"""trading_days.eod_targets — per-1min-bar end-of-day exit targets, locked to the data study anchors."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize import trading_days, data as data_mod
from optimize.signals import _box_dates_vec


def _md():
    _, df1, _, _, _ = data_mod.load_inputs("4h")
    return df1["Date"].to_numpy()


def test_eod_targets_anchors():
    md = _md()
    et, sl = trading_days.eod_targets(md, 15)
    assert et.shape == md.shape == sl.shape
    ts = pd.DatetimeIndex(md)
    tod = (ts.hour * 60 + ts.minute).to_numpy()
    box = pd.DatetimeIndex(_box_dates_vec(ts)).asi8
    starts = np.concatenate(([0], np.flatnonzero(np.diff(box)) + 1))
    ends = np.concatenate((np.flatnonzero(np.diff(box)) + 1, [len(md)]))
    last_tod = tod[ends - 1]
    targets = et[starts]                                   # one target per session
    n_full = int(((last_tod >= 16 * 60 + 55) & (last_tod <= 17 * 60 + 5)).sum())
    n_partial = int((last_tod < 16 * 60).sum())
    n_abnormal = int((targets < 0).sum())
    assert n_full == 342 and n_partial == 14 and n_abnormal == 1
    # every FULL-day target lands on the 16:45 bar (1005 min)
    full_mask = (last_tod >= 16 * 60 + 55) & (last_tod <= 17 * 60 + 5)
    assert set(tod[targets[full_mask]].tolist()) == {16 * 60 + 45}
    # every PARTIAL-day target is that session's last bar
    part_mask = last_tod < 16 * 60
    assert np.array_equal(targets[part_mask], (ends - 1)[part_mask])
    # session_last is constant within a session and equals the session's last index
    assert np.array_equal(sl[starts], ends - 1)
