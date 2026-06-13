"""Tier 3 — pre-flight contention smoke test.

Spawns N worker PROCESSES that hammer ONE shared Optuna store with a few trials each, then asserts ZERO
workers died on a storage lock (`StorageInternalError`, e.g. SQLite "database is locked"). Run this before
any multi-hour sweep — it reproduces the wsh4 failure mode in ~seconds and fails loudly if the store can't
take the concurrency. Complements the parity gate.

  python3 optimize/contention_smoke.py                       # default: 12 workers × 8 trials on a temp sqlite (WAL+timeout)
  python3 optimize/contention_smoke.py --workers 30 --trials 20 --url "$WSH_STORAGE_URL"   # e.g. Postgres pre-flight

Exit 0 ⇒ no lock deaths (safe to launch). Exit 1 ⇒ contention detected (do NOT launch the sweep).
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import sqlite3
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import optuna  # noqa: E402
from optuna.exceptions import StorageInternalError  # noqa: E402
from optimize import storage as study_storage  # noqa: E402

_STUDY = "contention_smoke"


def _worker(args) -> int:
    """One worker process: run `trials` trials against the shared store. 0=survived, 1=lock death, 2=other."""
    url, trials = args
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    try:
        st = optuna.storages.RDBStorage(url=url, engine_kwargs=study_storage.engine_kwargs(url))
        s = optuna.create_study(study_name=_STUDY, storage=st, direction="maximize", load_if_exists=True)
        # the catch= mirrors the production worker: a lock blip fails ONE trial, not the worker
        s.optimize(lambda t: t.suggest_float("x", 0.0, 1.0), n_trials=trials,
                   catch=(StorageInternalError,))
        return 0
    except StorageInternalError:
        return 1
    except Exception:
        return 2


def run_smoke(url: str, workers: int, trials: int) -> dict:
    """Returns {'workers','lock_deaths','other_deaths','ok'}; ok ⇔ no lock_deaths."""
    if study_storage.is_sqlite(url):                       # enable WAL once so readers/writer can coexist
        path = url.replace("sqlite:///", "")
        with sqlite3.connect(path) as c:
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA synchronous=NORMAL;")
    ctx = mp.get_context("spawn")                          # robust under pytest / mixed start methods
    with ctx.Pool(workers) as pool:
        res = pool.map(_worker, [(url, trials)] * workers)
    lock = sum(1 for r in res if r == 1)
    other = sum(1 for r in res if r == 2)
    return {"workers": workers, "lock_deaths": lock, "other_deaths": other, "ok": lock == 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--url", default=None, help="storage URL; default = a fresh temp sqlite file")
    a = ap.parse_args()
    url = a.url or f"sqlite:///{Path(tempfile.mkdtemp())/'contention_smoke.db'}"
    r = run_smoke(url, a.workers, a.trials)
    verdict = "OK ✓ no lock deaths" if r["ok"] else f"❌ {r['lock_deaths']} worker(s) died on a storage lock"
    print(f"contention smoke: {a.workers} workers × {a.trials} trials on {url}")
    print(f"  lock_deaths={r['lock_deaths']} other_deaths={r['other_deaths']} → {verdict}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
