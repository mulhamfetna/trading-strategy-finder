"""Interactive backtest server for the winning-strategy dashboard.

Self-contained (Python stdlib only). Loads the 4h/1m/box data + HAR-RV forecast ONCE at
startup, then serves:
  GET  /                 -> index.html (interactive dashboard)
  GET  /data.js          -> last static export (initial view)
  GET  /winner_backtest.py, /README.md  -> static files
  POST /api/backtest     -> {sl_soft,sl_hard,tp,gate_pct,dd_limit,cooldown,flip,window}
                            runs the verified CLONE engine + drawdown breaker, returns full JSON.

Engine = verified single-contract clone (engine_clone/); the main engine/dashboard are untouched.
Run:   python3 subprojects/meta-prophet/dashboard_winner/server.py [--port 8137]
then open http://localhost:8137/
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import winner_backtest as wb

print("loading data (4h / 1m / box / HAR-RV) ...", flush=True)
_t = time.time()
DF4, DF1, BOX, VF, N2025 = wb.load_inputs()
print(f"loaded in {time.time()-_t:.1f}s — ready.", flush=True)

_CTYPE = {".html": "text/html", ".js": "application/javascript",
          ".md": "text/markdown", ".py": "text/plain", ".json": "application/json"}


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # quieter
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        f = HERE / name
        if not f.is_file() or ".." in name:
            return self._send(404, "not found", "text/plain")
        self._send(200, f.read_bytes(), _CTYPE.get(f.suffix, "application/octet-stream"))

    def do_POST(self):
        if self.path.split("?")[0] != "/api/backtest":
            return self._send(404, '{"error":"unknown endpoint"}')
        try:
            n = int(self.headers.get("Content-Length", 0))
            params = json.loads(self.rfile.read(n) or b"{}")
            t0 = time.time()
            payload = wb.build_payload(DF4, DF1, BOX, VF, N2025, params)
            payload["meta"]["run_ms"] = round((time.time() - t0) * 1000)
            self._send(200, json.dumps(payload))
            s = payload["meta"]["summary"]
            print(f"backtest {params} -> P/L ${s['pnl']:,.0f} DD ${s['max_dd']:,.0f} "
                  f"n={s['n_taken']} ({payload['meta']['run_ms']}ms)", flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send(500, json.dumps({"error": str(e)}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8137)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("0.0.0.0", a.port), H)
    print(f"serving interactive winner dashboard at http://localhost:{a.port}/  (Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
