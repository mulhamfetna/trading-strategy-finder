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


def test_remap_aligns_coarse_entry_to_master_bar():
    # master = 1h grid (4 bars @ 00:00,01:00,02:00,03:00); coarse trade entered at 02:00
    one_h = _lv(60)
    four_h = _lv(240)
    four_h.dates = np.array([np.datetime64("2025-01-01T02:00")])      # single coarse bar at 02:00
    four_h.close = np.array([10.0])
    four_h.ledger = [dict(entry_idx=0, entry_price=10.0, direction="long",
                          exit_time=np.datetime64("2025-01-01T03:00"), exit_price=12.0,
                          exit_reason="tp", pnl_points=2.0, pnl=40.0)]
    out = mtf._remap_to_master(four_h, one_h)
    assert out[0]["entry_idx"] == 2          # 02:00 is master bar index 2
    assert out[0]["pnl"] == 40.0             # carried unchanged


def test_state_on_master_marks_open_window():
    one_h = _lv(60)                                   # 00:00..03:00
    coarse = _lv(240)
    coarse.dates = np.array([np.datetime64("2025-01-01T01:00")])
    coarse.ledger = [dict(entry_idx=0, entry_price=1.0, direction="long",
                          exit_time=np.datetime64("2025-01-01T03:00"), exit_price=1.0,
                          exit_reason="tp", pnl_points=0.0, pnl=0.0)]
    st = mtf._state_on_master(coarse, one_h)
    assert list(st) == [False, True, True, False]     # open over [01:00, 03:00)
