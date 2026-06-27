import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import core, contributor_masks as cm
from optimize.l2 import payload


def _params():
    return {"sl_soft": 150., "sl_hard": 167., "tp": 120., "gate_pct": 0., "dd_limit": 0.,
            "cooldown": 0, "flip": False, "window": "full", "indicators": [], "k": 1,
            "ind_1min": True, "cap_1min": 0}


def test_contrib_none_is_byte_identical():
    l1 = payload.run_l1_cached("4h")
    p = _params()
    a = core.backtest_metrics(l1.df_dec, l1.df1, l1.box, l1.vf, l1.n_split, p, l1.bar_td,
                              sig_int=np.asarray(l1.sig_int))
    b = core.backtest_metrics(l1.df_dec, l1.df1, l1.box, l1.vf, l1.n_split, p, l1.bar_td,
                              sig_int=np.asarray(l1.sig_int), contrib=None)
    assert a["pnl"] == b["pnl"] and a["n_taken"] == b["n_taken"]


def test_enabled_es_changes_the_book():
    l1 = payload.run_l1_cached("4h")
    p = _params()
    p2 = dict(p, contributor_topology="separate_and",
              contributors=[{"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
                             "signal": {"encoding": "stance", "mode": "both", "table": {}},
                             "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                            "params": {"fast": 20, "slow": 50}}]}])
    contrib = cm.precompute_contributor_masks(p2, l1.df_dec, l1.df1, l1.box, np.asarray(l1.sig_int), l1.bar_td)
    base = core.backtest_metrics(l1.df_dec, l1.df1, l1.box, l1.vf, l1.n_split, p, l1.bar_td,
                                 sig_int=np.asarray(l1.sig_int))
    withes = core.backtest_metrics(l1.df_dec, l1.df1, l1.box, l1.vf, l1.n_split, p2, l1.bar_td,
                                   sig_int=np.asarray(l1.sig_int), contrib=contrib)
    assert withes["n_taken"] != base["n_taken"]            # separate_and filters → fewer trades
