"""Optuna SQLite persistence + auto-resume behaviour."""

import os
import sys

import optuna
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.persistence import (
    create_study,
    list_studies,
    load_study,
    storage_url,
)


def test_create_and_load_study(tmp_path):
    db_path = tmp_path / 'studies.db'
    study = create_study(study_name='test-1', db_path=str(db_path))
    assert study.study_name == 'test-1'
    # Suggest + complete one trial so the study has state.
    trial = study.ask()
    x = trial.suggest_float('x', 0.0, 1.0)
    study.tell(trial, [x, -x])

    # Re-load by name.
    reloaded = load_study(study_name='test-1', db_path=str(db_path))
    assert len(reloaded.trials) == 1


def test_list_studies_includes_summary(tmp_path):
    db_path = tmp_path / 'studies.db'
    s1 = create_study(study_name='alpha', db_path=str(db_path))
    s2 = create_study(study_name='beta', db_path=str(db_path))
    # Each study runs one trial.
    for s in (s1, s2):
        t = s.ask()
        v = t.suggest_float('x', 0.0, 1.0)
        s.tell(t, [v, -v])

    studies = list_studies(db_path=str(db_path))
    names = {s['study_id'] for s in studies}
    assert names == {'alpha', 'beta'}


def test_storage_url_format(tmp_path):
    db_path = tmp_path / 'foo.db'
    url = storage_url(str(db_path))
    assert url.startswith('sqlite:///')
    assert url.endswith('foo.db')
