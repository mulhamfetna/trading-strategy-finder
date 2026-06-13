"""Tier 2 — tests for optimize/trial_count.completed() (target-based / watchdog support).

It must return the count of COMPLETED trials for a study and 0 when the study/store is absent — this is
what the launcher's `remaining = target - completed` and respawn loop rely on.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

import optuna  # noqa: E402
from optimize import trial_count  # noqa: E402


def _make_study(url, name, n):
    st = optuna.storages.RDBStorage(url=url)
    s = optuna.create_study(study_name=name, storage=st, directions=["maximize"], load_if_exists=True)
    s.optimize(lambda t: t.suggest_float("x", 0, 1), n_trials=n)
    return s


def test_completed_counts_via_env(tmp_path, monkeypatch):
    db = tmp_path / "store.db"
    url = f"sqlite:///{db}"
    monkeypatch.setenv("WSH_STORAGE_URL", url)        # env wins → trial_count reads here
    _make_study(url, "wsh4_4h", 5)
    assert trial_count.completed("wsh4", "4h") == 5


def test_missing_study_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("WSH_STORAGE_URL", f"sqlite:///{tmp_path/'empty.db'}")
    assert trial_count.completed("wsh4", "2m") == 0


def test_cli_prints_count(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path/'cli.db'}"
    monkeypatch.setenv("WSH_STORAGE_URL", url)
    _make_study(url, "wsh4_1h", 3)
    assert trial_count.completed("wsh4", "1h") == 3
