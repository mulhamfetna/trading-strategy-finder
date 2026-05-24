"""Schema validation tests for the NSGA-II optimiser endpoints.

No-fallback rule: every field is required. A request missing any field
must raise pydantic.ValidationError; a complete request must validate.
"""

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.schemas import (
    OptimizeBudget,
    OptimizeFoldsConfig,
    OptimizeRequest,
    OptimizeSearchSpace,
    ParetoPoint,
    StudySummary,
    TrialResult,
)
from tests._fixtures import box_params_dict


def _complete_search_space() -> dict:
    return {
        'sl_soft_points': [50.0, 300.0],
        'sl_hard_delta': [50.0, 600.0],
        'tp_target_points': [75.0, 250.0],
    }


def test_optimize_request_accepts_complete_payload():
    body = {
        'baseline_params': box_params_dict(),
        'search_space': _complete_search_space(),
        'budget': {'population_size': 40, 'generations': 15},
        'folds': {'count': 3, 'min_trades_per_fold': 15},
        'data_path': 'NQ_4h.csv',
        'box_data_path': 'NQ_full_data.csv',
        'max_duration_s': 1800,
    }
    req = OptimizeRequest(**body)
    assert req.budget.population_size == 40
    assert req.folds.count == 3


def test_optimize_request_rejects_missing_budget():
    body = {
        'baseline_params': box_params_dict(),
        'search_space': _complete_search_space(),
        # 'budget' missing
        'folds': {'count': 3, 'min_trades_per_fold': 15},
        'data_path': 'NQ_4h.csv',
        'box_data_path': 'NQ_full_data.csv',
        'max_duration_s': 1800,
    }
    with pytest.raises(ValidationError):
        OptimizeRequest(**body)


def test_search_space_rejects_inverted_range():
    # sl_soft_points lower > upper
    with pytest.raises(ValidationError):
        OptimizeSearchSpace(
            sl_soft_points=[300.0, 50.0],
            sl_hard_delta=[50.0, 600.0],
            tp_target_points=[75.0, 250.0],
        )


def test_trial_result_complete_shape():
    tr = TrialResult(
        trial_number=42,
        params={'sl_soft_points': 180.0, 'sl_hard_points': 280.0, 'tp_target_points': 175.0},
        values=[1.84, -2300.0],
        state='complete',
        pruned_reason=None,
    )
    assert tr.state == 'complete'


def test_pareto_point_requires_all_fields():
    with pytest.raises(ValidationError):
        ParetoPoint(trial_number=1, params={'a': 1.0})  # values missing


def test_study_summary_describes_resumable_study():
    s = StudySummary(
        study_id='abc123',
        trials_done=247,
        trials_total=600,
        started_at='2026-05-23T18:42:00Z',
        is_complete=False,
        pareto_size=12,
    )
    assert s.is_complete is False
