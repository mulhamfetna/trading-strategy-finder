import sys
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from http.server import ThreadingHTTPServer
import server                                   # noqa: E402 (runs data preload on import)
from optimize.l2 import payload                 # noqa: E402


def _serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _post(port, route, obj):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{route}",
                                 data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req)


def test_l2_routes_smoke():
    srv, port = _serve()
    try:
        cfg = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/l2_config").read())
        assert "indicator_schema" in cfg
        assert cfg["l1"]["n_trades"] == 277
    finally:
        srv.shutdown()


def test_causal_routes_smoke():
    srv, port = _serve()
    try:
        cfg = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        for view in ("l1", "l2", "combined"):
            out = json.loads(_post(port, "/api/causal_backtest",
                {"l1": cfg["l1_default"], "l2": cfg["l2_default"], "tf": "4h", "view": view}).read())
            assert "boxes" in out["meta"] and out["meta"]["view"] == view
            assert len(out["log"]) == out["meta"]["n"]
            assert "run_ms" in out["meta"]
        # combined boxes carry the per-box shapes (pnl no tag; streak tagged)
        comb = json.loads(_post(port, "/api/causal_backtest",
            {"l1": cfg["l1_default"], "l2": cfg["l2_default"], "view": "combined"}).read())
        b = comb["meta"]["boxes"]
        assert "layer" not in b["pnl"] and b["noentry_streak_n"]["layer"] in ("L1", "L2")
        # the CSV route serves the last log, with a layer column, one row per candle.
        # It is self-describing: provenance is prepended as #-comment rows (skippable by
        # pandas.read_csv(comment='#')), so the file can never be silently confused with another run.
        csv = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/causal_log.csv").read().decode()
        assert csv.startswith("# causal_log export")           # provenance stamp present
        assert "# l2_source=" in csv and "# NOTE:" in csv       # l2 provenance + equity caveat
        lines = [ln for ln in csv.strip().split("\n") if not ln.startswith("#")]
        hdr = lines[0].split(",")
        assert hdr[:4] == ["i", "time", "layer", "decision"]
        assert len(lines) - 1 == comb["meta"]["n"]
        # verbose-logs: the live CSV now carries every field, incl. JSON-encoded per-bar votes
        import csv as _csvmod, io as _io, json as _json
        for col in ("entry_price", "exit_price", "text", "veto_flip", "would_be_pnl", "indicators"):
            assert col in hdr, f"live CSV missing {col}"
        recs = list(_csvmod.DictReader(_io.StringIO("\n".join(lines))))
        ind_cells = [r["indicators"] for r in recs if r["indicators"] not in ("", "[]")]
        assert ind_cells and isinstance(_json.loads(ind_cells[0]), list), "indicators not JSON on live CSV"
        # bad view → 400
        try:
            _post(port, "/api/causal_backtest", {"l1": cfg["l1_default"], "l2": cfg["l2_default"], "view": "x"})
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()


def test_es_contributor_through_http_changes_trades():
    """Manual-test wiring: an ES contributor block POSTed exactly as the dashboard sends it survives
    validation, reaches run_l2 and changes the L2 book vs the contributor-free POST (and a disabled
    contributor is a no-op)."""
    srv, port = _serve()
    try:
        cfg = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        l2 = dict(cfg["l2_default"])
        es = {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
              "signal": {"encoding": "stance", "mode": "both", "table": {}},
              "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                             "params": {"fast": 20, "slow": 50}}]}
        base = json.loads(_post(port, "/api/causal_backtest",
            {"l1": cfg["l1_default"], "l2": l2, "tf": "4h", "view": "l2"}).read())
        on = json.loads(_post(port, "/api/causal_backtest",
            {"l1": cfg["l1_default"], "l2": {**l2, "contributor_topology": "separate_and",
             "contributors": [es]}, "tf": "4h", "view": "l2"}).read())
        off = json.loads(_post(port, "/api/causal_backtest",
            {"l1": cfg["l1_default"], "l2": {**l2, "contributor_topology": "separate_and",
             "contributors": [{**es, "enabled": False}]}, "tf": "4h", "view": "l2"}).read())
        assert on["trades"] != base["trades"]                 # enabled ES reshapes the L2 book
        assert off["trades"] == base["trades"]                # disabled ES is a pure no-op
    finally:
        srv.shutdown()


def test_combined_config_per_instrument():
    srv, port = _serve()
    try:
        import urllib.request, urllib.error
        nq = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        es = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?instrument=ES").read())
        assert nq.get("instrument", "NQ") == "NQ" and es["instrument"] == "ES"
        assert es["point_value"] == 50.0 and nq["point_value"] == 20.0
        assert es["l1_default"]["sl_soft"] != nq["l1_default"]["sl_soft"]   # scaled
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?instrument=QQQ")
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()


def test_combined_config_per_tf():
    srv, port = _serve()
    try:
        base = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        tf2h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?tf=2h").read())
        # no-tf == 4h (back-compat); 2h differs (its own champion); both carry the schema
        assert base["l1_default"]["sl_soft"] != tf2h["l1_default"]["sl_soft"] or base["l1_default"] != tf2h["l1_default"]
        assert "indicator_schema" in tf2h and tf2h["l1_default"]["ind_1min"] is True
        # bad tf → 400
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?tf=1m")
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()

