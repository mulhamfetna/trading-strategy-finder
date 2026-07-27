"""Task 3 parity gate: accelerated `dfa` reproduces the reference VOTE exactly (issue #54).

`np.polyfit` (reference) uses LAPACK lstsq, so the closed-form fast path is not bit-identical at the
float level. The contract that matters is the downstream vote — `both_veto(isfinite(alpha) & (alpha <
threshold))` — so we assert (a) the finite mask matches, (b) alpha is float-close, and (c) the vote
boolean is IDENTICAL across the entire threshold grid [0.30, 0.70] step 0.01. The server harness re-runs
this on the true 486,970-bar 1-minute frame before the accelerator is trusted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Parametric-Indicators root

import numpy as np
import pytest

from indicators.calc import quant as Q
from optimize.perf import cold_accel


def _random_walk(seed: int = 0, n_bars: int = 6000) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # NQ-like level with mixed persistent/anti-persistent stretches so alpha spans the threshold grid
    steps = rng.normal(0.0, 3.0, n_bars)
    steps[: n_bars // 3] = np.cumsum(rng.normal(0.0, 0.3, n_bars // 3))  # a trendy stretch
    return 21000.0 + np.cumsum(steps)


THRESHOLDS = np.round(np.arange(0.30, 0.7001, 0.01), 2)


@pytest.mark.parametrize("n", [100, 200])
def test_dfa_fast_reproduces_vote_boolean(n):
    close = _random_walk(seed=n, n_bars=6000)
    ref = Q.dfa_reference(close, n)      # the original loop (oracle)
    fast = Q.dfa(close, n)               # what the DFA indicator now actually calls

    assert fast.shape == ref.shape
    fin_ref, fin_fast = np.isfinite(ref), np.isfinite(fast)
    assert np.array_equal(fin_ref, fin_fast), "finite/NaN warm-up mask differs"

    # float-closeness on the finite region (closed-form vs LAPACK lstsq)
    assert np.allclose(ref[fin_ref], fast[fin_fast], rtol=1e-6, atol=1e-8), "alpha not float-close"

    # THE gate: identical veto vote for every threshold on the grid
    for thr in THRESHOLDS:
        vote_ref = fin_ref & (ref < thr)
        vote_fast = fin_fast & (fast < thr)
        flips = int(np.sum(vote_ref != vote_fast))
        assert flips == 0, f"n={n} thr={thr}: {flips} vote bars flipped"


def test_dfa_fast_matches_reference_shape_on_short_input():
    close = _random_walk(seed=1, n_bars=300)
    assert cold_accel.dfa_fast(close, 100).shape == Q.dfa_reference(close, 100).shape


def test_dfa_indicator_votes_match_reference_end_to_end():
    """The gate at the level that actually matters: the DFA Indicator's emitted veto directions."""
    from indicators import library
    from indicators.runner import market_context
    import pandas as pd

    close = _random_walk(seed=7, n_bars=4000)
    df = pd.DataFrame({"Date": pd.date_range("2020", periods=len(close), freq="min"),
                       "Open": close, "High": close + 2, "Low": close - 2,
                       "Close": close, "Volume": np.ones(len(close))})
    ctx = market_context(df)
    ind = library.from_specs([{"key": "dfa", "enabled": True, "mode": "veto",
                               "params": {"n": 100, "threshold": 0.5}}])[0]
    cdir_fast, vdir_fast = ind.directions(ctx)

    # recompute what the reference implementation would have voted
    from indicators import votes as V
    ref_alpha = Q.dfa_reference(close, 100)
    cdir_ref, vdir_ref = V.both_veto(np.isfinite(ref_alpha) & (ref_alpha < 0.5))
    assert np.array_equal(np.asarray(vdir_fast), np.asarray(vdir_ref))
    assert np.array_equal(np.asarray(cdir_fast), np.asarray(cdir_ref))
