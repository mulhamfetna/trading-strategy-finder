"""Backend for the standalone WS-G strategy app (Python stdlib only — no extra deps).

Loads market data + HAR-RV once, serves the frontend, and runs full backtests on demand against
the self-contained engine. Endpoints:
  GET  /                -> frontend/index.html
  GET  /<file>          -> static files from frontend/
  GET  /api/health      -> {status, params}
  GET  /api/config      -> {preset, dd_cap, pv, bounds, windows}  (the frontend hardcodes nothing)
  POST /api/backtest    -> {sl_soft,sl_hard,tp,gate_pct,dd_limit,cooldown,flip,window[,dd_cap,pv]} → full payload
                           400 {error} on any invalid/missing param (NEVER silently clamped); 500 {error} on failure

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
DF4, DF1, BOX, VF, N2025 = strategy.get_bundle("4h")   # preload+cache the default TF
print(f"ready in {time.time()-_t:.1f}s  ({len(DF4)} 4h bars, split at index {N2025}). "
      f"other timeframes load on first use.", flush=True)


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
        if path == "/api/config":
            # expose the preset + instrument constants + indicator schema so the frontend
            # hardcodes NOTHING (params, bounds, indicator keys/params, enums all come from here)
            from indicators import library
            from optimize import timeframes as TF
            import presets
            return self._send(200, json.dumps({
                "preset": config.WINNER, "dd_cap": config.DD_CAP, "pv": config.NQ_POINT_VALUE,
                # one-click importable winning strategies (plain winner + per-TF WS-I champions)
                "strategies": presets.strategies(),
                "bounds": {"sl_soft": [1, None], "sl_hard": [1, None], "tp": [1, None],
                           "gate_pct": [0, 100], "dd_limit": [0, None], "cooldown": [0, None],
                           "dd_cap": [1, None], "pv": [0.01, None]},
                "windows": ["full", "2025", "2026"],
                # coarsest→finest for the dropdown; 4h is the default (matches the winner preset)
                "timeframes": list(reversed(list(TF.TIMEFRAMES))), "default_timeframe": "4h",
                "indicator_schema": library.schema()}))
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
            # pick the decision-timeframe bundle (lazy-loaded + cached); bad TF → ParamError → 400
            bundle = strategy.get_bundle((params or {}).get("timeframe"))
            payload = strategy.build_payload(*bundle, params)
            payload["meta"]["run_ms"] = round((time.time() - t0) * 1000)
            self._send(200, json.dumps(payload))
            s = payload["meta"]["summary"]
            print(f"backtest [{payload['meta']['params'].get('timeframe','4h')}] {params} -> "
                  f"P/L ${s['pnl']:,.0f} DD ${s['max_dd']:,.0f} "
                  f"n={s['n_taken']} ({payload['meta']['run_ms']}ms)", flush=True)
        except strategy.ParamError as e:
            # invalid/missing parameter — surfaced to the UI as a 400 (NOT silently clamped)
            print(f"param error: {e}", flush=True)
            self._send(400, json.dumps({"error": f"Invalid parameter: {e}"}))
        except Exception as e:
            import traceback; traceback.print_exc()
            self._send(500, json.dumps({"error": f"Backtest failed: {e}"}))


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
