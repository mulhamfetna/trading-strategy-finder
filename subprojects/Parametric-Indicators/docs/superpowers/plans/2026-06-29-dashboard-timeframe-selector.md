# Dashboard timeframe selector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a timeframe dropdown (6 decision TFs) to the dashboard so the causal backtest runs at the chosen TF, loading that TF's deployed champion as the L1 default.

**Architecture:** Backend run path is already TF-parametric. Add (1) a per-TF L1 default (4h = lean champion unchanged; others from `wsh4_champions_full.json[tf]` via `presets._preset`), (2) a `?tf=` param on `/api/combined_config`, (3) a frontend `<select>` that re-fetches the per-TF config on change and threads `tf` into the three run POSTs.

**Tech Stack:** Python (stdlib http.server), vanilla JS. No new dependencies.

## Global Constraints

- **Back-compat / golden:** `l1_default_params("4h")` and `/api/combined_config` with no `tf` (or `tf=4h`) must be **byte-identical to today**; golden `perf/check_golden.py` must stay **6/6** (engine untouched).
- **TF set:** exactly `4h, 2h, 1h, 15m, 5m, 2m` (default `4h`). Unknown TF → HTTP 400.
- **L2 stays permissive for non-4h** (L2 champions are 4h-only). No engine change, no per-TF profile filtering, no `1m`.
- Run from `subprojects/Parametric-Indicators`. Python `python3`. No secrets in commits.

---

### Task 1: Per-TF L1 default (`payload.l1_default_params`)

**Files:**
- Modify: `optimize/l2/payload.py` (add `_TF_SET`, `_WSH4_CHAMPS`, `_champion_layer_params`, extend `l1_default_params`)
- Modify: `optimize/l2/optimize.py` (`_l1_params_from_champion` delegates to the new helper — DRY, no behavior change)
- Test: `optimize/l2/test_tf_defaults.py` (create)

**Interfaces:**
- Produces: `payload._champion_layer_params(tf: str, entry: dict) -> dict` (engine-ready L1 params from a
  `{box, indicators}` champion entry); `payload.l1_default_params(tf)` now valid for all 6 TFs;
  `payload._TF_SET = ("4h","2h","1h","15m","5m","2m")`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_tf_defaults.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import payload
from optimize.l2 import l1_runner

_W = Path(__file__).resolve().parents[1] / "results" / "wsh4_champions_full.json"


def test_4h_default_unchanged():
    # 4h stays the lean champion — byte-identical to the pre-change behavior
    assert payload.l1_default_params("4h") == payload.validate_layer_params(l1_runner._lean_params("4h"))


def test_per_tf_default_matches_wsh4_champion():
    champs = json.loads(_W.read_text())
    for tf in ("2h", "15m", "2m"):
        p = payload.l1_default_params(tf)
        assert p["sl_soft"] == float(champs[tf]["box"]["sl_soft"])      # box → params
        assert p["tp"] == float(champs[tf]["box"]["tp"])
        assert p["ind_1min"] is True                                   # L1 champions run on the 1-min frame
        assert isinstance(p["indicators"], list)


def test_tf_set_is_the_six_decision_tfs():
    assert payload._TF_SET == ("4h", "2h", "1h", "15m", "5m", "2m")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_tf_defaults.py -q`
Expected: FAIL — `_TF_SET` missing / `l1_default_params("2h")` raises `SystemExit` (lean champion is 4h-only).

- [ ] **Step 3: Implement in `optimize/l2/payload.py`**

Add near the other module constants (after the imports):

```python
_TF_SET = ("4h", "2h", "1h", "15m", "5m", "2m")          # the decision TFs (1m excluded — not in the champion sweep)
_WSH4_CHAMPS = Path(__file__).resolve().parents[1] / "results" / "wsh4_champions_full.json"


