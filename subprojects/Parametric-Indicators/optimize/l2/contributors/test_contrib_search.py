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


def test_es_source_cache_parity_and_speedup():
    import time
    import numpy as np
    from optimize.l2 import payload
    from optimize.l2.contributors import gate
    l1 = payload.run_l1_cached("4h")
    cfg = {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch",
           "signal": {"encoding": "stance", "mode": "both"},
           "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                          "params": {"fast": 20, "slow": 50}}]}
    gate._clear_caches()
    t = time.time(); v1, c1 = gate.contributor_gate_masks(cfg, l1); cold = time.time() - t
    t = time.time(); v2, c2 = gate.contributor_gate_masks(cfg, l1); warm = time.time() - t
    assert np.array_equal(v1, v2) and np.array_equal(c1, c2)   # cache is result-neutral (identical masks)
    assert ("ES", "4h") in gate._SRC_CACHE and ("ES", "4h") in gate._INPUT_CACHE
    assert warm < cold                                          # warm reuses the cached source => faster
    print(f"\n[cache] cold={cold:.2f}s warm={warm:.2f}s ({cold/max(warm,1e-3):.0f}x)")
