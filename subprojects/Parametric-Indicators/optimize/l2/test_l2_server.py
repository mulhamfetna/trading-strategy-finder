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
        assert cfg["l1"]["n_trades"] == 255

        out = json.loads(_post(port, "/api/l2_backtest", payload.PERMISSIVE).read())
        assert out["meta"]["summary"]["l2"]["n"] == 349
        assert "run_ms" in out["meta"]

        try:
            _post(port, "/api/l2_backtest", {**payload.PERMISSIVE, "sl_soft": -1})
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()


def test_combined_routes_smoke():
    srv, port = _serve()
    try:
        cfg = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        for k in ("indicator_schema", "l1_default", "l2_default"):
            assert k in cfg, k

        # combined backtest with the best-L1 + best-L2 defaults: 3 metric groups + labeled merged ledger
        out = json.loads(_post(port, "/api/combined_backtest",
                               {"l1": cfg["l1_default"], "l2": cfg["l2_default"], "tf": "4h"}).read())
        s = out["meta"]["summary"]
        assert set(s) == {"l1", "l2", "combined"}
        assert s["l1"]["n"] == 255                                  # L1 = the lean champion book
        assert len(out["ledger"]) == len(out["l1_trades"]) + len(out["l2_trades"])
        assert {r["layer"] for r in out["ledger"]} == {"L1", "L2"}
        assert "run_ms" in out["meta"]

        # editing L1 must change the L1 book (proves L1 is editable end-to-end)
        flipped = {**cfg["l1_default"], "flip": not cfg["l1_default"]["flip"]}
        out2 = json.loads(_post(port, "/api/combined_backtest",
                                {"l1": flipped, "l2": cfg["l2_default"]}).read())
        assert out2["meta"]["summary"]["l1"]["pnl"] != s["l1"]["pnl"]

        try:
            _post(port, "/api/combined_backtest",
                  {"l1": {**cfg["l1_default"], "gate_pct": 150}, "l2": cfg["l2_default"]})
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()