def _champion_layer_params(tf: str, entry: dict) -> dict:
    """Engine-ready L1 layer params from a {box, indicators} champion entry. L1 champions run on the
    1-minute frame, so ind_1min is forced True (mirrors optimize.optimize._l1_params_from_champion)."""
    import presets                                          # noqa: E402 (top-level module on sys.path)
    lp = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    lp["ind_1min"] = True
    return validate_layer_params(lp)
```

Then replace `l1_default_params`:

```python
def l1_default_params(tf: str = "4h") -> dict:
    """The 'best L1' preset for a TF, in the layer-param schema the forms speak. 4h = the frozen lean
    champion (unchanged); other TFs = that TF's deployed champion from wsh4_champions_full.json."""
    if tf == "4h":
        return validate_layer_params(l1_runner._lean_params(tf))
    champs = json.loads(_WSH4_CHAMPS.read_text())
    if tf not in champs:
        raise L2ParamError(f"no L1 champion for tf={tf!r} (known: {sorted(champs)})")
    return _champion_layer_params(tf, champs[tf])
```

(Confirm `json` and `Path` are already imported in payload.py — they are.)

- [ ] **Step 4: DRY the optimizer's champion loader to the shared helper**

In `optimize/l2/optimize.py`, replace the body of `_l1_params_from_champion` after `rec = json.loads(...)`:

```python
def _l1_params_from_champion(path: str, tf: str) -> dict:
    """Build an engine-ready L1 layer-params dict from a champion json (box + indicators dict) so L2 is
    scored on THIS L1's residuals instead of the frozen production L1."""
    rec = json.loads(Path(path).read_text())
    c = rec.get(tf, rec)                                    # accept {tf:{...}} or a bare champion record
    return payload._champion_layer_params(tf, c)
```

- [ ] **Step 5: Run tests (new + the optimizer's existing champion path)**

Run: `python3 -m pytest optimize/l2/test_tf_defaults.py optimize/l2/test_optimize.py -q -k "tf_default or per_tf or tf_set or champion or export"`
Expected: PASS (the `_l1_params_from_champion` refactor is behavior-preserving — same params out).

- [ ] **Step 6: Golden gate**

Run: `python3 perf/check_golden.py`
Expected: 6/6 MATCH (4h default unchanged; engine untouched).

- [ ] **Step 7: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/optimize.py optimize/l2/test_tf_defaults.py
git commit -m "feat(dashboard): per-TF L1 default (4h=lean unchanged; others from wsh4 champions)"
```

---

### Task 2: `/api/combined_config?tf=` (server)

**Files:**
- Modify: `server.py` (`do_GET` combined_config branch + query parse)
- Test: `optimize/l2/test_l2_server.py` (add a test)

