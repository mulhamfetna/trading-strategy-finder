"""Cross-series primitives: primary close `c` vs an aligned reference close `r` (both same length).
Reference NaNs (leading, from causal alignment) propagate to NaN output for that window.

PERFORMANCE (issue #74). Every cost scan was BLIND to these four: `bench_worstcase.py` builds a
single-instrument context, so they found `ctx.ref_close is None`, returned all-zero votes immediately,
and were reported at **0.00 s** — "never ran", not "cheap". Measured properly, with a reference series
attached, all four were **over the 2 s budget** (7.53 / 5.76 / 8.26 / 5.82 s = 27.4 s together), and
`core._cached_votes` deliberately never caches cross-series votes, so that would be paid on EVERY trial.

Each function keeps its original implementation verbatim as `<name>_reference` and dispatches to a
Numba kernel, falling back to the reference when Numba is absent. Window reductions go through
`_numba.pw_sum` / `pw_mean` / `pw_var`, which reproduce numpy's pairwise summation bit-for-bit — these
indicators compare ratios of similar-magnitude quantities and vote on a SIGN, exactly where a
differently-rounded sum flipped real bars in #62.

Parity: `rolling_corr`, `rolling_beta` and `spread_zscore` are **bit-identical**. `pca_factor` is not,
and cannot be — its reference builds the covariance with a BLAS `@` product and then calls
`np.linalg.eigh` (LAPACK) per bar; the kernel uses the closed-form 2×2 symmetric eigen-solve instead.
Its contract is the emitted VOTE across the searched grid, verified on the real 486,969-bar frame.
"""
from __future__ import annotations

import numpy as np

from .._numba import (HAVE_NUMBA as _HAVE_NUMBA, njit as _njit, pw_mean as _pw_mean,
                      pw_sum as _pw_sum, pw_var as _pw_var)


def _returns(x):
    d = np.full(len(x), np.nan)
    d[1:] = np.diff(np.asarray(x, dtype=float))
    return d


def _window_has_nan(a, b, n):
    """Per bar i: is there a NaN anywhere in a[i-n+1:i+1] or b[i-n+1:i+1]?

    The references ask `np.isnan(win).any()` per bar, which is O(n) work per bar on top of the O(n)
    arithmetic. A cumulative count answers the same question in O(1) per bar — an exact reformulation
    of the same predicate, not an approximation of it.
    """
    bad = np.isnan(np.asarray(a, float)) | np.isnan(np.asarray(b, float))
    cum = np.concatenate(([0], np.cumsum(bad.astype(np.int64))))
    N = len(bad)
    out = np.ones(N, dtype=np.bool_)
    idx = np.arange(N)
    ok = idx >= n - 1
    out[ok] = (cum[idx[ok] + 1] - cum[idx[ok] - n + 1]) > 0
    return out


# ----------------------------------------------------------------------------------------------
def rolling_corr_reference(c, r, n):
    """FROZEN reference for `rolling_corr` — the ORIGINAL per-bar loop (issue #74)."""
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


@_njit(cache=True, nogil=True, fastmath=False)
def _rolling_corr_core(rc, rr, n, skip):
    N = rc.shape[0]
    out = np.full(N, np.nan)
    buf = np.empty(n)
    prod = np.empty(n)
    for i in range(n, N):
        if skip[i]:
            continue
        s = i - n + 1
        sa = np.sqrt(_pw_var(rc, s, n, buf))
        sb = np.sqrt(_pw_var(rr, s, n, buf))
        if sa > 0 and sb > 0:
            ma = _pw_mean(rc, s, n)
            mb = _pw_mean(rr, s, n)
            for k in range(n):
                prod[k] = (rc[s + k] - ma) * (rr[s + k] - mb)
            out[i] = (_pw_sum(prod, 0, n) / n) / (sa * sb)
    return out


