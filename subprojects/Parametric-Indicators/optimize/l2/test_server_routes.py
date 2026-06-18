import json
import sys
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import server  # noqa: E402


def _serve():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
        return r.status, json.loads(r.read())


def _post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_l2_config_route():
    httpd, port = _serve()
    try:
        code, body = _get(port, "/api/l2_config")
        assert code == 200
        assert "indicator_schema" in body and "l1" in body and "profiles" in body
    finally:
        httpd.shutdown()


def test_l2_profiles_route_roundtrip_and_validation():
    httpd, port = _serve()
    name = "_pytest_route_profile"
    try:
        code, body = _post(port, "/api/l2_profiles",
                           {"name": name, "preset": {"sl_soft": 1, "indicators": []}})
        assert code == 200 and body["ok"] is True and name in body["profiles"]
        code, body = _post(port, "/api/l2_profiles", {"name": "", "preset": {}})
        assert code == 400 and "error" in body
    finally:
        httpd.shutdown()
        from optimize.l2 import payload
        all_p = payload.load_l2_profiles(); all_p.pop(name, None)
        payload._L2_PROFILES.write_text(json.dumps(all_p, indent=1))
