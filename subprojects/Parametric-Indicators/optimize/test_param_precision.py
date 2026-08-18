"""A champion's stops must survive extraction EXACTLY, at any price scale.

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

WHY THIS FILE NOW DEMANDS EXACTNESS RATHER THAN A SMALL ERROR (2026-07-29).

Note the shape of the mistake, repeated three times: 1 dp broke silver, so it was "fixed" to 4 dp, which
broke natural gas, so it was "fixed" to 12 SIGNIFICANT digits — scale-free, and ~10 orders of magnitude
safer. But that third fix shipped with a docstring claiming 12 digits "round-trips a float64 losslessly",
and that was false: measured, it reproduces the searched float exactly ~0.01% of the time (float64 needs
17 significant digits in the worst case). Each fix repaired the market that had just broken and left a
smaller copy of the same flaw behind.

So these tests no longer ask "is the error negligible?" — that question is what kept the bug alive
through three rewrites, because the answer was always yes right up until it was no. They ask "is the
value the optimizer searched the value the engine runs?" and accept nothing less than ==.

There is no cost to that. csv.DictWriter formats floats with str(), which in Python 3 is the shortest
string that round-trips EXACTLY. Writing the raw float is both the most precise option and the most
compact honest one: 10,000/10,000 exact round-trips from NG to YM price scales, versus ~1/10,000 for the
12-digit version. Rounding was never buying anything.
"""
import math
import pathlib
import re

import pytest

from optimize.report_wsi import _exact

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

# Values with long mantissas — the ones a 12-significant-digit round would actually damage. Real
# optimizer output looks like this, not like 12.3.
SEARCHED = [
    0.0008091912403781283, 0.003925881552422834, 0.0035520951848387813, 98.80210665435305,
    69.24880000000001, 1.2345678901234567, 44452.123456789012, 0.000123456789012345,
]


@pytest.mark.parametrize("mkt,v", sorted(REAL_STOPS.items()))
def test_persisted_value_is_bit_identical_at_every_price_scale(mkt, v):
    """The whole point: precision must not depend on how expensive the market is."""
    assert _exact(v) == v, f"{mkt}: {v!r} -> {_exact(v)!r} — a persisted price param was altered"


@pytest.mark.parametrize("v", SEARCHED)
def test_long_mantissa_values_survive_exactly(v):
    """These are what the optimizer actually searches. A 12-sig-digit round mangles most of them."""
    assert _exact(v) == v


@pytest.mark.parametrize("v", SEARCHED)
def test_roundtrips_through_csv_text_exactly(v):
    """The value is written to a CSV and read back. It must survive the trip BIT-FOR-BIT.

    csv.DictWriter formats floats with str(); asserting on str() here is testing the real write path.
    """
    assert float(str(_exact(v))) == v


def test_the_exact_value_that_flipped_ng_5m():
    """The champion parameter that cost us a day. 4 dp moved it 1.1%; that flipped a $38,079 win to a loss."""
    true = 0.0008091912403781283
    assert round(true, 4) == 0.0008                                  # what the oldest code wrote
    assert abs(round(true, 4) - true) / true > 0.01                  # a >1% distortion — not a rounding error
    assert _exact(true) == true                                      # what it writes now: the value itself


def test_twelve_significant_digits_was_still_lossy():
    """Guards the REASON for this rewrite, so nobody 'simplifies' back to significant-digit rounding.

    If someone reintroduces it, this documents what they would be giving up.
    """
    def sig12(v, digits=12):
        return round(v, -int(math.floor(math.log10(abs(v)))) + (digits - 1))
    lossy = [v for v in SEARCHED if sig12(v) != v]
    assert lossy, "expected 12-significant-digit rounding to be lossy on realistic optimizer output"
    assert all(_exact(v) == v for v in lossy), "exact persistence must keep every one of them"


def test_no_stop_is_ever_collapsed_to_zero():
    """A zero-width stop/target is a degenerate strategy the engine cannot express. It killed silver once."""
    for mkt, v in REAL_STOPS.items():
        assert _exact(v) != 0.0, f"{mkt}: {v!r} collapsed to zero"
    assert _exact(1e-12) == 1e-12                                    # even absurdly small values survive


