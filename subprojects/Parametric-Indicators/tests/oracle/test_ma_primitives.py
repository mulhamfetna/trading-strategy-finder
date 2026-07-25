"""Independent-oracle tests for the moving-average primitives (indicators/calc/ma.py).

Oracles are re-derived here (local EMA loop, pandas rolling, numpy polyfit) — NOT imported from the
production code — so a bug in calc/ma.py cannot hide behind a shared implementation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd

from indicators.calc import ma
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
C, V = D["close"], D["volume"]


def _ema_ref(x, n):
    a = 2.0 / (n + 1.0)
    out = np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1.0 - a) * out[i - 1]
    return out


def _wma_ref(x, n):
    w = np.arange(1, n + 1)
    return pd.Series(x).rolling(n).apply(lambda s: np.dot(s, w) / w.sum(), raw=True).to_numpy()


def _close(a, b):
    m = ~np.isnan(b)
    assert m.sum() > 50
    assert np.allclose(a[m], b[m], atol=1e-8), np.nanmax(np.abs(a[m] - b[m]))


def test_dema():
    e = _ema_ref(C, 20)
    _close(ma.dema(C, 20), 2.0 * e - _ema_ref(e, 20))


def test_tema():
    e = _ema_ref(C, 20)
    e2 = _ema_ref(e, 20)
    e3 = _ema_ref(e2, 20)
    _close(ma.tema(C, 20), 3.0 * e - 3.0 * e2 + e3)


def test_tma():
    n = 10                                   # ceil(10/2)=5, floor(10/2)+1=6
    o = pd.Series(pd.Series(C).rolling(5).mean()).rolling(6).mean().to_numpy()
    _close(ma.tma(C, n), o)


def test_hma():
    n = 16
    o = _wma_ref(2.0 * _wma_ref(C, n // 2) - _wma_ref(C, n), int(np.sqrt(n)))
    _close(ma.hma(C, n), o)


def test_zlema():
    n, = (14,)
    lag = (n - 1) // 2
    d = C.copy()
    d[lag:] = 2.0 * C[lag:] - C[:-lag]
    _close(ma.zlema(C, n), _ema_ref(d, n))


def test_sine_wma():
    n = 20
    k = np.arange(n)
    w = np.sin(np.pi * (k + 1) / (n + 1))
    w /= w.sum()
    o = pd.Series(C).rolling(n).apply(lambda s: np.dot(s, w), raw=True).to_numpy()
    _close(ma.sine_wma(C, n), o)


def test_vwma():
    n = 20
    num = pd.Series(C * V).rolling(n).sum().to_numpy()
    den = pd.Series(V).rolling(n).sum().to_numpy()
    _close(ma.vwma(C, V, n), num / den)


def test_lsma():
    n = 14
    out = np.full(len(C), np.nan)
    for i in range(n - 1, len(C)):
        y = C[i - n + 1:i + 1]
        b, a = np.polyfit(np.arange(n), y, 1)
        out[i] = a + b * (n - 1)
    _close(ma.lsma(C, n), out)


def test_alma():
    n, offset, sigma = 9, 0.85, 6.0
    m = offset * (n - 1)
    s = n / sigma
    k = np.arange(n)
    w = np.exp(-((k - m) ** 2) / (2.0 * s * s))
    w /= w.sum()
    o = pd.Series(C).rolling(n).apply(lambda z: np.dot(z, w), raw=True).to_numpy()
    _close(ma.alma(C, n, offset, sigma), o)


def test_t3_coeffs_sum_to_one_and_constant_fixed_point():
    const = np.full(120, 42.0)
    out = ma.t3(const, 10, 0.7)
    assert np.allclose(out[-1], 42.0, atol=1e-6)   # coeffs sum to 1 ⇒ MA of constant is the constant


def test_kama_properties():
    n, fast, slow = 10, 2, 30
    out = ma.kama(C, n, fast, slow)
    assert np.isnan(out[:n]).all() and out[n] == C[n]     # NaN warm-up + seed
    const = np.full(60, 7.0)
    assert np.allclose(ma.kama(const, n, fast, slow)[n:], 7.0, atol=1e-9)  # constant fixed point


def test_vidya_properties():
    n = 14
    out = ma.vidya(C, n)
    assert np.isnan(out[:n]).all() and out[n] == C[n]
    const = np.full(60, 5.0)
    assert np.allclose(ma.vidya(const, n)[n:], 5.0, atol=1e-9)


def test_mcginley_properties():
    out = ma.mcginley(C, 14)
    assert out[0] == C[0] and not np.isnan(out).any()
    const = np.full(50, 3.0)
    assert np.allclose(ma.mcginley(const, 14), 3.0, atol=1e-9)   # x/md==1 ⇒ no adjustment


def test_evwma_properties():
    n = 20
    out = ma.evwma(C, V, n)
    assert np.isnan(out[:n - 1]).all() and out[n - 1] == C[n - 1]
    const = np.full(60, 9.0)
    assert np.allclose(ma.evwma(const, V[:60], n)[n - 1:], 9.0, atol=1e-9)
