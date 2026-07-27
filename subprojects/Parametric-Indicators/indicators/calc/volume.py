"""Volume / money-flow primitives (pure, causal). Return float arrays; NaN/soft-seed during warm-up."""
from __future__ import annotations

import numpy as np

from .. import classic
from ..classic import ema as _ema
from ..classic import sma as _sma
from .osc import _shift, nan_sma, roll_sum_safe


def _mfm(high, low, close):
    """Money-flow multiplier ((C−L)−(H−C))/(H−L); 0 where H==L."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        m = ((c - l) - (h - c)) / rng
    m[rng == 0] = 0.0
    return m


def ad_line(high, low, close, volume):
    return np.cumsum(_mfm(high, low, close) * np.asarray(volume, float))


def cmf(high, low, close, volume, n):
    v = np.asarray(volume, float)
    return roll_sum_safe(_mfm(high, low, close) * v, n) / roll_sum_safe(v, n)


def chaikin_osc(high, low, close, volume, fast, slow):
    ad = ad_line(high, low, close, volume)
    return _ema(ad, fast) - _ema(ad, slow)


def pvt(close, volume):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    out = np.zeros(len(c))
    for i in range(1, len(c)):
        out[i] = out[i - 1] + (c[i] - c[i - 1]) / c[i - 1] * v[i]
    return out


def tvi(close, volume, min_tick):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    out = np.zeros(len(c))
    direction = 1
    for i in range(1, len(c)):
        ch = c[i] - c[i - 1]
        if ch > min_tick:
            direction = 1
        elif ch < -min_tick:
            direction = -1
        out[i] = out[i - 1] + (v[i] if direction > 0 else -v[i])
    return out


def nvi(close, volume):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    out = np.full(len(c), 1000.0)
    for i in range(1, len(c)):
        out[i] = out[i - 1] * (1.0 + (c[i] - c[i - 1]) / c[i - 1]) if v[i] < v[i - 1] else out[i - 1]
    return out


def pvi(close, volume):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    out = np.full(len(c), 1000.0)
    for i in range(1, len(c)):
        out[i] = out[i - 1] * (1.0 + (c[i] - c[i - 1]) / c[i - 1]) if v[i] > v[i - 1] else out[i - 1]
    return out


def eom(high, low, volume, n, scale=1e6):
    h, l, v = map(lambda a: np.asarray(a, float), (high, low, volume))
    hl2 = (h + l) / 2.0
    dist = hl2 - _shift(hl2, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        box = (v / scale) / (h - l)
        emv = dist / box
    return nan_sma(emv, n)


def force_index(close, volume, n):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    dc = np.zeros(len(c))
    dc[1:] = np.diff(c)
    return _ema(dc * v, n)


def klinger(high, low, close, volume, fast, slow, signal):
    h, l, c, v = map(lambda a: np.asarray(a, float), (high, low, close, volume))
    N = len(c)
    hlc = (h + l + c) / 3.0
    trend = np.zeros(N)
    for i in range(1, N):
        trend[i] = 1.0 if hlc[i] > hlc[i - 1] else -1.0
    dm = h - l
    cm = np.zeros(N)
    for i in range(1, N):
        cm[i] = cm[i - 1] + dm[i] if trend[i] == trend[i - 1] else dm[i - 1] + dm[i]
    with np.errstate(invalid="ignore", divide="ignore"):
        vf = v * np.abs(2.0 * (dm / cm - 1.0)) * trend * 100.0
    vf[~np.isfinite(vf)] = 0.0
    kvo = _ema(vf, fast) - _ema(vf, slow)
    return kvo, _ema(kvo, signal)


def vol_osc(volume, fast, slow):
    v = np.asarray(volume, float)
    ef, es = _ema(v, fast), _ema(v, slow)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * (ef - es) / es


def vzo(close, volume, n):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    dc = np.zeros(len(c))
    dc[1:] = np.sign(np.diff(c))
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * _ema(dc * v, n) / _ema(v, n)


def demand_index(close, volume, n):
    """Simplified demand/pressure index ∈ [−1,1]: EMA(up-volume) vs EMA(down-volume)."""
    c, v = np.asarray(close, float), np.asarray(volume, float)
    dc = np.zeros(len(c))
    dc[1:] = np.diff(c)
    bp = _ema(np.where(dc > 0, v, 0.0), n)
    sp = _ema(np.where(dc < 0, v, 0.0), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (bp - sp) / (bp + sp)


def twiggs_mf(high, low, close, volume, n):
    h, l, c, v = map(lambda a: np.asarray(a, float), (high, low, close, volume))
    trh = np.maximum(h, _shift(c, 1))
    trl = np.minimum(l, _shift(c, 1))
    with np.errstate(invalid="ignore", divide="ignore"):
        adc = (2.0 * c - trh - trl) / (trh - trl) * v
    return roll_sum_safe(adc, n) / roll_sum_safe(v, n)


def wvad(openp, high, low, close, volume, n):
    o, h, l, c, v = map(lambda a: np.asarray(a, float), (openp, high, low, close, volume))
    with np.errstate(invalid="ignore", divide="ignore"):
        bar = (c - o) / (h - l) * v
    bar[~np.isfinite(bar)] = 0.0
    return roll_sum_safe(bar, n)


def bw_mfi(high, low, volume):
    """Bill Williams MFI regime stance: +1 green (mfi↑ & vol↑), −1 fade (mfi↓ & vol↓), else 0."""
    h, l, v = map(lambda a: np.asarray(a, float), (high, low, volume))
    with np.errstate(invalid="ignore", divide="ignore"):
        mfi = (h - l) / v
    pm, pv = _shift(mfi, 1), _shift(v, 1)
    st = np.zeros(len(v))
    mfi_up, v_up = mfi > pm, v > pv
    st[mfi_up & v_up] = 1.0
    st[(~mfi_up) & (~v_up) & np.isfinite(pm)] = -1.0
    return st


def volume_ratio_asia(close, volume, n):
    c, v = np.asarray(close, float), np.asarray(volume, float)
    dc = np.zeros(len(c))
    dc[1:] = np.diff(c)
    up = np.where(dc > 0, v, 0.0) + np.where(dc == 0, 0.5 * v, 0.0)
    dn = np.where(dc < 0, v, 0.0) + np.where(dc == 0, 0.5 * v, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * roll_sum_safe(up, n) / roll_sum_safe(dn, n)


def anchored_vwap(high, low, close, volume, session_id):
    return classic.vwap(high, low, close, volume, session_id)
