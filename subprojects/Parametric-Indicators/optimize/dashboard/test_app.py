"""FastAPI control-plane tests (optimize/dashboard/app.py) — control.py is monkeypatched, no server."""
from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient

import optimize.dashboard.app as APP

client = TestClient(APP.app)


def test_config_endpoint_is_status_free(monkeypatch):
    # /api/config must NOT embed the slow status query (#41) — it returns config only.
    monkeypatch.setattr(APP.control, "config", lambda: {"samplers": ["nsga3", "gp"], "engines": ["single"]})
    monkeypatch.setattr(APP.control, "status", lambda: (_ for _ in ()).throw(AssertionError("status must not be called")))
    r = client.get("/api/config")
    assert r.status_code == 200 and "samplers" in r.json() and "status" not in r.json()


def test_plan_endpoint(monkeypatch):
    monkeypatch.setattr(APP.control, "plan", lambda cfg: {"dims": 56, "recommended_trials": 5600})
    r = client.post("/api/plan", json={"split_sltp": False})
    assert r.status_code == 200 and r.json()["recommended_trials"] == 5600


def test_run_delegates_to_owned_runner(monkeypatch):
    seen = {}
    monkeypatch.setattr(APP.runner._MGR, "start", lambda cfg: seen.update({"cfg": cfg}) or {"ok": True, "pid": 42})
    r = client.post("/api/run", json={"instrument": "NQ", "timeframes": ["4h"], "sampler": "gp"})
    assert r.status_code == 200 and r.json()["ok"] and seen["cfg"]["sampler"] == "gp"


def test_run_reports_missing_fields(monkeypatch):
    # real runner validation: an empty cfg returns ok:False + the missing fields (not a 500)
    r = client.post("/api/run", json={})
    assert r.status_code == 200 and r.json()["ok"] is False and "instrument" in r.json()["errors"]


def test_stop_endpoint(monkeypatch):
    monkeypatch.setattr(APP.runner._MGR, "stop", lambda: {"ok": True, "detail": "stopped"})
    assert client.post("/api/stop").json()["ok"]


def test_run_state_endpoint():
    st = client.get("/api/run/state").json()
    assert "running" in st and "study" in st


def test_resume_endpoint(monkeypatch):
    monkeypatch.setattr(APP.control, "resume", lambda cfg: {"ok": True, "resumed": True})
    assert client.post("/api/resume", json={}).json()["resumed"]


def test_status_endpoint(monkeypatch):
    monkeypatch.setattr(APP.control, "status", lambda: {"ok": True, "studies": [{"tf": "4h", "complete": 10}]})
    assert client.get("/api/status").json()["studies"][0]["tf"] == "4h"


def test_bundle_build_and_download(monkeypatch, tmp_path):
    f = tmp_path / "b.tar.gz"; f.write_bytes(b"payload")
    monkeypatch.setattr(APP.control, "build_bundle", lambda mode="full", stamp=None: str(f))
    jid = client.post("/api/bundle?mode=lite").json()["id"]
    r = client.get(f"/api/bundle/{jid}")
    assert r.status_code == 200 and r.content == b"payload"


def test_bundle_missing_404():
    assert client.get("/api/bundle/nope").status_code == 404


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and ("control" in r.text.lower() or "<" in r.text)
