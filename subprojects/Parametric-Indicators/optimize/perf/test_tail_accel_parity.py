"""Issue #56 parity gate: accelerated `autocorr` / `hurst_exp` reproduce the reference VOTE exactly.

Same contract as `dfa` (#54): the closed-form/Numba paths are not bit-identical to `np.corrcoef` /
per-bar numpy in the last float digits, so what is asserted is the DOWNSTREAM VETO DECISION —
  autocorr:  both_veto(isfinite(v) & (abs(v) < threshold)),  threshold grid [0.01, 0.50] step 0.01
  hurst_exp: both_veto(isfinite(v) & (v      < threshold)),  threshold grid [0.30, 0.70] step 0.01
must be identical at every threshold the optimizer can search.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pytest

from indicators import library
from indicators.calc import quant as Q


def _walk(seed=0, n_bars=6000):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 3.0, n_bars)
    steps[: n_bars // 3] = np.cumsum(rng.normal(0.0, 0.3, n_bars // 3))   # trendy stretch
    return 21000.0 + np.cumsum(steps)


def _grid(key, name):
    p = next(p for p in library.SCHEMA[key]["params"] if p["name"] == name)
    return np.round(np.arange(p["min"], p["max"] + 1e-9, p["step"]), 4)


def _assert_vote_identical(ref, fast, thresholds, absval=False):
    fin_r, fin_f = np.isfinite(ref), np.isfinite(fast)
    assert np.array_equal(fin_r, fin_f), "finite/NaN mask differs"
    assert np.allclose(ref[fin_r], fast[fin_f], rtol=1e-6, atol=1e-8), "values not float-close"
    r = np.abs(ref) if absval else ref
    f = np.abs(fast) if absval else fast
    for thr in thresholds:
        flips = int(np.sum((fin_r & (r < thr)) != (fin_f & (f < thr))))
        assert flips == 0, f"threshold {thr}: {flips} vote bars flipped"


@pytest.mark.parametrize("n", [10, 50, 200])
def test_autocorr_vote_identical(n):
    c = _walk(seed=n)
    _assert_vote_identical(Q.autocorr_reference(c, n), Q.autocorr(c, n),
                           _grid("autocorr", "threshold"), absval=True)


@pytest.mark.parametrize("n", [20, 100, 400])
def test_hurst_vote_identical(n):
    c = _walk(seed=n)
    _assert_vote_identical(Q.hurst_exp_reference(c, n), Q.hurst_exp(c, n),
                           _grid("hurst_exp", "threshold"))


@pytest.mark.parametrize("key,params", [
    ("autocorr", {"n": 50, "threshold": 0.1}),
    ("hurst_exp", {"n": 100, "threshold": 0.5}),
])
def test_indicator_directions_match_reference_end_to_end(key, params):
    """The gate at the level that matters: the Indicator object's emitted confirm/veto arrays."""
    import pandas as pd
    from indicators.runner import market_context
    from indicators import votes as V

    c = _walk(seed=7, n_bars=4000)
    df = pd.DataFrame({"Date": pd.date_range("2020", periods=len(c), freq="min"),
                       "Open": c, "High": c + 2, "Low": c - 2, "Close": c, "Volume": np.ones(len(c))})
    ctx = market_context(df)
    ind = library.from_specs([{"key": key, "enabled": True, "mode": "veto", "params": params}])[0]
    cdir_fast, vdir_fast = ind.directions(ctx)

    thr = float(params["threshold"])
    if key == "autocorr":
        ref = Q.autocorr_reference(c, int(params["n"]))
        mask = np.isfinite(ref) & (np.abs(ref) < thr)
    else:
        ref = Q.hurst_exp_reference(c, int(params["n"]))
        mask = np.isfinite(ref) & (ref < thr)
    cdir_ref, vdir_ref = V.both_veto(mask)
    assert np.array_equal(np.asarray(vdir_fast), np.asarray(vdir_ref))
    assert np.array_equal(np.asarray(cdir_fast), np.asarray(cdir_ref))
