"""FastAPI control plane — thin delegators to control.py. Bound to the private/VPN IP by run_dashboard.sh.
Serves the static control UI + REST + an SSE live-log stream + data-bundle build/download."""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from optimize.dashboard import control, progress, queue, run_presets

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


@app.get("/api/live/progress")
def api_live_progress(tf: str = "4h", target: int = 0):
    sp = control.study_progress(tf, target or None)
    return progress.live(tf, sp["done"], sp["target"], time.time())


@app.get("/api/presets")
def api_presets():
    names = run_presets.list_names()
    return {"names": names, "presets": {n: run_presets.get(n) for n in names}}


@app.get("/api/presets/{name}")
def api_preset_get(name: str):
    return {"name": name, "cfg": run_presets.get(name)}


@app.post("/api/presets/{name}")
def api_preset_save(name: str, cfg: dict = Body(default={})):
    run_presets.save(name, cfg)
    return {"ok": True, "names": run_presets.list_names()}


@app.delete("/api/presets/{name}")
def api_preset_delete(name: str):
    run_presets.delete(name)
    return {"ok": True, "names": run_presets.list_names()}


@app.post("/api/queue")
def api_queue_launch(cfg: dict = Body(default={})):
    return {"queue": queue.launch(cfg, control.start)}


@app.get("/api/queue")
def api_queue_state():
    return {"queue": queue.state()}


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
