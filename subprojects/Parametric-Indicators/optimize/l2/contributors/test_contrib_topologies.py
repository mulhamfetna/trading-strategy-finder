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
