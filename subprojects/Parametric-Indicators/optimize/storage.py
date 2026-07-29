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


# ────────────────────────────────────────────────────────────────────────────────────────────────────
# WHERE DOES A STUDY ACTUALLY LIVE? (2026-07-29)
#
# There are THREE possible backends — journal files, Postgres, and per-TF SQLite — selected by two
# environment variables that are usually unset. Nothing announced which one was live, and the study
# FILES are named identically regardless. That is not hypothetical: twice in one session a completed
# 12-study campaign was reported as LOST because Postgres was searched while the studies sat in SQLite.
#
# An empty result from one backend means "not here". It never means "nowhere".
# ────────────────────────────────────────────────────────────────────────────────────────────────────

# ── Optuna's INTERNAL tables, queried in exactly one place ──────────────────────────────────────────
# These helpers exist because `studies` and `trials` are Optuna's PRIVATE schema, and we read them
# directly rather than through Optuna's public API for a measured reason: get_all_study_summaries()
# hangs on this project once there are ~100+ studies. Bypassing it is correct — but it was previously
# open-coded in six modules, so an Optuna schema change would have broken six places silently, and
# nobody could see that we depended on a private schema at all. One definition, one place to fix.

def study_exists(db_path, study_name: str) -> bool:
    """True iff a study of this name lives in this SQLite file. Missing/corrupt file ⇒ False."""
    import sqlite3
    from pathlib import Path as _P
    if not _P(db_path).exists():
        return False
    try:
        con = sqlite3.connect(db_path)
        try:
            return con.execute("select 1 from studies where study_name = ?", (study_name,)).fetchone() is not None
        finally:
            con.close()
    except Exception:
        return False


def list_study_names(db_path) -> list[str]:
    """Every study name in this SQLite file (empty on a missing/unreadable file)."""
    import sqlite3
    from pathlib import Path as _P
    if not _P(db_path).exists():
        return []
    try:
        con = sqlite3.connect(db_path)
        try:
            return [r[0] for r in con.execute("select study_name from studies")]
        finally:
            con.close()
    except Exception:
        return []


def count_trials(db_path, study_name: str) -> int:
    """Number of trials recorded for a study in this SQLite file (0 if absent)."""
    import sqlite3
    from pathlib import Path as _P
    if not _P(db_path).exists():
        return 0
    try:
        con = sqlite3.connect(db_path)
        try:
            row = con.execute("select study_id from studies where study_name = ?", (study_name,)).fetchone()
            if not row:
                return 0
            return int(con.execute("select count(*) from trials where study_id = ?", (row[0],)).fetchone()[0])
        finally:
            con.close()
    except Exception:
        return 0


def describe_backend(sqlite_db_path=None) -> str:
    """One-line, human-readable description of the storage actually in use. Print this at study start."""
    jd = journal_dir()
    if jd:
        return f"journal files in {os.path.expanduser(jd)} (WSH_JOURNAL_DIR)"
    url = os.environ.get(ENV_VAR)
    if url:
        safe = url.split("@")[-1] if "@" in url else url        # never echo credentials
        return f"served RDB at {safe} ({ENV_VAR})"
    return f"SQLite file {sqlite_db_path} (default — {ENV_VAR} unset)"


def find_study(study_name: str, studies_dir=None, journal=None, url=None) -> list[dict]:
    """Search EVERY backend for a study and report where each copy lives.

    Answers "does this study exist?" without the caller having to know, or guess, which backend was in
    use when it was created. Returns one dict per location found: {backend, location, trials}.
    Never raises on an unreachable backend — an unreadable Postgres must not hide a SQLite hit.
    """
    import sqlite3
    out: list[dict] = []

    # 1. journal files — one .log per study
    jd = journal or journal_dir()
    if jd:
        p = Path(os.path.expanduser(jd)) / f"{study_name}.log"
        if p.exists():
            out.append({"backend": "journal", "location": str(p), "trials": None})

    # 2. served RDB (Postgres/MySQL)
    u = url or os.environ.get(ENV_VAR)
    if u:
        try:
            import sqlalchemy as sa
            eng = sa.create_engine(u, **engine_kwargs(u))
            with eng.connect() as c:
                row = c.execute(sa.text(
                    "select count(t.trial_id) from studies s left join trials t "
                    "on t.study_id = s.study_id where s.study_name = :n"), {"n": study_name}).scalar()
                if row is not None and int(row) >= 0:
                    exists = c.execute(sa.text(
                        "select 1 from studies where study_name = :n"), {"n": study_name}).scalar()
                    if exists:
                        out.append({"backend": "rdb", "location": u.split("@")[-1], "trials": int(row)})
        except Exception:
            pass                                                # unreachable RDB must not mask a hit

    # 3. per-TF SQLite files (the DEFAULT, and the one most often forgotten)
    sd = Path(studies_dir) if studies_dir else Path(__file__).resolve().parent / "studies"
    if sd.is_dir():
        for f in sorted(sd.glob("*.db")):
            try:
                con = sqlite3.connect(f)
                hit = con.execute("select study_id from studies where study_name = ?",
                                  (study_name,)).fetchone()
                if hit:
                    n = con.execute("select count(*) from trials where study_id = ?", (hit[0],)).fetchone()[0]
                    out.append({"backend": "sqlite", "location": str(f), "trials": int(n)})
                con.close()
            except Exception:
                continue
    return out


# ────────────────────────────────────────────────────────────────────────────────────────────────────
# REQUIRED POSTGRES TUNING (2026-07-11) — do not lose this when the DB is rebuilt.
#
#     ALTER DATABASE wsh SET synchronous_commit = off;
#
# Optuna issues ~70 commits PER TRIAL (one per searched param — 59 of them — plus 8 user_attrs and the
# trial create/complete). With the default synchronous_commit=on, every one of those waits for a WAL
# fsync, and profiling showed psycopg2 'commit' was **55% of ALL runtime** once the Numba SMC work
# removed the indicator cost. Turning it off measured **1.68x** solo / 1.14x at 20 workers.
#
# This is SAFE. It is NOT `fsync=off` and carries NO corruption risk: Postgres still writes the WAL, it
# just does not block waiting for the flush. The only exposure is losing the last ~200 ms of committed
# transactions on a hard crash/power-loss — i.e. a handful of trials out of 5,900, in a store whose
# campaigns are resumable and whose champions are re-derivable. Trading that for 1.68x is obviously right.
#
# Verify with:  docker exec wsh-pg psql -U wsh -d wsh -tAc "show synchronous_commit"
PG_TUNING_SQL = "ALTER DATABASE wsh SET synchronous_commit = off;"
