# Optimizer Control & Visualization Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A VPN-reachable, server-hosted dashboard to configure/launch/stop/pause the optimizer, watch live
trials + Pareto (via optuna-dashboard), pull full data as a download, and control/notify over Telegram.

**Architecture:** Hybrid. `optuna-dashboard` (official) renders all live graphs from the existing `wsh-pg`
Postgres. A thin FastAPI **control plane** + a **Telegram bot** both call ONE shared library `control.py`
that wraps `remote_wsi.sh` and reads Postgres. Everything binds to the server's **private/VPN IP only**.

**Tech Stack:** Python 3, FastAPI + uvicorn (control API + SSE), python-telegram-bot (long-polling),
optuna / optuna-dashboard, Pydantic, pytest. Frontend = one vanilla HTML file (no build) cloning the
existing dashboard patterns. Spec: `optimize/dashboard/SPEC_optimizer_dashboard.md`.

**Working dir for all paths:** `/mnt/data/projects/trading/subprojects/Parametric-Indicators/`
**Run tests with:** the project interpreter (`python3`), `pip install --break-system-packages` if needed.

---

## File structure (created/modified)

| File | Responsibility |
|---|---|
| `optimize/dashboard/control.py` | **The seam.** Pure functions: config/plan/start/stop/resume/status/logs/bundle. Only module touching `remote_wsi.sh` + Postgres. |
| `optimize/dashboard/app.py` | FastAPI app: REST + SSE + serves static UI. Thin delegators to `control.py`. |
| `optimize/dashboard/bot.py` | Telegram bot (long-poll). Notify loop + commands, allowlist-guarded. Calls `control.py`. |
| `optimize/dashboard/static/index.html` | Control UI (clone of `frontend/index.html` patterns). |
| `optimize/dashboard/run_dashboard.sh` | Launches optuna-dashboard + uvicorn + bot, bound to the private IP. |
| `optimize/dashboard/dashboard.env.example` | Documents env keys (real `dashboard.env` is gitignored). |
| `optimize/dashboard/test_control.py` | Unit tests for the seam (mock subprocess/DB). |
| `optimize/dashboard/test_app.py` | FastAPI TestClient tests. |
| `optimize/dashboard/test_bot.py` | Bot allowlist + command-dispatch tests. |
| `optimize/server/remote_wsi.sh` | **Modify:** accept `WSH_SAMPLER` / `WSH_ENGINE` (additive, default-off). |
| `requirements.txt` | **Modify:** add `fastapi`, `uvicorn`, `python-telegram-bot`, `optuna-dashboard`. |
| `.gitignore` | **Modify:** ignore `optimize/dashboard/dashboard.env` + `optimize/dashboard/bundles/`. |
| `optimize/dashboard/docker-compose.yml` | (P-F, later) compose for the whole dashboard. |

**Convention:** `control.py` returns plain dicts (JSON-serializable). It NEVER imports the scoring engine
(no golden impact). All shell calls go through one helper `_run_remote(args)` so they're mockable in tests.

---

## PHASE P-A — optuna-dashboard live on the server (visualization plane)

### Task A1: Add dashboard dependencies
**Files:** Modify `requirements.txt`

- [ ] **Step 1: Append deps**

Add these lines to `requirements.txt`:
```
fastapi
uvicorn[standard]
python-telegram-bot>=21
optuna-dashboard
```

- [ ] **Step 2: Install locally**

Run: `pip install --break-system-packages fastapi "uvicorn[standard]" "python-telegram-bot>=21" optuna-dashboard`
Expected: all install; `python3 -c "import fastapi, uvicorn, telegram, optuna_dashboard; print('ok')"` prints `ok`

- [ ] **Step 3: Commit**
```bash
git add requirements.txt
git commit -m "deps(dashboard): add fastapi, uvicorn, python-telegram-bot, optuna-dashboard"
```

### Task A2: Launcher script + bind-IP resolution
**Files:** Create `optimize/dashboard/run_dashboard.sh`, `optimize/dashboard/dashboard.env.example`; Modify `.gitignore`

