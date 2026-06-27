import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest
from optimize.l2 import payload, engine

_P = {"sl_soft": 140.0, "sl_hard": 200.0, "tp": 200.0, "gate_pct": 0.0, "dd_limit": 0.0,
      "cooldown": 0, "flip": False, "k": 1, "ind_1min": True,
      "indicators": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                      "params": {"fast": 20, "slow": 50}}]}
BASE_N = 162
BASE_PNL = -490.25


def _n_pnl(r):
    return len(r.ledger), round(sum(t["pnl_points"] for t in r.ledger), 4)


def test_no_contributors_is_byte_identical_baseline():
    l1 = payload.run_l1_cached("4h")
    assert _n_pnl(engine.run_l2(l1, _P)) == (BASE_N, BASE_PNL)                          # absent block
    assert _n_pnl(engine.run_l2(l1, {**_P, "contributors": []})) == (BASE_N, BASE_PNL)  # empty
    assert _n_pnl(engine.run_l2(l1, {**_P, "contributors": [
        {"token": "ES", "enabled": False}]})) == (BASE_N, BASE_PNL)                     # disabled


def _es_on(topology="separate_and"):
    return {**_P, "contributor_topology": topology, "contributors": [
        {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 1,
         "signal": {"encoding": "stance", "mode": "both"},
         "committee": [{"key": "cci", "enabled": True, "mode": "veto",
                        "params": {"n": 20, "threshold": 100}}]}]}


def test_separate_and_gate_is_a_subset_of_base():
    # SEPARATE-AND only ANDs sub-gates, so the eligible-bar GATE is a subset of the base gate.
    # (NB: the TAKEN-trade set is NOT monotonic — fast_backtest is sequential, so removing an early
    #  entry can free a later one. The invariant lives at the gate, not the ledger.)
    import numpy as np
    l1 = payload.run_l1_cached("4h")
    n = len(l1.df_dec)
    base = np.ones(n, dtype=bool)
    out = engine._apply_contributors(l1, _es_on(), base.copy())
    assert out.dtype == bool and len(out) == n
    assert bool((out <= base).all())      # contributor sub-gate only removes bars, never adds
    assert int((~out).sum()) > 0          # and it actually removes some (the ES cci-veto fires)


def test_separate_and_is_live_impossible_k_blocks_all():
    # a confirm source (stance 'confirm') with an unreachable k_es => sub-gate all-False => 0 L2 trades.
    # Proves the wiring is actually active (not a no-op), deterministically + data-independent.
    l1 = payload.run_l1_cached("4h")
    block = {**_P, "contributor_topology": "separate_and", "contributors": [
        {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "k_es": 999,
         "signal": {"encoding": "stance", "mode": "confirm"}, "committee": []}]}
    assert len(engine.run_l2(l1, block).ledger) == 0


def test_unsupported_topology_raises():
    l1 = payload.run_l1_cached("4h")
    with pytest.raises(ValueError, match="topology"):
        engine.run_l2(l1, _es_on(topology="merged"))   # B2b adds merged/or_boost
