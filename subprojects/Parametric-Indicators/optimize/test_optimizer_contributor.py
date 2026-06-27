import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optuna
import numpy as np
import warnings
warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)
from optimize import contributor_search as cs


def test_l1_es_exclude_drops_smc_and_two_heavies():
    for k in ("structure_trend", "order_block", "fvg", "ifvg", "breaker", "cisd", "stochastic", "adx"):
        assert k in cs.L1_ES_EXCLUDE
    study = optuna.create_study()
    t = study.ask()
    cs.suggest_contributor(t, "ES", exclude_committee=cs.L1_ES_EXCLUDE)
    assert "es_enabled" in t.params                       # searchable, not forced
    assert "es_en_stochastic" not in t.params and "es_en_ifvg" not in t.params
    assert "es_en_ema_trend" in t.params


def test_lookahead_guard_via_masks():
    from optimize import contributor_masks as cm
    from optimize.l2 import payload
    from optimize.l2.contributors import gate as g
    l1 = payload.run_l1_cached("4h")
    n = len(l1.df_dec)
    cfg = {"contributor_topology": "or_boost",
           "contributors": [{"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
                             "signal": {"encoding": "none"},
                             "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                                            "params": {"fast": 20, "slow": 50}}]}]}
    g._clear_caches()
    out = cm.precompute_contributor_masks(cfg, l1.df_dec, l1.df1, l1.box, np.asarray(l1.sig_int), l1.bar_td)
    assert out is not None and len(out["parsed"][0][0]) == n
    assert (out["parsed"][0][0] >= 0).all()