- [ ] **Step 1: Write `dashboard.env.example`**
```bash
# optimize/dashboard/dashboard.env.example — copy to dashboard.env (gitignored) and fill.
# The private IP the dashboard binds to (VPN/LAN-reachable, NEVER 0.0.0.0/public). Confirm from phone in P-A.
DASH_BIND_IP=127.0.0.1
DASH_CONTROL_PORT=8350
DASH_OPTUNA_PORT=8081
# Optuna storage URL (same Postgres the optimizer writes to)
WSH_STORAGE_URL=postgresql+psycopg2://USER:PASS@127.0.0.1:55432/wsh
# Telegram (token already lives in SERVER_DATA.env; copy it here or export before launch)
TELEGRAM_BOT_TOKEN=
# Comma-separated allowlist of numeric chat IDs permitted to command the bot
TELEGRAM_ALLOWED_CHAT_IDS=
```

- [ ] **Step 2: Write `run_dashboard.sh`**
```bash
#!/usr/bin/env bash
# Launch the three dashboard processes bound to the private/VPN IP. Run on the server.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; source "$HERE/dashboard.env"; set +a   # DASH_BIND_IP, ports, WSH_STORAGE_URL, TELEGRAM_*
: "${DASH_BIND_IP:?set DASH_BIND_IP in dashboard.env}"
echo "binding dashboard services to $DASH_BIND_IP (control:$DASH_CONTROL_PORT optuna:$DASH_OPTUNA_PORT)"

# 1) optuna-dashboard (live graphs/Pareto) — reads the same Postgres
optuna-dashboard "$WSH_STORAGE_URL" --host "$DASH_BIND_IP" --port "$DASH_OPTUNA_PORT" \
  > "$HERE/optuna_dashboard.log" 2>&1 &
echo "optuna-dashboard pid $!"

# 2) control plane (FastAPI)
( cd "$HERE/../.." && uvicorn optimize.dashboard.app:app --host "$DASH_BIND_IP" --port "$DASH_CONTROL_PORT" ) \
  > "$HERE/control.log" 2>&1 &
echo "control-plane pid $!"

# 3) Telegram bot (long-poll; no inbound port)
( cd "$HERE/../.." && python3 -m optimize.dashboard.bot ) > "$HERE/bot.log" 2>&1 &
echo "bot pid $!"
wait
```

- [ ] **Step 3: gitignore secrets + bundles**

Append to `.gitignore`:
```
optimize/dashboard/dashboard.env
optimize/dashboard/bundles/
optimize/dashboard/*.log
```

- [ ] **Step 4: Commit**
```bash
git add optimize/dashboard/run_dashboard.sh optimize/dashboard/dashboard.env.example .gitignore
git commit -m "feat(dashboard): launcher + env template + gitignore secrets"
```

### Task A3: Stand up optuna-dashboard on the server + confirm bind IP (manual smoke)
**Files:** none (ops verification — record result in the tracker)

- [ ] **Step 1: On the server**, `pip install optuna-dashboard` into `REMOTE_VENV`; create `dashboard.env`
      with the real `WSH_STORAGE_URL` (from `$WSI/pg.env`) and `DASH_BIND_IP` candidate = the LAN private IP.
- [ ] **Step 2:** Launch only optuna-dashboard: `optuna-dashboard "$WSH_STORAGE_URL" --host <private-ip> --port 8081`
- [ ] **Step 3: From the phone on VPN**, open `http://<private-ip>:8081` → Expected: study list incl. the live
      `wsh*_4h` study; open it → **Pareto front renders**. From phone OFF VPN → Expected: not reachable.
- [ ] **Step 4:** Record the working `DASH_BIND_IP` in `WORKSTREAM_optimizer_dashboard_TRACKER.md`. (No commit.)

---

## PHASE P-B — `control.py` seam + `remote_wsi.sh` extension + FastAPI API

### Task B1: `remote_wsi.sh` — accept WSH_SAMPLER / WSH_ENGINE (additive)
**Files:** Modify `optimize/server/remote_wsi.sh`

- [ ] **Step 1:** In `cmd_run()`, where the worker command is built (the `python3 -u optimize/optimizer.py ...`
      line), inject sampler/engine from env. Add near the top of `cmd_run()`:
```bash
  SAMPLER_ARG=""; [ -n "${WSH_SAMPLER:-}" ] && SAMPLER_ARG="--sampler ${WSH_SAMPLER}"
  ENGINE="${WSH_ENGINE:-single}"   # single | two_stage
```
- [ ] **Step 2:** Change the worker invocation so `single` uses `optimizer.py` (with `$SAMPLER_ARG`) and
      `two_stage` uses the P3 module. Replace the worker `python3 -u optimize/optimizer.py "$tf" --trials "$per" ...`
      with:
