# L2 Dashboard-inside-dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-contained `frontend/l2.html` page (+ thin `server.py` routes) that runs the cached frozen L1 (lean 4h) and a manually-tuned L2 profile over L1's dropped signals, visualizing the dropped set, the L1-flat mask, L2 trades (agree/oppose + `L1-entry` force-close), and the combined-book drawdown guardrail — manual apply/inspect + save L2 profiles, no optimizer launch.

**Architecture:** All orchestration lives in a new testable `optimize/l2/payload.py` (`build_l2_payload`, a process-level L1 cache, param validation, profile store). `server.py` gains three thin routes (`POST /api/l2_backtest`, `POST /api/l2_profiles`, `GET /api/l2_config`) that wrap it. The page `frontend/l2.html` is vanilla JS + lightweight-charts, reusing `index.html`'s theme/chart helpers. L1's engine bytes are never touched; `/api/backtest` and `index.html` are untouched except a one-line link.

**Tech Stack:** Python 3 stdlib `http.server`, NumPy/pandas, the built `optimize/l2/` package (`l1_runner`, `engine`, `metrics`, `dataset`), `indicators.library`, lightweight-charts@4.1.3 (CDN), pytest.

## Global Constraints

- **L1 frozen / golden:** no edits to `engine.py`, `optimize/fast_engine.py`, `optimize/core.py`, `indicators/*`, or the built `optimize/l2/{l1_runner,engine,metrics,dataset}.py`. `python3 perf/check_golden.py` must print **6/6 MATCH** after every task (run from subproject root `/mnt/data/projects/trading/subprojects/Parametric-Indicators`).
- **L1 base fixed:** the lean 4h champion via `l1_runner.run_l1("4h")`, cached once per process (first call ~38s).
- **Focused L2 levers only:** `indicators[]`, `k`, `gate_pct`, `sl_soft`, `sl_hard`, `tp`, `dd_limit`, `cooldown`, `flip`, `ind_1min`. No `window`/`retrace`/`wait`/`veto_as_flip`/split-SL-TP controls.
- **No silent fallback:** invalid L2 params → `L2ParamError` → HTTP `400` with the reason (project norm).
- **No optimizer launch** from this page (that is #237).
- **Profile store isolation:** L2 profiles in `profiles/l2_profiles.json` (separate from `user_profiles.json`).
- **Charts need unique, sorted times:** lightweight-charts line series throw on duplicate/unsorted timestamps — every equity series is deduped (keep last value per epoch second) and sorted.
- **Deterministic test anchor (permissive profile):** `{indicators:[], k:1, gate_pct:0, sl_soft:149.8, sl_hard:167.1, tp:120.2, dd_limit:0, cooldown:0, flip:false, ind_1min:false}` → L2 `n=349, pnl≈-64299.0, max_dd≈108453.0, n_l1_entry_exits=52`; combined `max_dd≈50574.0, l1_only_dd≈15491.0, dd_not_worse=false`; L1 `255 trades, $149,989`; dropped `492 (286 veto + 206 vol-gate), 410 flat`.
- **Commit only at the step that says so; stage explicitly by path** (never `git add -A`/`.`). Branch `dev`. Never stage repo-root secrets, `notes.md`, or the pre-existing modified working-tree files (demo/, docs/graphics/, .gitignore).

---

### Task 1: `payload.py` foundations — cache, validation, profile store

**Files:**
- Create: `optimize/l2/payload.py`
- Test: `optimize/l2/test_payload.py`

**Interfaces:**
- Consumes: `l1_runner.run_l1(tf) -> L1Result`; `indicators.library.from_specs`.
- Produces:
  - `class L2ParamError(ValueError)`.
  - `run_l1_cached(tf: str = "4h") -> L1Result` (module-level `_L1_CACHE: dict`).
  - `validate_l2_params(p: dict) -> dict` (returns a clean param dict with `window="full"`; raises `L2ParamError`).
  - `load_l2_profiles() -> dict`, `save_l2_profile(name: str, preset: dict) -> dict` (persist to `profiles/l2_profiles.json`).
  - `PERMISSIVE: dict` test constant (the deterministic anchor profile).

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_payload.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest
from optimize.l2 import payload


def test_validate_accepts_permissive_and_sets_window_full():
    p = payload.validate_l2_params(dict(payload.PERMISSIVE))
    assert p["window"] == "full"
    assert p["sl_soft"] == 149.8 and p["tp"] == 120.2
    assert p["cooldown"] == 0 and p["k"] == 1 and p["flip"] is False
    assert p["indicators"] == []


def test_validate_rejects_bad_params():
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "sl_soft": -1})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "gate_pct": 150})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "sl_soft": None})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE,
                                    "indicators": [{"key": "cci", "enabled": True,
                                                    "mode": "both", "params": {"n": -5}}]})


def test_l1_cache_returns_same_object():
    a = payload.run_l1_cached("4h")
    b = payload.run_l1_cached("4h")
    assert a is b
    assert len(a.ledger) == 255


