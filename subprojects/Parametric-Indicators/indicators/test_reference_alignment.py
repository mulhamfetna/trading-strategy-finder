"""Guard tests for causal cross-instrument reference alignment (runner.market_context ref_df)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from indicators import runner


def _frame(dates, close):
    return pd.DataFrame({"Date": pd.to_datetime(dates), "Open": close, "High": close,
                         "Low": close, "Close": close, "Volume": np.ones(len(close))})


def test_reference_aligns_backward_same_timestamp():
    d = pd.date_range("2025-01-01", periods=5, freq="D")
    dec = _frame(d, [1.0, 2, 3, 4, 5])
    ref = _frame(d, [10.0, 20, 30, 40, 50])
    ctx = runner.market_context(dec, ref_df=ref)
    assert np.array_equal(ctx.ref_close, [10, 20, 30, 40, 50])   # exact same-timestamp match


def test_reference_uses_last_prior_bar_when_missing():
    dec = _frame(pd.date_range("2025-01-01", periods=4, freq="D"), [1.0, 2, 3, 4])
    # reference missing day 2 (2025-01-02) ⇒ that decision bar must reuse day 1's ref, not day 3's
    ref = _frame(["2025-01-01", "2025-01-03", "2025-01-04"], [10.0, 30, 40])
    ctx = runner.market_context(dec, ref_df=ref)
    assert list(ctx.ref_close) == [10.0, 10.0, 30.0, 40.0]       # ffill from PAST only


def test_no_lookahead_future_ref_bars_cannot_change_the_past():
    d = pd.date_range("2025-01-01", periods=10, freq="D")
    dec = _frame(d, np.arange(10.0))
    ref = _frame(d, np.arange(100.0, 110.0))
    base = runner.market_context(dec, ref_df=ref).ref_close.copy()
    # Mutate the reference's FUTURE bars (indices 5..9) arbitrarily
    ref2 = ref.copy()
    ref2.loc[5:, "Close"] = [999, 888, 777, 666, 555]
    mutated = runner.market_context(dec, ref_df=ref2).ref_close
    # early decision bars (0..4) must be byte-identical — no future leak
    assert np.array_equal(base[:5], mutated[:5])


def test_leading_unmatched_is_nan():
    dec = _frame(pd.date_range("2025-01-01", periods=3, freq="D"), [1.0, 2, 3])
    ref = _frame(["2025-01-02", "2025-01-03"], [20.0, 30])       # no ref for day 1
    ctx = runner.market_context(dec, ref_df=ref)
    assert np.isnan(ctx.ref_close[0]) and ctx.ref_close[1] == 20.0


def test_none_ref_leaves_ref_close_none():
    dec = _frame(pd.date_range("2025-01-01", periods=3, freq="D"), [1.0, 2, 3])
    assert runner.market_context(dec).ref_close is None


def test_needs_ref_indicator_inactive_without_reference():
    """#19 framework fix: a cross-series (needs_ref) indicator with no ctx.ref_close is INACTIVE — it
    never tightens the K-rule. With a reference it becomes active and constrains the gate."""
    from indicators import confirm, library
    from indicators.base import MarketContext
    n = 160
    rng = np.random.default_rng(0)
    close = np.cumsum(rng.normal(0, 1, n)) + 100
    ref = close * 1.3 + np.cumsum(rng.normal(0, 0.3, n))
    box_dir = np.tile([1, -1, 0, 1], n // 4).astype(np.int8)
    ind = library.from_specs([{"key": "cointegration", "enabled": True, "mode": "both",
                               "params": {"n": 50, "lower": -2, "upper": 2}}])[0]
    z = np.ones(n)
    g0, _, active0 = confirm.build_gate(MarketContext(close, close, close, close, z, None, None),
                                        box_dir, [ind], k=1)
    assert active0[0] == np.False_ and g0.all()          # inactive ⇒ no constraint ⇒ everything allowed
    g1, _, active1 = confirm.build_gate(MarketContext(close, close, close, close, z, None, ref),
                                        box_dir, [ind], k=1)
    assert active1[0] == np.True_ and not np.array_equal(g0, g1)   # active ⇒ it changes the gate
