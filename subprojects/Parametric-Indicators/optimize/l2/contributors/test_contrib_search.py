import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import optuna
from optimize import optimizer as OPT


def test_suggest_indicators_prefix_namespaces_param_names():
    study = optuna.create_study()
    t = study.ask()
    OPT._suggest_indicators(t, prefix="es_")
    names = set(t.params)
    assert "es_en_ema_trend" in names and "es_ema_trend_fast" in names
    assert "en_ema_trend" not in names           # the default namespace is untouched


def test_prefix_default_is_unchanged():
    study = optuna.create_study()
    t = study.ask()
    OPT._suggest_indicators(t)
    assert "en_ema_trend" in t.params and "es_en_ema_trend" not in t.params


import json
from indicators import library as _lib


def _b_cap():
    b = OPT._load_json(OPT._BOUNDS)["4h"]
    cap = int(OPT._load_json(OPT._CAPS)["4h"]["cooldown_cap"])
    return b, cap


def test_suggest_l2_params_contributor_block_optin():
    from optimize.l2 import optimize as l2opt
    b, cap = _b_cap()
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = l2opt.suggest_l2_params(study.ask(), b, cap, contrib_tokens=["ES"])
    assert p["contributor_topology"] in ("separate_and", "merged", "or_boost")
    assert len(p["contributors"]) == 1
    c = p["contributors"][0]
    assert c["token"] == "ES" and c["state_def"] in ("touch", "traversal")
    assert c["signal"]["encoding"] in ("none", "stance", "truthtable")
    assert len(c["committee"]) == len(list(_lib.REGISTRY))
    assert isinstance(c["k_es"], int) and 1 <= c["k_es"] <= 5
    assert len(c["signal"]["table"]) == 6
    json.dumps(p)                       # the objective serializes params -> must be JSON-safe


def test_suggest_l2_params_no_tokens_is_backward_compatible():
    from optimize.l2 import optimize as l2opt
    b, cap = _b_cap()
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = l2opt.suggest_l2_params(study.ask(), b, cap)
    assert "contributors" not in p and "contributor_topology" not in p


def test_suggested_contributor_runs_in_engine():
    from optimize.l2 import optimize as l2opt, payload, engine
    b, cap = _b_cap()
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = l2opt.suggest_l2_params(study.ask(), b, cap, contrib_tokens=["ES"])
    l1 = payload.run_l1_cached("4h")
    r = engine.run_l2(l1, p)            # must not raise; produces a valid ledger
    assert isinstance(r.ledger, list)
