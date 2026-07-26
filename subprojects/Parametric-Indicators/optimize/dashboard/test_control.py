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


def test_plan_includes_command_string():
    p = C.plan({"timeframes": ["1h"], "only_indicators": ["rsi", "macd"], "reference": "ES",
                "instrument": "GC", "split_sltp": True, "cold_start": True, "max_enabled": 3,
                "trials_mode": "one", "trials": 8000, "ind_1min": True})
    cmd = p["command"]
    assert "optimize/optimizer.py 1h" in cmd
    assert "--only-indicators rsi,macd" in cmd and "--reference ES" in cmd
    assert "--instrument GC" in cmd and "--split-sltp" in cmd and "--no-warm-start" in cmd
    assert "--max-enabled 3" in cmd and "--ind-1min" in cmd and "--trials 8000" in cmd


def test_preview_command_minimal_is_bare():
    # No opt-in selections ⇒ command carries only the always-on flags (byte-identical to a bare run).
    cmd = C.preview_command({"timeframes": ["4h"], "trials_mode": "auto"})
    assert "optimize/optimizer.py 4h" in cmd and "--ind-1min" in cmd
    for flag in ("--only-indicators", "--exclude-indicators", "--reference",
                 "--instrument", "--split-sltp", "--no-warm-start", "--max-enabled"):
        assert flag not in cmd


def test_start_single_builds_env_and_calls_run(monkeypatch):
    seen = {}
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120: seen.update({"args": args}) or
                        {"ok": True, "stdout": "launcher-started", "stderr": "", "code": 0})
    out = C.start({"sampler": "gp", "engine": "single",
                   "prefix": "wsh6", "split_sltp": True, "trials": 5600})
    assert out["ok"] and out["launched"]
    assert seen["args"][0] == "run"
    assert os.environ["WSH_SAMPLER"] == "gp"
    assert os.environ["WSH_ENGINE"] == "single"
    assert os.environ["WSH_PREFIX"] == "wsh6"
    assert os.environ["WSH_SPLIT"] == "1"
    assert os.environ["WSH_CONFIRM"] == "1"


def test_start_two_stage_routes_to_two_stage_cmd(monkeypatch):
    """engine=two_stage must NOT use the watchdog `run` path (in-memory studies have no trial-count
    target ⇒ the watchdog would loop forever). It launches `remote_wsi.sh two-stage <tfs>` directly."""
    seen = {}
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120: seen.update({"args": args}) or
                        {"ok": True, "stdout": "launcher-started", "stderr": "", "code": 0})
    out = C.start({"engine": "two_stage", "stage_b": "gp", "prefix": "wsh6",
                   "split_sltp": True, "timeframes": ["4h", "2h"]})
    assert out["ok"] and out["launched"] and out["engine"] == "two_stage"
    assert seen["args"][0] == "two-stage"
    assert seen["args"][1] == "4h 2h"                     # selected TFs forwarded as one space-list arg
    assert os.environ["WSH_ENGINE"] == "two_stage"
    assert os.environ["WSH_STAGE_B"] == "gp"
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


def test_status_derives_running_and_study_count(monkeypatch):
    sample = ('{"studies":[{"tf":"4h","complete":10,"running":3},'
              '{"tf":"1h","complete":40,"running":0}]}')
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120:
                        {"ok": True, "stdout": sample, "stderr": "", "code": 0})
    s = C.status()
    assert s["running"] is True and s["n_studies"] == 2      # any worker>0 ⇒ running


def test_status_running_false_when_no_workers(monkeypatch):
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120:
                        {"ok": True, "stdout": '{"studies":[{"tf":"4h","complete":10,"running":0}]}',
                         "stderr": "", "code": 0})
    assert C.status()["running"] is False


def test_health_reports_studies_and_survives_no_psutil(monkeypatch):
    monkeypatch.setattr(C, "_run_remote", lambda args, timeout=120:
                        {"ok": True, "stdout": '{"studies":[{"tf":"4h","complete":10,"running":2}]}',
                         "stderr": "", "code": 0})
    h = C.health()
    assert h["n_studies"] == 1 and h["running"] is True and "cpu_pct" in h and "mem_pct" in h


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
