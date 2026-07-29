"""Deploy helper — migrate Optuna studies from the per-TF SQLite files into a destination store
(e.g. PostgreSQL) via `optuna.copy_study`. Used once when cutting the optimizer over to Postgres.

The SOURCE is always the SQLite files (per-TF `wsh_<tf>.db`, else the legacy shared `wsh.db`) — it does
NOT consult WSH_STORAGE_URL (that points at the DESTINATION during a migration). Idempotent: a study
already present in the destination is skipped, so re-running is safe.

  python3 optimize/migrate_to_pg.py --prefix wsh4 --dest "$WSH_STORAGE_URL" 4h 2h 1h 15m 5m 2m
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import optuna  # noqa: E402
from optimize import storage  # noqa: E402  — the ONE module that knows Optuna's private table names

_STUDIES = _HERE / "studies"


def _src_sqlite_url(tf: str, study_name: str, studies_dir: Path) -> str:
    """SOURCE url: per-TF `wsh_<tf>.db` if it holds the study, else legacy shared `wsh.db`. No env check."""
    per = studies_dir / f"wsh_{tf}.db"
    shared = studies_dir / "wsh.db"

    def _has(db: Path) -> bool:
        try:
            return db.exists() and study_name in [
                r for r in storage.list_study_names(db)]   # storage owns Optuna's private table names
        except Exception:
            return False

    db = per if _has(per) else (shared if _has(shared) else per)
    return f"sqlite:///{db}"


def _exists_in_dest(name: str, dest_url: str) -> bool:
    try:
        optuna.load_study(study_name=name, storage=dest_url)
        return True
    except Exception:
        return False


def migrate(prefix: str, tfs, dest_url: str, studies_dir: Path = _STUDIES) -> list:
    """Copy each `<prefix>_<tf>` study SQLite→dest. Returns [(tf, status, detail)]."""
    out = []
    for tf in tfs:
        name = f"{prefix}_{tf}"
        if _exists_in_dest(name, dest_url):
            out.append((tf, "skip", "already in destination"))
            continue
        src = _src_sqlite_url(tf, name, studies_dir)
        try:
            optuna.copy_study(from_study_name=name, from_storage=src,
                              to_storage=dest_url, to_study_name=name)
            n = len(optuna.load_study(study_name=name, storage=dest_url).trials)
            out.append((tf, "copied", f"{n} trials from {src}"))
        except Exception as e:
            out.append((tf, "ERROR", f"{type(e).__name__}: {e}"))
    return out


if __name__ == "__main__":
    import argparse
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    ap = argparse.ArgumentParser()
    ap.add_argument("tfs", nargs="+")
    ap.add_argument("--prefix", default="wsh4")
    ap.add_argument("--dest", required=True, help="destination storage URL (e.g. postgresql://…)")
    a = ap.parse_args()
    rows = migrate(a.prefix, a.tfs, a.dest)
    ok = sum(1 for _, s, _ in rows if s in ("copied", "skip"))
    for tf, status, detail in rows:
        print(f"  {tf:>4s}  {status:7s}  {detail}")
    print(f"migrate: {ok}/{len(rows)} ok")
    raise SystemExit(0 if ok == len(rows) else 1)
