"""Forward-return mechanics, both dumb controls, bootstrap CI and the power floor."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.informativeness import (               # noqa: E402
    block_bootstrap_ci, block_bootstrap_diff_ci, control_date, control_location,
    directional_forward_returns, min_detectable_effect,
)

_PAIRS = [("DU", "DL", "D")]


def test_directional_forward_returns_signs_and_nans():
    df = pd.DataFrame({
        "Date": pd.date_range("2025-01-02", periods=4, freq="4h"),
        "Close": [100.0, 110.0, 105.0, 130.0],
    })
    sig = np.array(["long", "short", "hold", "long"], dtype=object)
    r = directional_forward_returns(df, sig, horizon=1)
    assert r[0] == 10.0          # long, +10 -> +10
    assert r[1] == 5.0           # short, price fell 5 -> +5 in signal direction
    assert np.isnan(r[2])        # hold -> no measurement
    assert np.isnan(r[3])        # no bar after the last one


def test_control_location_preserves_zone_width():
    box = pd.DataFrame({"Date": pd.date_range("2025-01-02", periods=5, freq="D"),
                        "DU": np.full(5, 110.0), "DL": np.full(5, 100.0)}).set_index("Date", drop=False)
    out = control_location(box, _PAIRS, np.random.default_rng(0), frac=0.02)
    width_in = (box["DU"] - box["DL"]).to_numpy()
    width_out = (out["DU"] - out["DL"]).to_numpy()
    assert np.allclose(width_in, width_out)                      # width preserved
    assert not np.allclose(box["DU"].to_numpy(), out["DU"].to_numpy())   # location moved


def test_control_date_is_a_permutation_of_the_same_rows():
    box = pd.DataFrame({"Date": pd.date_range("2025-01-02", periods=6, freq="D"),
                        "DU": np.arange(6, dtype=float) + 100,
                        "DL": np.arange(6, dtype=float) + 90}).set_index("Date", drop=False)
    out = control_date(box, _PAIRS, np.random.default_rng(1))
    assert sorted(out["DU"].tolist()) == sorted(box["DU"].tolist())      # same multiset
    assert out.index.equals(box.index)                                    # dates unchanged


def test_block_bootstrap_ci_brackets_the_mean_of_a_constant_series():
    x = np.full(200, 7.0)
    lo, hi = block_bootstrap_ci(x, block=20, n_boot=200, alpha=0.10,
                                rng=np.random.default_rng(2))
    assert lo <= 7.0 <= hi


def test_block_bootstrap_ci_is_deterministic_for_a_fixed_seed():
    x = np.random.default_rng(9).normal(0, 1, 300)
    a = block_bootstrap_ci(x, 20, 200, 0.10, np.random.default_rng(3))
    b = block_bootstrap_ci(x, 20, 200, 0.10, np.random.default_rng(3))
    assert a == b


def test_diff_ci_detects_a_real_separation():
    rng = np.random.default_rng(11)
    x = rng.normal(10.0, 1.0, 500)      # clearly higher
    y = rng.normal(0.0, 1.0, 500)
    point, lo, hi = block_bootstrap_diff_ci(x, y, 20, 300, 0.10, np.random.default_rng(12))
    assert point > 9.0
    assert lo > 0.0, "a genuine +10 separation must exclude zero"


def test_diff_ci_includes_zero_for_identical_distributions():
    rng = np.random.default_rng(13)
    x = rng.normal(0.0, 1.0, 500)
    y = rng.normal(0.0, 1.0, 500)
    _point, lo, hi = block_bootstrap_diff_ci(x, y, 20, 300, 0.10, np.random.default_rng(14))
    assert lo <= 0.0 <= hi, "no true difference must not be called significant"


def test_min_detectable_effect_shrinks_as_n_grows():
    rng = np.random.default_rng(4)
    small = min_detectable_effect(rng.normal(0, 1, 100))
    large = min_detectable_effect(rng.normal(0, 1, 10000))
    assert large < small