```bash
      if [ "$ENGINE" = "two_stage" ]; then
        python3 -u -m optimize.two_stage "$tf" --stage-b "${WSH_STAGE_B:-cmaes}" $IND_ARGS >> "$log" 2>&1 || true
      else
        python3 -u optimize/optimizer.py "$tf" --trials "$per" --folds 5 --min-trades 5 $SAMPLER_ARG $IND_ARGS >> "$log" 2>&1 || true
      fi
```
- [ ] **Step 3: Verify default unchanged** — `bash -n optimize/server/remote_wsi.sh` (syntax OK) and confirm
      with `WSH_SAMPLER` unset the command equals the prior string (grep the generated launch.sh in a dry echo).
- [ ] **Step 4: Golden guard** — `python3 perf/check_golden.py` → Expected: ALL 6 MATCH (script change is
      additive/ops; engine untouched).
- [ ] **Step 5: Commit**
```bash
git add optimize/server/remote_wsi.sh
git commit -m "feat(server): remote_wsi.sh honors WSH_SAMPLER/WSH_ENGINE (default-off, unchanged)"
```

### Task B2: `control.py` — `_run_remote` helper + `config()`
**Files:** Create `optimize/dashboard/control.py`, `optimize/dashboard/test_control.py`

- [ ] **Step 1: Write the failing test** (`test_control.py`)
```python
import warnings; warnings.filterwarnings("ignore")
from optimize.dashboard import control

def test_config_shape():
    c = control.config()
    assert set(c["samplers"]) >= {"nsga3", "tpe", "gp"}           # from optimizer.SAMPLER_CHOICES
    assert c["engines"] == ["single", "two_stage"]
    assert c["stage_b"] == ["cmaes", "gp"]
    assert "4h" in c["timeframes"]
    assert isinstance(c["bounds"], dict) and "4h" in c["bounds"]   # per-TF sl/tp bounds
    assert isinstance(c["indicators"], list) and c["indicators"]   # library schema
    assert isinstance(c["presets"], list)
```
- [ ] **Step 2: Run → fail** `python3 -m pytest optimize/dashboard/test_control.py::test_config_shape -q` → Expected: ImportError/fail.
- [ ] **Step 3: Implement** (`control.py`)
```python
"""Dashboard control seam — the ONLY module that talks to remote_wsi.sh + the Optuna store.
Pure functions returning JSON-serializable dicts; never imports the scoring engine (no golden impact)."""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parent.parent                       # Parametric-Indicators root
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import optimizer as OPT            # SAMPLER_CHOICES, search_dims, recommended_trials, print_plan
from optimize import timeframes as TF
from indicators import library

_REMOTE = _PI / "optimize" / "server" / "remote_wsi.sh"
_BOUNDS = _PI / "optimize" / "sl_tp_bounds.json"
TIMEFRAMES = ["4h", "2h", "1h", "15m", "5m", "2m"]

def _run_remote(args: list[str], timeout: int = 120) -> dict:
    """Invoke remote_wsi.sh <args>. Returns {ok, stdout, stderr, code}. Mocked in tests."""
    proc = subprocess.run(["bash", str(_REMOTE), *args], capture_output=True, text=True, timeout=timeout)
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}

def config() -> dict:
    bounds = json.loads(_BOUNDS.read_text()) if _BOUNDS.exists() else {}
    try:
        import presets
        pl = [{"id": s["id"], "label": s["label"]} for s in presets.strategies()]
    except Exception:
        pl = []
    return {"samplers": list(OPT.SAMPLER_CHOICES), "engines": ["single", "two_stage"],
            "stage_b": ["cmaes", "gp"], "timeframes": TIMEFRAMES, "bounds": bounds,
            "indicators": library.schema().get("indicators", []), "presets": pl,
            "trials_per_dim": OPT.TRIALS_PER_DIM}
```
- [ ] **Step 4: Run → pass** same command → Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add optimize/dashboard/control.py optimize/dashboard/test_control.py
git commit -m "feat(dashboard): control.py config() + _run_remote helper + test"
```

### Task B3: `control.plan()` (acceptance preview)
**Files:** Modify `control.py`, `test_control.py`

- [ ] **Step 1: Failing test**
```python
def test_plan_scales_with_split():
    base = control.plan({"split_sltp": False})
    split = control.plan({"split_sltp": True})
    assert split["dims"] > base["dims"]
    assert split["recommended_trials"] == split["dims"] * base["trials_per_dim"]
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** (append to `control.py`)
```python
def plan(cfg: dict) -> dict:
    split = bool(cfg.get("split_sltp", False))
    per_dim = int(cfg.get("trials_per_dim", OPT.TRIALS_PER_DIM))
    dims = OPT.search_dims(split)
    return {"dims": dims["total"], "breakdown": dims, "trials_per_dim": per_dim,
            "recommended_trials": OPT.recommended_trials(split, per_dim)}
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): control.plan() acceptance preview + test`.

