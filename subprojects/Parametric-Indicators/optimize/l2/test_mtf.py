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


def test_dual_tf_secondary_fills_gap_then_primary_preempts():
    # master = 1h, 6 bars 00:00..05:00. Primary: one trade entering at 03:00.
    prim = _lv(60, n=6)
    prim.ledger = [dict(entry_idx=3, entry_price=3.0, direction="long",
                        exit_time=np.datetime64("2025-01-01T05:00"), exit_price=5.0,
                        exit_reason="tp", pnl_points=2.0, pnl=40.0)]
    prim.state = np.array([False, False, False, True, True, False])
    # Secondary (4h): one trade entering at 01:00, would exit 05:00 — but primary enters at 03:00.
    sec = _lv(240, n=2)
    sec.dates = np.array([np.datetime64("2025-01-01T01:00"), np.datetime64("2025-01-01T04:00")])
    sec.close = np.array([1.0, 4.0])
    sec.ledger = [dict(entry_idx=0, entry_price=1.0, direction="long",
                       exit_time=np.datetime64("2025-01-01T05:00"), exit_price=5.0,
                       exit_reason="tp", pnl_points=4.0, pnl=200.0)]
    sec.state = np.array([True, True])
    res = mtf.run_dual_tf(prim, sec, pv=50.0)
    owners = {t["owner"]: t for t in res.ledger}
    assert set(owners) == {"L1", "L2"}
    assert owners["L1"]["entry_idx"] == 3
    # secondary entered 01:00 (primary flat), force-closed at primary entry 03:00 (master close 3.0)
    l2 = owners["L2"]
    assert l2["entry_idx"] == 1
    assert l2["exit_reason"] == "L1-entry"
    assert l2["exit_price"] == 3.0
    assert l2["pnl"] == (3.0 - 1.0) * 50.0            # honest recompute: 100.0


def test_dual_tf_drops_secondary_when_primary_already_open():
    prim = _lv(60, n=4)
    prim.ledger = [dict(entry_idx=0, entry_price=0.0, direction="long",
                        exit_time=np.datetime64("2025-01-01T03:00"), exit_price=3.0,
                        exit_reason="tp", pnl_points=3.0, pnl=150.0)]
    prim.state = np.array([True, True, True, False])
    sec = _lv(240, n=1)
    sec.dates = np.array([np.datetime64("2025-01-01T01:00")])
    sec.close = np.array([1.0])
    sec.ledger = [dict(entry_idx=0, entry_price=1.0, direction="long",
                       exit_time=np.datetime64("2025-01-01T02:00"), exit_price=2.0,
                       exit_reason="tp", pnl_points=1.0, pnl=50.0)]
    sec.state = np.array([True])
    res = mtf.run_dual_tf(prim, sec, pv=50.0)
    assert [t["owner"] for t in res.ledger] == ["L1"]   # secondary dropped (primary open at 01:00)
