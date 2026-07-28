"""Issue #14 — `--max-enabled` must not privilege indicators by their position in the REGISTRY.

The repair that enforces the cap used to keep "the first `max_enabled` in REGISTRY order". That reads
as neutral bookkeeping. It is not: the registry lists the ORIGINAL 18 indicators at positions 0-17 and
the 147 added by #12 from position 18 onward, so an original always won the tie.

Measured on a live 16,000-trial adopt-gate study before the fix: **0 of 1,500 sampled trials kept a
single new-library indicator**, and the ten most-kept keys were all registry positions 0-13. The search
built to evaluate the new library was testing only the old one, and would have produced a confident and
entirely meaningless verdict.

These tests fail loudly if that bias ever returns.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest

from indicators import library
from optimize.optimizer import _suggest_indicators

_R = list(library.REGISTRY)
_N_ORIGINAL = 18                      # positions 0..17 predate the #12 calc-indicator library


class _AllOnTrial:
    """Minimal Trial stub: enables every indicator and returns each param's default, so the ONLY thing
    under test is the cap-repair's choice of which to keep."""

    def __init__(self, number):
        self.number = number

    def suggest_categorical(self, name, choices):
        return True if name.startswith("en_") else choices[0]

    def suggest_int(self, name, lo, hi, step=1):
        return lo

    def suggest_float(self, name, lo, hi, step=None):
        return lo


def _kept_positions(n_trials=400, max_enabled=3):
    pos = []
    for i in range(n_trials):
        specs = _suggest_indicators(_AllOnTrial(i), max_enabled=max_enabled)
        on = [s["key"] for s in specs if s["enabled"]]
        assert len(on) == max_enabled, f"cap not enforced: {len(on)} enabled"
        pos += [_R.index(k) for k in on]
    return np.array(pos)


def test_cap_is_enforced_exactly():
    for cap in (1, 3, 5):
        specs = _suggest_indicators(_AllOnTrial(0), max_enabled=cap)
        assert sum(1 for s in specs if s["enabled"]) == cap


def test_kept_indicators_are_not_concentrated_at_the_front_of_the_registry():
    """The regression: with every flag on, the kept set must sample the WHOLE registry, not its head."""
    pos = _kept_positions()
    mean_pos = float(pos.mean())
    expected = (len(_R) - 1) / 2.0
    assert mean_pos > expected * 0.6, (
        f"kept indicators average registry position {mean_pos:.1f} vs {expected:.1f} expected under "
        f"an unbiased draw — the cap is privileging the front of the registry again")


def test_the_new_library_actually_gets_selected():
    """The number that mattered: before the fix this was 0.00%."""
    pos = _kept_positions()
    frac_new = float((pos >= _N_ORIGINAL).mean())
    expected = (len(_R) - _N_ORIGINAL) / len(_R)          # ~0.89
    assert frac_new > 0.5 * expected, (
        f"only {100*frac_new:.1f}% of kept indicators come from the new library "
        f"(expected ~{100*expected:.0f}% under an unbiased draw) — the search is not testing it")


@pytest.mark.parametrize("cap", [1, 3])
def test_repair_is_reproducible_for_a_given_trial(cap):
    """Same trial number ⇒ same repair, so resumes and re-scores stay stable."""
    a = [s["key"] for s in _suggest_indicators(_AllOnTrial(7), max_enabled=cap) if s["enabled"]]
    b = [s["key"] for s in _suggest_indicators(_AllOnTrial(7), max_enabled=cap) if s["enabled"]]
    assert a == b


def test_no_cap_leaves_everything_enabled():
    specs = _suggest_indicators(_AllOnTrial(0), max_enabled=None)
    assert sum(1 for s in specs if s["enabled"]) == len(_R)
