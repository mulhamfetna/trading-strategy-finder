import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m1_fusion import finer_tf_directions


def test_direction_matrix_shape_and_values():
    C = cp.load_champion("4h")
    Z, cols = finer_tf_directions(C, tfs=("1h", "15m", "5m"))
    assert Z.shape == (C["n"], 4)                 # 3 finer TFs + the 4h voter
    assert cols[-1] == "4h"
    assert set(np.unique(Z)).issubset({-1, 0, 1})
    # the 4h voter column is the 4h box direction read at i-1
    assert Z[5, -1] == int(np.sign(C["sig"][4]))


def test_direction_matrix_is_causal():
    # truncating the context to the first m 4h bars must not change any row < m of Z.
    C = cp.load_champion("4h")
    Zfull, _ = finer_tf_directions(C, tfs=("1h", "15m"))
    m = 1200
    Ctrunc = dict(C)
    Ctrunc["d"] = C["d"].iloc[:m].copy()
    Ctrunc["sig"] = np.asarray(C["sig"])[:m]
    Ctrunc["n"] = m
    Ztrunc, _ = finer_tf_directions(Ctrunc, tfs=("1h", "15m"))
    assert np.array_equal(Ztrunc, Zfull[:m])
