"""Tier 1 — tests for the centralized Optuna storage URL helper (optimize/storage.py).

Proves the safety contract: with WSH_STORAGE_URL UNSET the URL is the per-TF sqlite path (byte-identical
to pre-Tier-1); with it SET the whole pipeline switches backend in one move; and the SQLAlchemy
engine_kwargs are backend-appropriate (sqlite busy_timeout vs a served-RDB pool).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from optimize import storage as study_storage  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(study_storage.ENV_VAR, raising=False)
    yield


def test_unset_falls_back_to_per_tf_sqlite():
    p = "/x/y/optimize/studies/wsh_4h.db"
    assert study_storage.storage_url(p) == f"sqlite:///{p}"


def test_env_overrides_all(monkeypatch):
    url = "postgresql://wsh:secret@localhost:5432/wsh"
    monkeypatch.setenv(study_storage.ENV_VAR, url)
    # the sqlite path is ignored entirely when the env var is set
    assert study_storage.storage_url("/anything/wsh_2m.db") == url


def test_empty_env_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv(study_storage.ENV_VAR, "")
    p = "/x/wsh_1h.db"
    assert study_storage.storage_url(p) == f"sqlite:///{p}"   # empty string is falsy → sqlite fallback


def test_is_sqlite():
    assert study_storage.is_sqlite("sqlite:////tmp/wsh_5m.db") is True
    assert study_storage.is_sqlite("postgresql://h/db") is False


def test_engine_kwargs_sqlite_has_busy_timeout():
    kw = study_storage.engine_kwargs("sqlite:////tmp/wsh_5m.db")
    assert kw == {"connect_args": {"timeout": 60}}


def test_engine_kwargs_postgres_has_pool():
    kw = study_storage.engine_kwargs("postgresql://wsh:***@localhost/wsh")
    assert kw.get("pool_size") and "max_overflow" in kw
    assert "connect_args" not in kw


def test_real_create_study_unset_uses_sqlite(tmp_path, monkeypatch):
    # end-to-end: unset env → an actual sqlite study file is created at the given path (no Postgres needed)
    import optuna
    db = tmp_path / "wsh_4h.db"
    url = study_storage.storage_url(db)
    st = optuna.storages.RDBStorage(url=url, engine_kwargs=study_storage.engine_kwargs(url))
    optuna.create_study(study_name="t1_4h", storage=st, directions=["maximize"], load_if_exists=True)
    assert db.exists()
