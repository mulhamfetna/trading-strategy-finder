# L2 Dashboard-Inside-Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-contained `frontend/l2.html` page + `server.py` routes that run the cached frozen lean L1, apply a manually-tuned L2 profile over its dropped (veto+vol-gate) signals, and visualize dropped signals, L1-flat shading, L2 trades (agree/oppose), force-closes, and the combined-book guardrail — with L2-profile saving.

**Architecture:** A pure orchestrator `optimize/l2/payload.py` (`build_l2_payload`) reuses the *built* `run_l1`/`run_l2`/`metrics` with a process-level L1 cache (first call ~38 s, then instant) and serializes chart series. Three thin `server.py` routes (`/api/l2_backtest`, `/api/l2_profiles`, `/api/l2_config`) call it. `frontend/l2.html` is a vanilla-JS + lightweight-charts page mirroring `index.html`'s patterns.

**Tech Stack:** Python 3 stdlib (`http.server`), NumPy/pandas, the built `optimize/l2/` package, the existing `indicators.library`/`presets` modules, lightweight-charts@4.1.3 (already vendored by `index.html`), pytest.

## Global Constraints

- **L1 frozen / golden.** No edits to `engine.py`, `optimize/fast_engine.py`, `optimize/core.py`, `indicators/*`, or the built `optimize/l2/{l1_runner,dataset,engine,metrics}.py`. `cd /mnt/data/projects/trading/subprojects/Parametric-Indicators && python3 perf/check_golden.py` must print **6/6 MATCH** after every task.
- **`/api/backtest` and `frontend/index.html` are untouched** (normal backtest stays ~234 ms).
- **L1 base fixed** to the lean 4h champion via `run_l1("4h")`; tf is always `"4h"`.
- **Focused L2-levers only** in the form/contract: `indicators` (subset+params+mode), `k`, `gate_pct`, `sl_soft`, `sl_hard`, `tp`, `dd_limit`, `cooldown`, `flip`, `ind_1min`. No window/retrace/wait/split/veto_as_flip.
- **No silent dead controls; no optimizer launch** (that is #237).
- **Times are epoch seconds (UTC)**, matching the existing payload series shape `{time, value}` / `{time,open,high,low,close}`.
- **L2 profiles** persist to `profiles/l2_profiles.json`, separate from `profiles/user_profiles.json`.
- **Commit only by explicit path** (never `git add -A`/`.`); never stage repo-root secrets or pre-existing modified files. Branch `dev`.
- All run commands assume cwd = `/mnt/data/projects/trading/subprojects/Parametric-Indicators`.

---

### Task 1: `payload.py` — L1 cache + `build_l2_payload`

**Files:**
- Create: `optimize/l2/payload.py`
- Test: `optimize/l2/test_payload.py`

**Interfaces:**
- Consumes (built): `l1_runner.run_l1(tf) -> L1Result` (fields `df_dec, ledger, dropped_signals, state_timeline, sig_int`); `engine.run_l2(l1, l2_params) -> L2Result` (`ledger` trades have `entry_idx, entry_time, entry_price, direction, exit_time, exit_price, exit_reason, pnl, l2_dir_vs_box`); `metrics.score(l2) -> dict`, `metrics.combined(l1, l2) -> dict`; `dataset.build_dataset(l1) -> DroppedSignalSet(n_veto, n_vol_gate, __len__, flat_candidates())`.
- Produces: `get_l1(tf="4h") -> L1Result` (cached); `build_l2_payload(l2_params: dict, tf: str = "4h") -> dict` with keys `meta, candles, l1_spans, dropped, l2_trades, l2_equity, combined_equity, l1_equity`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_payload.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import payload, l1_runner, engine, metrics


PERMISSIVE = dict(sl_soft=149.8, sl_hard=167.1, tp=120.2, gate_pct=0.0, dd_limit=0.0,
                  cooldown=0, flip=False, k=1, ind_1min=False, indicators=[])


def test_get_l1_caches_same_object():
    a = payload.get_l1("4h")
    b = payload.get_l1("4h")
    assert a is b                      # cached — no second ~38s run


def test_build_l2_payload_keys_and_summary_match_metrics():
    p = payload.build_l2_payload(PERMISSIVE, "4h")
    for key in ("meta", "candles", "l1_spans", "dropped", "l2_trades",
                "l2_equity", "combined_equity", "l1_equity"):
        assert key in p, f"missing {key}"

    # summary blocks equal the metrics functions on the same run
    l1 = payload.get_l1("4h")
    res = engine.run_l2(l1, PERMISSIVE)
    assert p["meta"]["summary"]["l2"] == metrics.score(res)
    assert p["meta"]["summary"]["combined"] == metrics.combined(l1, res)
    assert isinstance(p["meta"]["run_ms"], int)

    # L1 context block
    assert p["meta"]["l1"]["n_trades"] == len(l1.ledger)
    assert p["meta"]["l1"]["dropped"] == len(l1.dropped_signals)

    # series sanity
    assert len(p["candles"]) == len(l1.df_dec)
    assert p["meta"]["l1"]["dropped"] == len(p["dropped"])
    assert all(t["l2_dir_vs_box"] in ("agree", "oppose") for t in p["l2_trades"])
    assert all(set(c) == {"time", "open", "high", "low", "close"} for c in p["candles"][:3])


def test_l2_trades_carry_computed_sl_tp_lines():
    p = payload.build_l2_payload(PERMISSIVE, "4h")
    if p["l2_trades"]:
        t = p["l2_trades"][0]
        for k in ("sl_soft_line", "sl_hard_line", "tp_hard_line"):
            assert k in t
        # long: tp above entry, sl below; short: mirrored
        if t["direction"] == "long":
            assert t["tp_hard_line"] > t["entry_price"] > t["sl_hard_line"]
        else:
            assert t["tp_hard_line"] < t["entry_price"] < t["sl_hard_line"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_payload.py -v`
Expected: FAIL — `ImportError: cannot import name 'payload'`.

- [ ] **Step 3: Write `payload.py`**

```python
# optimize/l2/payload.py
"""L2 dashboard orchestrator — the L2 analogue of strategy.build_payload. Runs the CACHED frozen L1
once per process, applies an L2 profile via the built run_l2, scores it (standalone + combined
guardrail), and serializes everything the l2.html charts need. Pure (no HTTP). Also: L2-profile store."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import l1_runner, engine, metrics, dataset        # noqa: E402

_L2_PROFILES = _PI / "profiles" / "l2_profiles.json"
_l1_cache: dict = {}


def get_l1(tf: str = "4h"):
    """Run the frozen lean L1 once per process; cache by timeframe (first call ~38s)."""
    if tf not in _l1_cache:
        _l1_cache[tf] = l1_runner.run_l1(tf)
    return _l1_cache[tf]


def _epoch(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


def _spans(state_timeline: np.ndarray, dec_dates: np.ndarray) -> list[dict]:
    """Contiguous True runs of the L1 in-position timeline -> [{from, to}] in epoch seconds."""
    out = []
    n = len(state_timeline)
    i = 0
    while i < n:
        if state_timeline[i]:
            j = i
            while j + 1 < n and state_timeline[j + 1]:
                j += 1
            out.append({"from": _epoch(dec_dates[i]), "to": _epoch(dec_dates[j])})
            i = j + 1
        else:
            i += 1
    return out


def _equity(trades: list[dict]) -> list[dict]:
    """Cumulative equity points at each trade's exit_time (sorted)."""
    pts = sorted(((_epoch(t["exit_time"]), float(t["pnl"])) for t in trades), key=lambda x: x[0])
    out, cum = [], 0.0
    for ts, pnl in pts:
        cum += pnl
        out.append({"time": ts, "value": round(cum, 2)})
    return out


def _l2_trade_rows(trades: list[dict], l2_params: dict) -> list[dict]:
    """Serialize L2 trades + compute SL/TP lines from entry_price ± params (fast_backtest trades do
    not carry the lines; the slow engine does — we reconstruct them deterministically)."""
    ss = float(l2_params["sl_soft"]); sh = float(l2_params["sl_hard"]); tp = float(l2_params["tp"])
    rows = []
    for t in trades:
        ep = float(t["entry_price"])
        is_long = t["direction"] == "long"
        rows.append({
            "entry_time": _epoch(t["entry_time"]), "exit_time": _epoch(t["exit_time"]),
            "direction": t["direction"], "entry_price": ep, "exit_price": float(t["exit_price"]),
            "sl_soft_line": ep - ss if is_long else ep + ss,
            "sl_hard_line": ep - sh if is_long else ep + sh,
            "tp_hard_line": ep + tp if is_long else ep - tp,
            "exit_reason": t["exit_reason"], "pnl": round(float(t["pnl"]), 2),
            "l2_dir_vs_box": t.get("l2_dir_vs_box", "agree"),
        })
    return rows


def build_l2_payload(l2_params: dict, tf: str = "4h") -> dict:
    t0 = time.time()
    l1 = get_l1(tf)
    res = engine.run_l2(l1, l2_params)
    ds = dataset.build_dataset(l1)
    dec_dates = l1.df_dec["Date"].to_numpy()

    candles = [{"time": _epoch(d), "open": float(o), "high": float(h), "low": float(lo),
                "close": float(c)}
               for d, o, h, lo, c in zip(dec_dates, l1.df_dec["Open"], l1.df_dec["High"],
                                         l1.df_dec["Low"], l1.df_dec["Close"])]
    dropped = [{"time": _epoch(d["ts"]), "reason": d["reason"], "box_dir": d["box_dir"]}
               for d in l1.dropped_signals]

    meta = {"summary": {"l2": metrics.score(res), "combined": metrics.combined(l1, res)},
            "l1": {"n_trades": len(l1.ledger),
                   "pnl": round(sum(t["pnl"] for t in l1.ledger), 2),
                   "dropped": len(ds), "veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                   "flat_candidates": len(ds.flat_candidates())},
            "params": dict(l2_params, timeframe=tf),
            "run_ms": round((time.time() - t0) * 1000)}

    return {"meta": meta, "candles": candles,
            "l1_spans": _spans(l1.state_timeline, dec_dates),
            "dropped": dropped,
            "l2_trades": _l2_trade_rows(res.ledger, l2_params),
            "l2_equity": _equity(res.ledger),
            "combined_equity": _equity(list(l1.ledger) + list(res.ledger)),
            "l1_equity": _equity(l1.ledger)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest optimize/l2/test_payload.py -v`
Expected: 3 PASS (first run ~40 s for the L1 cache fill, then fast).

- [ ] **Step 5: Golden gate**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH.

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/test_payload.py
git commit -m "feat(l2): payload orchestrator — cached L1 + build_l2_payload chart serialization

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `payload.py` — L2-profile store + `l2_config`

**Files:**
- Modify: `optimize/l2/payload.py` (append functions)
- Test: `optimize/l2/test_payload_profiles.py`

**Interfaces:**
- Consumes: `get_l1` + `dataset.build_dataset` (Task 1); `indicators.library.schema()`.
- Produces: `load_l2_profiles() -> dict`; `save_l2_profile(name: str, preset: dict) -> dict`; `l2_config() -> dict` with keys `indicator_schema, l1, profiles`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_payload_profiles.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import payload


def test_save_and_load_l2_profile_roundtrip():
    name = "_pytest_tmp_profile"
    preset = dict(sl_soft=120.0, sl_hard=140.0, tp=100.0, gate_pct=50.0, dd_limit=0.0,
                  cooldown=0, flip=True, k=1, ind_1min=False, indicators=[])
    try:
        profs = payload.save_l2_profile(name, preset)
        assert name in profs
        assert payload.load_l2_profiles()[name]["flip"] is True
    finally:
        # cleanup: drop the temp profile
        all_p = payload.load_l2_profiles()
        all_p.pop(name, None)
        payload._L2_PROFILES.write_text(__import__("json").dumps(all_p, indent=1))


def test_save_l2_profile_requires_name():
    import pytest
    with pytest.raises(ValueError):
        payload.save_l2_profile("  ", {})


def test_l2_config_has_schema_l1_and_profiles():
    c = payload.l2_config()
    assert "indicator_schema" in c and isinstance(c["indicator_schema"], (list, dict))
    assert "profiles" in c and isinstance(c["profiles"], dict)
    assert set(("dropped", "veto", "vol_gate", "flat_candidates", "n_trades")).issubset(c["l1"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_payload_profiles.py -v`
Expected: FAIL — `AttributeError: module 'optimize.l2.payload' has no attribute 'save_l2_profile'`.

- [ ] **Step 3: Append to `payload.py`**

```python
# --- L2-profile store (mirrors presets.load_user_profiles/save_user_profile) ------------------------
def load_l2_profiles() -> dict:
    if not _L2_PROFILES.exists():
        return {}
    try:
        d = json.loads(_L2_PROFILES.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_l2_profile(name: str, preset: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("L2 profile name is required")
    profs = load_l2_profiles()
    profs[name] = preset
    _L2_PROFILES.parent.mkdir(parents=True, exist_ok=True)
    _L2_PROFILES.write_text(json.dumps(profs, indent=1))
    return profs


def l2_config(tf: str = "4h") -> dict:
    """Drives the L2 form: indicator schema, the fixed-L1 summary, and saved L2 profiles."""
    from indicators import library
    l1 = get_l1(tf)
    ds = dataset.build_dataset(l1)
    return {"indicator_schema": library.schema(),
            "l1": {"label": "lean 4h champion (frozen)", "n_trades": len(l1.ledger),
                   "dropped": len(ds), "veto": ds.n_veto, "vol_gate": ds.n_vol_gate,
                   "flat_candidates": len(ds.flat_candidates())},
            "profiles": load_l2_profiles()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest optimize/l2/test_payload_profiles.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Golden gate + commit**

```bash
python3 perf/check_golden.py        # expect 6/6 MATCH
git add optimize/l2/payload.py optimize/l2/test_payload_profiles.py
git commit -m "feat(l2): L2-profile store (l2_profiles.json) + l2_config for the dashboard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `server.py` — three L2 routes

**Files:**
- Modify: `server.py` (add one `GET` branch in `do_GET`, two `POST` branches in `do_POST`)
- Test: `optimize/l2/test_server_routes.py`

**Interfaces:**
- Consumes: `optimize.l2.payload.{build_l2_payload, save_l2_profile, l2_config}` (Tasks 1-2).
- Produces: HTTP routes `GET /api/l2_config`, `POST /api/l2_backtest`, `POST /api/l2_profiles`. The existing static handler already serves `frontend/l2.html` (no route needed).

- [ ] **Step 1: Write the failing test** (live server on an ephemeral port; only the fast routes — `/api/l2_backtest` is covered by Task 1's `build_l2_payload` test + the manual smoke, to avoid the ~38 s L1 fill in the suite)

```python
# optimize/l2/test_server_routes.py
import json
import sys
import threading
import urllib.request
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_server_routes.py -v`
Expected: FAIL — `/api/l2_config` returns 404 ("not found"), so `json.loads` / asserts fail.

- [ ] **Step 3: Add the GET route** — in `server.py` `do_GET`, immediately after the `/api/config` block (after line 76, before the `name = "index.html" ...` static fallback), insert:

```python
        if path == "/api/l2_config":
            from optimize.l2 import payload as l2p
            return self._send(200, json.dumps(l2p.l2_config()))
```

- [ ] **Step 4: Add the two POST routes** — in `server.py` `do_POST`, immediately after the `/api/profiles` block (after line 101), insert:

```python
        if path == "/api/l2_profiles":
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                from optimize.l2 import payload as l2p
                profs = l2p.save_l2_profile(body.get("name"), body.get("preset") or {})
                print(f"saved L2 profile '{body.get('name')}' -> profiles/l2_profiles.json", flush=True)
                return self._send(200, json.dumps({"ok": True, "profiles": profs}))
            except ValueError as e:
                return self._send(400, json.dumps({"error": str(e)}))
            except Exception as e:
                return self._send(500, json.dumps({"error": f"Save failed: {e}"}))
        if path == "/api/l2_backtest":
            try:
                n = int(self.headers.get("Content-Length", 0))
                l2_params = json.loads(self.rfile.read(n) or b"{}")
                from optimize.l2 import payload as l2p
                payload_out = l2p.build_l2_payload(l2_params, "4h")
                self._send(200, json.dumps(payload_out))
                s = payload_out["meta"]["summary"]
                print(f"l2_backtest {l2_params} -> L2 P/L ${s['l2']['pnl']:,.0f} "
                      f"n={s['l2']['n']} combined DD ${s['combined']['max_dd']:,.0f} "
                      f"({payload_out['meta']['run_ms']}ms)", flush=True)
                return
            except Exception as e:
                import traceback; traceback.print_exc()
                return self._send(500, json.dumps({"error": f"L2 backtest failed: {e}"}))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest optimize/l2/test_server_routes.py -v`
Expected: 2 PASS.

- [ ] **Step 6: Golden gate + commit**

```bash
python3 perf/check_golden.py        # expect 6/6 MATCH (server.py routes are additive)
git add server.py optimize/l2/test_server_routes.py
git commit -m "feat(l2): server routes — /api/l2_config, /api/l2_backtest, /api/l2_profiles

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `frontend/l2.html` — the page

**Files:**
- Create: `frontend/l2.html`
- Reference (read, copy patterns): `frontend/index.html` — chart setup `mk()`/theme (~lines 215-235), indicator-panel builder `buildIndicatorPanel` (~lines 388-470), `indicatorSpecs()` (collects `indicators` array), marker/line drawing (~lines 257-318).
- Test: none new (vanilla JS, no framework — matches the existing dashboard; covered by Tasks 1-3 + manual smoke).

**Interfaces:**
- Consumes: `GET /api/l2_config`, `POST /api/l2_backtest`, `POST /api/l2_profiles` (Task 3); the payload shape from Task 1.

This task builds one self-contained HTML page. Reuse `index.html`'s scaffolding rather than reinventing it; the new, L2-specific JS is given in full below.

- [ ] **Step 1: Scaffold the page** — create `frontend/l2.html` with: the `<head>` + `<style>` copied from `index.html` (same dark theme, `.panel` class, the lightweight-charts `<script src>` tag); a left settings panel containing **only** the L2 levers — the indicator panel mount point `<div id="indpanel">`, plus inputs `sl_soft, sl_hard, tp, gate_pct, dd_limit, cooldown` (number), `flip` (select true/false), `k` (number), `ind_1min` (checkbox); a saved-profile `<select id="l2profile">`; buttons `Run L2`, `Save L2 profile`; a status line `<div id="status">`. The right side: a metric-cards `<div id="cards">`, a price chart `<div id="price">`, an equity chart `<div id="equity">`, an L2 ledger `<table id="l2trades">`, and a dropped-signal `<table id="dropped">`. Add a back-link `<a href="/">← main dashboard</a>`.

- [ ] **Step 2: Config load + form build** — add this script (reuse `buildIndicatorPanel`/`indicatorSpecs` copied from `index.html`):

```javascript
let L1INFO = null;
async function loadConfig() {
  const c = await (await fetch('/api/l2_config')).json();
  buildIndicatorPanel(c.indicator_schema);          // copied from index.html
  L1INFO = c.l1;
  status(`L1 = ${c.l1.label}: ${c.l1.n_trades} trades, ${c.l1.dropped} dropped `
       + `(${c.l1.veto} veto + ${c.l1.vol_gate} vol-gate), ${c.l1.flat_candidates} flat candidates`);
  const sel = document.getElementById('l2profile');
  sel.innerHTML = '<option value="">— pick a saved L2 profile —</option>'
    + Object.keys(c.profiles).map(n => `<option value="${n}">${n}</option>`).join('');
  sel.onchange = () => { const p = c.profiles[sel.value]; if (p) setForm(p); };
}
function status(msg) { document.getElementById('status').textContent = msg; }
```

- [ ] **Step 3: Param collection + Run** — add:

```javascript
function l2params() {
  return {
    indicators: indicatorSpecs(),                   // copied from index.html
    k: +document.getElementById('k').value || 1,
    gate_pct: +document.getElementById('gate_pct').value,
    sl_soft: +document.getElementById('sl_soft').value,
    sl_hard: +document.getElementById('sl_hard').value,
    tp: +document.getElementById('tp').value,
    dd_limit: +document.getElementById('dd_limit').value,
    cooldown: +document.getElementById('cooldown').value,
    flip: document.getElementById('flip').value === 'true',
    ind_1min: document.getElementById('ind_1min').checked,
  };
}
function setForm(p) {
  ['k','gate_pct','sl_soft','sl_hard','tp','dd_limit','cooldown'].forEach(id => {
    if (p[id] != null) document.getElementById(id).value = p[id]; });
  document.getElementById('flip').value = String(!!p.flip);
  document.getElementById('ind_1min').checked = !!p.ind_1min;
  if (p.indicators) setIndicatorPanel(p.indicators);   // copied from index.html (setForm's indicator part)
}
async function run() {
  status('computing L1 (first run, ~40s)… then applying L2…');
  const r = await fetch('/api/l2_backtest', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(l2params())});
  const D = await r.json();
  if (D.error) { status('error: ' + D.error); return; }
  render(D);
  status(`done in ${D.meta.run_ms}ms`);
}
```

- [ ] **Step 4: Render** — add the full render (charts + overlays + cards + tables):

```javascript
let priceC, candle, mkrS, ssS, shS, tpS, l1band, eqC, combLine, l1Line;
function initCharts() {
  priceC = LightweightCharts.createChart(document.getElementById('price'),
    {height: 420, layout: {background: {color: '#0e0e12'}, textColor: '#ccc'},
     grid: {vertLines: {color: '#1c1c24'}, horzLines: {color: '#1c1c24'}}});
  l1band = priceC.addAreaSeries({topColor: 'rgba(120,120,140,.18)', bottomColor: 'rgba(120,120,140,.04)',
                                 lineColor: 'rgba(120,120,140,.35)', priceLineVisible: false, lastValueVisible: false});
  candle = priceC.addCandlestickSeries();
  tpS = priceC.addLineSeries({color: '#26a69a', lineWidth: 1, priceLineVisible: false, lastValueVisible: false});
  shS = priceC.addLineSeries({color: '#ef5350', lineWidth: 1, priceLineVisible: false, lastValueVisible: false});
  ssS = priceC.addLineSeries({color: '#ef9a9a', lineWidth: 1, priceLineVisible: false, lastValueVisible: false});
  mkrS = candle;
  eqC = LightweightCharts.createChart(document.getElementById('equity'),
    {height: 200, layout: {background: {color: '#0e0e12'}, textColor: '#ccc'}});
  combLine = eqC.addLineSeries({color: '#42a5f5', lineWidth: 2, title: 'L1+L2'});
  l1Line = eqC.addLineSeries({color: '#9e9e9e', lineWidth: 1, title: 'L1 only'});
}
function render(D) {
  const S = D.meta.summary, L = S.l2, C = S.combined;
  const card = (t, v) => `<div class="card"><div class="k">${t}</div><div class="v">${v}</div></div>`;
  const ddColor = C.dd_not_worse ? '#26a69a' : '#ef5350';
  document.getElementById('cards').innerHTML =
      card('L2 P/L', `$${L.pnl.toLocaleString()}`) + card('L2 maxDD', `$${L.max_dd.toLocaleString()}`)
    + card('L2 trades', L.n) + card('L2 win%', L.win) + card('L1-entry exits', L.n_l1_entry_exits)
    + card('Combined P/L', `$${C.pnl.toLocaleString()}`)
    + `<div class="card"><div class="k">Combined maxDD (L1-only ${C.l1_only_dd.toLocaleString()})</div>`
    + `<div class="v" style="color:${ddColor}">$${C.max_dd.toLocaleString()} `
    + `${C.dd_not_worse ? 'OK' : 'WORSE'}</div></div>`;

  candle.setData(D.candles);
  // L1 in-position shading: a step band that is high during spans, 0 elsewhere (visual mask)
  const hi = Math.max(...D.candles.map(c => c.high));
  const band = [];
  D.candles.forEach(c => {
    const inpos = D.l1_spans.some(s => c.time >= s.from && c.time <= s.to);
    band.push({time: c.time, value: inpos ? hi : 0});
  });
  l1band.setData(band);

  // dropped-signal markers (veto orange / vol-gate blue) + L2 trade markers (agree solid / oppose hollow)
  const mks = [];
  D.dropped.forEach(d => mks.push({time: d.time, position: 'aboveBar',
    color: d.reason === 'veto' ? '#ffa726' : '#42a5f5', shape: 'circle',
    text: d.reason === 'veto' ? 'v' : 'g'}));
  D.l2_trades.forEach(t => {
    const opp = t.l2_dir_vs_box === 'oppose';
    mks.push({time: t.entry_time, position: 'belowBar',
      color: t.direction === 'long' ? '#26a69a' : '#ef5350',
      shape: opp ? 'arrowDown' : 'arrowUp', text: opp ? 'L2!' : 'L2'});
    mks.push({time: t.exit_time, position: 'inBar',
      color: t.exit_reason === 'L1-entry' ? '#ab47bc' : (t.pnl > 0 ? '#26a69a' : '#ef5350'),
      shape: 'circle', text: t.exit_reason === 'L1-entry' ? 'X' : ''});
  });
  mks.sort((a, b) => a.time - b.time);
  mkrS.setMarkers(mks);

  // SL/TP lines per L2 trade (segment from entry to exit)
  const tpD = [], shD = [], ssD = [];
  D.l2_trades.forEach(t => {
    tpD.push({time: t.entry_time, value: t.tp_hard_line}, {time: t.exit_time, value: t.tp_hard_line});
    shD.push({time: t.entry_time, value: t.sl_hard_line}, {time: t.exit_time, value: t.sl_hard_line});
    ssD.push({time: t.entry_time, value: t.sl_soft_line}, {time: t.exit_time, value: t.sl_soft_line});
  });
  const dedup = a => { const m = new Map(); a.forEach(p => m.set(p.time, p)); return [...m.values()].sort((x,y)=>x.time-y.time); };
  tpS.setData(dedup(tpD)); shS.setData(dedup(shD)); ssS.setData(dedup(ssD));

  combLine.setData(D.combined_equity);
  l1Line.setData(D.l1_equity);

  document.getElementById('l2trades').innerHTML =
    '<thead><tr><th>entry</th><th>exit</th><th>dir</th><th>vs box</th><th>reason</th><th>P/L</th></tr></thead><tbody>'
    + D.l2_trades.map(t => `<tr><td>${new Date(t.entry_time*1000).toISOString().slice(0,16)}</td>`
      + `<td>${new Date(t.exit_time*1000).toISOString().slice(0,16)}</td><td>${t.direction}</td>`
      + `<td>${t.l2_dir_vs_box}</td><td>${t.exit_reason}</td>`
      + `<td style="color:${t.pnl>0?'#26a69a':'#ef5350'}">$${t.pnl.toLocaleString()}</td></tr>`).join('')
    + '</tbody>';
  document.getElementById('dropped').innerHTML =
    '<thead><tr><th>time</th><th>reason</th><th>box dir</th></tr></thead><tbody>'
    + D.dropped.map(d => `<tr><td>${new Date(d.time*1000).toISOString().slice(0,16)}</td>`
      + `<td>${d.reason}</td><td>${d.box_dir}</td></tr>`).join('') + '</tbody>';
}
```

- [ ] **Step 5: Save-profile + wire-up** — add:

```javascript
async function saveProfile() {
  const name = prompt('Save L2 profile as:');
  if (!name) return;
  const r = await fetch('/api/l2_profiles', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, preset: l2params()})});
  const d = await r.json();
  if (d.error) { status('save error: ' + d.error); return; }
  const sel = document.getElementById('l2profile');
  sel.innerHTML = '<option value="">— pick a saved L2 profile —</option>'
    + Object.keys(d.profiles).map(n => `<option value="${n}">${n}</option>`).join('');
  status(`saved L2 profile "${name}"`);
}
document.getElementById('runbtn').onclick = run;
document.getElementById('savebtn').onclick = saveProfile;
initCharts();
loadConfig();
```

- [ ] **Step 6: Manual smoke**

Run (background): `python3 server.py --port 8200`
Then: open `http://localhost:8200/l2.html`. Verify: the L1 summary line shows `255 trades, 492 dropped (286 veto + 206 vol-gate), 410 flat candidates`; click **Run L2** with the default (empty-indicators) form → after ~40 s the cards populate (L2 n≈349, P/L ≈ −$64,299, 52 L1-entry exits; Combined maxDD ≈ $50,574 shown WORSE/red), the price chart shows shading + orange/blue dropped markers + L2 arrows + a purple X for force-closes, and both equity lines draw. Click **Save L2 profile**, name it, confirm it appears in the dropdown. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add frontend/l2.html
git commit -m "feat(l2): l2.html dashboard-inside-dashboard — form, full-context charts, ledger, save

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Docs + tracker + final commit

**Files:**
- Create: `optimize/l2/UPDATE_l2_dashboard.md`
- Modify: `docs/superpowers/specs/2026-06-18-l2-dashboard-design.md:7` (status → built)
- Modify: `optimize/l2/UPDATE_l2_backtester.md` ("Next" line → dashboard done, optimizer next)

- [ ] **Step 1: Write `UPDATE_l2_dashboard.md`** with a Mermaid architecture diagram (mirror spec §3), a module/route table, the manual-smoke figures captured in Task 4 Step 6, and a "Next: optimizer #237 (prefix l2v1)" line. (Visuals Mermaid, never ASCII.)

- [ ] **Step 2: Update spec status** — change `docs/superpowers/specs/2026-06-18-l2-dashboard-design.md` line 7 to:
`  status: BUILT (2026-06-18) — next = optimizer (#237)`

- [ ] **Step 3: Full L2 suite + golden**

Run: `python3 -m pytest optimize/l2/ -q && python3 perf/check_golden.py`
Expected: all L2 tests PASS; golden 6/6 MATCH.

- [ ] **Step 4: Commit**

```bash
git add optimize/l2/UPDATE_l2_dashboard.md docs/superpowers/specs/2026-06-18-l2-dashboard-design.md optimize/l2/UPDATE_l2_backtester.md
git commit -m "docs(l2): dashboard build report; spec status -> built

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Spec coverage self-check

- §2 Q1 separate page + `/api/l2_backtest` → Tasks 3 (route) + 4 (page). ✅
- §2 Q2 fixed lean 4h → `get_l1("4h")` cache, tf hardcoded in route (Tasks 1, 3). ✅
- §2 Q3 focused form → Task 4 form + `l2params()` (only the 10 levers). ✅
- §2 Q4 full-context charts (L1 shading, dropped-by-reason, agree/oppose, force-close flag, combined-vs-L1 equity) → Task 4 `render`. ✅
- §2 Q5 manual + save, no optimizer → Tasks 2/3/4 (profiles), no launch anywhere. ✅
- §3 architecture (`payload.py` orchestrator + cache + thin routes) → Tasks 1-3. ✅
- §4 components 1-3 → Tasks 1-2 (payload), 3 (server), 4 (l2.html). ✅
- §5 endpoint contracts (request levers, response keys) → Task 1 payload keys + Task 3 routes + Task 4 `l2params`. ✅
- §6 visualization → Task 4. ✅
- §7 caching (run-once per process) → Task 1 `get_l1` + identity test. ✅
- §8 edge cases: golden (every task), no dead controls (Q3 form), empty result (render handles n=0), first-run latency (status message), profile isolation (`l2_profiles.json`), epoch serialization (`_epoch`) → Tasks 1-4. ✅
- §9 testing: golden 6/6; `build_l2_payload` keys + summary==metrics; cache identity; profile roundtrip; series sanity; frontend manual smoke → Tasks 1-4. ✅
- §10 build order + out-of-scope (optimizer/selectable-L1/speed) → task order; explicitly excluded. ✅
