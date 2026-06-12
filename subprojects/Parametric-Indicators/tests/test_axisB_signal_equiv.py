"""Equivalence tests for Axis B · Step B1 (task #210).

The VECTORIZED `optimize.signals.decision_signals` (numpy) MUST equal the FROZEN per-bar reference
`optimize.signals.decision_signals_ref` (which calls engine._stage1_candle_signal directly — the spec)
ELEMENT-FOR-ELEMENT, on synthetic random + adversarial frames AND on the real champion frames. Any
divergence fails immediately. This is the precision gate that lets Step B2 inject the precomputed signal
into the engine with confidence the trades stay byte-identical.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))
sys.path.insert(0, str(_PROJ / "perf"))

from engine import _LEVEL_PAIRS                              # noqa: E402
from box_lookup import BoxLookup                             # noqa: E402
from optimize.signals import decision_signals, decision_signals_ref  # noqa: E402


def _assert_signals_identical(label, df_dec, box):
    got = decision_signals(df_dec, box)
    ref = decision_signals_ref(df_dec, box)
    assert len(got) == len(ref) == len(df_dec), f"{label}: length mismatch"
    assert got.dtype == object and ref.dtype == object, f"{label}: dtype not object"
    # element-for-element exact (no tolerance — these are categorical labels)
    mism = [(i, got[i], ref[i]) for i in range(len(ref)) if got[i] != ref[i]]
    assert not mism, f"{label}: {len(mism)} mismatches, first 5: {mism[:5]}"
    # sanity: the labels are exactly the allowed set
    assert set(np.unique(ref)).issubset({"long", "short", "hold"}), f"{label}: unexpected labels"


# ---------------------------------------------------------------------------------------------------
# Synthetic frame generator — overlapping price/level ranges so long/short/hold all occur, with
# missing box dates, NaN levels, and dojis injected.
# ---------------------------------------------------------------------------------------------------
def _make_frames(seed, n=300, missing_frac=0.12, nan_frac=0.2, drop_cols=()):
    g = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01 00:00", periods=n, freq="1h")
    base = 20000 + np.cumsum(g.normal(0, 15, n))
    O = base + g.normal(0, 6, n)
    C = base + g.normal(0, 6, n)
    H = np.maximum(O, C) + np.abs(g.normal(0, 12, n))
    L = np.minimum(O, C) - np.abs(g.normal(0, 12, n))
    doji = g.random(n) < 0.1
    C[doji] = O[doji]                                  # exact dojis ⇒ must map to 'hold'
    df = pd.DataFrame({"Date": dates, "Open": O, "High": H, "Low": L, "Close": C})

    all_box_dates = pd.DatetimeIndex(
        [BoxLookup._candle_to_box_date(pd.Timestamp(d)) for d in dates]).unique()
    keep = all_box_dates[g.random(len(all_box_dates)) >= missing_frac]   # some dates absent ⇒ 'hold'
    cols = {}
    for u, l, _lab in _LEVEL_PAIRS:
        if u in drop_cols or l in drop_cols:
            continue                                   # whole pair column missing
        uu = 20000 + g.normal(0, 40, len(keep))
        ll = uu - np.abs(g.normal(25, 12, len(keep)))
        uu[g.random(len(keep)) < nan_frac] = np.nan    # NaN levels ⇒ pair invalid
        ll[g.random(len(keep)) < nan_frac] = np.nan
        cols[u] = uu
        cols[l] = ll
    box = pd.DataFrame(cols, index=pd.DatetimeIndex(keep))
    box["Date"] = box.index
    box.index.name = "Date"
    return df, box


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6, 7, 8])
def test_signal_equiv_random(seed):
    df, box = _make_frames(seed)
    _assert_signals_identical(f"random seed={seed}", df, box)


def test_signal_equiv_all_dates_missing():
    # box has NO matching dates ⇒ every bar must be 'hold'
    df, box = _make_frames(11, missing_frac=1.0)
    got = decision_signals(df, box)
    assert (got == "hold").all()
    _assert_signals_identical("all-missing", df, box)


def test_signal_equiv_all_levels_nan():
    df, box = _make_frames(12, nan_frac=1.0)
    got = decision_signals(df, box)
    assert (got == "hold").all()                        # no valid pair anywhere ⇒ all hold
    _assert_signals_identical("all-nan-levels", df, box)


def test_signal_equiv_some_columns_absent():
    # drop a few whole level-pair columns ⇒ those pairs never contribute (matches scalar `continue`)
    drop = ("WTHU", "WTHD", "MRLU", "MRLD")
    df, box = _make_frames(13, drop_cols=drop)
    _assert_signals_identical("cols-absent", df, box)


def test_signal_equiv_doji_heavy():
    # force ~half the bars to be exact dojis (close==open) ⇒ all of those must be 'hold'
    df, box = _make_frames(14)
    g = np.random.default_rng(99)
    mask = g.random(len(df)) < 0.5
    df.loc[mask, "Close"] = df.loc[mask, "Open"].to_numpy()
    _assert_signals_identical("doji-heavy", df, box)


def test_signal_equiv_boundary_touches():
    # craft exact-boundary rows: low==upper, high==lower, close==upper, close==lower — to pin the
    # <=/>=/>/< conventions against the scalar rule.
    u, l, _ = _LEVEL_PAIRS[0]
    dates = pd.date_range("2025-03-03 00:00", periods=6, freq="1h")
    rows = [   # (open, high, low, close)  designed around upper=20010, lower=19990
        (20000, 20010, 19990, 20020),   # green, touched, close>upper ⇒ long
        (20000, 20010, 19990, 19980),   # red,   touched, close<lower ⇒ short
        (20000, 20010, 20010, 20010),   # low==upper (boundary touch), close==upper (not >) ⇒ hold
        (20000, 19990, 19990, 19990),   # high==lower boundary, close==lower (not <) ⇒ hold
        (20000, 20009, 19991, 20005),   # inside the box, no break ⇒ hold
        (20005, 20005, 20005, 20005),   # doji ⇒ hold
    ]
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"])
    df.insert(0, "Date", dates)
    keep = pd.DatetimeIndex([BoxLookup._candle_to_box_date(pd.Timestamp(d)) for d in dates]).unique()
    box = pd.DataFrame({u: 20010.0, l: 19990.0, "Date": keep}, index=keep)
    box.index.name = "Date"
    _assert_signals_identical("boundary", df, box)


def test_signal_equiv_empty():
    df = pd.DataFrame({"Date": pd.to_datetime([]), "Open": [], "High": [], "Low": [], "Close": []})
    box = pd.DataFrame({c: [] for c in ("WTHU", "WTHD", "Date")})
    got = decision_signals(df, box)
    assert len(got) == 0


# ---------------------------------------------------------------------------------------------------
# Real champion frames — the strongest test (real box geometry + real OHLC distribution).
# Coarse + 15m only in CI (the ref loop on 5m/2m is slow); full 6-TF real check is run manually in the
# Step-B1 verification and recorded in perf/UPDATE_step_B1_*.md.
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("tf", ["4h", "2h", "1h", "15m"])
def test_signal_equiv_real(tf):
    from _common import load_bundle
    df_dec, _df1, box, *_ = load_bundle(tf)
    _assert_signals_identical(f"real {tf}", df_dec, box)
