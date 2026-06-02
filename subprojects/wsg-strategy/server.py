"""Backend for the standalone WS-G strategy app (Python stdlib only — no extra deps).

Loads market data + HAR-RV once, serves the frontend, and runs full backtests on demand against
the self-contained engine. Endpoints:
  GET  /                -> frontend/index.html
  GET  /<file>          -> static files from frontend/
  GET  /api/health      -> {status, params}
  POST /api/backtest    -> {sl_soft,sl_hard,tp,gate_pct,dd_limit,cooldown,flip,window} → full payload

Run:  python3 subprojects/wsg-strategy/server.py [--port 8200]   then open http://localhost:8200/
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
import config
import strategy

FRONTEND = HERE / "frontend"
_CTYPE = {".html": "text/html", ".js": "application/javascript", ".css": "text/css",
          ".json": "application/json", ".md": "text/markdown"}

print("loading data (4h / 1m / box) + computing HAR-RV ...", flush=True)
_t = time.time()
DF4, DF1, BOX, VF, N2025 = strategy.load_inputs()
print(f"ready in {time.time()-_t:.1f}s  ({len(DF4)} 4h bars, split at index {N2025})", flush=True)


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

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            return self._send(200, json.dumps({"status": "ok", "bars": len(DF4), "winner": config.WINNER}))
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        f = FRONTEND / name
        if ".." in name or not f.is_file():
            return self._send(404, "not found", "text/plain")
        self._send(200, f.read_bytes(), _CTYPE.get(f.suffix, "application/octet-stream"))

    def do_POST(self):
        if self.path.split("?")[0] != "/api/backtest":
            return self._send(404, '{"error":"unknown endpoint"}')
        try:
            n = int(self.headers.get("Content-Length", 0))
            params = json.loads(self.rfile.read(n) or b"{}")
            t0 = time.time()
            payload = strategy.build_payload(DF4, DF1, BOX, VF, N2025, params)
            payload["meta"]["run_ms"] = round((time.time() - t0) * 1000)
            self._send(200, json.dumps(payload))
            s = payload["meta"]["summary"]
            print(f"backtest {params} -> P/L ${s['pnl']:,.0f} DD ${s['max_dd']:,.0f} "
                  f"n={s['n_taken']} ({payload['meta']['run_ms']}ms)", flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send(500, json.dumps({"error": str(e)}))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8200)
    port = ap.parse_args().port
    print(f"WS-G strategy app at http://localhost:{port}/   (Ctrl-C to stop)", flush=True)
    try:
        ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
