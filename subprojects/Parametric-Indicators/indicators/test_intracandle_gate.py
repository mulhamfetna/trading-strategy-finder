import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import numpy as np  # noqa: E402
from indicators import runner  # noqa: E402
from optimize import counterfactual_pause as cp  # noqa: E402


def test_gate_arrays_shape_and_causal():
    C = cp.load_champion("4h")
    inds = C["indicators"]
    g = runner.intracandle_gate_arrays(C["d1"], inds, C["K"])
    n1 = len(C["d1"])
    assert set(g.keys()) == {+1, -1}
    assert g[+1].shape == (n1,) and g[+1].dtype == bool
    # causality: truncating the 1-min frame past bar m leaves gate[:m] unchanged (no look-ahead)
    m = n1 // 2
    g_tr = runner.intracandle_gate_arrays(C["d1"].iloc[:m].copy(), inds, C["K"])
    assert np.array_equal(g[+1][:m], g_tr[+1][:m])
    assert np.array_equal(g[-1][:m], g_tr[-1][:m])
