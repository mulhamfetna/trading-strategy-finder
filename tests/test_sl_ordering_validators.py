"""Regression lock for the SL ordering invariants (user rule 2026-05-24).

`BoxParamsModel._sl_ordering` enforces:
  - sl_hard_points > sl_soft_points (strict)
  - soft_sl_confirmation_timeframe_minutes > hard_sl_confirmation_timeframe_minutes (strict)

Both rules raise pydantic.ValidationError when violated, which the FastAPI
exception handler maps to a 422 with `code='request-validation-error'`.
"""
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.schemas import BoxParamsModel
from tests._fixtures import box_params_dict


def _base():
    """A complete BoxParamsModel payload that PASSES every validator —
    use it as a starting point and override fields per test."""
    return box_params_dict()


def test_default_payload_passes():
    """Sanity: the playbook defaults must satisfy the invariants."""
    BoxParamsModel(**_base())


def test_rejects_hard_le_soft_points():
    """sl_hard_points <= sl_soft_points → ValidationError."""
    body = _base()
    body['sl_soft_points'] = 200.0
    body['sl_hard_points'] = 200.0   # equal — must reject (strict >)
    with pytest.raises(ValidationError) as exc:
        BoxParamsModel(**body)
    assert 'sl_hard_points' in str(exc.value)


def test_rejects_soft_tf_le_hard_tf():
    """soft_sl_tf <= hard_sl_tf → ValidationError."""
    body = _base()
    body['soft_sl_confirmation_timeframe_minutes'] = 1
    body['hard_sl_confirmation_timeframe_minutes'] = 2  # soft confirms FASTER, invalid
    with pytest.raises(ValidationError) as exc:
        BoxParamsModel(**body)
    assert 'soft_sl_confirmation_timeframe_minutes' in str(exc.value)


def test_rejects_equal_timeframes():
    """Strict >: timeframes equal must reject."""
    body = _base()
    body['soft_sl_confirmation_timeframe_minutes'] = 2
    body['hard_sl_confirmation_timeframe_minutes'] = 2
    with pytest.raises(ValidationError):
        BoxParamsModel(**body)


def test_minimum_valid_ordering_passes():
    """Tightest valid pair: hard=1pt-more-than-soft, soft_tf=1min-more-than-hard_tf."""
    body = _base()
    body['sl_soft_points'] = 100.0
    body['sl_hard_points'] = 101.0
    body['soft_sl_confirmation_timeframe_minutes'] = 2
    body['hard_sl_confirmation_timeframe_minutes'] = 1
    BoxParamsModel(**body)  # no raise