### Task B4: `control.start()` / `stop()` / `resume()` (env + command, mocked)
**Files:** Modify `control.py`, `test_control.py`

- [ ] **Step 1: Failing test** (mock `_run_remote` to capture env)
```python
import optimize.dashboard.control as C

def test_start_builds_sampler_engine_env(monkeypatch):
    captured = {}
    def fake_run(args, timeout=120):
        captured["args"] = args; captured["env"] = dict(os.environ); return {"ok": True, "stdout": "launcher-started", "stderr": "", "code": 0}
    monkeypatch.setattr(C, "_run_remote", fake_run)
    out = C.start({"sampler": "gp", "engine": "two_stage", "stage_b": "cmaes",
                   "prefix": "wsh6", "split_sltp": True, "ind_1min": True, "trials": 5600})
    assert out["ok"] and captured["args"][0] == "run"
    assert os.environ.get("WSH_SAMPLER") == "gp"
    assert os.environ.get("WSH_ENGINE") == "two_stage"
    assert os.environ.get("WSH_PREFIX") == "wsh6"
    assert os.environ.get("WSH_CONFIRM") == "1"      # UI already showed the plan

def test_stop_calls_stop(monkeypatch):
    seen = {}
    monkeypatch.setattr(C, "_run_remote", lambda a, timeout=120: seen.setdefault("a", a) or {"ok": True, "stdout": "", "stderr": "", "code": 0})
    C.stop(); assert seen["a"] == ["stop"]
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** (append to `control.py`)
```python
import os as _os

def _apply_env(cfg: dict) -> None:
    """Translate a UI config into the env remote_wsi.sh reads. Only sets keys present in cfg."""
    m = {"sampler": "WSH_SAMPLER", "engine": "WSH_ENGINE", "stage_b": "WSH_STAGE_B",
         "prefix": "WSH_PREFIX"}
    for k, env in m.items():
        if cfg.get(k) not in (None, ""):
            _os.environ[env] = str(cfg[k])
    _os.environ["WSH_SPLIT"] = "1" if cfg.get("split_sltp") else "0"
    _os.environ["WSH_CONFIRM"] = "1"                # UI showed plan + user accepted → skip interactive gate
    if cfg.get("ind_1min"):
        _os.environ["WSH_IND_1MIN"] = "1"

def start(cfg: dict) -> dict:
    _apply_env(cfg)
    args = ["run"]
    if cfg.get("trials") and not cfg.get("auto_trials"):
        args.append(str(int(cfg["trials"])))
    r = _run_remote(args)
    return {"ok": r["ok"], "launched": "launcher-started" in r["stdout"], "detail": r["stdout"][-400:]}

def stop() -> dict:
    r = _run_remote(["stop"]); return {"ok": r["ok"], "detail": (r["stdout"] + r["stderr"])[-400:]}

def resume(cfg: dict) -> dict:
    return start(cfg)                                # watchdog continues target − completed
```
> Note: requires `remote_wsi.sh` to read `WSH_IND_1MIN`→`$IND_ARGS` and `WSH_PREFIX`/`WSH_SPLIT` (already used per NEXT_OPTIMIZER_NOTES §2d). If `WSH_IND_1MIN` is not yet wired, add it in B1's edits.
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): control.start/stop/resume + env mapping + tests`.

### Task B5: `control.status()` (parse `stats --json` + workers)
**Files:** Modify `control.py`, `test_control.py`

