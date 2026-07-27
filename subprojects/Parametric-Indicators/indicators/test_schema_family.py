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


def test_every_indicator_has_a_lead_lag_class():
    inds = library.schema()["indicators"]
    ll = {i["key"]: i["lead_lag"] for i in inds}
    assert all(v in ("leading", "lagging", "filter") for v in ll.values())
    from collections import Counter
    c = Counter(ll.values())
    assert c == {"leading": 80, "lagging": 61, "filter": 24}, dict(c)   # doc #30 counts


def test_lead_lag_spot_checks():
    ll = {i["key"]: i["lead_lag"] for i in library.schema()["indicators"]}
    assert ll["ema_trend"] == "lagging" and ll["wma"] == "lagging"        # moving averages
    assert ll["rsi"] == "leading" and ll["stoch_rsi"] == "leading"        # oscillators
    assert ll["order_block"] == "leading" and ll["pivot_floor"] == "leading"
    assert ll["qqe"] == "leading" and ll["elder_ray"] == "leading"        # momentum-core hybrids
    assert ll["atr_norm"] == "filter" and ll["hurst_exp"] == "filter"     # regime/vol vetoes
    assert ll["supertrend"] == "lagging" and ll["donchian"] == "lagging"
