"""Tier 1 — single source of truth for the Optuna trial-store URL.

The optimizer's results store used to be hard-coded as a `sqlite:///…` literal in three places
(`optimizer.py`, `report_wsi.py`, `remote_wsi.sh`). This module centralizes it so SQLite ↔ PostgreSQL is
**one environment variable**, not a three-file edit (see
`optimize/server/REPORT_system_scaling_study.md` §6 Tier 1, `EXPLAINER_tier1_postgres_and_history.md`).

DEFAULT BEHAVIOUR IS UNCHANGED: with `WSH_STORAGE_URL` **unset**, every study uses its per-timeframe
SQLite file exactly as before — byte-identical to the pre-Tier-1 system. Setting

    export WSH_STORAGE_URL="postgresql://wsh:***@localhost:5432/wsh"

switches ALL studies to that backend at once — the PostgreSQL path whose MVCC removes SQLite's
single-writer lock contention (the root cause of the wsh4 incident).
"""
from __future__ import annotations

import os

ENV_VAR = "WSH_STORAGE_URL"


def storage_url(sqlite_db_path) -> str:
    """Return the Optuna storage URL. `WSH_STORAGE_URL` wins when set (shared across every TF/study);
    otherwise fall back to the per-TF SQLite file the caller already resolved (`sqlite:///<path>`).
    Env-unset ⇒ identical to the pre-Tier-1 behaviour."""
    return os.environ.get(ENV_VAR) or f"sqlite:///{sqlite_db_path}"


def is_sqlite(url: str) -> bool:
    """True for a SQLite URL (the only backend that needs the WAL/busy_timeout file hardening)."""
    return str(url).startswith("sqlite:")


def engine_kwargs(url: str) -> dict:
    """Backend-appropriate SQLAlchemy engine kwargs:
      • SQLite — a 60 s busy_timeout so a worker WAITS for the lock instead of erroring (Tier 0.2).
      • a served RDB (PostgreSQL/MySQL) — a connection pool sized to the ~30-worker fleet."""
    if is_sqlite(url):
        return {"connect_args": {"timeout": 60}}
    return {"pool_size": 32, "max_overflow": 8}