- [ ] **Step 1: Failing test**
```python
def test_status_parses_stats(monkeypatch):
    sample = '{"prefix":"wsh4","studies":[{"tf":"4h","complete":5483,"running":2,"fail":0,"pruned":614}]}'
    monkeypatch.setattr(C, "_run_remote", lambda a, timeout=120: {"ok": True, "stdout": sample, "stderr": "", "code": 0})
    s = C.status()
    assert s["studies"][0]["tf"] == "4h" and s["studies"][0]["complete"] == 5483
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement**
```python
def status() -> dict:
    r = _run_remote(["stats", "--json"])
    try:
        data = json.loads(r["stdout"])
    except Exception:
        return {"ok": False, "studies": [], "raw": r["stdout"][-400:]}
    data["ok"] = r["ok"]
    return data
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): control.status() + test`.

### Task B6: `control.tail_logs()` + `follow_logs()` (SSE source)
**Files:** Modify `control.py`, `test_control.py`

- [ ] **Step 1: Failing test** (tail a temp file)
```python
def test_tail_logs(tmp_path, monkeypatch):
    log = tmp_path / "4h.log"; log.write_text("l1\nl2\nl3\n")
    monkeypatch.setattr(C, "_log_path", lambda tf: log)
    assert C.tail_logs("4h", n=2).strip().splitlines() == ["l2", "l3"]
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** (the real log dir is `$WSH_LOGS_DIR` or a configured remote-pull cache)
```python
_LOGS_DIR = Path(_os.environ.get("WSH_LOGS_DIR", str(_PI / "optimize" / "server" / "server_logs")))

def _log_path(tf: str) -> Path:
    return _LOGS_DIR / f"{tf}.log"

def tail_logs(tf: str, n: int = 200) -> str:
    p = _log_path(tf)
    if not p.exists():
        return ""
    return "\n".join(p.read_text(errors="replace").splitlines()[-n:])

def follow_logs(tf: str):
    """Generator yielding new log lines (for SSE). Polls the file; stops when the caller closes."""
    p = _log_path(tf); pos = 0
    while True:
        if p.exists():
            with p.open(errors="replace") as f:
                f.seek(pos); chunk = f.read(); pos = f.tell()
            if chunk:
                for line in chunk.splitlines():
                    yield line
        time.sleep(1.0)
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): control log tail/follow + test`.

### Task B7: `control.build_bundle(mode)` (full | lite)
**Files:** Modify `control.py`, `test_control.py`

- [ ] **Step 1: Failing test** (lite mode builds a tar without pg_dump)
```python
def test_build_bundle_lite(tmp_path, monkeypatch):
    res = tmp_path / "results"; res.mkdir(); (res / "x.json").write_text("{}")
    monkeypatch.setattr(C, "_RESULTS_DIR", res)
    monkeypatch.setattr(C, "_BUNDLES_DIR", tmp_path / "bundles")
    monkeypatch.setattr(C, "_LOGS_DIR", tmp_path / "nologs")
    path = C.build_bundle("lite")
    assert path.endswith(".tar.gz") and Path(path).exists()
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement**
```python
import tarfile

_RESULTS_DIR = _PI / "optimize" / "results"
_BUNDLES_DIR = _HERE / "bundles"

def build_bundle(mode: str = "full", stamp: str | None = None) -> str:
    """Build a .tar.gz of optimizer artifacts. mode='full' adds a pg_dump of the studies; 'lite' omits it.
    `stamp` (timestamp) is passed in by the caller (no Date.now in lib). Returns the tar path."""
    if mode not in ("full", "lite"):
        raise ValueError(f"mode must be full|lite, got {mode!r}")
    _BUNDLES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = stamp or "bundle"
    out = _BUNDLES_DIR / f"optimizer_{mode}_{stamp}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        if _RESULTS_DIR.exists():
            tar.add(_RESULTS_DIR, arcname="results")
        if _LOGS_DIR.exists():
            tar.add(_LOGS_DIR, arcname="logs")
        if mode == "full":
            dump = _BUNDLES_DIR / f"studies_{stamp}.sql"
            url = _os.environ.get("WSH_STORAGE_URL", "")
            if url.startswith("postgres"):
                subprocess.run(["pg_dump", "--dbname", url.replace("+psycopg2", ""), "-f", str(dump)],
                               check=False, timeout=600)
                if dump.exists():
                    tar.add(dump, arcname="studies.sql"); dump.unlink()
    return str(out)
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): control.build_bundle(full|lite) + test`.

### Task B8: FastAPI `app.py` — config/plan/run/stop/resume/status
**Files:** Create `optimize/dashboard/app.py`, `optimize/dashboard/test_app.py`

- [ ] **Step 1: Failing test**
```python
import warnings; warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient
import optimize.dashboard.app as APP
client = TestClient(APP.app)