def rolling_corr(c, r, n):
    """Rolling Pearson correlation of the two return series over n. Bit-identical to the reference."""
    rc, rr = _returns(c), _returns(r)
    if not _HAVE_NUMBA or n <= 0 or len(rc) <= n:
        return rolling_corr_reference(c, r, n)
    return _rolling_corr_core(np.ascontiguousarray(rc), np.ascontiguousarray(rr), int(n),
                              _window_has_nan(rc, rr, n))


# ----------------------------------------------------------------------------------------------
def rolling_beta_reference(c, r, n):
    """FROZEN reference for `rolling_beta` — the ORIGINAL per-bar loop (issue #74)."""
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


@_njit(cache=True, nogil=True, fastmath=False)
def _rolling_beta_core(rc, rr, n, skip):
    N = rc.shape[0]
    out = np.full(N, np.nan)
    buf = np.empty(n)
    prod = np.empty(n)
    for i in range(n, N):
        if skip[i]:
            continue
        s = i - n + 1
        vb = _pw_var(rr, s, n, buf)
        if vb > 0:
            ma = _pw_mean(rc, s, n)
            mb = _pw_mean(rr, s, n)
            for k in range(n):
                prod[k] = (rc[s + k] - ma) * (rr[s + k] - mb)
            out[i] = (_pw_sum(prod, 0, n) / n) / vb
    return out


def rolling_beta(c, r, n):
    """Rolling OLS beta of primary returns on reference returns (cov/var) over n. Bit-identical."""
    rc, rr = _returns(c), _returns(r)
    if not _HAVE_NUMBA or n <= 0 or len(rc) <= n:
        return rolling_beta_reference(c, r, n)
    return _rolling_beta_core(np.ascontiguousarray(rc), np.ascontiguousarray(rr), int(n),
                              _window_has_nan(rc, rr, n))


# ----------------------------------------------------------------------------------------------
def spread_zscore_reference(c, r, n):
    """FROZEN reference for `spread_zscore` — the ORIGINAL per-bar loop (issue #74)."""
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


@_njit(cache=True, nogil=True, fastmath=False)
def _spread_zscore_core(c, r, n, skip):
    N = c.shape[0]
    out = np.full(N, np.nan)
    buf = np.empty(n)
    prod = np.empty(n)
    spread = np.empty(n)
    for i in range(n, N):
        if skip[i]:
            continue
        s = i - n + 1
        vr = _pw_var(r, s, n, buf)
        if vr <= 0:
            continue
        mc = _pw_mean(c, s, n)
        mr = _pw_mean(r, s, n)
        for k in range(n):
            prod[k] = (c[s + k] - mc) * (r[s + k] - mr)
        b = (_pw_sum(prod, 0, n) / n) / vr
        for k in range(n):
            spread[k] = c[s + k] - b * r[s + k]
        sd = np.sqrt(_pw_var(spread, 0, n, buf))
        if sd > 0:
            out[i] = (spread[n - 1] - _pw_mean(spread, 0, n)) / sd
    return out


def spread_zscore(c, r, n):
    """Engle-Granger-style pair spread z-score: hedge ratio b=cov(c,r)/var(r) over the window,
    spread = c − b·r, z of the latest spread. Bit-identical to the reference. (Full ADF cointegration
    test deferred.)"""
    c = np.asarray(c, float)
    r = np.asarray(r, float)
    if not _HAVE_NUMBA or n <= 0 or len(c) <= n:
        return spread_zscore_reference(c, r, n)
    return _spread_zscore_core(np.ascontiguousarray(c), np.ascontiguousarray(r), int(n),
                               _window_has_nan(c, r, n))


# ----------------------------------------------------------------------------------------------
def pca_factor_reference(c, r, n):
    """FROZEN reference for `pca_factor` — the ORIGINAL per-bar `np.linalg.eigh` loop (issue #74)."""
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


