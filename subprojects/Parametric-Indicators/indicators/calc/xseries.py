"""Cross-series primitives: primary close `c` vs an aligned reference close `r` (both same length).
Reference NaNs (leading, from causal alignment) propagate to NaN output for that window."""
from __future__ import annotations

import numpy as np


def _returns(x):
    d = np.full(len(x), np.nan)
    d[1:] = np.diff(np.asarray(x, dtype=float))
    return d


def rolling_corr(c, r, n):
    """Rolling Pearson correlation of the two return series over n."""
    rc, rr = _returns(c), _returns(r)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n, N):
        a, b = rc[i - n + 1:i + 1], rr[i - n + 1:i + 1]
        if np.isnan(a).any() or np.isnan(b).any():
            continue
        sa, sb = a.std(), b.std()
        if sa > 0 and sb > 0:
            out[i] = np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb)
    return out


def rolling_beta(c, r, n):
    """Rolling OLS beta of primary returns on reference returns (cov/var) over n."""
    rc, rr = _returns(c), _returns(r)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n, N):
        a, b = rc[i - n + 1:i + 1], rr[i - n + 1:i + 1]
        if np.isnan(a).any() or np.isnan(b).any():
            continue
        vb = b.var()
        if vb > 0:
            out[i] = np.mean((a - a.mean()) * (b - b.mean())) / vb
    return out


def spread_zscore(c, r, n):
    """Engle-Granger-style pair spread z-score: hedge ratio b=cov(c,r)/var(r) over the window,
    spread = c − b·r, z of the latest spread. (Full ADF cointegration test deferred.)"""
    c = np.asarray(c, float)
    r = np.asarray(r, float)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n, N):
        cc, rr = c[i - n + 1:i + 1], r[i - n + 1:i + 1]
        if np.isnan(cc).any() or np.isnan(rr).any():
            continue
        vr = rr.var()
        if vr <= 0:
            continue
        b = np.mean((cc - cc.mean()) * (rr - rr.mean())) / vr
        spread = cc - b * rr
        s = spread.std()
        if s > 0:
            out[i] = (spread[-1] - spread.mean()) / s
    return out


def pca_factor(c, r, n):
    """2-series rolling PCA of [primary_ret, ref_ret]: latest point's projection on PC1, signed by the
    primary loading (positive ⇒ shared up-move). Extend to a basket later for a true common factor."""
    rc, rr = _returns(c), _returns(r)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n, N):
        a, b = rc[i - n + 1:i + 1], rr[i - n + 1:i + 1]
        if np.isnan(a).any() or np.isnan(b).any():
            continue
        ac, bc = a - a.mean(), b - b.mean()
        cov = np.vstack([ac, bc]) @ np.vstack([ac, bc]).T / (n - 1)
        _, vecs = np.linalg.eigh(cov)          # ascending eigenvalues
        pc1 = vecs[:, -1]                       # dominant component
        score = np.array([ac[-1], bc[-1]]) @ pc1
        out[i] = score * (np.sign(pc1[0]) if pc1[0] != 0 else 1.0)
    return out