def test_config_endpoint(monkeypatch):
    monkeypatch.setattr(APP.control, "config", lambda: {"samplers": ["nsga3"], "engines": ["single", "two_stage"]})
    r = client.get("/api/config"); assert r.status_code == 200 and "samplers" in r.json()

def test_run_delegates(monkeypatch):
    seen = {}
    monkeypatch.setattr(APP.control, "start", lambda cfg: seen.setdefault("cfg", cfg) or {"ok": True})
    r = client.post("/api/run", json={"sampler": "gp", "engine": "single"})
    assert r.status_code == 200 and r.json()["ok"] and seen["cfg"]["sampler"] == "gp"

def test_stop_endpoint(monkeypatch):
    monkeypatch.setattr(APP.control, "stop", lambda: {"ok": True})
    assert client.post("/api/stop").json()["ok"]
```
- [ ] **Step 2: Run → fail** `python3 -m pytest optimize/dashboard/test_app.py -q`.
- [ ] **Step 3: Implement** (`app.py`)
```python
"""FastAPI control plane — thin delegators to control.py. Binds to the private IP via run_dashboard.sh."""
from __future__ import annotations
import json, time
from pathlib import Path
from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from optimize.dashboard import control

app = FastAPI(title="Optimizer Control Plane")
_STATIC = Path(__file__).resolve().parent / "static"

@app.get("/api/config")
def api_config():
    cfg = control.config(); cfg["status"] = control.status(); return cfg

@app.post("/api/plan")
def api_plan(cfg: dict = Body(...)):
    return control.plan(cfg)

@app.post("/api/run")
def api_run(cfg: dict = Body(...)):
    return control.start(cfg)

@app.post("/api/resume")
def api_resume(cfg: dict = Body(...)):
    return control.resume(cfg)

@app.post("/api/stop")
def api_stop():
    return control.stop()

@app.get("/api/status")
def api_status():
    return control.status()

@app.get("/api/progress")
def api_progress(tf: str = "4h"):
    def gen():
        for line in control.follow_logs(tf):
            yield f"data: {json.dumps({'line': line})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/", response_class=HTMLResponse)
def index():
    f = _STATIC / "index.html"
    return f.read_text() if f.exists() else "<h1>control plane up</h1>"
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): FastAPI app config/plan/run/stop/resume/status + SSE + tests`.

### Task B9: Bundle endpoints (build async + download)
**Files:** Modify `app.py`, `test_app.py`

- [ ] **Step 1: Failing test**
```python
def test_bundle_build_and_download(monkeypatch, tmp_path):
    f = tmp_path / "b.tar.gz"; f.write_bytes(b"x")
    monkeypatch.setattr(APP.control, "build_bundle", lambda mode="full", stamp=None: str(f))
    jid = client.post("/api/bundle?mode=lite").json()["id"]
    r = client.get(f"/api/bundle/{jid}")
    assert r.status_code == 200 and r.content == b"x"
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** (append to `app.py`)
```python
_BUNDLES: dict[str, str] = {}

@app.post("/api/bundle")
def api_bundle(mode: str = "full"):
    stamp = str(int(time.time()))
    path = control.build_bundle(mode, stamp=stamp)
    _BUNDLES[stamp] = path
    return {"id": stamp, "path": path, "size_bytes": Path(path).stat().st_size}

@app.get("/api/bundle/{bid}")
def api_bundle_get(bid: str):
    path = _BUNDLES.get(bid)
    return FileResponse(path, filename=Path(path).name) if path else HTMLResponse("not found", 404)
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): bundle build+download endpoints + test`.

---

## PHASE P-C — control web UI (`static/index.html`)

### Task C1: Clone the existing dashboard shell + config panel
**Files:** Create `optimize/dashboard/static/index.html`

- [ ] **Step 1:** Copy the **head/CSS/theme + fetch helpers + `.mathnum` inline-math input + schema-driven
      panel builder** from `frontend/index.html` (lines for `:root` theme, `evalMath/commitField`, and the
      indicator-panel builder ~373–414) into the new file. Reuse, don't reinvent.
