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


# ── the end-to-end test, which is the one that would actually have caught this ──────────────────────
# The unit tests above passed while the bug was still live, because the rounding existed in TWO places:
# report_wsi wrote the pareto CSV, and build_champions_from_pareto re-rounded it back down to 4 dp on the
# way into the champion JSON. Fixing one and testing the helper in isolation proved nothing. Test the
# PIPELINE — csv -> champion — or you are testing a function, not the thing that ships.

def test_pipeline_csv_to_champion_preserves_precision(tmp_path, monkeypatch):
    """A real pareto CSV goes through the real champion_for() and comes back as a champion box.

    This is the test that would have caught the bug. The isolated _sig() tests above all PASSED while the
    champion on disk was still corrupt, because a second round(x, 4) sat downstream in this very function.
    """
    import csv

    import optimize.build_champions_from_pareto as B

    true_sl = 0.0008091912403781283       # the NG 5m values that flipped the sign
    true_tp = 0.003925881552422834
    true_dd = 0.0035520951848387813
    true_gate = 98.80210665435305

    row = {"tf": "5m", "median_pnl": "1", "full_pnl": "1", "full_dd": "1", "win": "50",
           "sl_soft": repr(true_sl), "sl_hard": repr(true_sl * 1.25), "tp": repr(true_tp),
           "gate_pct": repr(true_gate), "dd_limit": repr(true_dd), "cooldown": "1",
           "flip": "False", "k": "1", "cap_1min": "0", "cap_mode": "eod",
           "n_indicators": "0", "indicators": ""}

    monkeypatch.setattr(B, "_RESULTS", tmp_path)
    monkeypatch.setattr(B, "_SUF", "_NG")
    with open(tmp_path / "5m_wsi_pareto_NG.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row)); w.writeheader(); w.writerow(row)

    box = B.champion_for("5m")["box"]           # the REAL extraction path, end to end

    assert box["sl_soft"] == pytest.approx(true_sl, rel=1e-9), (
        f"champion on disk carries {box['sl_soft']!r}, not {true_sl!r} — something re-rounded it")
    assert box["tp"] == pytest.approx(true_tp, rel=1e-9)
    assert box["dd_limit"] == pytest.approx(true_dd, rel=1e-9)
    assert box["gate_pct"] == pytest.approx(true_gate, rel=1e-9)


def test_no_module_persists_a_price_param_with_fixed_decimals():
    """Guard against a THIRD copy of the bug appearing. round(x, 4) on a price param is always wrong."""
    import pathlib
    import re
    bad = []
    for f in ("optimize/report_wsi.py", "optimize/build_champions_from_pareto.py"):
        src = pathlib.Path(f).read_text()
        for m in re.finditer(r"round\(\s*[^,()]*\b(sl_soft|sl_hard|tp|dd_limit|gate_pct)\b[^,()]*,\s*\d+\s*\)", src):
            bad.append(f"{f}: {m.group(0)}")
    assert not bad, "price params must be persisted with _sig(), not round(x, N):\n  " + "\n  ".join(bad)
