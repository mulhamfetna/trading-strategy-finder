"""study_signals must reproduce the production rule EXACTLY when handed the production level set,
and must refuse to run without an explicit `pairs` argument."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from engine import _LEVEL_PAIRS                                   # noqa: E402
from optimize.signals import decision_signals                     # noqa: E402
from research.daily_boxes.study_signals import study_signals      # noqa: E402


def _synthetic(seed: int, n_bars: int = 400):
    """Random-but-deterministic decision frame + box frame covering it."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-02 18:00", periods=n_bars, freq="4h")
    close = 20000 + np.cumsum(rng.normal(0, 25, n_bars))
    open_ = close + rng.normal(0, 15, n_bars)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 10, n_bars))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 10, n_bars))
    df_dec = pd.DataFrame({"Date": dates, "Open": open_, "High": high,
                           "Low": low, "Close": close})

    box_dates = pd.date_range("2025-01-01", periods=n_bars, freq="D").normalize()
    mid = 20000 + np.cumsum(rng.normal(0, 30, len(box_dates)))
    box = pd.DataFrame({"Date": box_dates})
    # every W/M/D column the rule may look at, as a band around `mid`
    for u, l, _lab in _LEVEL_PAIRS:
        half = rng.uniform(10, 60, len(box_dates))
        box[u] = mid + half
        box[l] = mid - half
    return df_dec, box.set_index("Date", drop=False)


def test_pairs_argument_is_required():
    df_dec, box = _synthetic(0)
    with pytest.raises(TypeError):
        study_signals(df_dec, box)          # type: ignore[call-arg]


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_production_on_the_production_level_set(seed):
    df_dec, box = _synthetic(seed)
    got = study_signals(df_dec, box, _LEVEL_PAIRS)
    ref = decision_signals(df_dec, box)
    assert len(got) == len(ref) == len(df_dec)
    mismatch = [(i, g, r) for i, (g, r) in enumerate(zip(got, ref)) if g != r]
    assert not mismatch, f"seed={seed}: {len(mismatch)} mismatches, first={mismatch[:3]}"


def test_empty_frame_returns_empty():
    _, box = _synthetic(0)
    empty = pd.DataFrame({"Date": [], "Open": [], "High": [], "Low": [], "Close": []})
    assert len(study_signals(empty, box, _LEVEL_PAIRS)) == 0


def test_subset_of_pairs_produces_no_more_signals_than_the_full_set():
    df_dec, box = _synthetic(7)
    full = study_signals(df_dec, box, _LEVEL_PAIRS)
    half = study_signals(df_dec, box, _LEVEL_PAIRS[:4])
    assert (half != "hold").sum() <= (full != "hold").sum()