@_njit(cache=True, nogil=True, fastmath=False)
def _pca_factor_core(rc, rr, n, skip):
    """Closed-form 2×2 symmetric eigen-solve in place of a per-bar LAPACK `eigh`.

    The eigenvector of the LARGER eigenvalue of [[caa, cab], [cab, cbb]] is (cos θ, sin θ) with

        θ = ½ · atan2(2·cab, caa − cbb)

    ⚠️ **Not** the algebraically-equivalent (cab, λ − caa) with λ from the quadratic formula. That form
    was tried first and FAILED the gate: when the window is near-degenerate both `cab` and `λ − caa`
    are tiny, `λ − caa` cancels catastrophically, and the eigenvector direction falls apart. At n=5 —
    a legal grid point — it produced a max |Δ| of **0.156** (not 1e-14) and **flipped 3 real stances**
    on the 486,969-bar frame. `atan2` is well-conditioned across every quadrant and needs no
    subtraction of nearly-equal quantities, and it returns a unit vector for free.

    `eigh`'s sign convention does not matter: the reference immediately multiplies by `sign(pc1[0])`,
    which normalises it. The one case that survives is `pc1[0] == 0` exactly (cab == 0 and cbb > caa),
    where the reference substitutes 1.0 — and so does this.
    """
    N = rc.shape[0]
    out = np.full(N, np.nan)
    refine = np.zeros(N, dtype=np.bool_)
    aa = np.empty(n)
    bb = np.empty(n)
    prod = np.empty(n)
    for i in range(n, N):
        if skip[i]:
            continue
        s = i - n + 1
        ma = _pw_mean(rc, s, n)
        mb = _pw_mean(rr, s, n)
        for k in range(n):
            aa[k] = rc[s + k] - ma
            bb[k] = rr[s + k] - mb
        for k in range(n):
            prod[k] = aa[k] * aa[k]
        caa = _pw_sum(prod, 0, n) / (n - 1)
        for k in range(n):
            prod[k] = bb[k] * bb[k]
        cbb = _pw_sum(prod, 0, n) / (n - 1)
        for k in range(n):
            prod[k] = aa[k] * bb[k]
        cab = _pw_sum(prod, 0, n) / (n - 1)

        # Eigen-gap = λ₂ − λ₁. When it is small relative to the trace the PRINCIPAL DIRECTION is
        # ill-conditioned: an O(1e-16) difference in the covariance rotates the eigenvector by
        # O(1e-16 / gap), so a closed form and LAPACK can disagree by O(1) — not in the last digits.
        # Flag those bars for exact recomputation instead of pretending the closed form is close.
        dd = caa - cbb
        gap = np.sqrt(dd * dd + 4.0 * cab * cab)
        tr = caa + cbb                          # trace of a covariance ⇒ >= 0
        if not (gap > _GAP_REL * tr):           # `not (>)` also catches NaN
            refine[i] = True

        if cab != 0.0:
            theta = 0.5 * np.arctan2(2.0 * cab, caa - cbb)
            u0, u1 = np.cos(theta), np.sin(theta)
        elif caa >= cbb:                        # diagonal: eigh returns the axis vectors
            u0, u1 = 1.0, 0.0
        else:
            u0, u1 = 0.0, 1.0
        if np.isnan(u0) or np.isnan(u1):
            refine[i] = True
            continue
        # The indicator multiplies by `sign(pc1[0])`, which is DISCONTINUOUS as the primary loading
        # crosses zero — i.e. whenever the principal direction lies near the reference-series axis.
        # There the sign is decided by ~1e-16 of noise, and this kernel's noise and LAPACK's need not
        # agree: seen with cov ≈ [[0.4375, -2.8e-17], [-2.8e-17, 0.5833]], a WELL-conditioned matrix
        # (gap/trace = 0.14) whose result still came out exactly negated. Flag it.
        if np.abs(u0) < _U0_EPS:
            refine[i] = True
        score = aa[n - 1] * u0 + bb[n - 1] * u1
        if u0 > 0.0:
            out[i] = score
        elif u0 < 0.0:
            out[i] = -score
        else:
            out[i] = score                      # u0 == 0 ⇒ the reference's `else 1.0` branch
        if np.abs(out[i]) < _PCA_EPS:           # score sits on the sign boundary
            refine[i] = True
    return out, refine


