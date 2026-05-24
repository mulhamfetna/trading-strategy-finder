"""SQLite persistence for Optuna studies.

Studies are stored in a SQLite DB shared across studies (single file).
Study names double as `study_id` — opaque to the caller but human-readable
when inspected with sqlite3.

The optimiser writes every trial to the DB so that server restarts can
auto-resume in-progress studies (see GET /api/optimize/studies).
"""
from __future__ import annotations

from typing import Dict, List

import optuna


def storage_url(db_path: str) -> str:
    """Translate a filesystem path into an Optuna-friendly RFC 1738 SQLite URL."""
    return f'sqlite:///{db_path}'


def create_study(study_name: str, db_path: str) -> optuna.Study:
    """Create a new persistent multi-objective study using NSGA-II.

    Direction map: PF is maximised, MaxDD is maximised (less negative → closer
    to zero). The caller passes the raw dollar drawdown (non-positive) so the
    'maximize' direction picks the candidate with the smallest |drawdown|.
    """
    return optuna.create_study(
        study_name=study_name,
        storage=storage_url(db_path),
        sampler=optuna.samplers.NSGAIISampler(),
        directions=['maximize', 'maximize'],
        load_if_exists=False,
    )


def load_study(study_name: str, db_path: str) -> optuna.Study:
    """Re-attach to an existing study by name."""
    return optuna.load_study(
        study_name=study_name,
        storage=storage_url(db_path),
    )


def list_studies(db_path: str) -> List[Dict]:
    """Return a summary record for every study in the DB.

    Each record: {study_id, trials_done, trials_total, started_at, is_complete,
                  pareto_size}.
    """
    summaries: List[Dict] = []
    for summary in optuna.get_all_study_summaries(storage=storage_url(db_path)):
        try:
            study = load_study(study_name=summary.study_name, db_path=db_path)
        except KeyError:
            continue
        trials_done = sum(
            1 for t in study.trials
            if t.state in (
                optuna.trial.TrialState.COMPLETE,
                optuna.trial.TrialState.PRUNED,
                optuna.trial.TrialState.FAIL,
            )
        )
        trials_total = study.user_attrs.get('trials_total', trials_done)
        started_at = study.user_attrs.get('started_at', '')
        try:
            pareto_size = len(study.best_trials)
        except (ValueError, RuntimeError):
            pareto_size = 0
        summaries.append({
            'study_id': summary.study_name,
            'trials_done': trials_done,
            'trials_total': int(trials_total),
            'started_at': started_at,
            'is_complete': trials_done >= int(trials_total),
            'pareto_size': pareto_size,
        })
    return summaries
