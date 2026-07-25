"""Ichimoku + session-pivot primitives (pure, causal).

Pivots use the PRIOR completed session's OHLC (from session_id), so they are constant within a session
and never peek into the current one. Ichimoku spans are read at their displaced (past) position."""
from __future__ import annotations

import numpy as np

from ..classic import _roll_max, _roll_min
from .osc import _shift


def _mid(high, low, n):
    return (_roll_max(high, n) + _roll_min(low, n)) / 2.0


def ichimoku_lines(high, low, t, k, b):
    tenkan = _mid(high, low, t)
    kijun = _mid(high, low, k)
    span_a = (tenkan + kijun) / 2.0
    span_b = _mid(high, low, b)
    return tenkan, kijun, span_a, span_b


def cloud_past(high, low, t, k, b, shift=26):
    """Leading spans read at the current bar = spans computed `shift` bars ago (causal Kumo)."""
    _, _, span_a, span_b = ichimoku_lines(high, low, t, k, b)
    return _shift(span_a, shift), _shift(span_b, shift)


def prior_session_ohlc(openp, high, low, close, session_id):
    """Per-bar (O,H,L,C) of the most recent COMPLETED session before this bar (NaN until one exists)."""
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    sid = np.asarray(session_id)
    N = len(c)
    pO = np.full(N, np.nan); pH = np.full(N, np.nan); pL = np.full(N, np.nan); pC = np.full(N, np.nan)
    prev = (np.nan, np.nan, np.nan, np.nan)
    cur_sid = None
    co = ch = cl = cc = np.nan
    for i in range(N):
        if cur_sid is None or sid[i] != cur_sid:
            if cur_sid is not None:
                prev = (co, ch, cl, cc)
            cur_sid, co, ch, cl, cc = sid[i], o[i], h[i], l[i], c[i]
        else:
            ch, cl, cc = max(ch, h[i]), min(cl, l[i]), c[i]
        pO[i], pH[i], pL[i], pC[i] = prev
    return pO, pH, pL, pC


def floor_pp(pH, pL, pC):
    return (pH + pL + pC) / 3.0


def woodie_pp(pH, pL, pC):
    return (pH + pL + 2.0 * pC) / 4.0


def demark_pp(pO, pH, pL, pC):
    x = np.where(pC < pO, pH + 2.0 * pL + pC, np.where(pC > pO, 2.0 * pH + pL + pC, pH + pL + 2.0 * pC))
    return x / 4.0


def camarilla_bands(pH, pL, pC):
    rng = pH - pL
    return pC + rng * 1.1 / 4.0, pC - rng * 1.1 / 4.0     # R3, S3


def fib_levels(pH, pL, pC):
    pp = floor_pp(pH, pL, pC)
    rng = pH - pL
    return pp + 0.382 * rng, pp - 0.382 * rng             # R1(fib), S1(fib)


def cpr_levels(pH, pL, pC):
    pp = floor_pp(pH, pL, pC)
    bc = (pH + pL) / 2.0
    tc = 2.0 * pp - bc
    return np.maximum(tc, bc), np.minimum(tc, bc)         # top, bottom of central range
