import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from indicators import votes
from indicators.base import BOTH


def test_band_directions_matches_rsi_at_mid_50():
    r = np.array([np.nan, 25.0, 45.0, 50.0, 55.0, 80.0])
    c1, v1 = votes.band_directions(r, 30, 70, 50.0)
    c2, v2 = votes.rsi_directions(r, 30, 70)
    assert np.array_equal(c1, c2) and np.array_equal(v1, v2)


def test_band_directions_custom_mid():
    # Williams %R style: range -100..0, mid -50
    wr = np.array([-90.0, -60.0, -50.0, -40.0, -10.0])
    c, v = votes.band_directions(wr, lower=-80, upper=-20, mid=-50.0)
    # -90 <= -80 -> oversold long; -60 in (-80,-50) bearish short; -50 == mid neutral;
    # -40 in (-50,-20) bullish long; -10 >= -20 overbought short
    assert list(c) == [1, -1, 0, 1, -1]
    assert list(v) == [-1, 1, 0, -1, 1]


def test_magnitude_veto_flags_low_ratio_both_sides():
    val = np.array([1.0, 1.0, 1.0])
    ref = np.array([2.0, 1.0, np.nan])
    c, v = votes.magnitude_veto(val, ref, threshold=0.8)  # 0.5<0.8 veto; 1.0 no; nan no
    assert v[0] == BOTH and v[1] == 0 and v[2] == 0 and not c.any()


def test_both_veto_sets_both_on_mask():
    m = np.array([False, True, False])
    c, v = votes.both_veto(m)
    assert v[1] == BOTH and v[0] == 0 and v[2] == 0 and not c.any()
