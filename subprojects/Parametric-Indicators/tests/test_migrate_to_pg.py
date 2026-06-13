"""Deploy helper test — migrate_to_pg.migrate() copies studies SQLite→dest and is idempotent.

Uses sqlite→sqlite (a stand-in for sqlite→Postgres; `optuna.copy_study` is storage-agnostic) so it runs
with no server. Verifies: a study is copied with all its trials, and a second run skips it.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

import optuna  # noqa: E402
from optimize import migrate_to_pg  # noqa: E402


def _seed(studies_dir: Path, tf: str, n: int):
    db = studies_dir / f"wsh_{tf}.db"
    s = optuna.create_study(study_name=f"wsh4_{tf}", storage=f"sqlite:///{db}",
                            directions=["maximize"], load_if_exists=True)
    s.optimize(lambda t: t.suggest_float("x", 0, 1), n_trials=n)


def test_migrate_copies_and_is_idempotent(tmp_path):
    studies = tmp_path / "studies"; studies.mkdir()
    _seed(studies, "4h", 5)
    dest = f"sqlite:///{tmp_path/'dest.db'}"

    r1 = migrate_to_pg.migrate("wsh4", ["4h"], dest, studies_dir=studies)
    assert r1[0][1] == "copied", r1
    assert len(optuna.load_study(study_name="wsh4_4h", storage=dest).trials) == 5

    # second run: already in destination → skip (idempotent)
    r2 = migrate_to_pg.migrate("wsh4", ["4h"], dest, studies_dir=studies)
    assert r2[0][1] == "skip", r2


def test_missing_source_reports_error_not_crash(tmp_path):
    studies = tmp_path / "studies"; studies.mkdir()
    dest = f"sqlite:///{tmp_path/'dest.db'}"
    r = migrate_to_pg.migrate("wsh4", ["2m"], dest, studies_dir=studies)  # no source study
    assert r[0][1] == "ERROR"
