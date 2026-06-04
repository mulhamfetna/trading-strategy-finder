"""TDD — the vote-mapping logic and the confirmation aggregator (K rule)."""
import numpy as np
import pytest

from indicators import confirm, votes
from indicators.base import (CONFIRM, VETO, NEUTRAL, LONG, SHORT, HOLD, apply_wait,
                             Indicator, IndicatorConfig, IndicatorParamError, MarketContext)


# ---- IndicatorConfig validation (no silent fallback) ----
def test_config_rejects_bad_mode():
    with pytest.raises(IndicatorParamError):
        IndicatorConfig(mode="sometimes").validate()


def test_config_rejects_negative_wait_and_bad_unit():
    with pytest.raises(IndicatorParamError):
        IndicatorConfig(wait_bars=-1).validate()
    with pytest.raises(IndicatorParamError):
        IndicatorConfig(retrace_unit="percent").validate()


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


# ---- wait_bars debounce on confirms ----
def test_apply_wait_delays_confirm_runs():
    v = np.array([CONFIRM, CONFIRM, CONFIRM, VETO, CONFIRM, CONFIRM], dtype=np.int8)
    # wait_bars=2 ⇒ confirm only on the 3rd consecutive; veto immediate; run resets after veto
    np.testing.assert_array_equal(apply_wait(v, 2), [0, 0, CONFIRM, VETO, 0, 0])


def test_apply_wait_zero_is_identity():
    v = np.array([CONFIRM, VETO, CONFIRM], dtype=np.int8)
    np.testing.assert_array_equal(apply_wait(v, 0), v)


def test_vote_applies_wait_bars():
    # confirm long on every bar, wait_bars=1 ⇒ first confirm suppressed, then live
    f = _Fixed(cdir=[+1, +1, +1], vdir=[0, 0, 0], config=IndicatorConfig(mode="both", wait_bars=1))
    box = np.array([LONG, LONG, LONG])
    np.testing.assert_array_equal(f.vote(_ctx(3), box), [NEUTRAL, CONFIRM, CONFIRM])


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
