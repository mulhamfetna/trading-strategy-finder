"""Issue #62 parity gate — the accelerated indicators reproduce their references.

Runs in the normal suite, on synthetic data, and — crucially — **in CI too, where Numba is absent**.
It does that by forcing each module's `_HAVE_NUMBA` flag on: the `njit` decorator degrades to a no-op,
so the kernel body still executes, in pure Python, and its LOGIC is checked. Without this the tests
would compare the reference against itself and pass while testing nothing.

Two strengths of gate, matching what each change actually claims:

  bit-identical   the shared leaves (`_roll_max`/`_roll_min`, `ema`, `rma`, `nan_ema`) and the two SMC
                  state machines (`ifvg`, `order_blocks`). These are exact selections, sequential
                  recurrences and pure comparisons — nothing was reassociated, so nothing may differ.
  vote-identical  the rolling-OLS / window-statistic family, where a left-to-right window sum replaces
                  numpy's pairwise summation. The last float digits may differ; the EMITTED
                  confirm/veto arrays may not.

The real-frame version of this gate (486,969 bars, full parameter sweep, plus a dumb control) is
`optimize/perf/bench_budget.py`; results in `optimize/perf/results/budget_accel.json`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

from indicators import _numba as NB, classic, library, smc
from indicators import _reference as REF
from indicators.calc import (dsp as DSP, ma as MA, osc as OSC, quant as Q, tier2 as T2, trend as TR,
                             vol as V, xseries as XS)
from indicators.runner import market_context

_NUMBA_FLAG_MODULES = (classic, smc, DSP, MA, OSC, Q, T2, TR, V, XS)


@pytest.fixture(autouse=True)
def _force_kernel_path(monkeypatch):
    """Take the kernel branch even when Numba is not installed (the decorator is then a no-op, so the
    kernel runs as plain Python). Without this the gate is vacuous in CI."""
    for m in _NUMBA_FLAG_MODULES:
        if hasattr(m, "_HAVE_NUMBA"):
            monkeypatch.setattr(m, "_HAVE_NUMBA", True)


def _walk(seed=0, n=1500, start=21000.0):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 3.0, n)
    steps[: n // 3] = np.cumsum(rng.normal(0.0, 0.3, n // 3))       # a trendy stretch
    return start + np.cumsum(steps)


def _ohlc(seed=0, n=1500):
    c = _walk(seed, n)
    rng = np.random.default_rng(seed + 991)
    wick = np.abs(rng.normal(4.0, 2.0, n))
    o = c + rng.normal(0.0, 2.0, n)
    return o, c + wick, c - wick, c


def _edge_series():
    """Degenerate inputs that break naive kernels: constants (zero range), monotone runs, NaN holes."""
    n = 240
    yield "constant", np.full(n, 21000.0)
    yield "monotonic_up", np.linspace(20000.0, 22000.0, n)
    yield "monotonic_down", np.linspace(22000.0, 20000.0, n)
    s = _walk(3, n); s[:5] = np.nan
    yield "leading_nan", s
    s2 = _walk(4, n); s2[n // 2] = np.nan
    yield "mid_nan", s2
    yield "ties", np.repeat(_walk(5, n // 6), 6)


def _assert_exact(name, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert a.shape == b.shape, f"{name}: shape {a.shape} != {b.shape}"
    na, nb = np.isnan(a), np.isnan(b)
    assert np.array_equal(na, nb), f"{name}: NaN pattern differs ({na.sum()} vs {nb.sum()})"
    assert np.array_equal(a[~na], b[~nb]), f"{name}: values differ (max |Δ| = {np.nanmax(np.abs(a - b))})"


# ---- bit-identical: the shared leaves ----------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 3, 5, 14, 52, 200, 400])
def test_roll_extremes_bit_identical(n):
    c = _walk(n)
    _assert_exact(f"_roll_max n={n}", classic._roll_max(c, n), REF.roll_max_ref(c, n))
    _assert_exact(f"_roll_min n={n}", classic._roll_min(c, n), REF.roll_min_ref(c, n))


@pytest.mark.parametrize("name,series", list(_edge_series()))
@pytest.mark.parametrize("n", [1, 3, 20, 300])
def test_roll_extremes_bit_identical_on_edge_cases(name, series, n):
    _assert_exact(f"_roll_max {name} n={n}", classic._roll_max(series, n), REF.roll_max_ref(series, n))
    _assert_exact(f"_roll_min {name} n={n}", classic._roll_min(series, n), REF.roll_min_ref(series, n))


def test_roll_extremes_handle_infinities():
    """±inf must not be confused with the deque's sentinels, and NaN must still propagate."""
    x = np.array([1.0, np.inf, -np.inf, np.nan, 2.0, -np.inf, 3.0, np.inf])
    for n in (1, 2, 3, 4):
        _assert_exact(f"inf max n={n}", classic._roll_max(x, n), REF.roll_max_ref(x, n))
        _assert_exact(f"inf min n={n}", classic._roll_min(x, n), REF.roll_min_ref(x, n))


