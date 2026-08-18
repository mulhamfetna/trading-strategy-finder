"""Single place where the OPTIONAL Numba dependency is imported (issue #62).

Numba is an accelerator and nothing more. Every function that uses it keeps a verbatim pure-Python /
pure-numpy reference, and dispatches to it when Numba is absent — so a missing optional dependency can
never change a number, only the wall-clock. Import `njit` from here rather than from `numba` directly,
so there is exactly one place to look when asking "is the fast path live?".

    from .._numba import njit, HAVE_NUMBA

Kernels are compiled with ``cache=True`` (persist across processes — the optimizer spawns many),
``nogil=True`` and, deliberately, ``fastmath=False``: fastmath licenses reassociation, which would
break the IEEE semantics the parity gates assert.
"""
from __future__ import annotations

import numpy as np

try:                                    # pragma: no cover - trivially environment-dependent
    from numba import njit
    HAVE_NUMBA = True
except ImportError:                     # pragma: no cover
    HAVE_NUMBA = False

    def njit(*a, **k):                  # no-op decorator so every module still imports
        def deco(f):
            return f
        return deco if not a else a[0]


@njit(cache=True, nogil=True, fastmath=False)
def pw_sum(a, start, n):
    """`a[start:start+n].sum()`, BIT-IDENTICAL to numpy — a replica of `npy_pairwise_sum_DOUBLE`.

    Why this exists (issue #62). A window reduction written as a plain left-to-right loop is *not*
    numpy's answer: numpy sums in pairs, so the rounding error differs in the last digits. That is
    usually invisible, but several indicators compare the result to ZERO (`ou_halflife` vetoes on
    `b >= 0`) or to a price (`sign(close − line)`), and there the last digit decides the vote. The
    gate caught exactly that — 1 flipped bar in `ou_halflife`, 2 in `frama` — on the real 486,969-bar
    frame. Summing the way numpy sums removes the whole class of risk instead of measuring it away.

    Verified against `ndarray.sum()` over 1,168 cases (every length 1..139 plus 200/255/256/257/400/
    1000/4096, at zero and non-zero offsets): zero mismatches. `test_budget_accel_parity.py` keeps
    that honest, so a future numpy that changes its reduction order fails loudly rather than silently.

    Derived helpers — `mean = pw_sum/n`, and numpy's two-pass `var` — are below.
    """
    if n <= 128:
        return _pw_block(a, start, n)
    # numpy recurses here; we cannot. A RECURSIVE @njit function called from inside another kernel
    # SEGFAULTS under Numba 0.65 (it took down the whole verification run), so the recursion is
    # emulated with an explicit stack that reproduces the evaluation order exactly:
    #     f(s, m) = f(s, n2) + f(s + n2, m - n2),  n2 = (m // 2) rounded DOWN to a multiple of 8
    # Depth is log2(n / 128), so 64 frames covers any array that fits in memory. Only reached for
    # windows over 128 bars, where the block work dominates the one-off stack allocation.
    st_s = np.empty(64, dtype=np.int64)
    st_m = np.empty(64, dtype=np.int64)
    st_ph = np.empty(64, dtype=np.int64)          # 0 = LEFT child pending, 1 = RIGHT child pending
    st_left = np.empty(64, dtype=np.float64)
    sp = 0
    st_s[0] = start
    st_m[0] = n
    st_ph[0] = 0
    val = 0.0
    returning = False
    while True:
        if not returning:
            m = st_m[sp]
            if m <= 128:
                val = _pw_block(a, st_s[sp], m)
                returning = True
            else:
                n2 = m // 2
                n2 -= n2 % 8
                st_ph[sp] = 0
                sp += 1
                st_s[sp] = st_s[sp - 1]
                st_m[sp] = n2
                st_ph[sp] = 0
                continue
        if sp == 0:
            return val
        sp -= 1
        if st_ph[sp] == 0:                        # the LEFT child just produced `val`
            st_left[sp] = val
            st_ph[sp] = 1
            m = st_m[sp]
            n2 = m // 2
            n2 -= n2 % 8
            sp += 1
            st_s[sp] = st_s[sp - 1] + n2
            st_m[sp] = m - n2
            st_ph[sp] = 0
            returning = False
        else:                                     # the RIGHT child just produced `val`
            val = st_left[sp] + val
            returning = True


@njit(cache=True, nogil=True, fastmath=False)
def _pw_block(a, start, n):
    """numpy's leaf case: sequential below 8, otherwise 8 independent accumulators combined as a tree."""
    if n < 8:
        res = 0.0
        for i in range(n):
            res += a[start + i]
        return res
    r0 = a[start]; r1 = a[start + 1]; r2 = a[start + 2]; r3 = a[start + 3]
    r4 = a[start + 4]; r5 = a[start + 5]; r6 = a[start + 6]; r7 = a[start + 7]
    i = 8
    while i < n - (n % 8):
        r0 += a[start + i]; r1 += a[start + i + 1]; r2 += a[start + i + 2]; r3 += a[start + i + 3]
        r4 += a[start + i + 4]; r5 += a[start + i + 5]; r6 += a[start + i + 6]; r7 += a[start + i + 7]
        i += 8
    res = ((r0 + r1) + (r2 + r3)) + ((r4 + r5) + (r6 + r7))
    while i < n:
        res += a[start + i]
        i += 1
    return res


@njit(cache=True, nogil=True, fastmath=False)
def pw_mean(a, start, n):
    """`a[start:start+n].mean()` — numpy divides the pairwise sum by the count."""
    return pw_sum(a, start, n) / n


@njit(cache=True, nogil=True, fastmath=False)
def pw_var(a, start, n, buf):
    """`a[start:start+n].var()` (population, ddof=0) — numpy's TWO-PASS form: subtract the mean, square,
    then pairwise-sum. NOT E[x²]−E[x]², which differs in the last digits (and cancels catastrophically
    at price levels ~2e4). `buf` is a scratch array of length ≥ n, reused across bars."""
    m = pw_mean(a, start, n)
    for k in range(n):
        d = a[start + k] - m
        buf[k] = d * d
    return pw_sum(buf, 0, n) / n


__all__ = ["njit", "HAVE_NUMBA", "pw_sum", "pw_mean", "pw_var"]
