"""Unit tests for the control seam (optimize/dashboard/control.py). Shell + DB are mocked — no server."""
from __future__ import annotations

import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import optimize.dashboard.control as C


def test_config_shape():
    c = C.config()
    assert set(c["samplers"]) >= {"nsga3", "tpe", "gp"}
    assert c["engines"] == ["single", "two_stage"]
    assert c["stage_b"] == ["cmaes", "gp"]
    assert "4h" in c["timeframes"]
    assert isinstance(c["indicators"], list) and c["indicators"]
    assert isinstance(c["presets"], list)


def test_plan_scales_with_split():
    base = C.plan({"split_sltp": False})
    split = C.plan({"split_sltp": True})
    assert split["dims"] > base["dims"]
    assert split["recommended_trials"] == split["dims"] * base["trials_per_dim"]


def test_start_builds_env_and_calls_run(monkeypatch):
    seen = {}
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120: seen.update({"args": args}) or
                        {"ok": True, "stdout": "launcher-started", "stderr": "", "code": 0})
    out = C.start({"sampler": "gp", "engine": "two_stage", "stage_b": "cmaes",
                   "prefix": "wsh6", "split_sltp": True, "trials": 5600})
    assert out["ok"] and out["launched"]
    assert seen["args"][0] == "run"
    assert os.environ["WSH_SAMPLER"] == "gp"
    assert os.environ["WSH_ENGINE"] == "two_stage"
    assert os.environ["WSH_PREFIX"] == "wsh6"
    assert os.environ["WSH_SPLIT"] == "1"
    assert os.environ["WSH_CONFIRM"] == "1"


def test_start_auto_trials_omits_number(monkeypatch):
    seen = {}
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120: seen.update({"args": args}) or
                        {"ok": True, "stdout": "launcher-started", "stderr": "", "code": 0})
    C.start({"auto_trials": True, "trials": 5600})
    assert seen["args"] == ["run"]                       # no trial number when auto


def test_stop_calls_stop(monkeypatch):
    seen = {}
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120: seen.update({"args": args}) or
                        {"ok": True, "stdout": "stop signal sent.", "stderr": "", "code": 0})
    assert C.stop()["ok"] and seen["args"] == ["stop"]


def test_status_parses_stats(monkeypatch):
    sample = '{"prefix":"wsh4","studies":[{"tf":"4h","complete":5483,"running":2,"fail":0,"pruned":614}]}'
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120:
                        {"ok": True, "stdout": sample, "stderr": "", "code": 0})
    s = C.status()
    assert s["ok"] and s["studies"][0]["tf"] == "4h" and s["studies"][0]["complete"] == 5483


def test_status_bad_json_is_safe(monkeypatch):
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120:
                        {"ok": False, "stdout": "boom", "stderr": "", "code": 1})
    s = C.status()
    assert s["ok"] is False and s["studies"] == []


def test_tail_logs(tmp_path, monkeypatch):
    log = tmp_path / "4h.log"; log.write_text("l1\nl2\nl3\n")
    monkeypatch.setattr(C, "_log_path", lambda tf: log)
    assert C.tail_logs("4h", n=2).splitlines() == ["l2", "l3"]


def test_build_bundle_lite(tmp_path, monkeypatch):
    res = tmp_path / "results"; res.mkdir(); (res / "x.json").write_text("{}")
    monkeypatch.setattr(C, "_RESULTS_DIR", res)
    monkeypatch.setattr(C, "_BUNDLES_DIR", tmp_path / "bundles")
    monkeypatch.setattr(C, "_LOGS_DIR", tmp_path / "nologs")
    path = C.build_bundle("lite", stamp="t1")
    assert path.endswith(".tar.gz") and Path(path).exists()


def test_build_bundle_bad_mode():
    try:
        C.build_bundle("banana")
    except ValueError as e:
        assert "full|lite" in str(e); return
    raise AssertionError("bad mode must raise")
