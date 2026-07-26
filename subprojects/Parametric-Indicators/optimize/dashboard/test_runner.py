import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import runner


def test_validate_flags_missing_mandatory():
    assert set(runner.validate({})) >= {"instrument", "timeframe"}
    assert runner.validate({"instrument": "NQ", "timeframes": ["4h"], "trials_mode": "auto"}) == []
    # 'one' mode needs a trials count
    assert "trials" in runner.validate({"instrument": "NQ", "timeframes": ["4h"], "trials_mode": "one"})
    # only/exclude modes need a selection
    assert "only_indicators" in runner.validate(
        {"instrument": "NQ", "timeframes": ["4h"], "indicator_mode": "only", "only_indicators": []})


def test_study_prefix_is_selection_unique():
    a = {"instrument": "NQ", "only_indicators": ["rsi"], "indicator_mode": "only"}
    b = {"instrument": "NQ", "only_indicators": ["rsi", "macd"], "indicator_mode": "only"}
    c = {"instrument": "ES", "only_indicators": ["rsi"], "indicator_mode": "only"}
    assert runner.study_prefix(a) != runner.study_prefix(b)      # different indicators → different study
    assert runner.study_prefix(a) != runner.study_prefix(c)      # different instrument → different study
    assert runner.study_prefix(a) == runner.study_prefix(dict(a))  # stable for the same selection
    assert runner.study_prefix(a).startswith("cc")


def test_study_name_mirrors_optimizer():
    cfg = {"instrument": "ES", "only_indicators": ["rsi"], "indicator_mode": "only"}
    nm = runner.study_name(cfg, "4h")
    assert nm == f"{runner.study_prefix(cfg)}_4h_ES"
    assert runner.study_name({"instrument": "NQ"}, "1h") == f"{runner.study_prefix({'instrument':'NQ'})}_1h"


def test_build_command_reflects_selection():
    cmd = runner.build_command({"instrument": "GC", "timeframes": ["1h"], "trials_mode": "one",
                                "trials": 8000, "only_indicators": ["rsi", "macd"], "indicator_mode": "only",
                                "reference": "ES", "split_sltp": True, "cold_start": True, "max_enabled": 3}, "1h")
    s = " ".join(cmd)
    assert "optimize/optimizer.py 1h" in s and "--study-prefix cc" in s
    assert "--trials 8000" in s and "--only-indicators rsi,macd" in s and "--reference ES" in s
    assert "--split-sltp" in s and "--no-warm-start" in s and "--max-enabled 3" in s and "--instrument GC" in s


def test_auto_mode_uses_auto_trials():
    cmd = runner.build_command({"instrument": "NQ", "timeframes": ["4h"], "trials_mode": "auto"}, "4h")
    assert "--auto-trials" in cmd and "--trials" not in cmd


def test_expanded_cell_trials_are_honored():
    # a queue.expand()-ed cell carries auto_trials/trials (NOT trials_mode) — the fleet must honor them
    from optimize.dashboard import queue
    cell = queue.expand({"instruments": ["NQ"], "timeframes": ["4h"], "trials_mode": "one", "trials": 8})[0]
    assert "trials_mode" not in cell and cell["auto_trials"] is False and cell["trials"] == 8
    cmd = runner.build_command(cell, "4h")
    assert "--trials 8" in " ".join(cmd) and "--auto-trials" not in cmd     # was the bug: ran auto
    assert runner.target_trials(cell, "4h") == 8


def test_expanded_cell_budget_clamp_is_honored():
    from optimize.dashboard import queue
    cell = queue.expand({"instruments": ["NQ"], "timeframes": ["4h"], "trials_mode": "auto",
                         "max_trials": 5000})[0]
    cmd = runner.build_command(cell, "4h")
    assert "--trials 5000" in " ".join(cmd)          # budget guard actually reaches the command
    assert runner.target_trials(cell, "4h") == 5000


def test_start_rejects_invalid_cfg():
    mgr = runner.RunManager()
    r = mgr.start({})
    assert r["ok"] is False and "instrument" in r["errors"]


def test_lifecycle_owned_process_starts_streams_and_stops(monkeypatch):
    """Real Popen lifecycle with a FAKE command (no optimizer): start → running + logs → stop → dead."""
    fake = [sys.executable, "-u", "-c",
            "import time,sys\n"
            "print('trial 1 done', flush=True)\n"
            "time.sleep(30)\n"]
    monkeypatch.setattr(runner, "build_command", lambda cfg, tf: fake)
    monkeypatch.setattr(runner, "target_trials", lambda cfg, tf=None: 100)
    mgr = runner.RunManager()
    r = mgr.start({"instrument": "NQ", "timeframes": ["4h"], "trials_mode": "auto"})
    assert r["ok"] is True and r["pid"] > 0
    # give it a moment to print + be seen as running
    for _ in range(50):
        if mgr.tail() and mgr.running():
            break
        time.sleep(0.1)
    assert mgr.running() is True
    assert any("trial 1 done" in ln for ln in mgr.tail())
    st = mgr.stop()
    assert st["ok"] is True
    time.sleep(0.3)
    assert mgr.running() is False           # real stop — the owned process group is gone


def test_stop_when_nothing_running_is_safe():
    assert runner.RunManager().stop()["ok"] is True


# ── fleet (Launch-matrix queue on owned runs, #36) ────────────────────────────────────────────────
_FAKE = [sys.executable, "-u", "-c", "import time; print('go', flush=True); time.sleep(30)"]


def _fake_fleet(monkeypatch):
    monkeypatch.setattr(runner, "build_command", lambda cfg, tf: _FAKE)
    monkeypatch.setattr(runner, "target_trials", lambda cfg, tf=None: 10)
    monkeypatch.setattr(runner.RunManager, "done_count", lambda self: 0)   # avoid trial_count.py subprocess


def test_fleet_launches_one_owned_run_per_cell(monkeypatch):
    _fake_fleet(monkeypatch)
    q = runner.fleet_launch({"instruments": ["NQ", "ES"], "timeframes": ["4h"], "trials_mode": "auto"})
    assert len(q) == 2
    assert {(i["instrument"], i["timeframe"]) for i in q} == {("NQ", "4h"), ("ES", "4h")}
    assert all(i["state"] == "running" and i["running"] for i in q)
    st = runner.fleet_stop()
    assert st["ok"] and st["stopped"] == 2
    time.sleep(0.3)
    assert all(not i["running"] for i in runner.fleet_state())


def test_fleet_defers_cells_beyond_worker_cap(monkeypatch):
    _fake_fleet(monkeypatch)
    monkeypatch.setattr(runner, "_worker_cap", lambda: 1)                 # force a tiny cap
    q = runner.fleet_launch({"instruments": ["NQ", "ES", "GC"], "timeframes": ["4h"], "trials_mode": "auto"})
    states = [i["state"] for i in q]
    assert states.count("running") == 1 and states.count("deferred") == 2  # cap enforced + surfaced
    runner.fleet_stop()
