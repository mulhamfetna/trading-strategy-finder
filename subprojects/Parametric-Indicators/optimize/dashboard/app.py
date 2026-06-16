"""FastAPI control plane — thin delegators to control.py. Bound to the private/VPN IP by run_dashboard.sh.
Serves the static control UI + REST + an SSE live-log stream + data-bundle build/download."""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from optimize.dashboard import control

app = FastAPI(title="Optimizer Control Plane")
_STATIC = Path(__file__).resolve().parent / "static"
_BUNDLES: dict[str, str] = {}


@app.get("/api/config")
def api_config():
    cfg = control.config()
    cfg["status"] = control.status()
    return cfg


@app.post("/api/plan")
def api_plan(cfg: dict = Body(default={})):
    return control.plan(cfg)


@app.post("/api/run")
def api_run(cfg: dict = Body(default={})):
    return control.start(cfg)


@app.post("/api/resume")
def api_resume(cfg: dict = Body(default={})):
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


@app.post("/api/bundle")
def api_bundle(mode: str = "full"):
    stamp = str(int(time.time()))
    path = control.build_bundle(mode, stamp=stamp)
    _BUNDLES[stamp] = path
    return {"id": stamp, "path": path, "size_bytes": Path(path).stat().st_size, "mode": mode}


@app.get("/api/bundle/{bid}")
def api_bundle_get(bid: str):
    path = _BUNDLES.get(bid)
    if not path or not Path(path).exists():
        return HTMLResponse("not found", status_code=404)
    return FileResponse(path, filename=Path(path).name, media_type="application/gzip")


@app.get("/", response_class=HTMLResponse)
def index():
    f = _STATIC / "index.html"
    return f.read_text() if f.exists() else "<h1>optimizer control plane up</h1>"
