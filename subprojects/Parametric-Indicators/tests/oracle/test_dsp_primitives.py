"""Tests for Tier-2 DSP primitives (indicators/calc/dsp.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from indicators.calc import dsp
from tests.oracle.fixture import ohlcv

C = ohlcv(300)["close"]


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
