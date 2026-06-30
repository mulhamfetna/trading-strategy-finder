"""Multi-timeframe layer fusion (spec 2026-06-30). Unit tests over synthetic LayerViews + real-data
integration through run_causal/build_view_payload. The residual path must stay byte-identical."""
import numpy as np
import pandas as pd

from optimize.l2 import mtf


def _lv(bar_minutes, n=4):
    dates = np.array([np.datetime64("2025-01-01T00:00") + np.timedelta64(bar_minutes * i, "m")
                      for i in range(n)])
    return mtf.LayerView(dates=dates, close=np.arange(n, dtype=float),
                         ledger=[], state=np.zeros(n, bool), bar_td=pd.Timedelta(minutes=bar_minutes))


def test_master_grid_picks_finer_as_first():
    one_h, four_h = _lv(60), _lv(240)
    finer, coarser = mtf.master_grid(one_h, four_h)       # primary=1h, secondary=4h
    assert finer.bar_td == pd.Timedelta(minutes=60)
    assert coarser.bar_td == pd.Timedelta(minutes=240)


def test_master_grid_primary_wins_tie():
    a, b = _lv(60), _lv(60)
    finer, _ = mtf.master_grid(a, b)
    assert finer is a
