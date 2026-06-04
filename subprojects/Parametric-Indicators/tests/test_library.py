"""TDD — indicator library classes + the orchestrator (build_gate), incl. the parity invariant."""
import numpy as np

from indicators import confirm, library, votes
from indicators.base import IndicatorConfig, LONG, SHORT, HOLD, MarketContext


def test_stance_directions():
    c, v = votes.stance_directions([+1, -1, 0])
    np.testing.assert_array_equal(c, [+1, -1, 0])
    np.testing.assert_array_equal(v, [-1, +1, 0])


def _trend_ctx():
    # strictly rising closes ⇒ EMA fast > slow, close above fast ⇒ bullish stance after warm-up
    close = np.arange(1, 31, dtype=float) * 10
    z = close
    return MarketContext(open=close, high=close + 1, low=close - 1, close=close,
                         volume=np.full(30, 100.0))


def test_ema_trend_bullish_on_uptrend():
    ind = library.EMATrend(IndicatorConfig(enabled=True, params={"fast": 3, "slow": 5}))
    st = ind.stance(_trend_ctx())
    assert st[-1] == 1                      # clear uptrend at the end
    assert set(np.unique(st)).issubset({-1, 0, 1})


def test_adx_no_trend_vetoes_both_sides():
    # choppy/oscillating market ⇒ ADX defined but low ⇒ veto either direction
    n = 40
    close = 100.0 + (np.arange(n) % 2)      # 100,101,100,101,... (range-bound)
    ctx = MarketContext(open=close, high=close + 0.5, low=close - 0.5, close=close,
                        volume=np.full(n, 100.0))
    ind = library.ADXVeto(IndicatorConfig(enabled=True, mode="veto", params={"n": 5, "threshold": 25}))
    box = np.full(n, LONG)
    vote = ind.vote(ctx, box)
    assert (vote[-5:] == -1).all()          # vetoes the long in the flat tail
    box_s = np.full(n, SHORT)
    assert (ind.vote(ctx, box_s)[-5:] == -1).all()   # and vetoes the short too


def test_build():
    assert isinstance(library.build("rsi"), library.RSIZone)


# ---- orchestrator ----
def _ctx(n):
    z = np.zeros(n)
    return MarketContext(open=z, high=z, low=z, close=z, volume=z)


def test_build_gate_no_active_is_parity():
    box = np.array([LONG, SHORT, HOLD, LONG])
    base = np.array([True, False, True, True])
    # disabled indicator present but inactive ⇒ gate == base
    disabled = library.RSIZone(IndicatorConfig(enabled=False))
    gate, votes_arr, active = confirm.build_gate(_ctx(4), box, [disabled], k=1, base_gate=base)
    np.testing.assert_array_equal(gate, base)
    assert active.tolist() == [False]
    assert votes_arr.shape == (1, 4)        # still computed (for logging)


def test_build_gate_empty_indicators_is_parity():
    box = np.array([LONG, LONG])
    base = np.array([True, False])
    gate, _, _ = confirm.build_gate(_ctx(2), box, [], k=1, base_gate=base)
    np.testing.assert_array_equal(gate, base)


class _FixedVote(library.Indicator):
    key = "fv"
    def __init__(self, votes, config=None):
        super().__init__(config)
        self._votes = np.asarray(votes, dtype=np.int8)
    def directions(self, ctx):
        return np.zeros(0), np.zeros(0)
    def vote(self, ctx, box_dir):
        return self._votes


def test_build_gate_active_indicator_narrows_gate():
    box = np.array([LONG, LONG, LONG, LONG])
    base = np.array([True, True, True, True])
    fv = _FixedVote([+1, -1, 0, +1], IndicatorConfig(enabled=True))
    gate, _, active = confirm.build_gate(_ctx(4), box, [fv], k=1, base_gate=base)
    np.testing.assert_array_equal(gate, [True, False, False, True])  # confirm, veto, no-confirm, confirm
    assert active.tolist() == [True]