- [ ] **Step 2:** Replace the backtest form with the **optimizer config panel** populated from `GET /api/config`:
      `<select>`s for **sampler** (from `samplers`), **engine** (`single|two_stage`) + **stage_b** (`cmaes|gp`,
      shown only when engine=two_stage), number inputs for **trials** + an **auto-trials** checkbox, **folds**,
      **min-trades**, a **timeframes** multiselect, **split-sltp** + **ind-1min** + **warm-start** checkboxes,
      **prefix** text, and a **bounds editor** rendered from `config.bounds[tf]`.
- [ ] **Step 3: Verify** — serve `uvicorn optimize.dashboard.app:app` locally, open `/`, confirm the panel
      renders every control from `/api/config` (mock status if no server). Expected: all fields present.
- [ ] **Step 4: Commit** `feat(dashboard): control UI shell + schema-driven config panel`.

### Task C2: Plan preview + Start/Pause/Resume controls
**Files:** Modify `static/index.html`

- [ ] **Step 1:** Add a **"Preview plan"** button → `POST /api/plan` with the current config → render
      `dims → recommended_trials` (the acceptance preview). Add **Start** (`POST /api/run`), **Pause**
      (`POST /api/stop`), **Resume** (`POST /api/resume`) buttons. Start is disabled until a plan is previewed.
- [ ] **Step 2: Verify** — click Preview → see dims/trials; Start → POST fires with the config body (check
      network tab / mock). Expected: correct payload.
- [ ] **Step 3: Commit** `feat(dashboard): plan preview + start/pause/resume controls`.

### Task C3: Status cards + live-log SSE + links
**Files:** Modify `static/index.html`

- [ ] **Step 1:** Poll `GET /api/status` every 5s → render **per-TF cards** (complete/feasible/running/
      pruned/fail) + uptime + alive workers + best P/L@DD. Open an `EventSource('/api/progress?tf=…')` →
      append lines to a scrollable **live-log** panel (auto-tail, pause toggle). Add **"Open live graphs"**
      link to `http://<host>:<DASH_OPTUNA_PORT>` and a **"Download full data"** + **"Download lite"** pair
      (`POST /api/bundle?mode=…` → poll → `window.location = /api/bundle/<id>`).
- [ ] **Step 2: Verify (Playwright smoke)** — clone the pattern in `tests/e2e_dashboard_inputs.py`
      (system Chrome via `executable_path`, `--no-sandbox`): load `/`, assert the status cards + log panel
      exist and the SSE connection opens. Run it headless.
- [ ] **Step 3: Commit** `feat(dashboard): status cards + live-log SSE + graph/data links + e2e smoke`.

---

## PHASE P-E — Telegram bot (notify + control, allowlisted)

### Task E1: Bot allowlist guard + command dispatch
**Files:** Create `optimize/dashboard/bot.py`, `optimize/dashboard/test_bot.py`

- [ ] **Step 1: Failing test** (allowlist + dispatch, no network)
```python
import os, warnings; warnings.filterwarnings("ignore")
os.environ["TELEGRAM_ALLOWED_CHAT_IDS"] = "111,222"
from optimize.dashboard import bot

def test_allowlist():
    assert bot.allowed(111) and bot.allowed(222) and not bot.allowed(999)

def test_dispatch_status(monkeypatch):
    monkeypatch.setattr(bot.control, "status", lambda: {"studies": [{"tf": "4h", "complete": 10}]})
    msg = bot.handle_command("/status", chat_id=111)
    assert "4h" in msg and "10" in msg

def test_dispatch_blocked():
    assert bot.handle_command("/stop", chat_id=999) == bot.DENIED
```
- [ ] **Step 2: Run → fail** `python3 -m pytest optimize/dashboard/test_bot.py -q`.
- [ ] **Step 3: Implement** (`bot.py` — split pure logic from the network loop so it's testable)
```python
"""Telegram bot — long-polling, allowlist-guarded, shares control.py. Pure dispatch is unit-tested;
the network loop (run()) is only started by __main__."""
from __future__ import annotations
import os
from optimize.dashboard import control

DENIED = "⛔ not authorized"
def _allow_ids() -> set[int]:
    return {int(x) for x in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if x.strip()}
def allowed(chat_id: int) -> bool:
    return chat_id in _allow_ids()

def handle_command(text: str, chat_id: int) -> str:
    if not allowed(chat_id):
        return DENIED
    cmd = text.strip().split()[0]
    if cmd == "/status":
        s = control.status()
        return "\n".join(f"{x['tf']}: {x.get('complete',0)} complete" for x in s.get("studies", [])) or "no studies"
    if cmd == "/stop":
        return "paused ⏸" if control.stop().get("ok") else "stop failed"
    if cmd == "/resume":
        return "resumed ▶" if control.resume({}).get("ok") else "resume failed"
    if cmd == "/pull":
        import time; p = control.build_bundle("lite", stamp=str(int(time.time())))
        return f"bundle ready: {p}"
    return "commands: /status /stop /resume /pull /pareto"

def run():                                            # pragma: no cover (network)
    from telegram.ext import Application, MessageHandler, filters
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    async def on_msg(update, ctx):
        await update.message.reply_text(handle_command(update.message.text or "", update.effective_chat.id))
    app.add_handler(MessageHandler(filters.TEXT, on_msg))
    app.run_polling()

if __name__ == "__main__":                            # pragma: no cover
    run()
```
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): telegram bot allowlist + command dispatch + tests`.

### Task E2: Notify loop (new champion / run state / Pareto image)
**Files:** Modify `bot.py`, `test_bot.py`

- [ ] **Step 1: Failing test** (diff detects a new champion)
```python
def test_champion_change_detected():
    prev = {"4h": 33587.0}; cur = {"4h": 35000.0}
    assert bot.new_champions(prev, cur) == [("4h", 35000.0)]
    assert bot.new_champions(cur, cur) == []
