"""Tier 3 — tests for observability helpers: study_stats (state counts) + contention_smoke (lock probe)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

import optuna  # noqa: E402


def test_study_stats_counts(tmp_path, monkeypatch):
    from optimize import study_stats
    url = f"sqlite:///{tmp_path/'s.db'}"
    monkeypatch.setenv("WSH_STORAGE_URL", url)
    st = optuna.storages.RDBStorage(url=url)
    s = optuna.create_study(study_name="wsh4_4h", storage=st, direction="maximize", load_if_exists=True)
    s.optimize(lambda t: t.suggest_float("x", 0, 1), n_trials=6)
    r = study_stats.stats("wsh4", "4h")
    assert r["complete"] == 6 and r["total"] == 6 and r["fail"] == 0


def test_study_stats_absent_is_zero(tmp_path, monkeypatch):
    from optimize import study_stats
    monkeypatch.setenv("WSH_STORAGE_URL", f"sqlite:///{tmp_path/'none.db'}")
    r = study_stats.stats("wsh4", "2m")
    assert r == {"tf": "2m", "complete": 0, "running": 0, "fail": 0, "pruned": 0, "total": 0}


def test_contention_smoke_no_lock_deaths(tmp_path):
    # small concurrency on a fresh sqlite (WAL+timeout) must produce ZERO lock deaths
    from optimize import contention_smoke
    url = f"sqlite:///{tmp_path/'c.db'}"
    r = contention_smoke.run_smoke(url, workers=4, trials=3)
    assert r["ok"] is True and r["lock_deaths"] == 0
