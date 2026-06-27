import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import contributor_masks as cm
from optimize.l2 import payload


def _l1():
    return payload.run_l1_cached("4h")


def test_none_when_no_contributors():
    l1 = _l1()
    assert cm.precompute_contributor_masks({"indicators": []}, l1.df_dec, l1.df1, l1.box,
                                           np.asarray(l1.sig_int), l1.bar_td) is None
    assert cm.precompute_contributor_masks(
        {"contributors": [{"token": "ES", "enabled": False}]}, l1.df_dec, l1.df1, l1.box,
        np.asarray(l1.sig_int), l1.bar_td) is None


def test_enabled_es_returns_aligned_masks():
    l1 = _l1()
    n = len(l1.df_dec)
    p = {"contributor_topology": "or_boost",
         "contributors": [{"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
                           "signal": {"encoding": "stance", "mode": "both", "table": {}},
                           "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                          "params": {"fast": 20, "slow": 50}}]}]}
    out = cm.precompute_contributor_masks(p, l1.df_dec, l1.df1, l1.box, np.asarray(l1.sig_int), l1.bar_td)
    assert out["topology"] == "or_boost"
    assert out["veto"].dtype == bool and len(out["veto"]) == n
    assert len(out["parsed"]) == 1
    ccount, k_es, has = out["parsed"][0]
    assert ccount.dtype == np.int64 and len(ccount) == n and k_es == 1 and has is True
