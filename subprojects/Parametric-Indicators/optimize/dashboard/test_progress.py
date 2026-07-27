import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import progress


def test_eta_from_trailing_rate():
    # 100 trials over 100s ⇒ 1/s ⇒ 60/min; last done=200, target=400 ⇒ 200 remaining ⇒ 200s
    r = progress.compute_eta([(1000.0, 100), (1100.0, 200)], target=400)
    assert r["done"] == 200 and r["target"] == 400
    assert abs(r["rate_per_min"] - 60.0) < 1e-6
    assert abs(r["eta_seconds"] - 200.0) < 1e-6


def test_eta_none_when_no_progress():
    r = progress.compute_eta([(1000.0, 50), (1100.0, 50)], target=400)
    assert r["rate_per_min"] == 0.0 and r["eta_seconds"] is None   # rate 0 ⇒ unknown ETA


def test_eta_zero_when_done():
    r = progress.compute_eta([(1000.0, 380), (1100.0, 400)], target=400)
    assert r["eta_seconds"] == 0.0                                  # already at target ⇒ 0 remaining


def test_single_or_empty_sample_is_safe():
    assert progress.compute_eta([], target=400)["eta_seconds"] is None
    assert progress.compute_eta([(1000.0, 10)], target=400)["eta_seconds"] is None


def test_study_progress_reads_done_and_target(monkeypatch):
    from optimize.dashboard import control
    monkeypatch.setattr(control, "status", lambda: {"studies": [
        {"tf": "1h", "complete": 5, "target": 100},
        {"tf": "4h", "complete": 123, "target": 41100},
    ]})
    sp = control.study_progress("4h")
    assert sp["done"] == 123 and sp["target"] == 41100
    assert control.study_progress("4h", target=50000)["target"] == 50000   # explicit target wins
