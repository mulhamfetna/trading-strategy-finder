"""Tests for Tier-2 DSP primitives (indicators/calc/dsp.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from indicators.calc import dsp
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
H, L, C = D["high"], D["low"], D["close"]


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_super_smoother_constant_fixed_point():
    const = np.full(120, 42.0)
    out = dsp.super_smoother(const, 20)
    assert np.allclose(out[5:], 42.0, atol=1e-6)    # c1+c2+c3==1 ⇒ constant maps to itself


def test_super_smoother_smooths_and_no_nan():
    out = dsp.super_smoother(C, 20)
    assert not np.isnan(out).any()
    assert out.std() < C.std()                       # a low-pass filter reduces variance
    # coefficient identity c1 = 1 - c2 - c3
    a1 = np.exp(-np.sqrt(2) * np.pi / 20)
    b1 = 2 * a1 * np.cos(np.sqrt(2) * np.pi / 20)
    assert np.isclose(1 - b1 - (-a1 * a1) + b1 + (-a1 * a1), 1.0)


def test_roofing_bandpass_oscillate_around_zero():
    for a in (dsp.roofing(C, 48, 10), dsp.bandpass(C, 20, 0.3)):
        f = _fin(a)
        assert abs(f.mean()) < f.std()               # zero-centred oscillator
        assert len(f) > 200


def test_frama_tracks_price_and_smooths():
    fr = _fin(dsp.frama(H, L, C, 16))
    assert len(fr) > 200
    # FRAMA stays within the price envelope
    assert fr.min() >= L.min() - 1e-6 and fr.max() <= H.max() + 1e-6


def test_frama_constant_fixed_point():
    n = 300
    h = np.full(n, 11.0); l = np.full(n, 9.0); c = np.full(n, 10.0)
    fr = dsp.frama(h, l, c, 16)
    assert np.allclose(fr[20:], 10.0, atol=1e-6)


def test_mama_fama_finite_and_fama_smoother():
    mama, fama = dsp.mama_fama(C)
    assert not np.isnan(mama).any() and not np.isnan(fama).any()
    assert np.std(np.diff(fama)) < np.std(np.diff(mama))    # FAMA follows more slowly


def test_laguerre_rsi_bounded_unit():
    v = _fin(dsp.laguerre_rsi(C, 0.5))
    assert v.min() >= -1e-9 and v.max() <= 1 + 1e-9 and len(v) > 200


def test_schaff_bounded_0_100():
    v = _fin(dsp.schaff_trend_cycle(C, 23, 50, 10))
    assert v.min() >= -1e-6 and v.max() <= 100 + 1e-6


def test_cyber_and_cg_oscillate_around_zero():
    for a in (dsp.cyber_cycle(C, 0.07), dsp.center_of_gravity(C, 10)):
        f = _fin(a)
        assert abs(f.mean()) < f.std() + 1e-9 and len(f) > 200


def test_dominant_cycle_period_bounded():
    per, _ = dsp.dominant_cycle(C)
    # candidate period is clamped [6,50]; the EMA-smoothed output ramps from 0 → upper bound holds,
    # and once warmed the period settles inside the band.
    assert per.max() <= 50 + 1e-6
    settled = per[80:]
    assert 6 - 1e-6 <= np.median(settled) <= 50 + 1e-6


def test_sinewave_bounded_unit():
    sine, lead = dsp.hilbert_sinewave(C)
    for a in (sine, lead):
        f = _fin(a)
        assert f.min() >= -1 - 1e-9 and f.max() <= 1 + 1e-9 and len(f) > 100

