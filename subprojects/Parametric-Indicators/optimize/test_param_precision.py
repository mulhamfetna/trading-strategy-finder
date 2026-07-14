"""A champion's stops must survive extraction at ANY price scale.

THE BUG THIS LOCKS OUT — it cost a full day and nearly shipped a losing strategy as a winner.

`report_wsi` persisted searched price params with round(x, 4): four DECIMAL PLACES. Our markets span four
orders of magnitude — the Dow trades near $44,000, natural gas near $3.57 — so a stop is ~10 points on YM
and ~0.0008 on NG. A fixed decimal count is therefore correct for one market and destructive to another:

    1 dp  destroyed silver    tp 0.04 -> 0.0                (a zero-width target)
    4 dp  destroyed nat gas   sl 0.00080919 -> 0.0008       (a 1.1% shift)
          and copper          stops start at 0.0013         (2 significant digits survive)

On NG 5m that 1.1% shift moved the champion's P/L by $39,793 and FLIPPED ITS SIGN: the optimizer measured
+$38,079, we wrote a mangled champion to disk, the causal engine faithfully reported -$1,714 for the
strategy we actually gave it, and we concluded the optimizer's fast engine was lying. It never lied. Six
"engine disagreements" across NG/HG/SI/CL — the four lowest-priced markets — were all this one bug.

Note the shape of the original mistake: 1 dp broke silver, so it was "fixed" to 4 dp. That fixed the market
that had just broken and left the ones nobody had tested yet. The lesson is not "use more decimals" — it is
that DECIMAL PLACES ARE THE WRONG UNIT. Significant digits are scale-free.
"""
import math

import pytest

from optimize.report_wsi import _sig

# Real champion stop sizes, smallest observed per market, across every champion set on disk.
# NG/HG are where 4-dp rounding does its damage; NQ/YM are where it is invisible.
REAL_STOPS = {
    "NG": 0.0008091912403781283,      # natural gas  ~$3.57   <- 4 dp leaves ONE significant digit
    "HG": 0.0013,                     # copper       ~$4.33   <- two
    "SI": 0.0124,                     # silver       ~$31     <- three
    "CL": 0.0188,                     # crude oil    ~$73
    "ES": 1.4527,                     # S&P 500      ~$6,053
    "GC": 1.4782,                     # gold         ~$2,763
    "RTY": 1.1397,                    # russell      ~$2,287
    "NQ": 12.3,                       # nasdaq       ~$21,614
    "YM": 10.246,                     # dow          ~$44,452
}


@pytest.mark.parametrize("mkt,v", sorted(REAL_STOPS.items()))
def test_relative_error_is_negligible_at_every_price_scale(mkt, v):
    """The whole point: precision must not depend on how expensive the market is."""
    err = abs(_sig(v) - v) / abs(v)
    assert err < 1e-9, f"{mkt}: {v!r} -> {_sig(v)!r} is a {err:.2%} distortion"


@pytest.mark.parametrize("mkt,v", sorted(REAL_STOPS.items()))
def test_roundtrips_through_csv_text(mkt, v):
    """The value is written to a CSV and read back. It must survive the trip."""
    assert float(str(_sig(v))) == pytest.approx(v, rel=1e-9)


def test_the_exact_value_that_flipped_ng_5m():
    """The champion parameter that cost us a day. 4 dp moved it 1.1%; that flipped a $38,079 win to a loss."""
    true = 0.0008091912403781283
    assert round(true, 4) == 0.0008                                  # what the old code wrote
    assert abs(round(true, 4) - true) / true > 0.01                  # a >1% distortion — not a rounding error
    assert _sig(true) == pytest.approx(true, rel=1e-9)               # what it writes now


def test_no_stop_is_ever_collapsed_to_zero():
    """A zero-width stop/target is a degenerate strategy the engine cannot express. It killed silver once."""
    for mkt, v in REAL_STOPS.items():
        assert _sig(v) != 0.0, f"{mkt}: {v!r} collapsed to zero"
    assert _sig(1e-12) != 0.0                                        # even absurdly small values survive


def test_significant_digits_beat_decimal_places_by_construction():
    """Same relative precision across 8 orders of magnitude — which round(x, N) can never give."""
    for exp in range(-6, 6):
        v = 1.2345678901234 * (10 ** exp)
        assert abs(_sig(v) - v) / v < 1e-9, f"failed at 1e{exp}"


def test_edges():
    assert _sig(0.0) == 0.0
    assert _sig(None) is None
    assert math.isnan(_sig(float("nan")))
    assert math.isinf(_sig(float("inf")))
    assert _sig(-0.0008091912403781283) == pytest.approx(-0.0008091912403781283, rel=1e-9)
