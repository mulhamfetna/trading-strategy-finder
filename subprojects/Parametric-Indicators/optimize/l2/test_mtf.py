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


def test_run_causal_independent_mode_combines_two_tfs():
    from optimize.l2 import logbook, payload
    l1p = payload.l1_default_params("1h")          # primary = 1h champion
    l2p = payload.l1_default_params("4h")          # secondary = 4h (a full profile)
    res = logbook.run_causal(l1p, l2p, tf="1h", instrument="NQ", l2_mode="independent", l2_tf="4h")
    owners = {r.position_owner for r in res.log if r.decision == "entry"}
    assert owners <= {"L1", "L2"} and "L1" in owners
    # master grid = finer tf (1h) → n == number of 1h decision bars
    assert res.n == len(payload.run_l1_cached("1h", params=l1p, instrument="NQ").df_dec)
    # at most one entry per master bar (single shared position)
    idxs = [r.i for r in res.log if r.decision == "entry"]
    assert len(idxs) == len(set(idxs))


def test_run_causal_residual_default_unchanged():
    from optimize.l2 import logbook, payload
    l1p, l2p = payload.l1_default_params("4h"), dict(payload.PERMISSIVE)
    a = logbook.run_causal(l1p, l2p, tf="4h", instrument="NQ")
    b = logbook.run_causal(l1p, l2p, tf="4h", instrument="NQ", l2_mode="residual")
    assert a.n == b.n and len(a.log) == len(b.log)
    assert [(r.layer, r.decision, r.pnl) for r in a.log] == [(r.layer, r.decision, r.pnl) for r in b.log]


def test_build_view_payload_independent_combined_has_both_owners():
    from optimize.l2 import payload
    l1p, l2p = payload.l1_default_params("1h"), payload.l1_default_params("4h")
    out = payload.build_view_payload(l1p, l2p, tf="1h", view="combined", instrument="NQ",
                                     l2_mode="independent", l2_tf="4h")
    owners = {r.get("position_owner") for r in out["log"] if r.get("decision") == "entry"}
    assert "L1" in owners
    assert out["meta"]["n"] == len(out["log"])


def test_build_view_payload_default_is_residual():
    from optimize.l2 import payload
    l1p, l2p = payload.l1_default_params("4h"), dict(payload.PERMISSIVE)
    a = payload.build_view_payload(l1p, l2p, tf="4h", view="combined", instrument="NQ")
    b = payload.build_view_payload(l1p, l2p, tf="4h", view="combined", instrument="NQ", l2_mode="residual")
    assert a["meta"]["n"] == b["meta"]["n"] and len(a["log"]) == len(b["log"])


def test_build_view_payload_independent_rejects_coarser_primary():
    from optimize.l2 import payload
    l1p, l2p = payload.l1_default_params("4h"), payload.l1_default_params("1h")
    try:
        payload.build_view_payload(l1p, l2p, tf="4h", view="combined", instrument="NQ",
                                   l2_mode="independent", l2_tf="1h")
        assert False, "expected L2ParamError (primary must be finer-or-equal)"
    except payload.L2ParamError as e:
        assert "finer" in str(e).lower()


def _serve_app():
    import threading
    from http.server import ThreadingHTTPServer
    import server                                       # noqa: E402 (data preload on import)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _post(port, route, obj):
    import urllib.request
    import urllib.error
    req = urllib.request.Request(f"http://127.0.0.1:{port}{route}",
                                 data=__import__("json").dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        return r.status, __import__("json").loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, __import__("json").loads(e.read())


def test_api_causal_backtest_independent_mode():
    import json as _json
    import urllib.request
    from optimize.l2 import payload
    srv, port = _serve_app()
    try:
        body = {"l1": payload.l1_default_params("1h"), "l2": payload.l1_default_params("4h"),
                "tf": "1h", "instrument": "NQ", "view": "combined",
                "l2_mode": "independent", "l2_tf": "4h"}
        status, out = _post(port, "/api/causal_backtest", body)
        assert status == 200
        assert out["meta"]["n"] == len(out["log"])
    finally:
        srv.shutdown()


def test_api_causal_backtest_bad_l2_tf_400():
    srv, port = _serve_app()
    try:
        body = {"l1": {}, "l2": {}, "tf": "1h", "view": "combined",
                "l2_mode": "independent", "l2_tf": "9q"}
        status, out = _post(port, "/api/causal_backtest", body)
        assert status == 400 and "9q" in out["error"]
    finally:
        srv.shutdown()
