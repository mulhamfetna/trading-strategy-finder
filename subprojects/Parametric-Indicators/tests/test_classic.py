"""TDD — Group A classic-indicator math, checked against hand-computed values on a tiny series.

Series (7 bars):
  close  = [10, 11, 12, 11, 10, 12, 13]
  volume = [100,110,120, 90, 80,130,140]
"""
import numpy as np

from indicators import classic

CLOSE = np.array([10, 11, 12, 11, 10, 12, 13], dtype=float)
HIGH = np.array([10.5, 11.5, 12.5, 11.5, 10.5, 12.5, 13.5], dtype=float)
LOW = np.array([9.5, 10.5, 11.5, 10.5, 9.5, 11.5, 12.5], dtype=float)
VOL = np.array([100, 110, 120, 90, 80, 130, 140], dtype=float)


def _assert(actual, expected):
    a = np.asarray(actual, dtype=float)
    e = np.asarray(expected, dtype=float)
    assert a.shape == e.shape, f"shape {a.shape} != {e.shape}"
    # NaN positions must match; finite values close.
    assert np.array_equal(np.isnan(a), np.isnan(e)), f"NaN mask differs:\n{a}\n{e}"
    m = ~np.isnan(e)
    assert np.allclose(a[m], e[m], atol=1e-6), f"values differ:\n{a}\n{e}"


def test_sma_n3():
    exp = [np.nan, np.nan, 11.0, 34/3, 11.0, 11.0, 35/3]
    _assert(classic.sma(CLOSE, 3), exp)


def test_ema_n3_seeded_with_first_close():
    # alpha = 0.5, EMA[0]=close[0]=10
    exp = [10.0, 10.5, 11.25, 11.125, 10.5625, 11.28125, 12.140625]
    _assert(classic.ema(CLOSE, 3), exp)


def test_rma_n3_seeded_with_first_value():
    # alpha = 1/3, RMA[0]=10
    r = [10.0]
    for x in CLOSE[1:]:
        r.append((r[-1] * 2 + x) / 3)
    _assert(classic.rma(CLOSE, 3), r)


def test_obv_signed_volume_accumulation():
    exp = [0.0, 110.0, 230.0, 140.0, 60.0, 190.0, 330.0]
    _assert(classic.obv(CLOSE, VOL), exp)


def test_rsi_n3_wilder():
    # deltas +1+1-1-1+2+1; avg gain/loss SMA-seeded at n then RMA-smoothed.
    exp = [np.nan, np.nan, np.nan, 66.666667, 44.444444, 72.222222, 79.797980]
    _assert(classic.rsi(CLOSE, 3), exp)


def test_true_range():
    exp = [1.0, 1.5, 1.5, 1.5, 1.5, 2.5, 1.5]
    _assert(classic.true_range(HIGH, LOW, CLOSE), exp)


def test_atr_n3_rma_of_tr():
    exp = [1.0, 1.166667, 1.277778, 1.351852, 1.401235, 1.767490, 1.678327]
    _assert(classic.atr(HIGH, LOW, CLOSE, 3), exp)


def test_macd_composition_contract():
    # MACD locks the documented composition over the verified ema().
    fast, slow, sig = 2, 3, 2
    line, signal, hist = classic.macd(CLOSE, fast, slow, sig)
    exp_line = classic.ema(CLOSE, fast) - classic.ema(CLOSE, slow)
    exp_signal = classic.ema(exp_line, sig)
    _assert(line, exp_line)
    _assert(signal, exp_signal)
    _assert(hist, exp_line - exp_signal)


def test_stochastic_n3_d3():
    k_exp = [np.nan, np.nan, 250/3, 25.0, 50/3, 250/3, 87.5]
    d_exp = [np.nan, np.nan, np.nan, np.nan, 125/3, 125/3, 62.5]
    k, d = classic.stochastic(HIGH, LOW, CLOSE, 3, 3)
    _assert(k, k_exp)
    _assert(d, d_exp)


def test_cci_n3():
    exp = [np.nan, np.nan, 100.0, -50.0, -100.0, 100.0, 80.0]
    _assert(classic.cci(HIGH, LOW, CLOSE, 3), exp)


def test_bollinger_contract():
    n, k = 3, 2.0
    mid, up, lo = classic.bollinger(CLOSE, n, k)
    _assert(mid, classic.sma(CLOSE, n))
    # independent rolling population std
    std = np.full(len(CLOSE), np.nan)
    for t in range(n - 1, len(CLOSE)):
        std[t] = np.std(CLOSE[t - n + 1:t + 1])  # ddof=0
    _assert(up - mid, k * std)
    _assert(mid - lo, k * std)


def test_keltner_contract():
    n, m = 3, 2.0
    mid, up, lo = classic.keltner(HIGH, LOW, CLOSE, n, m)
    _assert(mid, classic.ema(CLOSE, n))
    a = classic.atr(HIGH, LOW, CLOSE, n)
    _assert(up - mid, m * a)
    _assert(mid - lo, m * a)


def test_vwap_single_and_multi_session():
    sess = np.array([0, 0, 0, 1, 1, 1, 1])
    tp = (HIGH + LOW + CLOSE) / 3.0
    out = classic.vwap(HIGH, LOW, CLOSE, VOL, sess)
    # hand: per-session cumulative tp*vol / cumulative vol
    exp = np.full(len(CLOSE), np.nan)
    cpv = cv = 0.0
    cur = None
    for t in range(len(CLOSE)):
        if sess[t] != cur:
            cur = sess[t]; cpv = cv = 0.0
        cpv += tp[t] * VOL[t]; cv += VOL[t]
        exp[t] = cpv / cv
    _assert(out, exp)


def test_mfi_n3_contract():
    n = 3
    tp = (HIGH + LOW + CLOSE) / 3.0
    flow = tp * VOL
    pos = np.zeros(len(tp)); neg = np.zeros(len(tp))
    for t in range(1, len(tp)):
        if tp[t] > tp[t - 1]:
            pos[t] = flow[t]
        elif tp[t] < tp[t - 1]:
            neg[t] = flow[t]
    exp = np.full(len(tp), np.nan)
    for t in range(n, len(tp)):
        p = pos[t - n + 1:t + 1].sum(); q = neg[t - n + 1:t + 1].sum()
        ratio = np.inf if q == 0 else p / q
        exp[t] = 100.0 - 100.0 / (1.0 + ratio)
    _assert(classic.mfi(HIGH, LOW, CLOSE, VOL, n), exp)


def test_adx_dm_logic_and_contract():
    n = 3
    adxv, pdi, mdi = classic.adx(HIGH, LOW, CLOSE, n)
    # independent +DM/-DM via explicit loop
    pdm = np.zeros(len(CLOSE)); ndm = np.zeros(len(CLOSE))
    for t in range(1, len(CLOSE)):
        up = HIGH[t] - HIGH[t - 1]
        dn = LOW[t - 1] - LOW[t]
        pdm[t] = up if (up > dn and up > 0) else 0.0
        ndm[t] = dn if (dn > up and dn > 0) else 0.0
    tr = classic.true_range(HIGH, LOW, CLOSE)
    atr_ = classic.rma(tr, n)
    exp_pdi = 100.0 * classic.rma(pdm, n) / atr_
    exp_mdi = 100.0 * classic.rma(ndm, n) / atr_
    _assert(pdi, exp_pdi)
    _assert(mdi, exp_mdi)
    dx = 100.0 * np.abs(exp_pdi - exp_mdi) / (exp_pdi + exp_mdi)
    _assert(adxv, classic.rma(dx, n))