def test_edges():
    assert _exact(0.0) == 0.0
    assert _exact(None) is None
    assert math.isnan(_exact(float("nan")))
    assert math.isinf(_exact(float("inf")))
    assert _exact(-0.0008091912403781283) == -0.0008091912403781283


# ── the end-to-end test, which is the one that would actually have caught this ──────────────────────
# The unit tests above passed while the bug was still live, because the rounding existed in TWO places:
# report_wsi wrote the pareto CSV, and build_champions_from_pareto re-rounded it back down to 4 dp on the
# way into the champion JSON. Fixing one and testing the helper in isolation proved nothing. Test the
# PIPELINE — csv -> champion — or you are testing a function, not the thing that ships.

def test_pipeline_csv_to_champion_preserves_precision(tmp_path, monkeypatch):
    """A real pareto CSV goes through the real champion_for() and comes back as a champion box.

    This is the test that would have caught the bug. The isolated helper tests above all PASSED while the
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

    # EXACT, not approx: the champion the engine runs must be the champion the optimizer searched.
    assert box["sl_soft"] == true_sl, (
        f"champion on disk carries {box['sl_soft']!r}, not {true_sl!r} — something re-rounded it")
    assert box["tp"] == true_tp
    assert box["dd_limit"] == true_dd
    assert box["gate_pct"] == true_gate


def test_price_scaled_defaults_are_not_rounded():
    """The copy the file-scanning guard below could NOT see (issue #2, 2026-07-29).

    `payload._scaled_permissive()` scaled the permissive anchor to an instrument's price and then applied
    round(x, 4) — the same bug, in the one place it does most damage: scaling a NQ-sized stop DOWN to a
    cheap market. A 40-point NQ stop becomes ~0.0071 on natural gas, and 4 dp leaves that two significant
    digits. The regex guard missed it for two years because the field name is a loop variable, so there
    was no literal `sl_soft` next to the `round(` to match.

    This is a BEHAVIOURAL check for exactly that reason — it cannot be evaded by how the code is spelled.

    The scale factor is INJECTED rather than read from price data, which keeps this runnable in CI (no
    market CSVs) and lets us pick the ratios that actually expose rounding — a real NG/NQ ratio near
    1.8e-4 is precisely where round(x, 4) eats a stop alive.
    """
    from optimize import instruments
    from optimize.l2 import payload as P

    # (label, scale factor). NG/NQ ~ 3.57/20000; HG/NQ ~ 4.5/20000; plus an exact-power-of-two control.
    for label, sf in [("NG-like", 3.57 / 20000), ("HG-like", 4.5 / 20000), ("SI-like", 31.0 / 20000),
                      ("GC-like", 2763.0 / 20000), ("same-scale", 1.0), ("pow2", 0.03125)]:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(instruments, "scale_factor", lambda _inst, _sf=sf: _sf)
            scaled = P._scaled_permissive("NG")
            for f in ("sl_soft", "sl_hard", "tp", "dd_limit"):
                want = P.PERMISSIVE.get(f)
                if want is None:
                    continue
                assert scaled[f] == float(want) * sf, (
                    f"{label}: {f} scaled to {scaled[f]!r}, exact product is {float(want) * sf!r} — "
                    f"something rounded a price-scaled parameter")


def test_no_module_persists_a_price_param_with_fixed_decimals():
    """Guard against another copy of the bug appearing.

    Widened 2026-07-29: it used to scan only report_wsi and build_champions_from_pareto, which is why the
    live copy in l2/payload.py went unnoticed. Regexes cannot catch the loop-variable spelling — that is
    what test_price_scaled_defaults_are_not_rounded is for — so this is the cheap net, not the only one.
    """
    files = ["optimize/report_wsi.py", "optimize/build_champions_from_pareto.py", "optimize/l2/payload.py",
             "optimize/optimizer.py", "presets.py", "strategy.py"]
    bad = []
    for f in files:
        p = pathlib.Path(f)
        if not p.exists():
            continue
        src = p.read_text()
        for m in re.finditer(
                r"round\(\s*[^,()]*\b(sl_soft|sl_hard|tp|dd_limit|gate_pct)\b[^,()]*,\s*\d+\s*\)", src):
            bad.append(f"{f}: {m.group(0)}")
    assert not bad, "price params must be persisted exactly, never round(x, N):\n  " + "\n  ".join(bad)
