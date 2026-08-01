import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import optuna
import numpy as np
import warnings
warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)
from optimize import contributor_search as cs


def test_the_historical_exclusion_still_works_when_it_is_ASKED_FOR():
    """#95 removed this as the DEFAULT, not as a capability. Reproducing a pre-2026-08-01 run means
    naming the keys explicitly, and that must keep working exactly as it did."""
    for k in ("structure_trend", "order_block", "fvg", "ifvg", "breaker", "cisd", "stochastic", "adx"):
        assert k in cs.L1_ES_EXCLUDE
    study = optuna.create_study()
    t = study.ask()
    cs.suggest_contributor(t, "ES", exclude_committee=cs.L1_ES_EXCLUDE)
    assert "es_enabled" in t.params                       # searchable, not forced
    assert "es_en_stochastic" not in t.params and "es_en_ifvg" not in t.params
    assert "es_en_ema_trend" in t.params


def test_nothing_is_withheld_by_DEFAULT_any_more():
    """THE #95 CHANGE. The eight were excluded on a cost that has since fallen ~100x — and the control
    showed four of the six were never expensive at all, excluded by FAMILY MEMBERSHIP rather than by
    measurement. A search that cannot reach an indicator can never learn it is useless either."""
    assert cs.DEFAULT_COMMITTEE_EXCLUDE == ()
    study = optuna.create_study()
    t = study.ask()
    cs.suggest_contributor(t, "ES")                       # no exclude_committee argument at all
    for k in ("ifvg", "breaker", "cisd", "fvg", "structure_trend", "order_block", "stochastic", "adx"):
        assert f"es_en_{k}" in t.params, f"{k} is still not searchable by default"


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