**Interfaces:**
- Consumes: `payload.l1_default_params(tf)`, `payload._TF_SET` (Task 1).
- Produces: `GET /api/combined_config?tf=<tf>` → per-TF `l1_default` + label; default/absent/`4h` unchanged; bad tf → 400.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/l2/test_l2_server.py
def test_combined_config_per_tf():
    srv, port = _serve()
    try:
        import urllib.request, urllib.error
        base = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config").read())
        tf2h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?tf=2h").read())
        # no-tf == 4h (back-compat); 2h differs (its own champion); both carry the schema
        assert base["l1_default"]["sl_soft"] != tf2h["l1_default"]["sl_soft"] or base["l1_default"] != tf2h["l1_default"]
        assert "indicator_schema" in tf2h and tf2h["l1_default"]["ind_1min"] is True
        # bad tf → 400
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/combined_config?tf=1m")
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/l2/test_l2_server.py::test_combined_config_per_tf -q`
Expected: FAIL — `?tf=2h` returns the same as 4h (query ignored) and `tf=1m` doesn't 400.

- [ ] **Step 3: Implement in `server.py`**

In `do_GET`, the query is currently stripped (`path = self.path.split("?")[0]`). Add a parsed-query helper at
the top of `do_GET`:

```python
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
```

Replace the `combined_config` branch body with a TF-aware version:

```python
        if path == "/api/combined_config":
            from indicators import library
            tf = (q.get("tf", ["4h"])[0])
            if tf not in l2payload._TF_SET:
                return self._send(400, json.dumps({"error": f"unknown tf {tf!r}; known {list(l2payload._TF_SET)}"}))
            l1_label = "🍃 WS lean 4h champion" if tf == "4h" else f"🏆 WS champion {tf}"
            return self._send(200, json.dumps({
                "indicator_schema": library.schema(),
                "l1_default": l2payload.l1_default_params(tf),
                "l2_default": l2payload.l2_default_params(),
                "l1_profiles": l2payload.load_l1_profiles(),
                "l2_profiles": l2payload.load_l2_profiles(),
                "tf": tf,
                "l1_label": l1_label, "l2_label": "🔁 L2 (extend champion)"}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/l2/test_l2_server.py::test_combined_config_per_tf optimize/l2/test_l2_server.py::test_l2_routes_smoke -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add server.py optimize/l2/test_l2_server.py
git commit -m "feat(dashboard): /api/combined_config?tf= — per-TF defaults (no-tf == 4h, bad tf 400)"
```

---

### Task 3: TF selector + wiring (`frontend/dashboard.html`)

**Files:**
- Modify: `frontend/dashboard.html` (header select; `loadConfig(tf)` factor; `run()` POSTs; `collectES` tf)

**Interfaces:**
- Consumes: `GET /api/combined_config?tf=` (Task 2).
- Produces: `$('tf_select').value` is the single source of truth for the run TF.

- [ ] **Step 1: Add the TF select to the header**

In `frontend/dashboard.html`, inside `.hdr-right` (line ~36), **before** the Run button (`<button class="run" id="run">`), insert:

```html
    <label class="tfsel" title="decision timeframe — switches the L1 champion + the backtest frame">
      <select id="tf_select">
        <option value="4h" selected>4h</option><option value="2h">2h</option><option value="1h">1h</option>
        <option value="15m">15m</option><option value="5m">5m</option><option value="2m">2m</option>
      </select></label>
```

- [ ] **Step 2: Factor `loadConfig(tf)` and call it on TF change**

Replace the `try{ const r=await fetch('/api/combined_config'); … }` block in the init IIFE (line ~611) with a
call to a reusable `loadConfig`, and define `loadConfig` above the IIFE:

```javascript
async function loadConfig(tf){
  const r=await fetch('/api/combined_config?tf='+encodeURIComponent(tf)); if(!r.ok) throw new Error('config HTTP '+r.status);
  const c=await r.json();
  DB.buildPanel($('l1_indpanel'),c.indicator_schema,DB.markDirty);
  DB.buildPanel($('l2_indpanel'),c.indicator_schema,DB.markDirty);
  DB.buildPanel($('l2_es_indpanel'),c.indicator_schema,DB.markDirty);
  fillDropdown('l1',{[c.l1_label||'L1 champion']:c.l1_default, ...(c.l1_profiles||{})});
  fillDropdown('l2',{[c.l2_label||'L2 champion']:c.l2_default, ...(c.l2_profiles||{})});
  setLayer('l1',c.l1_default); setLayer('l2',c.l2_default);
  DB.mathify(document.querySelector('aside'));
}
```

Init block becomes:
```javascript
  try{
    await loadConfig($('tf_select').value);
    DB.markDirty(); DB.status('ready · best L1 + best L2 loaded · click Run');
  }catch(e){ DB.markDirty(); DB.showErr(`Cannot reach backend — start server.py then reload. (${e.message})`); }
```

And register the change handler (next to the other `aside`/control listeners, e.g. after the `['l1','l2'].forEach(...)` block):
```javascript
  $('tf_select').addEventListener('change',async()=>{ try{ await loadConfig($('tf_select').value);
    DB.markDirty(); DB.status('switched to '+$('tf_select').value+' — click Run'); }
    catch(e){ DB.showErr('config reload failed: '+e.message); } });
```

- [ ] **Step 3: Thread the selected TF into the three run POSTs**

In `run()` (line ~563), replace the three hardcoded `'4h'`:
```javascript
    const tf=$('tf_select').value;
    const [l1,l2,comb]=await Promise.all([
      grab(fetch('/api/backtest_causal', J({...l1lay, timeframe:tf}))),
      grab(fetch('/api/causal_backtest', J({l1:l1lay, l2:l2lay, tf, view:'l2'}))),
      grab(fetch('/api/causal_backtest', J({l1:l1lay, l2:l2lay, tf, view:'combined'}))),
    ]);
```

And in `collectES()` (line ~217) change the contributor `tf:'4h'` to follow the selected TF:
```javascript
function collectES(){ return {token:'ES', enabled:$('l2_es_enable').value==='true', tf:$('tf_select').value,
```

- [ ] **Step 4: JS parse check**

Run:
```bash
cd frontend && node -e "const fs=require('fs');const h=fs.readFileSync('dashboard.html','utf8');
const m=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)];let blk=m.map(x=>x[1]).join('\n').replace(/await /g,'').replace(/^const TH=DB.*/m,'const DB={TH:{},\$:()=>({value:\"4h\"}),specsOf:()=>[],applySpecsTo:()=>{},buildPanel:()=>{},markDirty:()=>{},markClean:()=>{},status:()=>{},showErr:()=>{},mathify:()=>{},dt:()=>{},toCSV:()=>{},downloadCSV:()=>{}};');
new Function(blk); console.log('JS parse OK');"
```
Expected: `JS parse OK`

- [ ] **Step 5: Live smoke (server + a 2h run)**

Run:
```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
(python3 server.py --port 8210 >/tmp/tfdash.log 2>&1 &) ; sleep 6
curl -s "http://localhost:8210/api/combined_config?tf=2h" | python3 -c "import sys,json;d=json.load(sys.stdin);print('cfg tf=2h ok, label=',d['l1_label'])"
curl -s -X POST http://localhost:8210/api/causal_backtest -H 'Content-Type: application/json' \
  -d "$(curl -s 'http://localhost:8210/api/combined_config?tf=2h' | python3 -c "import sys,json;c=json.load(sys.stdin);print(json.dumps({'l1':c['l1_default'],'l2':c['l2_default'],'tf':'2h','view':'l2'}))")" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('2h causal run trades=', d['meta'].get('n_trades', d['meta'].get('n')))"
pkill -f "server.py --port 8210"
```
Expected: prints the 2h label + a trade count (non-error).

- [ ] **Step 6: Commit**

```bash
git add frontend/dashboard.html
git commit -m "feat(dashboard): timeframe selector — re-fetch per-TF config on switch + thread tf into runs"
```

---

## Self-Review

**Spec coverage:** §4.1 per-TF L1 default → Task 1 (`_champion_layer_params` + `l1_default_params`; 4h unchanged; DRY `_l1_params_from_champion`). §4.2 `combined_config?tf` → Task 2 (query parse, 400 on bad, no-tf==4h). §4.3 frontend selector + re-fetch + run-POST threading + `collectES` tf → Task 3. §3 TF set → Task 1 `_TF_SET` + Task 2 validation. §6 testing → Task 1 (default-unchanged + per-TF + golden), Task 2 (server per-tf + 400 + back-compat), Task 3 (JS parse + live smoke). §7 out-of-scope respected (L2 permissive, no profile filter, no 1m, no engine change).

**Placeholder scan:** none — every step has real code/commands.

**Type consistency:** `_champion_layer_params(tf, entry) -> dict` defined in Task 1, consumed by Task 1's
`l1_default_params` and Task 1-step-4's `_l1_params_from_champion`. `_TF_SET` (Task 1) used in Task 2's
validation. `l1_default_params(tf)` (Task 1) consumed by Task 2's endpoint. `$('tf_select').value` is the
single TF source in Task 3 (config reload, run POSTs, collectES). `loadConfig(tf)` defined once, called by
init + the change handler.