@pytest.mark.parametrize("n", [2, 9, 14, 100])
def test_ema_rma_nan_ema_bit_identical(n):
    c = _walk(n + 7)
    _assert_exact(f"ema n={n}", classic.ema(c, n), REF.ema_ref(c, n))
    _assert_exact(f"rma n={n}", classic.rma(c, n), REF.rma_ref(c, n))
    _assert_exact(f"nan_ema n={n}", OSC.nan_ema(c, n), OSC.nan_ema_reference(c, n))
    holed = c.copy(); holed[:4] = np.nan; holed[len(c) // 2] = np.nan
    _assert_exact(f"rma holed n={n}", classic.rma(holed, n), REF.rma_ref(holed, n))
    _assert_exact(f"nan_ema holed n={n}", OSC.nan_ema(holed, n), OSC.nan_ema_reference(holed, n))


# ---- bit-identical: the SMC state machines -----------------------------------------------------
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_ifvg_bit_identical(seed):
    o, h, l, c = _ohlc(seed)
    fast = smc.ifvg(h, l, c)
    ref = smc._ifvg_py(np.asarray(h, float), np.asarray(l, float), np.asarray(c, float), None)
    assert np.array_equal(fast, ref)


@pytest.mark.parametrize("swing_l", [1, 2, 6])
def test_order_blocks_bit_identical(swing_l):
    o, h, l, c = _ohlc(7)
    fast = smc.order_blocks(o, h, l, c, swing_l)
    assert np.array_equal(fast, REF.order_blocks_ref(o, h, l, c, swing_l))   # the ORIGINAL loop
    sh, sl = smc.market_structure(np.asarray(c, float), swing_l)
    py = smc._order_blocks_py(np.asarray(o, float), np.asarray(h, float), np.asarray(l, float),
                              np.asarray(c, float), sh, sl, int(swing_l), None)
    assert np.array_equal(fast, py)                                          # and the numpy fallback


@pytest.mark.parametrize("swing_l", [2, 6])
def test_smc_sampled_paths_match_full(swing_l):
    """`signal_at` sampling must still equal the full computation at the sampled bars."""
    o, h, l, c = _ohlc(11)
    S = np.unique(np.random.default_rng(3).integers(0, len(c), size=len(c) // 20))
    for full, sampled in ((smc.order_blocks(o, h, l, c, swing_l),
                           smc.order_blocks(o, h, l, c, swing_l, signal_at=S)),
                          (smc.ifvg(h, l, c), smc.ifvg(h, l, c, signal_at=S))):
        assert np.array_equal(sampled[S], full[S])
        mask = np.ones(len(c), bool); mask[S] = False
        assert np.all(sampled[mask] == 0)


# ---- bit-identical: numpy's pairwise summation, reproduced --------------------------------------
@pytest.mark.parametrize("n", [0, 1, 3, 7, 8, 9, 15, 63, 127, 128, 129, 200, 255, 256, 257, 1000])
def test_pw_sum_matches_numpy_exactly(n):
    """`pw_sum` claims to be numpy's reduction, not merely a good sum. If a future numpy changes its
    pairwise order this fails HERE, loudly, instead of silently drifting an indicator's last digit."""
    rng = np.random.default_rng(n + 1)
    for offset in (0, 1, 13):
        x = np.ascontiguousarray(rng.normal(21000.0, 50.0, n + offset + 5))
        assert NB.pw_sum(x, offset, n) == x[offset:offset + n].sum(), f"n={n} offset={offset}"
        if n:
            assert NB.pw_mean(x, offset, n) == x[offset:offset + n].mean()
            assert NB.pw_var(x, offset, n, np.empty(n)) == x[offset:offset + n].var()


# ---- the window-statistic family: bit-identical via pw_sum --------------------------------------
_BIT_CASES = [
    # (registry key, module, attr, reference attr, calc args builder)
    ("frama",       DSP, "frama",          "frama_reference",
     [lambda o, h, l, c, n=n: ((h, l, c, n), {}) for n in (4, 8, 16, 61)]),
    ("proj_bands",  V,   "proj_bands",     "proj_bands_reference",
     [lambda o, h, l, c, n=n: ((h, l, n), {}) for n in (2, 5, 14, 60, 130)]),
    ("ulcer",       V,   "ulcer",          "ulcer_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (2, 5, 14, 50, 200)]),
    ("ou_halflife", T2,  "ou_coefficient", "ou_coefficient_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (3, 10, 50, 150)]),
    ("cmo_dmi",     OSC, "dynamic_dmi",    "dynamic_dmi_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (3, 5, 14, 40)]),
    ("linreg_dev",  TR,  "linreg_dev",     "linreg_dev_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (2, 20, 100, 200)]),
    ("linreg_slope", TR, "linreg_slope",   "linreg_slope_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (2, 5, 20, 100)]),
    ("linreg_r2",   Q,   "linreg_r2",      "linreg_r2_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (2, 10, 20, 80, 129)]),
    ("lsma",        MA,  "lsma",           "lsma_reference",
     [lambda o, h, l, c, n=n: ((c, n), {}) for n in (2, 5, 25, 100, 129)]),
]


@pytest.mark.parametrize("name,mod,attr,ref_attr,builders", _BIT_CASES, ids=[c[0] for c in _BIT_CASES])
def test_window_statistics_bit_identical(name, mod, attr, ref_attr, builders):
    """These reproduce numpy's pairwise summation, so nothing may differ — not one digit. The weaker
    vote gate is not good enough for them: `ou_halflife` vetoes on `b >= 0` and `lsma`/`frama` vote
    `sign(close − line)`, and a left-to-right sum flipped real bars on the real frame (issue #62)."""
    o, h, l, c = _ohlc(21)
    fast_fn, ref_fn = getattr(mod, attr), getattr(mod, ref_attr)
    for build in builders:
        args, kw = build(o, h, l, c)
        got, exp = fast_fn(*args, **kw), ref_fn(*args, **kw)
        if isinstance(got, tuple):
            for j, (g, e) in enumerate(zip(got, exp)):
                _assert_exact(f"{name}{args[1:]}[{j}]", g, e)
        else:
            _assert_exact(f"{name}{args[1:]}", got, exp)


# ---- vote-identical: the Ehlers filters (trig inside the kernel) ---------------------------------
_VOTE_CASES = [
    # (registry key, fast fn holder, attr, reference attr, params to test)
    ("sinewave",           DSP, "hilbert_sinewave",   "hilbert_sinewave_reference",   [{}]),
    ("hilbert_cycle",      DSP, "dominant_cycle",     "dominant_cycle_reference",
     [{"threshold": t} for t in (6.0, 10.0, 20.0)]),
    ("mama_fama",          DSP, "mama_fama",          "mama_fama_reference",
     [{"fast": 0.5, "slow": 0.05}, {"fast": 0.9, "slow": 0.01}]),
    ("schaff_trend_cycle", DSP, "schaff_trend_cycle", "schaff_trend_cycle_reference",
     [{"fast": 23, "slow": 50, "cycle": 10}, {"fast": 5, "slow": 80, "cycle": 4}]),
    ("frama",              DSP, "frama",              "frama_reference",
     [{"n": n} for n in (8, 16, 60)]),
    ("proj_bands",         V,   "proj_bands",         "proj_bands_reference",
     [{"n": n} for n in (5, 14, 60)]),
    ("ulcer",              V,   "ulcer",              "ulcer_reference",
     [{"n": n} for n in (5, 14, 50)]),
    ("ou_halflife",        T2,  "ou_coefficient",     "ou_coefficient_reference",
     [{"n": n} for n in (10, 50, 150)]),
    ("cmo_chande_dmi",     OSC, "dynamic_dmi",        "dynamic_dmi_reference",
     [{"n": n} for n in (5, 14, 40)]),
    ("linreg_channel",     TR,  "linreg_dev",         "linreg_dev_reference",
     [{"n": n, "k": k} for n in (20, 100) for k in (1.0, 2.0, 3.5)]),
    ("linreg_slope",       TR,  "linreg_slope",       "linreg_slope_reference",
     [{"n": n} for n in (5, 20, 100)]),
    ("linreg_r2",          Q,   "linreg_r2",          "linreg_r2_reference",
     [{"n": n, "threshold": t} for n in (10, 20, 80) for t in (0.05, 0.2, 0.6)]),
    ("lsma",               MA,  "lsma",               "lsma_reference",
     [{"n": n} for n in (5, 25, 100)]),
]


def _ctx(seed=13, n=1500):
    o, h, l, c = _ohlc(seed, n)
    df = pd.DataFrame({"Date": pd.date_range("2020", periods=n, freq="min"),
                       "Open": o, "High": h, "Low": l, "Close": c, "Volume": np.ones(n)})
    return market_context(df)


def _emit(key, params, ctx):
    base = {p["name"]: p["default"] for p in library.SCHEMA[key].get("params", [])}
    base.update(params)
    ind = library.from_specs([{"key": key, "enabled": True,
                               "mode": library.SCHEMA[key]["mode"], "params": base}])[0]
    cdir, vdir = ind.directions(ctx)
    return np.asarray(cdir), np.asarray(vdir)


@pytest.mark.parametrize("key,mod,attr,ref_attr,param_sets",
                         _VOTE_CASES, ids=[c[0] for c in _VOTE_CASES])
def test_indicator_vote_identical(key, mod, attr, ref_attr, param_sets, monkeypatch):
    ctx = _ctx()
    fast = [_emit(key, p, ctx) for p in param_sets]
    monkeypatch.setattr(mod, attr, getattr(mod, ref_attr))
    ref = [_emit(key, p, ctx) for p in param_sets]
    for params, (cf, vf), (cr, vr) in zip(param_sets, fast, ref):
        flips = int(np.sum(cf != cr)) + int(np.sum(vf != vr))
        assert flips == 0, f"{key} {params}: {flips} vote bars flipped vs the reference"


# ---- cross-series (issue #74) -------------------------------------------------------------------
def _pair(seed=5, n=1500):
    """A primary and a correlated-but-not-identical reference close, plus a NaN-holed variant — the
    leading NaNs are what causal `merge_asof` alignment actually produces."""
    rng = np.random.default_rng(seed)
    shared = rng.normal(0.0, 2.0, n)
    c = 21000.0 + np.cumsum(shared + rng.normal(0.0, 1.0, n))
    r = 5300.0 + np.cumsum(0.25 * shared + rng.normal(0.0, 0.3, n))
    holed = r.copy()
    holed[:7] = np.nan
    holed[n // 2] = np.nan
    return c, r, holed


@pytest.mark.parametrize("n", [2, 5, 50, 120, 129, 300])
@pytest.mark.parametrize("holes", [False, True])
def test_xseries_bit_identical(n, holes):
    """`rolling_corr` / `rolling_beta` / `spread_zscore` reproduce numpy's reductions via `pw_sum`, so
    nothing may differ. They vote on ratios of similar-magnitude quantities — the case where a
    differently-rounded sum flips real bars (#62)."""
    c, r, holed = _pair(n)
    ref = holed if holes else r
    _assert_exact(f"rolling_corr n={n}", XS.rolling_corr(c, ref, n), XS.rolling_corr_reference(c, ref, n))
    _assert_exact(f"rolling_beta n={n}", XS.rolling_beta(c, ref, n), XS.rolling_beta_reference(c, ref, n))
    _assert_exact(f"spread_zscore n={n}", XS.spread_zscore(c, ref, n),
                  XS.spread_zscore_reference(c, ref, n))


@pytest.mark.parametrize("n", [3, 5, 50, 120, 300])
def test_pca_factor_vote_identical_and_nan_matched(n):
    """`pca_factor` canNOT be bit-identical — the reference builds the covariance with a BLAS product
    and calls LAPACK `eigh` per bar. The contract is the emitted STANCE, which is `sign(out)`."""
    c, r, _ = _pair(n + 1)
    fast = np.asarray(XS.pca_factor(c, r, n), float)
    ref = np.asarray(XS.pca_factor_reference(c, r, n), float)
    assert np.array_equal(np.isnan(fast), np.isnan(ref)), "NaN pattern differs"
    m = ~np.isnan(ref)
    assert np.allclose(fast[m], ref[m], rtol=1e-6, atol=1e-12), "values not float-close"
    flips = int(np.sum(np.sign(fast[m]) != np.sign(ref[m])))
    assert flips == 0, f"pca_factor n={n}: {flips} stance bars flipped vs the reference"


def _tick_pair(seed=31, n=6000):
    """Quarter-tick-quantised prices. Real futures data is quantised, which is exactly what produces
    the degenerate windows where the PCA score is mathematically zero — smooth Gaussian walks do not
    reach them, so testing only on those would miss the failure this band exists to prevent."""
    rng = np.random.default_rng(seed)
    shared = np.round(rng.normal(0.0, 2.0, n) * 4) / 4
    c = 21000.0 + np.cumsum(shared + np.round(rng.normal(0.0, 1.0, n) * 4) / 4)
    r = 5300.0 + np.cumsum(np.round((0.25 * shared + rng.normal(0.0, 0.3, n)) * 4) / 4)
    return c, r


@pytest.mark.parametrize("n", [3, 5, 8, 20, 50, 300])
def test_pca_factor_no_stance_flips_on_degenerate_windows(n):
    """The regression this band exists for: at n=5 the plain closed form flipped 12 real stances on
    the 486,969-bar frame, at bars whose score is mathematically zero (LAPACK snaps a near-diagonal
    covariance to an exact axis vector; a closed form leaves a ~1e-18 residue)."""
    c, r = _tick_pair(n)
    fast = np.asarray(XS.pca_factor(c, r, n), float)
    ref = np.asarray(XS.pca_factor_reference(c, r, n), float)
    assert np.array_equal(np.isnan(fast), np.isnan(ref)), "NaN pattern differs"
    m = ~np.isnan(ref)
    flips = int(np.sum(np.sign(fast[m]) != np.sign(ref[m])))
    assert flips == 0, f"pca_factor n={n}: {flips} stance bars flipped"


def test_pca_fallback_band_is_live_and_covers_the_drift():
    """Two ways this safety net could rot silently: it never fires (dead code proving nothing), or the
    drift on the bars it does NOT cover grows into the sign boundary. Assert both."""
    n = 3                                        # the most degenerate case, so the band must be busy
    fired = total = 0
    worst_drift = 0.0
    for seed in (3, 5, 7):
        c, r = _tick_pair(seed)
        rc, rr = XS._returns(c), XS._returns(r)
        _raw, refine = XS._pca_factor_core(np.ascontiguousarray(rc), np.ascontiguousarray(rr), n,
                                           XS._window_has_nan(rc, rr, n))
        fired += int(refine.sum())
        total += len(rc)
        fast = np.asarray(XS.pca_factor(c, r, n), float)
        ref = np.asarray(XS.pca_factor_reference(c, r, n), float)
        keep = np.isfinite(fast) & np.isfinite(ref) & ~refine      # the bars the band did NOT cover
        if keep.any():
            worst_drift = max(worst_drift, float(np.abs(fast[keep] - ref[keep]).max()))
    assert fired > 0, "the fallback band never fired — it is dead code and proves nothing"
    assert fired < total * 0.2, f"the band fires on {fired}/{total} bars — it is not a fallback any more"
    assert worst_drift < XS._PCA_EPS / 1000, (
        f"on bars the band does NOT cover, drift is {worst_drift:.3e} vs a sign-boundary guard of "
        f"{XS._PCA_EPS:.0e} — the band no longer covers the sign-flip risk")


@pytest.mark.parametrize("key,params", [
    ("rolling_corr", {"n": 50, "threshold": 0.9}),
    ("rolling_beta", {"n": 50, "lag": 5}),
    ("cointegration", {"n": 50, "lower": -2, "upper": 2}),
    ("pca_factor", {"n": 50}),
])
def test_xseries_end_to_end_with_a_reference(key, params, monkeypatch):
    """The gate at the level that matters — and it must NOT be vacuous. A cross-series indicator on a
    reference-free context returns all zeros, so this attaches a real reference and asserts the vote is
    actually non-trivial before comparing fast against reference (issue #74)."""
    c, r, _ = _pair(17)
    n = len(c)
    df = pd.DataFrame({"Date": pd.date_range("2020", periods=n, freq="min"),
                       "Open": c, "High": c + 3, "Low": c - 3, "Close": c, "Volume": np.ones(n)})
    ref_df = pd.DataFrame({"Date": df["Date"], "Open": r, "High": r + 1, "Low": r - 1,
                           "Close": r, "Volume": np.ones(n)})
    ctx = market_context(df, ref_df)
    assert ctx.ref_close is not None and np.isfinite(ctx.ref_close).any()

    cf, vf = _emit(key, params, ctx)
    assert np.count_nonzero(cf) + np.count_nonzero(vf) > 0, \
        f"{key} emitted nothing even WITH a reference — the gate would be vacuous"

    for attr in ("rolling_corr", "rolling_beta", "spread_zscore", "pca_factor"):
        monkeypatch.setattr(XS, attr, getattr(XS, f"{attr}_reference"))
    cr, vr = _emit(key, params, ctx)
    flips = int(np.sum(cf != cr)) + int(np.sum(vf != vr))
    assert flips == 0, f"{key} {params}: {flips} vote bars flipped vs the reference"


def test_xseries_are_inert_without_a_reference():
    """Documents the behaviour that made every cost scan blind (issue #74) — and #75's bug surface.
    Without a reference these emit NOTHING, so a 0.00 s timing is 'never ran', not 'cheap'."""
    c, _r, _ = _pair(23)
    n = len(c)
    df = pd.DataFrame({"Date": pd.date_range("2020", periods=n, freq="min"),
                       "Open": c, "High": c + 3, "Low": c - 3, "Close": c, "Volume": np.ones(n)})
    ctx = market_context(df)                                  # no reference
    assert ctx.ref_close is None
    for key in ("rolling_corr", "rolling_beta", "cointegration", "pca_factor"):
        cd, vd = _emit(key, {}, ctx)
        assert np.count_nonzero(cd) == 0 and np.count_nonzero(vd) == 0, \
            f"{key} emitted a vote with no reference — the inert-without-reference contract changed"


def test_vote_gate_is_not_vacuous(monkeypatch):
    """A control on the control: swapping in a DELIBERATELY WRONG implementation must be detected.
    If this passes trivially, every test above is meaningless."""
    ctx = _ctx()
    good = _emit("linreg_r2", {"n": 20, "threshold": 0.2}, ctx)
    monkeypatch.setattr(Q, "linreg_r2", lambda close, n: Q.linreg_r2_reference(close, n) * 0.5)
    bad = _emit("linreg_r2", {"n": 20, "threshold": 0.2}, ctx)
    assert int(np.sum(good[1] != bad[1])) > 0, "the gate cannot see a wrong implementation"
