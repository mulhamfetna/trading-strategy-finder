import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pytest
from optimize.l2 import payload, engine

_P = {"sl_soft": 140.0, "sl_hard": 200.0, "tp": 200.0, "gate_pct": 0.0, "dd_limit": 0.0,
      "cooldown": 0, "flip": False, "k": 2, "ind_1min": True,
      "indicators": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                      "params": {"fast": 20, "slow": 50}},
                     {"key": "macd", "enabled": True, "mode": "confirm",
                      "params": {"fast": 12, "slow": 26, "signal": 9}}]}


def test_nq_components_confirm_count_reconstructs_mask():
    l1 = payload.run_l1_cached("4h")
    vol_gate, veto, confirm, cc, k_eff, ncf = engine._nq_components(l1, _P)
    n = len(confirm)
    rebuilt = np.ones(n, dtype=bool)
    rebuilt[1:] = (cc[1:] >= k_eff)               # cc is already entry-shifted; idx0 identity True
    assert k_eff == 2 and ncf == 2
    assert np.array_equal(rebuilt, confirm)        # count reconstructs runner.confirm_mask exactly


def test_l2_gate_components_unchanged_after_delegation():
    l1 = payload.run_l1_cached("4h")
    vg, vt, cf = engine.l2_gate_components(l1, _P)
    vg2, vt2, cf2, _, _, _ = engine._nq_components(l1, _P)
    assert np.array_equal(vg, vg2) and np.array_equal(vt, vt2) and np.array_equal(cf, cf2)


def _n_pnl(r):
    return len(r.ledger), round(sum(t["pnl_points"] for t in r.ledger), 4)


def _es(topology, k_es=1, mode="both", enabled=True):
    return {**_P, "contributor_topology": topology, "contributors": [
        {"token": "ES", "enabled": enabled, "tf": "4h", "state_def": "touch", "k_es": k_es,
         "signal": {"encoding": "stance", "mode": mode}, "committee": []}]}


def test_disabled_contributor_byte_parity_all_topologies():
    l1 = payload.run_l1_cached("4h")
    base = _n_pnl(engine.run_l2(l1, _P))
    for topo in ("separate_and", "merged", "or_boost"):
        assert _n_pnl(engine.run_l2(l1, _es(topo, enabled=False))) == base


def test_separate_tightens_or_boost_loosens_confirm_gate_level():
    l1 = payload.run_l1_cached("4h")
    n = len(l1.df_dec)
    base = engine._l2_eligibility(l1, _P)
    sep = engine._l2_eligibility(l1, _es("separate_and", k_es=1, mode="confirm"))
    org = engine._l2_eligibility(l1, _es("or_boost", k_es=1, mode="confirm"))
    mer = engine._l2_eligibility(l1, _es("merged", k_es=1, mode="confirm"))
    assert sep.shape == org.shape == mer.shape == (n,)
    assert bool((sep <= base).all())                  # separate-AND (confirm-only) only tightens
    assert bool((base <= org).all())                  # or-boost (confirm-only, no veto) only loosens
    assert int((~sep).sum()) > int((~base).sum())     # separate actually removes some eligible bars
    assert int(org.sum()) > int(base.sum())           # or-boost actually adds some eligible bars


def test_unsupported_topology_raises():
    l1 = payload.run_l1_cached("4h")
    with pytest.raises(ValueError, match="topology"):
        engine.run_l2(l1, _es("nonsense"))
