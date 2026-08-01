"""Tier 1 — single source of truth for the Optuna trial store.

The optimizer's results store used to be hard-coded as a `sqlite:///…` literal in three places
(`optimizer.py`, `report_wsi.py`, `remote_wsi.sh`). This module centralizes it so SQLite ↔ PostgreSQL is
**one environment variable**, not a three-file edit (see
`optimize/server/REPORT_system_scaling_study.md` §6 Tier 1, `EXPLAINER_tier1_postgres_and_history.md`).

DEFAULT BEHAVIOUR IS UNCHANGED: with `WSH_STORAGE_URL` **unset**, every study uses its per-timeframe
SQLite file exactly as before. Setting

    export WSH_STORAGE_URL="postgresql://wsh:***@localhost:5432/wsh"

switches ALL studies to that backend at once — the PostgreSQL path whose MVCC removes SQLite's
single-writer lock contention (the root cause of the wsh4 incident).

────────────────────────────────────────────────────────────────────────────────────────────────────
Tier 2 (2026-07-11) — JOURNAL storage, the fix for the measured trial-store wall.

Profiling a campaign showed the trial STORE, not the engine, is the bottleneck:

    NQ 15m, solo:   with Postgres  274 trials/min
                    with no store 1435 trials/min      ⇒ the store costs ~80% of every trial

Two causes, both intrinsic to RDBStorage:
  1. every param/value/attr is its own row ⇒ ~70 COMMITs per trial (measured: 2,806 commits / 40 trials);
  2. NSGA-III rebuilds its population from ALL trials each trial, so an RDB study re-FETCHES the whole
     history every trial — O(n²). This is why a campaign DECELERATES: the first 60 trials run at
     ~439/min but the full 5,900-trial campaign averages ~105/min.

JournalStorage fixes both: it APPENDS one record per operation and keeps an in-memory replica, so reads
become RAM lookups instead of round-trips.

And crucially, our campaigns are INDEPENDENT studies (one per instrument×timeframe) that all run on ONE
machine — they never share a study. So they don't need a shared networked DB at all: each campaign gets
its OWN journal file ⇒ zero cross-worker contention, no server, no network.

    export WSH_JOURNAL_DIR=~/Mulham/wsg-i/journals     # opt-in; overrides WSH_STORAGE_URL

Postgres remains the archive: each campaign still writes its pareto CSV, and journals can be imported.
Opt-in only — unset ⇒ byte-identical to the previous behaviour.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "WSH_STORAGE_URL"
JOURNAL_ENV = "WSH_JOURNAL_DIR"


def journal_dir() -> str | None:
    """The journal directory when journal mode is enabled, else None (⇒ RDB path, unchanged)."""
    return os.environ.get(JOURNAL_ENV) or None


def make_storage(sqlite_db_path, study_name: str):
    """Return an Optuna storage OBJECT for this study.

    Journal mode (WSH_JOURNAL_DIR set) ⇒ a per-study append-only journal file — no shared DB, no
    contention, in-memory reads. Otherwise the RDB path exactly as before (Postgres via
    WSH_STORAGE_URL, else the per-TF SQLite file).
    """
    import optuna

    jd = journal_dir()
    if jd:
        d = Path(os.path.expanduser(jd))
        d.mkdir(parents=True, exist_ok=True)
        # one file PER STUDY: independent campaigns never touch each other's log
        path = str(d / f"{study_name}.log")
        try:                                                    # optuna >= 4.0
            from optuna.storages.journal import JournalFileBackend
            backend = JournalFileBackend(path)
        except ImportError:                                     # older optuna
            backend = optuna.storages.JournalFileStorage(path)
        return optuna.storages.JournalStorage(backend)

    url = storage_url(sqlite_db_path)
    return optuna.storages.RDBStorage(url=url, engine_kwargs=engine_kwargs(url))


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
