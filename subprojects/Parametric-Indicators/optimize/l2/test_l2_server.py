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
