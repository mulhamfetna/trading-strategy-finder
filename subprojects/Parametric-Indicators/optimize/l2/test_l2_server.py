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