```
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** (append to `bot.py`)
```python
def new_champions(prev: dict, cur: dict) -> list[tuple[str, float]]:
    """Return (tf, best) pairs whose best P/L improved vs prev (drives push notifications)."""
    out = []
    for tf, best in cur.items():
        if best > prev.get(tf, float("-inf")):
            out.append((tf, best))
    return out
```
> The notify loop (in `run()`) polls `control.status()` best-P/L per TF every N seconds, diffs with
> `new_champions`, and pushes a message + optional Pareto image to each allowlisted chat. (Network-only;
> not unit-tested — covered by the server smoke.)
- [ ] **Step 4: Run → pass. Step 5: Commit** `feat(dashboard): champion-diff notify helper + test`.

---

## PHASE P-F (LATER) — containerize

### Task F1: docker-compose for the dashboard
**Files:** Create `optimize/dashboard/docker-compose.yml`
- [ ] Compose three services (optuna-dashboard official image; control-plane + bot from a small Dockerfile),
      all on the private network beside `wsh-pg`, env from `dashboard.env`. Acceptance: `docker compose up`
      brings the dashboard up on a fresh host and it's reachable over VPN. (Deferred per spec D5.)

---

## Final: server smoke + docs
- [ ] **Server smoke:** deploy, start a tiny run via the UI, confirm trials appear in optuna-dashboard,
      Pause/Resume works, both bundles download + `pg_restore` loads the full one locally, bot `/status`
      replies and a new-champion alert fires.
- [ ] **Docs:** write `optimize/dashboard/UPDATE_optimizer_dashboard.md` (verbose, Mermaid only) + update
      `SYSTEM_UPDATES_MEGADOC.md` index + the workstream tracker. Commit.

---

## Self-review (done while writing)
- **Spec coverage:** §3 architecture → all phases; §3.0 access → A2/A3 bind rule; §4.1 control.py → B2–B7;
  §4.2 API → B8–B9; §4.3 UI → C1–C3; §4.4 bot → E1–E2; §4.5 optuna-dashboard → A2/A3; §4.6 remote_wsi.sh → B1;
  §5 bundle (both modes) → B7/B9/C3; §6 security → A2 (bind), E1 (allowlist), gitignore; §7 testing → tests in
  each task; §8 phasing → P-A..P-F. No uncovered section.
- **Placeholders:** none (every code step has real code; ops/manual steps are explicit verifications).
- **Type consistency:** `control.config/plan/start/stop/resume/status/tail_logs/follow_logs/build_bundle`
  signatures match across `control.py`, `app.py`, `bot.py`, and tests; bundle `mode` is `full|lite` throughout;
  env keys (`WSH_SAMPLER/WSH_ENGINE/WSH_STAGE_B/WSH_PREFIX/WSH_SPLIT/WSH_CONFIRM/WSH_IND_1MIN`) consistent
  between B1 and B4.
