"""Issue #75 — the cross-series reference must reach the context the votes are computed from.

Three bugs lived here, all invisible because the four cross-series indicators had apparently never been
run end-to-end:

  1. `runner.indicator_source_1min` built `market_context(df1)` with no reference at ANY call site, so
     on the production `--ind-1min` path every cross-series indicator short-circuited on
     `ctx.ref_close is None` and voted nothing — regardless of `--reference`.
  2. Worse than dormant: `confirm_mask` counted such an indicator among the confirmers whenever a
     reference was *configured*, and `k_eff = min(k, len(confirmers))`. Enabling one therefore added a
     confirmer that could never confirm, making the K-rule strictly harder — the optimizer would learn
     to avoid cross-series indicators for a reason that was purely a wiring bug.
  3. `build_entry_resolver` referenced a name `ref_df` that was not one of its parameters. `and`
     short-circuits, so `ind.needs_ref and ref_df is None` never evaluated `ref_df` for an ordinary
     indicator — the NameError only fired once a cross-series one was enabled, i.e. on the dashboard /
     exact-engine path.

Everything here must hold with NO reference too: that path is the golden-gated one and must not move.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from indicators import library, runner

_XS = ("rolling_corr", "rolling_beta", "cointegration", "pca_factor")


def _frames(n=800, seed=0):
    rng = np.random.default_rng(seed)
    shared = rng.normal(0.0, 2.0, n)
    c = 21000.0 + np.cumsum(shared + rng.normal(0.0, 1.0, n))
    r = 5300.0 + np.cumsum(0.25 * shared + rng.normal(0.0, 0.3, n))
    minutes = pd.date_range("2024-01-01", periods=n, freq="min")
    df1 = pd.DataFrame({"Date": minutes, "Open": c, "High": c + 2, "Low": c - 2,
                        "Close": c, "Volume": np.ones(n)})
    ref1 = pd.DataFrame({"Date": minutes, "Open": r, "High": r + 1, "Low": r - 1,
                         "Close": r, "Volume": np.ones(n)})
    dec_idx = np.arange(0, n, 60)                      # a 1-hour decision frame over the same span
    df_dec = df1.iloc[dec_idx].reset_index(drop=True)
    box = pd.DataFrame({"Date": df_dec["Date"],
                        "zone_high": df_dec["Close"] + 8, "zone_low": df_dec["Close"] - 8})
    return df_dec, df1, ref1, box


def _specs(keys, mode=None):
    out = []
    for k in keys:
        spec = library.SCHEMA[k]
        out.append({"key": k, "enabled": True, "mode": mode or spec["mode"],
                    "params": {p["name"]: p["default"] for p in spec.get("params", [])}})
    return out


# ---- bug 1: the reference must reach the 1-minute context ---------------------------------------
def test_indicator_source_1min_carries_the_reference():
    df_dec, df1, ref1, _box = _frames()
    bar = pd.Timedelta(hours=1)
    assert runner.indicator_source_1min(df_dec, df1, bar)[0].ref_close is None, \
        "no reference passed ⇒ must stay None (this is the golden-gated path)"
    ctx, _j = runner.indicator_source_1min(df_dec, df1, bar, ref1)
    assert ctx.ref_close is not None and np.isfinite(ctx.ref_close).all()
    assert len(ctx.ref_close) == len(df1), "the reference aligns to the 1-MINUTE frame, not the decision one"


@pytest.mark.parametrize("key", _XS)
def test_cross_series_produce_directions_on_the_1min_path(key):
    """The regression that matters: with a reference wired, these actually produce a direction on the
    1-minute context. (Asserted on `directions()` rather than the emitted vote, because a vote also
    needs the box to be signalling — that is the box's business, not the reference's.)"""
    df_dec, df1, ref1, _box = _frames()
    bar = pd.Timedelta(hours=1)
    spec = _specs([key])[0]
    # `rolling_corr` vetoes when |corr| < threshold, and these two series are correlated by
    # construction, so at its 0.3 default it is legitimately silent. Test it where it CAN fire —
    # otherwise the assertion below would be unfalsifiable for this one indicator.
    if key == "rolling_corr":
        spec["params"]["threshold"] = 0.95
    ind = library.from_specs([spec])[0]

    ctx_dead, _ = runner.indicator_source_1min(df_dec, df1, bar)          # the old behaviour
    cd, vd = ind.directions(ctx_dead)
    assert np.count_nonzero(cd) + np.count_nonzero(vd) == 0, "no reference in the ctx ⇒ inert"

    ctx_live, _ = runner.indicator_source_1min(df_dec, df1, bar, ref1)
    cd, vd = ind.directions(ctx_live)
    assert np.count_nonzero(cd) + np.count_nonzero(vd) > 0, \
        f"{key} produces nothing even with a reference wired into the 1-minute context"


# ---- bug 2: activity must follow the VOTE-PRODUCING context, not the configured reference --------
def test_confirmer_count_follows_the_context_not_the_config():
    """A cross-series indicator whose reference does not reach the 1-minute context must NOT be counted
    among the confirmers — otherwise it raises `k_eff` while contributing zero confirmations."""
    df_dec, df1, ref1, box = _frames()
    bar = pd.Timedelta(hours=1)
    inds = library.from_specs(_specs(["rsi", "rolling_beta"], mode="confirm"))

    # reference CONFIGURED but absent from the 1-minute ctx — the exact pre-fix situation
    _cc, n_conf = runner.confirm_count(df_dec, box, inds,
                                       src=runner.indicator_source_1min(df_dec, df1, bar),
                                       ref_df=df_dec)
    assert n_conf == 1, f"a never-voting cross-series indicator is still inflating k_eff (n={n_conf})"

    # reference actually wired through ⇒ it counts, because now it can confirm
    _cc2, n_conf2 = runner.confirm_count(df_dec, box, inds,
                                         src=runner.indicator_source_1min(df_dec, df1, bar, ref1),
                                         ref_df=df_dec)
    assert n_conf2 == 2


def test_confirm_mask_not_starved_by_an_unwired_cross_series_confirmer():
    """End-to-end shape of bug 2: with k=2 and one real + one unwired cross-series confirmer, the old
    behaviour could never satisfy the K-rule. It must now equal the single-confirmer gate."""
    df_dec, df1, ref1, box = _frames()
    bar = pd.Timedelta(hours=1)
    src = runner.indicator_source_1min(df_dec, df1, bar)          # NO reference in the ctx
    only_rsi = runner.confirm_mask(df_dec, box, library.from_specs(_specs(["rsi"], mode="confirm")),
                                   k=2, src=src, ref_df=df_dec)
    with_dead = runner.confirm_mask(df_dec, box,
                                    library.from_specs(_specs(["rsi", "rolling_beta"], mode="confirm")),
                                    k=2, src=src, ref_df=df_dec)
    assert np.array_equal(only_rsi, with_dead), \
        "an unwired cross-series confirmer is still tightening the K-rule"


# ---- bug 3: the latent NameError ----------------------------------------------------------------
@pytest.mark.parametrize("key", _XS)
def test_entry_resolver_does_not_crash_on_a_cross_series_indicator(key):
    """`build_entry_resolver` referenced an undefined `ref_df`; `and` short-circuiting hid it for every
    indicator with needs_ref=False, so it only fired once one of these was enabled."""
    df_dec, _df1, _ref1, box = _frames()
    inds = library.from_specs(_specs([key], mode="confirm"))
    assert inds[0].needs_ref, "test premise: this indicator must be reference-dependent"
    runner.build_entry_resolver(df_dec, box, inds, k=1)                       # must not raise
    runner.build_layer(df_dec, box, inds, k=1, vol_gate=np.ones(len(df_dec), bool))


# ---- the memo must not serve a reference-free source to a reference-carrying run -----------------
def test_cached_source_memo_keys_on_the_reference():
    from optimize import core
    df_dec, df1, ref1, _box = _frames()
    bar = pd.Timedelta(hours=1)
    core._clear_caches()
    a = core._cached_source(df_dec, df1, bar)                      # no reference
    b = core._cached_source(df_dec, df1, bar, ref1)                # same slice, WITH a reference
    assert a[0].ref_close is None
    assert b[0].ref_close is not None, \
        "the memo served the reference-free source — it is not keyed on the reference"
    assert core._cached_source(df_dec, df1, bar)[0].ref_close is None, "and back again"