def test_save_and_load_l2_profile_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "_PROFILES", tmp_path / "l2_profiles.json")
    profs = payload.save_l2_profile("mine", dict(payload.PERMISSIVE))
    assert "mine" in profs
    assert payload.load_l2_profiles()["mine"]["tp"] == 120.2
    with pytest.raises(payload.L2ParamError):
        payload.save_l2_profile("", dict(payload.PERMISSIVE))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_payload.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError: cannot import name 'payload'`.

- [ ] **Step 3: Write `payload.py` (foundations only)**

```python
# optimize/l2/payload.py
"""L2 dashboard backend — orchestration for the dashboard-inside-dashboard (frontend/l2.html).
Runs the cached frozen L1 (lean 4h) + a manual L2 profile, serializes a chart-ready payload, and
persists hand-tuned L2 profiles. server.py is a thin router over this module."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, engine, metrics, dataset   # noqa: E402
from indicators import library                                # noqa: E402

_PROFILES = _PI / "profiles" / "l2_profiles.json"
_L1_CACHE: dict = {}

# Deterministic anchor profile (no indicators / no vol gate ⇒ take every flat dropped signal).
PERMISSIVE: dict = {"indicators": [], "k": 1, "gate_pct": 0, "sl_soft": 149.8, "sl_hard": 167.1,
                    "tp": 120.2, "dd_limit": 0, "cooldown": 0, "flip": False, "ind_1min": False}


class L2ParamError(ValueError):
    """Invalid L2 profile parameter — surfaced to the UI as HTTP 400 (never silently clamped)."""


def run_l1_cached(tf: str = "4h"):
    """Frozen L1 (lean champion), computed once per process (~38s first call, then instant)."""
    if tf not in _L1_CACHE:
        _L1_CACHE[tf] = l1_runner.run_l1(tf)
    return _L1_CACHE[tf]


def validate_l2_params(p: dict) -> dict:
    """Validate the focused L2 levers; return a clean engine-ready dict (window='full'). Raise on any
    bad/missing value (no silent fallback)."""
    if not isinstance(p, dict):
        raise L2ParamError("params must be an object")

    def num(key, lo=None, hi=None):
        if key not in p or p[key] is None:
            raise L2ParamError(f"missing {key}")
        try:
            v = float(p[key])
        except (TypeError, ValueError):
            raise L2ParamError(f"{key} must be a number")
        if lo is not None and v < lo:
            raise L2ParamError(f"{key} must be >= {lo}")
        if hi is not None and v > hi:
            raise L2ParamError(f"{key} must be <= {hi}")
        return v

    out = dict(
        sl_soft=num("sl_soft", 1e-6), sl_hard=num("sl_hard", 1e-6), tp=num("tp", 1e-6),
        gate_pct=num("gate_pct", 0, 100), dd_limit=num("dd_limit", 0),
        cooldown=int(num("cooldown", 0)), k=int(num("k", 1)),
        flip=bool(p.get("flip", False)), ind_1min=bool(p.get("ind_1min", False)),
        window="full",
    )
    inds = p.get("indicators", [])
    if not isinstance(inds, list):
        raise L2ParamError("indicators must be a list")
    try:
        library.from_specs([s for s in inds if s.get("enabled")])   # validates indicator params
    except Exception as e:
        raise L2ParamError(f"bad indicator config: {e}")
    out["indicators"] = inds
    return out


def load_l2_profiles() -> dict:
    if not _PROFILES.exists():
        return {}
    try:
        d = json.loads(_PROFILES.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_l2_profile(name: str, preset: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise L2ParamError("profile name is required")
    validate_l2_params(preset)                       # reject garbage (no silent save)
    profs = load_l2_profiles()
    profs[name] = preset
    _PROFILES.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES.write_text(json.dumps(profs, indent=1))
    return profs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_payload.py -v`
Expected: 4 PASS (the cache test runs `run_l1` once, ~38s).

- [ ] **Step 5: Golden gate**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/payload.py optimize/l2/test_payload.py
git commit -m "feat(l2): payload foundations — L1 cache, param validation, profile store

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `build_l2_payload` + serialization

**Files:**
- Modify: `optimize/l2/payload.py` (append serialization helpers + `build_l2_payload`)
- Test: `optimize/l2/test_payload.py` (append)

**Interfaces:**
- Consumes (Task 1): `validate_l2_params`, `run_l1_cached`, `PERMISSIVE`; `engine.run_l2(l1, params) -> L2Result`; `metrics.score(l2) -> dict`, `metrics.combined(l1, l2) -> dict`; `dataset.build_dataset(l1)`.
- Produces: `build_l2_payload(l2_params: dict, tf: str = "4h") -> dict` (response per spec §6). Internal helpers `_epoch`, `_spans_from_timeline`, `_derive_lines`, `_equity_series`, `_combined_equity_series`, `_dedupe`.

- [ ] **Step 1: Write the failing test (append to `test_payload.py`)**

```python
def test_build_l2_payload_permissive_matches_metrics():
    out = payload.build_l2_payload(dict(payload.PERMISSIVE))
    # all documented top-level keys present
    for key in ("meta", "candles", "l1_spans", "dropped", "l2_trades",
                "l2_equity", "l1_equity", "combined_equity"):
        assert key in out, key
    m = out["meta"]
    assert m["l1"]["n_trades"] == 255
    assert round(m["l1"]["pnl"]) == 149989
    s = m["summary"]["l2"]
    assert s["n"] == 349 and s["n_l1_entry_exits"] == 52
    assert round(s["pnl"]) == -64299
    g = m["summary"]["combined"]
    assert g["dd_not_worse"] is False
    assert round(g["max_dd"]) == 50574 and round(g["l1_only_dd"]) == 15491
    assert m["dropped_counts"] == {"veto": 286, "vol_gate": 206, "total": 492, "flat_candidates": 410}
    # series are non-empty, sorted, unique-timed
    assert len(out["candles"]) > 0 and len(out["dropped"]) == 492
    for ser in ("l2_equity", "l1_equity", "combined_equity"):
        ts = [pt["time"] for pt in out[ser]]
        assert ts == sorted(ts) and len(ts) == len(set(ts)), ser
    # a long L2 trade's derived SL/TP lines bracket entry by the points
    longs = [t for t in out["l2_trades"] if t["direction"] == "long"]
    assert longs, "expected at least one long L2 trade"
    t = longs[0]
    assert abs(t["sl_hard_line"] - (t["entry_price"] - 167.1)) < 1e-6
    assert abs(t["tp_hard_line"] - (t["entry_price"] + 120.2)) < 1e-6


def test_derive_lines_short_mirrors_long():
    line = payload._derive_lines(
        {"entry_price": 1000.0, "direction": "short"},
        {"sl_soft": 10.0, "sl_hard": 20.0, "tp": 30.0})
    assert line == {"sl_hard_line": 1020.0, "sl_soft_line": 1010.0, "tp_hard_line": 970.0}


def test_dedupe_keeps_last_and_sorts():
    out = payload._dedupe([{"time": 3, "value": 1}, {"time": 1, "value": 2}, {"time": 3, "value": 9}])
    assert out == [{"time": 1, "value": 2}, {"time": 3, "value": 9}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_payload.py::test_build_l2_payload_permissive_matches_metrics -v`
Expected: FAIL — `AttributeError: module 'optimize.l2.payload' has no attribute 'build_l2_payload'`.

- [ ] **Step 3: Append serialization + `build_l2_payload` to `payload.py`**

```python
def _epoch(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


def _dedupe(series: list) -> list:
    """lightweight-charts needs unique, sorted times; keep the last value per timestamp."""
    last = {}
    for pt in series:
        last[pt["time"]] = pt["value"]
    return [{"time": t, "value": last[t]} for t in sorted(last)]


def _spans_from_timeline(state_timeline, dec_dates) -> list:
    """Contiguous [from,to] epoch spans where L1 is in-position (for chart shading)."""
    spans = []
    n = len(state_timeline)
    i = 0
    while i < n:
        if state_timeline[i]:
            j = i
            while j < n and state_timeline[j]:
                j += 1
            spans.append({"from": _epoch(dec_dates[i]), "to": _epoch(dec_dates[min(j, n - 1)])})
            i = j
        else:
            i += 1
    return spans


def _derive_lines(t: dict, p: dict) -> dict:
    """SL/TP line levels for display only (entry_price ± points; engine fill convention)."""
    ep = float(t["entry_price"])
    sl_hard = float(p["sl_hard"]); sl_soft = float(p["sl_soft"]); tp = float(p["tp"])
    if t["direction"] == "long":
        return {"sl_hard_line": ep - sl_hard, "sl_soft_line": ep - sl_soft, "tp_hard_line": ep + tp}
    return {"sl_hard_line": ep + sl_hard, "sl_soft_line": ep + sl_soft, "tp_hard_line": ep - tp}


def _equity_series(ledger: list) -> list:
    rows = sorted(ledger, key=lambda t: pd.Timestamp(t["exit_time"]))
    out = []
    eq = 0.0
    for t in rows:
        eq += float(t["pnl"])
        out.append({"time": _epoch(t["exit_time"]), "value": round(eq, 2)})
    return _dedupe(out)


def _combined_equity_series(l1_ledger: list, l2_ledger: list) -> list:
    merged = [(pd.Timestamp(t["exit_time"]), float(t["pnl"])) for t in l1_ledger] \
        + [(pd.Timestamp(t["exit_time"]), float(t["pnl"])) for t in l2_ledger]
    merged.sort(key=lambda x: x[0])
    out = []
    eq = 0.0
    for ts, pnl in merged:
        eq += pnl
        out.append({"time": int(ts.timestamp()), "value": round(eq, 2)})
    return _dedupe(out)


def build_l2_payload(l2_params: dict, tf: str = "4h") -> dict:
    p = validate_l2_params(l2_params)
    l1 = run_l1_cached(tf)
    res = engine.run_l2(l1, p)
    ds = dataset.build_dataset(l1)
    dec_dates = l1.df_dec["Date"].to_numpy()

    candles = [{"time": _epoch(d), "open": float(o), "high": float(h), "low": float(lo), "close": float(c)}
               for d, o, h, lo, c in zip(l1.df_dec["Date"], l1.df_dec["Open"], l1.df_dec["High"],
                                         l1.df_dec["Low"], l1.df_dec["Close"])]
    dropped = [{"time": _epoch(d["ts"]), "reason": d["reason"], "box_dir": d["box_dir"],
                "l1_flat": (not bool(l1.state_timeline[d["idx"]]))} for d in l1.dropped_signals]
    l2_trades = []
    for t in res.ledger:
        row = {"entry_time": _epoch(t["entry_time"]), "exit_time": _epoch(t["exit_time"]),
               "direction": t["direction"], "entry_price": float(t["entry_price"]),
               "exit_price": float(t["exit_price"]), "exit_reason": t["exit_reason"],
               "pnl": round(float(t["pnl"]), 2), "l2_dir_vs_box": t.get("l2_dir_vs_box", "agree")}
        row.update(_derive_lines(t, p))
        l2_trades.append(row)

    return {
        "meta": {
            "l1": {"n_trades": len(l1.ledger), "pnl": round(sum(t["pnl"] for t in l1.ledger), 2)},
            "summary": {"l2": metrics.score(res), "combined": metrics.combined(l1, res)},
            "dropped_counts": {"veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                               "total": len(ds), "flat_candidates": len(ds.flat_candidates())},
        },
        "candles": candles,
        "l1_spans": _spans_from_timeline(l1.state_timeline, dec_dates),
        "dropped": dropped,
        "l2_trades": l2_trades,
        "l2_equity": _equity_series(res.ledger),
        "l1_equity": _equity_series(l1.ledger),
        "combined_equity": _combined_equity_series(l1.ledger, res.ledger),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_payload.py -v`
Expected: all PASS (7 total in this file).

- [ ] **Step 5: Golden gate**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/payload.py optimize/l2/test_payload.py
git commit -m "feat(l2): build_l2_payload — chart-ready serialization of L1/L2/combined

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `server.py` routes + `index.html` link

**Files:**
- Modify: `server.py` (module import + 1 GET route + 2 POST routes)
- Modify: `frontend/index.html` (one "L2 layer" link)
- Test: `optimize/l2/test_l2_server.py`

**Interfaces:**
- Consumes (Tasks 1–2): `payload.build_l2_payload`, `payload.save_l2_profile`, `payload.load_l2_profiles`, `payload.run_l1_cached`, `payload.L2ParamError`; `indicators.library.schema()`.
- Produces: HTTP routes `GET /api/l2_config`, `POST /api/l2_backtest`, `POST /api/l2_profiles` on the existing `server.H` handler.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_l2_server.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_l2_server.py -v`
Expected: FAIL — the `/api/l2_config` request returns 404 (route not wired) → `HTTPError`/assertion fails.

- [ ] **Step 3: Add the module import to `server.py`**

After the `import strategy` line (near the top, ~line 26), add:

```python
from optimize.l2 import payload as l2payload
```

- [ ] **Step 4: Add the `GET /api/l2_config` route**

In `server.py` `do_GET`, immediately after the `if path == "/api/config":` block (before the `name = "index.html" ...` static-serving line), add:

```python
        if path == "/api/l2_config":
            from indicators import library
            l1 = l2payload.run_l1_cached("4h")
            return self._send(200, json.dumps({
                "indicator_schema": library.schema(),
                "l2_profiles": l2payload.load_l2_profiles(),
                "l1": {"n_trades": len(l1.ledger),
                       "pnl": round(sum(t["pnl"] for t in l1.ledger), 2)},
                "l1_label": "🍃 WS lean 4h · 3-ind cci/OB/structure"}))
```

- [ ] **Step 5: Add the two POST routes**

In `server.py` `do_POST`, immediately after the `if path == "/api/warmup":` block (before `if path != "/api/backtest":`), add:

```python
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
```

- [ ] **Step 6: Add the link in `index.html`**

In `frontend/index.html`, find the top header/title area (the first `<h1>`/header block near the top of `<body>`). Add a link to the L2 page right after the page title text. Concretely, locate the first occurrence of a header element and append:

```html
<a href="l2.html" style="margin-left:12px;font-size:13px;color:#2962ff;text-decoration:none">→ L2 layer</a>
```

If no obvious header exists, add it as the first child of `<body>`:

```html
<div style="padding:6px 12px;background:#131722;color:#d1d4dc;font-size:13px">
  <a href="l2.html" style="color:#2962ff;text-decoration:none">→ L2 second-layer dashboard</a>
</div>
```

- [ ] **Step 7: Run the route test to verify it passes**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/test_l2_server.py -v`
Expected: PASS (slow — imports `server` which preloads data, and warms L1 ~38s).

- [ ] **Step 8: Golden gate**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 9: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add server.py optimize/l2/test_l2_server.py frontend/index.html
git commit -m "feat(l2): server routes /api/l2_config /api/l2_backtest /api/l2_profiles + index link

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `frontend/l2.html` page

**Files:**
- Create: `frontend/l2.html`
- Test: none automated (vanilla page, matches the existing dashboard's no-FE-test norm); verified by Task 3's route test + a manual page smoke in Task 5.

**Interfaces:**
- Consumes: `GET /api/l2_config` (indicator schema + saved profiles + L1 summary), `POST /api/l2_backtest` (payload per spec §6), `POST /api/l2_profiles`.

- [ ] **Step 1: Create `frontend/l2.html`** (complete, self-contained — reuses `index.html`'s theme/helpers)

```html
<!doctype html><html><head><meta charset="utf-8"><title>L2 second-layer dashboard</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{box-sizing:border-box} body{margin:0;font:13px/1.4 system-ui,Segoe UI,Roboto,sans-serif;background:#0e1117;color:#d1d4dc}
header{padding:8px 14px;background:#131722;border-bottom:1px solid #363a45;display:flex;align-items:center;gap:14px}
header b{font-size:15px} header a{color:#2962ff;text-decoration:none;font-size:13px}
.wrap{display:flex;height:calc(100vh - 41px)}
aside{width:320px;min-width:240px;max-width:760px;overflow:auto;padding:12px;border-right:1px solid #363a45}
main{flex:1;overflow:auto;padding:10px}
.row{display:flex;gap:8px;margin:6px 0;align-items:center}
.row label{flex:1;color:#9aa0aa} .row input,.row select{width:120px;background:#1c2230;color:#d1d4dc;border:1px solid #363a45;border-radius:4px;padding:4px}
button{background:#2962ff;color:#fff;border:0;border-radius:5px;padding:8px 12px;cursor:pointer;font-size:13px}
button.sec{background:#2a2f3a}
.panel{background:#131722;border:1px solid #363a45;border-radius:6px;padding:8px;margin-bottom:10px}
.cards{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.card{background:#131722;border:1px solid #363a45;border-radius:6px;padding:8px 10px;min-width:120px}
.card .v{font-size:18px;font-weight:600}.card .k{color:#787b86;font-size:11px}
.v.good{color:#00c853}.v.bad{color:#ff5252}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:3px 6px;border-bottom:1px solid #20242f;text-align:right}th:first-child,td:first-child{text-align:left}
#err{color:#ff5252;margin:6px 0;min-height:16px}
.chart{height:auto}
#ind .ind{border-top:1px solid #20242f;padding:6px 0}
</style></head>
<body>
<header>
  <b>🍃→🔁 L2 second-layer</b>
  <span id="l1info" style="color:#787b86"></span>
  <a href="index.html">← L1 backtest</a>
</header>
<div class="wrap">
<aside>
  <div class="panel">
    <div class="row"><label>Saved L2 profile</label>
      <select id="profile"><option value="">— none —</option></select></div>
    <div class="row"><label>gate_pct (vol)</label><input id="gate_pct" type="number" value="0" min="0" max="100"></div>
    <div class="row"><label>K (confirmers)</label><input id="k" type="number" value="1" min="1"></div>
    <div class="row"><label>sl_soft</label><input id="sl_soft" type="number" value="149.8"></div>
    <div class="row"><label>sl_hard</label><input id="sl_hard" type="number" value="167.1"></div>
    <div class="row"><label>tp</label><input id="tp" type="number" value="120.2"></div>
    <div class="row"><label>dd_limit</label><input id="dd_limit" type="number" value="0"></div>
    <div class="row"><label>cooldown</label><input id="cooldown" type="number" value="0"></div>
    <div class="row"><label>flip</label><select id="flip"><option value="false">false</option><option value="true">true</option></select></div>
    <div class="row"><label>indicators on 1-min</label><select id="ind_1min"><option value="false">false</option><option value="true">true</option></select></div>
    <div class="row"><button id="run">Run L2</button>
      <button id="save" class="sec">Save profile</button></div>
    <div id="err"></div>
  </div>
  <div class="panel"><div style="color:#9aa0aa;margin-bottom:4px">Indicators (L2)</div><div id="ind"></div></div>
</aside>
<main>
  <div class="cards" id="cards"></div>
  <div class="panel"><div class="chart" id="price" style="height:430px"></div></div>
  <div class="panel"><div class="chart" id="equity" style="height:200px"></div></div>
  <div class="panel"><b>L2 trades</b><div id="trades"></div></div>
  <div class="panel"><b>Dropped signals</b> <span id="dropinfo" style="color:#787b86"></span>
    <div id="droptbl" style="max-height:260px;overflow:auto"></div></div>
</main>
</div>
<script>
const TH={bg:'#131722',text:'#d1d4dc',border:'#363a45',green:'#00c853',red:'#ff5252',blue:'#2962ff',orange:'#ff9800',muted:'#787b86'};
const COMMON={layout:{background:{color:TH.bg},textColor:TH.text},grid:{vertLines:{color:'#20242f'},horzLines:{color:'#20242f'}},timeScale:{timeVisible:true,borderColor:TH.border},rightPriceScale:{borderColor:TH.border},crosshair:{mode:0}};
const $=id=>document.getElementById(id);
const dt=t=>new Date(t*1000).toISOString().slice(0,16).replace('T',' ');
const money=n=>(n>=0?'+':'')+'$'+Math.round(n).toLocaleString();
const card=(v,k,cls='')=>`<div class="card"><div class="v ${cls}">${v}</div><div class="k">${k}</div></div>`;
const charts=[],ctns=[];
const mk=(id,h)=>{const el=$(id);const c=LightweightCharts.createChart(el,{...COMMON,width:el.clientWidth,height:h});charts.push(c);ctns.push(el);return c;};
const priceC=mk('price',430), eqC=mk('equity',200);
const candle=priceC.addCandlestickSeries({upColor:TH.green,downColor:TH.red,wickUpColor:TH.green,wickDownColor:TH.red,borderVisible:false});
const seg=c=>priceC.addLineSeries({color:c,lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
const tpS=seg('rgba(0,200,83,.6)'),shS=seg('rgba(255,82,82,.6)'),ssS=seg('rgba(255,152,0,.6)');
const shadeS=priceC.addLineSeries({color:'rgba(120,123,134,.0)',lastValueVisible:false,priceLineVisible:false});
const mkrS=priceC.addLineSeries({color:'rgba(0,0,0,0)',lastValueVisible:false,priceLineVisible:false});
const l1EqS=eqC.addLineSeries({color:TH.muted,lineWidth:1}),combEqS=eqC.addLineSeries({color:TH.orange,lineWidth:2}),l2EqS=eqC.addLineSeries({color:TH.blue,lineWidth:1});
let sy=false;charts.forEach(s=>s.timeScale().subscribeVisibleTimeRangeChange(r=>{if(sy||!r)return;sy=true;charts.forEach(o=>{if(o!==s){try{o.timeScale().setVisibleRange(r)}catch(e){}}});sy=false;}));
function fit(){charts.forEach((c,i)=>{const w=ctns[i].clientWidth;if(w>0)c.applyOptions({width:w})})}
window.addEventListener('resize',fit);

let SCHEMA=null;
function buildIndicators(schema){
  SCHEMA=schema; const host=$('ind'); host.innerHTML='';
  Object.entries(schema).forEach(([key,meta])=>{
    const wrap=document.createElement('div'); wrap.className='ind';
    let h=`<div class="row"><label><input type="checkbox" data-en="${key}"> ${meta.label||key}</label>
      <select data-mode="${key}">${(meta.modes||['both']).map(m=>`<option ${m===(meta.mode||'both')?'selected':''}>${m}</option>`).join('')}</select></div>`;
    (meta.params||[]).forEach(p=>{ h+=`<div class="row"><label>${p.name}</label><input data-p="${key}.${p.name}" type="number" value="${p.default}"></div>`; });
    wrap.innerHTML=h; host.appendChild(wrap);
  });
}
function indicatorSpecs(){
  if(!SCHEMA) return [];
  return Object.entries(SCHEMA).map(([key,meta])=>{
    const en=document.querySelector(`[data-en="${key}"]`).checked;
    const mode=document.querySelector(`[data-mode="${key}"]`).value;
    const params={}; (meta.params||[]).forEach(p=>{ params[p.name]=+document.querySelector(`[data-p="${key}.${p.name}"]`).value; });
    return {key,enabled:en,mode,params};
  });
}
function params(){
  return {indicators:indicatorSpecs(), k:+$('k').value||1, gate_pct:+$('gate_pct').value,
    sl_soft:+$('sl_soft').value, sl_hard:+$('sl_hard').value, tp:+$('tp').value,
    dd_limit:+$('dd_limit').value, cooldown:+$('cooldown').value,
    flip:$('flip').value==='true', ind_1min:$('ind_1min').value==='true'};
}
function setForm(p){
  ['gate_pct','k','sl_soft','sl_hard','tp','dd_limit','cooldown'].forEach(k=>{ if(p[k]!=null)$(k).value=p[k]; });
  $('flip').value=String(!!p.flip); $('ind_1min').value=String(!!p.ind_1min);
  if(SCHEMA && p.indicators){ p.indicators.forEach(s=>{ const en=document.querySelector(`[data-en="${s.key}"]`);
    if(en){ en.checked=!!s.enabled; const md=document.querySelector(`[data-mode="${s.key}"]`); if(md&&s.mode)md.value=s.mode;
      Object.entries(s.params||{}).forEach(([n,v])=>{const el=document.querySelector(`[data-p="${s.key}.${n}"]`);if(el)el.value=v;}); } }); }
}
function showErr(m){ $('err').textContent=m||''; }

async function loadConfig(){
  const c=await (await fetch('/api/l2_config')).json();
  buildIndicators(c.indicator_schema);
  $('l1info').textContent=`${c.l1_label} — L1 ${c.l1.n_trades} trades / ${money(c.l1.pnl)}`;
  window.L2PROFILES=c.l2_profiles||{};
  const sel=$('profile'); sel.innerHTML='<option value="">— none —</option>'+Object.keys(window.L2PROFILES).map(n=>`<option>${n}</option>`).join('');
}
$('profile').addEventListener('change',()=>{ const p=window.L2PROFILES[$('profile').value]; if(p) setForm(p); });

function render(D){
  const m=D.meta, s=m.summary.l2, g=m.summary.combined;
  $('cards').innerHTML=[
    card(s.n,'L2 trades'), card(money(s.pnl),'L2 P/L',s.pnl>=0?'good':'bad'),
    card('$'+Math.round(s.max_dd).toLocaleString(),'L2 maxDD'), card(s.win+'%','L2 win'),
    card(s.n_l1_entry_exits,'L1-entry exits'),
    card(money(g.pnl),'combined P/L',g.pnl>=0?'good':'bad'),
    card('$'+Math.round(g.max_dd).toLocaleString(),'combined maxDD'),
    card(g.dd_not_worse?'OK':'WORSE','DD guardrail',g.dd_not_worse?'good':'bad'),
  ].join('');
  candle.setData(D.candles);
  // L1 in-position shading: draw a faint top-of-range band across each span
  const hi=Math.max(...D.candles.map(c=>c.high)), lo=Math.min(...D.candles.map(c=>c.low));
  const shade=[]; D.l1_spans.forEach(sp=>{ shade.push({time:sp.from,value:hi},{time:sp.to,value:hi},{time:sp.to+1}); });
  shadeS.applyOptions({color:'rgba(120,123,134,.25)',lineWidth:6}); try{shadeS.setData(dedupe(shade));}catch(e){}
  // L2 SL/TP lines + markers
  const tp=[],sh=[],ss=[],mks=[];
  D.l2_trades.forEach(t=>{ const e=t.entry_time,x=t.exit_time;
    tp.push({time:e,value:t.tp_hard_line},{time:x,value:t.tp_hard_line},{time:x+1});
    sh.push({time:e,value:t.sl_hard_line},{time:x,value:t.sl_hard_line},{time:x+1});
    ss.push({time:e,value:t.sl_soft_line},{time:x,value:t.sl_soft_line},{time:x+1});
    const opp=t.l2_dir_vs_box==='oppose';
    mks.push({time:e,position:t.direction==='long'?'belowBar':'aboveBar',color:opp?TH.orange:TH.blue,
      shape:t.direction==='long'?'arrowUp':'arrowDown',text:opp?'opp':''});
    mks.push({time:x,position:'inBar',color:t.exit_reason==='L1-entry'?TH.muted:(t.pnl>0?TH.green:TH.red),
      shape:'circle',text:t.exit_reason==='L1-entry'?'L1':''});
  });
  // dropped-signal markers (veto=orange, vol_gate=blue; dimmed if not flat)
  D.dropped.forEach(d=>{ mks.push({time:d.time,position:'aboveBar',
    color:(d.reason==='veto'?'rgba(255,152,0,':'rgba(41,98,255,')+(d.l1_flat?'.9)':'.3)'),
    shape:'square',size:0}); });
  try{tpS.setData(dedupe(tp));shS.setData(dedupe(sh));ssS.setData(dedupe(ss));}catch(e){}
  mkrS.setData(D.candles.map(c=>({time:c.time,value:c.close}))); mks.sort((a,b)=>a.time-b.time); mkrS.setMarkers(mks);
  l1EqS.setData(D.l1_equity); combEqS.setData(D.combined_equity); l2EqS.setData(D.l2_equity);
  $('trades').innerHTML='<table><thead><tr><th>entry</th><th>exit</th><th>dir</th><th>vs box</th><th>reason</th><th>P/L</th></tr></thead><tbody>'+
    D.l2_trades.map(t=>`<tr><td>${dt(t.entry_time)}</td><td>${dt(t.exit_time)}</td><td>${t.direction}</td><td>${t.l2_dir_vs_box}</td><td>${t.exit_reason}</td><td style="color:${t.pnl>=0?TH.green:TH.red}">${money(t.pnl)}</td></tr>`).join('')+'</tbody></table>';
  const dc=m.dropped_counts; $('dropinfo').textContent=`${dc.total} total · ${dc.veto} veto · ${dc.vol_gate} vol-gate · ${dc.flat_candidates} flat`;
  $('droptbl').innerHTML='<table><thead><tr><th>time</th><th>reason</th><th>box dir</th><th>L1 flat</th></tr></thead><tbody>'+
    D.dropped.map(d=>`<tr><td>${dt(d.time)}</td><td>${d.reason}</td><td>${d.box_dir}</td><td>${d.l1_flat?'yes':'no'}</td></tr>`).join('')+'</tbody></table>';
  fit();
}
function dedupe(a){const m={};a.forEach(p=>{if(p.value!=null)m[p.time]=p.value;});return Object.keys(m).map(Number).sort((x,y)=>x-y).map(t=>({time:t,value:m[t]}));}

async function run(){
  showErr('Running L2 (first run computes L1 — up to ~40s)…');
  try{ const r=await fetch('/api/l2_backtest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(params())});
    const D=await r.json(); if(!r.ok){ showErr(D.error||'error'); return; }
    showErr(D.l2_trades.length?'':'L2 took 0 trades for this profile.'); render(D);
  }catch(e){ showErr(String(e)); }
}
async function save(){
  const name=prompt('Save L2 profile as:'); if(!name) return;
  const r=await fetch('/api/l2_profiles',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,preset:params()})});
  const D=await r.json(); if(!r.ok){ showErr(D.error||'save failed'); return; }
  window.L2PROFILES=D.profiles; $('profile').innerHTML='<option value="">— none —</option>'+Object.keys(D.profiles).map(n=>`<option ${n===name?'selected':''}>${n}</option>`).join('');
  showErr(`saved "${name}"`);
}
$('run').addEventListener('click',run);
$('save').addEventListener('click',save);
loadConfig();
</script>
</body></html>
```

- [ ] **Step 2: Golden gate** (no engine touched, but per discipline)

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 3: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add frontend/l2.html
git commit -m "feat(l2): l2.html — second-layer dashboard page (form, charts, ledger, dropped table, save)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: End-to-end smoke + build report

**Files:**
- Create: `optimize/l2/UPDATE_l2_dashboard.md`
- Modify: `docs/superpowers/specs/2026-06-18-l2-dashboard-inside-dashboard-design.md:7` — status → "BUILT (2026-06-18) — next = optimizer #237"
- Modify: `optimize/l2/UPDATE_l2_backtester.md` "Next" line (optional pointer to the dashboard)

- [ ] **Step 1: Run the full L2 suite + golden**

Run: `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 -m pytest optimize/l2/ -q && python3 perf/check_golden.py`
Expected: all L2 tests PASS (the prior 10 + payload tests + the server route test); golden 6/6.

- [ ] **Step 2: Manual page smoke**

Run (background): `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 server.py --port 8200`
Then: open `http://localhost:8200/l2.html`, confirm the indicator panel + L1 info load; click **Run L2** with the default (permissive-ish) form; confirm cards show L2 trades + combined maxDD + a red "WORSE" guardrail, the price chart shows dropped-signal squares + L2 markers + L1 shading, the equity chart shows 3 lines, and both tables populate. Stop the server afterward.

- [ ] **Step 3: Write `UPDATE_l2_dashboard.md`** (a verbose Mermaid build report mirroring `UPDATE_l2_backtester.md`: architecture diagram, the route table, the module/test table, the manual-smoke result, and "Next: optimizer #237"). Fill the real test counts + smoke observations.

- [ ] **Step 4: Update the spec status line** (`...design.md` line 7) to `status: BUILT (2026-06-18) — next = optimizer #237`.

- [ ] **Step 5: Commit**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
git add optimize/l2/UPDATE_l2_dashboard.md \
        docs/superpowers/specs/2026-06-18-l2-dashboard-inside-dashboard-design.md \
        optimize/l2/UPDATE_l2_backtester.md
git commit -m "docs(l2): dashboard-inside-dashboard build report; spec status -> built

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Spec coverage self-check

- §2 attach = separate `l2.html` + routes → Tasks 3, 4. ✅
- §2 L1 fixed lean 4h + cache → Task 1 `run_l1_cached`. ✅
- §2 focused L2 form → Task 1 `validate_l2_params` + Task 4 form (only the levers). ✅
- §2 full-context charts → Task 4 (`l1_spans` shading, dropped markers by reason, agree/oppose markers, `L1-entry` flag, combined-vs-L1 equity). ✅
- §2 save L2 profiles, no optimizer → Task 1 profile store + Task 3/4 save; no launch anywhere. ✅
- §3 orchestration in `payload.py`, thin `server.py` → Tasks 1–3. ✅
- §4 components (payload module, 3 routes, page) → Tasks 1–4. ✅
- §6 endpoint contracts (request/response keys, SL/TP-line derivation note) → Task 2 `build_l2_payload` + Task 3 routes + Task 2 `_derive_lines`. ✅
- §8 edge cases: slow-L1 cache + "computing" state (Task 1 cache + Task 4 run() message), 0-trade profiles (Task 4 "0 trades" note + zero cards), no silent fallback (Task 1 validate → 400 Task 3), L1 frozen/golden (golden each task), profile isolation (`l2_profiles.json`). ✅
- §9 testing: payload metrics-match + cache identity + validate + profile round-trip + line derivation (Tasks 1–2); route smoke 200/400 (Task 3); golden each task; manual page smoke (Task 5). ✅
- §10 build order: backend → frontend → profile save → smoke → exactly Tasks 1–5. ✅
- §11 out of scope (optimizer/selectable-L1/speed) → not in any task. ✅

(Placeholder scan: none. Type consistency: `build_l2_payload`, `run_l1_cached`, `validate_l2_params`, `save_l2_profile`, `_derive_lines`, `_dedupe`, `L2ParamError`, `PERMISSIVE` used identically across tasks and tests. The frontend `dedupe()` is a separate JS helper — intentional, page-local.)
