import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import control

_KEYS = ("WSH_ONLY", "WSH_EXCLUDE", "WSH_REFERENCE", "WSH_MAXENABLED", "WSH_INSTRUMENT",
         "WSH_IND1MIN", "WSH_TFS", "WSH_NOWARM", "WSH_DD_CAP")


def _clear():
    for k in _KEYS:
        os.environ.pop(k, None)


def test_apply_env_maps_the_new_selections():
    _clear()
    control._apply_env({"only_indicators": ["rsi", "macd"], "reference": "ES", "max_enabled": 3,
                        "instrument": "NQ", "ind_1min": False, "timeframes": ["4h", "1h"],
                        "cold_start": True, "dd_cap": 0.5})
    assert os.environ["WSH_ONLY"] == "rsi,macd"
    assert os.environ["WSH_REFERENCE"] == "ES"
    assert os.environ["WSH_MAXENABLED"] == "3"
    assert os.environ["WSH_INSTRUMENT"] == "NQ"
    assert os.environ["WSH_TFS"] == "4h 1h"
    assert os.environ["WSH_IND1MIN"] == "0"          # decision-TF (ind_1min False)
    assert os.environ["WSH_NOWARM"] == "1"           # cold start
    assert os.environ["WSH_DD_CAP"] == "0.5"


def test_config_exposes_instruments_and_indicator_families():
    cfg = control.config()
    assert set(("NQ", "ES", "GC")).issubset(set(cfg["instruments"]))   # matrix picker source (D2)
    inds = cfg["indicators"]
    assert inds and all("family" in i and "key" in i for i in inds)    # family-grouped picker (D1)


def test_apply_env_exclude_list_and_defaults():
    _clear()
    control._apply_env({"exclude_indicators": ["ifvg", "breaker"]})
    assert os.environ["WSH_EXCLUDE"] == "ifvg,breaker"
    assert os.environ.get("WSH_ONLY", "") == ""       # absent selection ⇒ unset ⇒ remote_wsi.sh omits the flag
    assert os.environ["WSH_IND1MIN"] == "1"           # default ON (backward-compatible)
