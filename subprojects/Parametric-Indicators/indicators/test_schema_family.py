import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indicators import library


def test_every_indicator_has_a_family():
    inds = library.schema()["indicators"]
    assert all("family" in i for i in inds), [i["key"] for i in inds if "family" not in i]
    fams = {i["family"] for i in inds}
    assert {"ma", "oscillator", "trend", "cross_series"} <= fams, fams
    # families cover the whole registry
    assert len(inds) == len(library.REGISTRY)


def test_family_assignment_is_correct():
    fam = {i["key"]: i["family"] for i in library.schema()["indicators"]}
    assert fam["wma"] == "ma"
    assert fam["rsi_cutler"] == "oscillator"
    assert fam["supertrend"] == "trend"
    assert fam["cointegration"] == "cross_series"
    assert fam["super_smoother"] == "dsp"
    assert fam["ema_trend"] == "builtin"      # one of the 18 originals
