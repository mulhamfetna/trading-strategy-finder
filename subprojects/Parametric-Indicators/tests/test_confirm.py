"""TDD — the vote-mapping logic and the confirmation aggregator (K rule)."""
import numpy as np
import pytest

from indicators import confirm, votes
from indicators.base import (CONFIRM, VETO, NEUTRAL, LONG, SHORT, HOLD,
                             Indicator, IndicatorConfig, IndicatorParamError, MarketContext)


# ---- IndicatorConfig validation (no silent fallback) ----
def test_config_rejects_bad_mode():
    with pytest.raises(IndicatorParamError):
        IndicatorConfig(mode="sometimes").validate()


# retrace + wait are GLOBAL now (validated in strategy.validate_params), not per-indicator —
# IndicatorConfig no longer carries them. See tests/test_build_payload.py for global validation.


# ---- RSI direction zones ----
def test_rsi_directions_zones():
    vals = np.array([np.nan, 25, 35, 55, 75, 50])
    cdir, vdir = votes.rsi_directions(vals, lower=30, upper=70)
    np.testing.assert_array_equal(cdir, [0, +1, -1, +1, -1, 0])
    np.testing.assert_array_equal(vdir, [0, -1, +1, -1, +1, 0])


# ---- vote() mode filtering, via a fixed-direction test double ----
class _Fixed(Indicator):
    key = "fixed"

    def __init__(self, cdir, vdir, config=None):
        super().__init__(config)
        self._c = np.asarray(cdir, dtype=np.int8)
        self._v = np.asarray(vdir, dtype=np.int8)

    def directions(self, ctx):
        return self._c, self._v


def _ctx(n):
    z = np.zeros(n)
    return MarketContext(open=z, high=z, low=z, close=z, volume=z)


def test_vote_both_mode_veto_overrides_confirm():
    # bar0: confirm long; bar1: veto long; bar2: confirm AND veto long -> veto wins
    f = _Fixed(cdir=[+1, 0, +1], vdir=[0, +1, +1], config=IndicatorConfig(mode="both"))
    box = np.array([LONG, LONG, LONG])
    np.testing.assert_array_equal(f.vote(_ctx(3), box), [CONFIRM, VETO, VETO])


def test_vote_confirm_mode_ignores_veto():
    f = _Fixed(cdir=[+1, 0, +1], vdir=[0, +1, +1], config=IndicatorConfig(mode="confirm"))
    box = np.array([LONG, LONG, LONG])
    np.testing.assert_array_equal(f.vote(_ctx(3), box), [CONFIRM, NEUTRAL, CONFIRM])


def test_vote_veto_mode_ignores_confirm():
    f = _Fixed(cdir=[+1, 0, +1], vdir=[0, +1, +1], config=IndicatorConfig(mode="veto"))
    box = np.array([LONG, LONG, LONG])
    np.testing.assert_array_equal(f.vote(_ctx(3), box), [NEUTRAL, VETO, VETO])


def test_vote_neutral_when_box_is_hold():
    f = _Fixed(cdir=[+1], vdir=[-1], config=IndicatorConfig(mode="both"))
    np.testing.assert_array_equal(f.vote(_ctx(1), np.array([HOLD])), [NEUTRAL])


def test_vote_short_direction():
    # indicator supports short on bar0, supports long (=> veto short) on bar1
    f = _Fixed(cdir=[-1, +1], vdir=[+1, -1], config=IndicatorConfig(mode="both"))
    box = np.array([SHORT, SHORT])
    np.testing.assert_array_equal(f.vote(_ctx(2), box), [CONFIRM, VETO])


# ---- vote is now RAW (no per-indicator wait debounce; global wait is a 1-min entry delay) ----
def test_vote_is_raw_no_decision_bar_debounce():
    # confirm long on every bar ⇒ confirm on EVERY bar (wait no longer suppresses on decision bars)
    f = _Fixed(cdir=[+1, +1, +1], vdir=[0, 0, 0], config=IndicatorConfig(mode="both"))
    box = np.array([LONG, LONG, LONG])
    np.testing.assert_array_equal(f.vote(_ctx(3), box), [CONFIRM, CONFIRM, CONFIRM])


# ---- aggregate() K rule ----
def test_aggregate_k1_veto_any_and_confirm_count():
    votes_arr = np.array([[+1, -1, 0, +1],
                          [+1, +1, +1, -1]])
    active = np.array([True, True])
    np.testing.assert_array_equal(confirm.aggregate(votes_arr, active, k=1), [True, False, True, False])


def test_aggregate_k2_needs_two_confirms():
    votes_arr = np.array([[+1, -1, 0, +1],
                          [+1, +1, +1, -1]])
    active = np.array([True, True])
    np.testing.assert_array_equal(confirm.aggregate(votes_arr, active, k=2), [True, False, False, False])


def test_aggregate_inactive_indicator_ignored():
    votes_arr = np.array([[+1, -1, 0, +1],
                          [+1, +1, +1, -1]])  # second ignored
    active = np.array([True, False])
    np.testing.assert_array_equal(confirm.aggregate(votes_arr, active, k=1), [True, False, False, True])
