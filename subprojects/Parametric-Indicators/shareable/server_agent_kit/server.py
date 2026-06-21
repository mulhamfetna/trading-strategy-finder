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
from optimize.l2 import payload as l2payload

FRONTEND = HERE / "frontend"
_CTYPE = {".html": "text/html", ".js": "application/javascript", ".css": "text/css",
          ".json": "application/json", ".md": "text/markdown"}
_LAST_CAUSAL: dict = {}     # caches the last /api/causal_backtest log so GET /api/causal_log.csv can serve it

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
                           # split long/short SL/TP (optional; blank ⇒ falls back to the shared value)
                           "long_sl_soft": [1, None], "long_sl_hard": [1, None], "long_tp": [1, None],
                           "short_sl_soft": [1, None], "short_sl_hard": [1, None], "short_tp": [1, None],
                           "gate_pct": [0, 100], "dd_limit": [0, None], "cooldown": [0, None],
                           "dd_cap": [1, None], "pv": [0.01, None]},
                "windows": ["full", "full+20d", "2024", "2025", "2026", "2026+20d"],
                # coarsest→finest for the dropdown; 4h is the default (matches the winner preset)
                "timeframes": list(reversed(list(TF.TIMEFRAMES))), "default_timeframe": "4h",
                "indicator_schema": library.schema()}))
        if path == "/api/l2_config":
            from indicators import library
            l1 = l2payload.run_l1_cached("4h")
            return self._send(200, json.dumps({
                "indicator_schema": library.schema(),
                "l2_profiles": l2payload.load_l2_profiles(),
                "l1": {"n_trades": len(l1.ledger),
                       "pnl": round(sum(t["pnl"] for t in l1.ledger), 2)},
                "l1_label": "🍃 WS lean 4h · 3-ind cci/OB/structure"}))
        if path == "/api/combined_config":
            # Combined dashboard: BOTH layers editable. Defaults = best L1 (frozen lean champion)
            # + best L2 (promoted extend champion); profile lists + the shared indicator schema.
            from indicators import library
            return self._send(200, json.dumps({
                "indicator_schema": library.schema(),
                "l1_default": l2payload.l1_default_params("4h"),
                "l2_default": l2payload.l2_default_params(),
                "l1_profiles": l2payload.load_l1_profiles(),
                "l2_profiles": l2payload.load_l2_profiles(),
                "l1_label": "🍃 WS lean 4h champion", "l2_label": "🔁 L2 (extend champion)"}))
        if path == "/api/causal_log.csv":
            # full per-candle causal log as CSV (the `layer` column lets L1/L2 be separated downstream).
            # GET can't carry the L1/L2 params cleanly, so this serves the LAST /api/causal_backtest log
            # (cached per-process). One row per candle.
            rows = _LAST_CAUSAL.get("log")
            if not rows:
                return self._send(409, "run /api/causal_backtest first", "text/plain")
            cols = list(rows[0].keys())

            def cell(v):
                s = "" if v is None else str(v)
                return ('"' + s.replace('"', '""') + '"') if ("," in s or '"' in s or "\n" in s) else s
            csv = "\n".join([",".join(cols)] + [",".join(cell(r[c]) for c in cols) for r in rows])
            return self._send(200, csv, "text/csv")
        name = "dashboard.html" if path in ("/", "") else path.lstrip("/")   # the unified 3-tab app
        f = FRONTEND / name
        if ".." in name or not f.is_file():
            return self._send(404, "not found", "text/plain")
        self._send(200, f.read_bytes(), _CTYPE.get(f.suffix, "application/octet-stream"))

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/profiles":
            # persist a user profile server-side (shared store; same shape as the built-in presets)
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                name, preset = body.get("name"), body.get("preset")
                if not (name or "").strip():
                    return self._send(400, json.dumps({"error": "profile name is required"}))
                strategy.validate_params(preset)          # reject garbage (no silent save)
                import presets
                presets.save_user_profile(name, preset)
                print(f"saved profile '{name}' → profiles/user_profiles.json", flush=True)
                return self._send(200, json.dumps({"ok": True, "strategies": presets.strategies()}))
            except strategy.ParamError as e:
                return self._send(400, json.dumps({"error": f"Invalid profile: {e}"}))
            except Exception as e:
                return self._send(500, json.dumps({"error": f"Save failed: {e}"}))
        if path == "/api/warmup":
            # Live warmup/data-footprint for the CURRENT indicator config (interactive boxes). Single source
            # of truth = indicators/library.warmup_bars() — the frontend never duplicates the formulas.
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                from indicators import library
                on = [s for s in (body.get("indicators") or []) if s.get("enabled")]
                inds = library.from_specs(on)                      # validates params; raises on bad config
                per = sorted(({"key": ind.key, "label": library.SCHEMA[ind.key]["label"],
                               "bars": int(ind.warmup_bars())} for ind in inds),
                             key=lambda d: d["bars"], reverse=True)
                mx = per[0] if per else None
                return self._send(200, json.dumps({
                    "per": per, "n_enabled": len(per), "frame": "1min",
                    "max_bars": (mx["bars"] if mx else 0), "driver": mx}))
            except Exception as e:
                return self._send(400, json.dumps({"error": f"warmup calc: {e}"}))
        if path == "/api/l2_backtest":
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                t0 = time.time()
                out = l2payload.build_l2_payload(body)
                out["meta"]["run_ms"] = round((time.time() - t0) * 1000)
                return self._send(200, json.dumps(out))
            except l2payload.L2ParamError as e:
                return self._send(400, json.dumps({"error": f"Invalid L2 parameter: {e}"}))
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._send(500, json.dumps({"error": f"L2 backtest failed: {e}"}))
        if path == "/api/l2_profiles":
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                profs = l2payload.save_l2_profile(body.get("name"), body.get("preset") or {})
                print(f"saved L2 profile '{body.get('name')}' → profiles/l2_profiles.json", flush=True)
                return self._send(200, json.dumps({"ok": True, "profiles": profs}))
            except l2payload.L2ParamError as e:
                return self._send(400, json.dumps({"error": f"Invalid L2 profile: {e}"}))
            except Exception as e:
                return self._send(500, json.dumps({"error": f"Save failed: {e}"}))
        if path == "/api/l1_profiles":
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                profs = l2payload.save_l1_profile(body.get("name"), body.get("preset") or {})
                print(f"saved L1 profile '{body.get('name')}' → profiles/l1_profiles.json", flush=True)
                return self._send(200, json.dumps({"ok": True, "profiles": profs}))
            except l2payload.L2ParamError as e:
                return self._send(400, json.dumps({"error": f"Invalid L1 profile: {e}"}))
            except Exception as e:
                return self._send(500, json.dumps({"error": f"Save failed: {e}"}))
        if path == "/api/backtest_causal":
            # Unified L1 view: same body as /api/backtest (full strategy params). Returns the engine's
            # complete L1 dashboard payload (strategy.build_payload — all features) + the causal per-candle
            # log + log-derived L1 boxes, so index.html runs entirely off the causal log with no feature loss.
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                t0 = time.time()
                l1lay = l2payload._layer_from_strategy(body)
                out = l2payload.build_view_payload(l1lay, {}, body.get("timeframe", "4h"), "l1", l1_engine=body)
                out["meta"]["run_ms"] = round((time.time() - t0) * 1000)
                _LAST_CAUSAL["log"] = out["log"]
                print(f"backtest_causal [l1] n={out['meta']['n']} ({out['meta']['run_ms']}ms)", flush=True)
                return self._send(200, json.dumps(out))
            except (l2payload.L2ParamError, strategy.ParamError) as e:
                return self._send(400, json.dumps({"error": f"Invalid parameter: {e}"}))
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._send(500, json.dumps({"error": f"L1 causal backtest failed: {e}"}))
        if path == "/api/causal_backtest":
            # causal log-first backtest for one view (l1 | l2 | combined). Boxes/charts/log all derive
            # from the SAME per-candle log; the full log is cached for the CSV route.
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                t0 = time.time()
                out = l2payload.build_view_payload(body.get("l1") or {}, body.get("l2") or {},
                                                   body.get("tf", "4h"), body.get("view", "combined"))
                out["meta"]["run_ms"] = round((time.time() - t0) * 1000)
                _LAST_CAUSAL["log"] = out["log"]
                print(f"causal backtest [{out['meta']['view']}] n={out['meta']['n']} "
                      f"({out['meta']['run_ms']}ms)", flush=True)
                return self._send(200, json.dumps(out))
            except l2payload.L2ParamError as e:
                return self._send(400, json.dumps({"error": f"Invalid parameter: {e}"}))
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._send(500, json.dumps({"error": f"Causal backtest failed: {e}"}))
        if path == "/api/combined_backtest":
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                t0 = time.time()
                out = l2payload.build_combined_payload(body.get("l1") or {}, body.get("l2") or {},
                                                       body.get("tf", "4h"))
                out["meta"]["run_ms"] = round((time.time() - t0) * 1000)
                s = out["meta"]["summary"]
                print(f"combined backtest -> L1 ${s['l1']['pnl']:,.0f} + L2 ${s['l2']['pnl']:,.0f} "
                      f"= ${s['combined']['pnl']:,.0f} (DD ${s['combined']['max_dd']:,.0f}) "
                      f"({out['meta']['run_ms']}ms)", flush=True)
                return self._send(200, json.dumps(out))
            except l2payload.L2ParamError as e:
                return self._send(400, json.dumps({"error": f"Invalid parameter: {e}"}))
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._send(500, json.dumps({"error": f"Combined backtest failed: {e}"}))
        if path != "/api/backtest":
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