# Two independent ways `pca_factor`'s fast path can disagree with LAPACK. A bar tripping EITHER is
# recomputed with the reference, so disagreement is impossible rather than merely unobserved.
#
#   _PCA_EPS   the score sits on the SIGN boundary. Must be far above the observed fast-vs-reference
#              drift (5.7e-14 on the real frame) and far below an informative score (the 0.1st
#              percentile of |score| is ~4e-3). 1e-9 is ~5 orders clear of the drift, ~6 of the signal.
#   _GAP_REL   the two eigenvalues nearly coincide, so the principal DIRECTION is undefined and the
#              eigenvector error is ~1e-16/gap — an O(1) disagreement, which no score-magnitude test
#              can catch. (Found at n=3: drift 1.33, with scores nowhere near zero.) Theory says
#              gap/trace > 1e-8 keeps the direction error under 1e-8; 1e-6 leaves two decades of margin.
#   _U0_EPS    the primary LOADING is near zero, so `sign(pc1[0])` — which the indicator multiplies
#              through — is decided by noise. Independent of the other two: it bites on
#              well-conditioned matrices with a large score. With gap/trace >= 1e-6 the loading error
#              is <= ~1e-10, so 1e-8 leaves two decades of margin.
_PCA_EPS = 1e-9
_GAP_REL = 1e-6
_U0_EPS = 1e-8


def _pca_reference_at(rc, rr, n, i):
    """The reference's per-bar body, verbatim — BLAS covariance, LAPACK `eigh`, same sign convention."""
    a, b = rc[i - n + 1:i + 1], rr[i - n + 1:i + 1]
    if np.isnan(a).any() or np.isnan(b).any():
        return np.nan
    ac, bc = a - a.mean(), b - b.mean()
    cov = np.vstack([ac, bc]) @ np.vstack([ac, bc]).T / (n - 1)
    _, vecs = np.linalg.eigh(cov)
    pc1 = vecs[:, -1]
    score = np.array([ac[-1], bc[-1]]) @ pc1
    return score * (np.sign(pc1[0]) if pc1[0] != 0 else 1.0)


def pca_factor(c, r, n):
    """2-series rolling PCA of [primary_ret, ref_ret]: latest point's projection on PC1, signed by the
    primary loading (positive ⇒ shared up-move). Extend to a basket later for a true common factor.

    Numba-accelerated (issue #74) with an **exact fallback band**, because this one cannot be made
    bit-identical: the reference forms the covariance with a BLAS product and calls LAPACK `eigh` per
    bar. Measured on the real frame, the kernel tracks it to 5.7e-14 — except at bars where the score
    is *mathematically zero*, and there LAPACK snaps a near-diagonal covariance to an exact axis
    vector (score exactly 0.0) while the closed form leaves a ~1e-18 off-axis residue. The vote is
    `sign(score)`, so those bars flipped: **12 of 486,969 at n=5**, the grid minimum.

    Chasing LAPACK's snapping heuristics is unwinnable, so instead the result is made correct **by
    construction**: a bar is recomputed with the reference whenever the fast path could possibly
    disagree — either the score is within `_PCA_EPS` of the sign boundary, or the eigen-gap is below
    `_GAP_REL` of the trace, which means the principal direction itself is ill-conditioned. Every
    remaining bar is further from its decision boundary than the drift can reach. So no bar *can*
    disagree — not "was measured not to". The fallback fires on well under 0.1% of bars, so it is free.

    `pca_factor_reference` remains the oracle and runs verbatim when Numba is absent.
    """
    rc, rr = _returns(c), _returns(r)
    if not _HAVE_NUMBA or n <= 1 or len(rc) <= n:
        return pca_factor_reference(c, r, n)
    out, refine = _pca_factor_core(np.ascontiguousarray(rc), np.ascontiguousarray(rr), int(n),
                                   _window_has_nan(rc, rr, n))
    for i in np.flatnonzero(refine):
        out[i] = _pca_reference_at(rc, rr, int(n), int(i))
    return out
