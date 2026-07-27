"""Tests for Tier-2 approximate/stateful primitives (indicators/calc/tier2.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from indicators.calc import tier2 as T2
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
H, L, C = D["high"], D["low"], D["close"]


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_jma_tracks_price_and_smooths():
    j = T2.jma(C, 14, 0, 2)
    assert not np.isnan(j).any()
    assert j.min() >= C.min() - 5 and j.max() <= C.max() + 5
    assert np.std(np.diff(j)) < np.std(np.diff(C))     # smoother than price


def test_jma_constant_fixed_point():
    const = np.full(200, 25.0)
    assert np.allclose(T2.jma(const, 14, 0, 2)[20:], 25.0, atol=1e-6)


def test_ewma_vol_positive():
    v = _fin(T2.ewma_vol(C, 0.94))
    assert v.min() >= 0 and len(v) > 200


def test_td_signals_are_ternary_and_fire():
    for s in (T2.td_sequential(C), T2.td_combo(C)):
        assert set(np.unique(s).tolist()).issubset({-1.0, 0.0, 1.0})
        assert (s != 0).sum() >= 1
    # combo (perfected) fires no more often than sequential
    assert (T2.td_combo(C) != 0).sum() <= (T2.td_sequential(C) != 0).sum()


def test_td_buy_setup_hand_case():
    # 4 warmup + 9 strictly-decreasing-vs-4-bars-ago closes ⇒ buy setup at bar 12
    c = np.array([100, 100, 100, 100, 99, 98, 97, 96, 95, 94, 93, 92, 91.0])
    s = T2.td_sequential(c)
    assert s[12] == 1.0


def test_kalman_tracks_and_smooths():
    k = T2.kalman(C, 0.001, 0.1)
    assert not np.isnan(k).any() and np.std(np.diff(k)) < np.std(np.diff(C))


def test_ou_coefficient_mostly_negative_on_meanreverting():
    # AR(1) mean-reverting series ⇒ OU coefficient b < 0
    rng = np.random.default_rng(1)
    x = np.zeros(400)
    for i in range(1, 400):
        x[i] = 10 + 0.7 * (x[i - 1] - 10) + rng.normal(0, 0.5)
    b = _fin(T2.ou_coefficient(x, 50))
    assert np.median(b) < 0
