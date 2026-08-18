"""Tier 2 helper — completed-trial count for a study, for target-based / idempotent runs + the watchdog.

Prints the number of COMPLETED trials (values not None) for `<prefix>_<tf>`, honouring the Tier-1 storage
URL (WSH_STORAGE_URL if set, else the per-TF sqlite file with the legacy-shared fallback). Prints 0 if the
study or store is absent — so the launcher can compute `remaining = target - completed` and decide whether
to (re)spawn a worker. Quiet by design (no fallback chatter) so the launcher can capture a clean integer.

CLI:  python3 optimize/trial_count.py <tf> [--prefix wsh4]
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import optuna  # noqa: E402
from optimize import storage as study_storage  # noqa: E402

_STUDIES = _HERE / "studies"
_INSTRUMENT = os.environ.get("WSI_INSTRUMENT", "NQ")   # NQ (default) or ES; non-NQ → suffixed study/db
_SUF = "" if _INSTRUMENT == "NQ" else f"_{_INSTRUMENT}"


def _quiet_url(tf: str, study_name: str) -> str:
    """Resolve the storage URL WITHOUT printing (mirrors optimizer._db_for's per-TF + shared fallback,
    then defers to the Tier-1 helper so WSH_STORAGE_URL still wins)."""
    per = _STUDIES / f"wsh_{tf}{_SUF}.db"
    shared = _STUDIES / "wsh.db"

    def _has(db: Path) -> bool:
        try:
            return db.exists() and study_name in [
                r[0] for r in sqlite3.connect(str(db)).execute("SELECT study_name FROM studies")]
        except Exception:
            return False

    db = shared if (not per.exists() and _has(shared)) else per
    return study_storage.storage_url(db)


def completed(prefix: str, tf: str) -> int:
    """Completed-trial count for `<prefix>_<tf>` (0 if the study/store is absent or unreadable)."""
    name = f"{prefix}_{tf}{_SUF}"
    try:
        study = optuna.load_study(study_name=name, storage=_quiet_url(tf, name))
        return sum(1 for t in study.trials if t.values is not None)
    except Exception:
        return 0


if __name__ == "__main__":
    import argparse
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    ap = argparse.ArgumentParser()
    ap.add_argument("tf")
    ap.add_argument("--prefix", default="wsh4")
    a = ap.parse_args()
    print(completed(a.prefix, a.tf))
