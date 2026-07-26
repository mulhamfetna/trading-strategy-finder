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
    monkeypatch.setattr(runner, "target_trials", lambda cfg: 100)
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
