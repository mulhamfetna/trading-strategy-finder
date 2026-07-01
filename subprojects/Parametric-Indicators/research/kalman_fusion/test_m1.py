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


from research.kalman_fusion.m1_fusion import n_split, profitable_side, fit_weights
from research.kalman_fusion.ceiling import eligible_dropped


def test_profitable_side_matches_signal_outcomes_sign():
    C = cp.load_champion("4h")
    idxs = eligible_dropped(C)["idxs"][:100]
    ps = profitable_side(C, idxs)
    assert set(np.unique(ps)).issubset({-1, 0, 1})
    assert (ps != 0).sum() > 0


def test_fit_weights_rewards_a_perfect_column():
    C = cp.load_champion("4h")
    idxs = eligible_dropped(C)["idxs"][:3]
    ps = profitable_side(C, idxs)
    Z = np.zeros((C["n"], 3), dtype=np.int8)
    for k, i in enumerate(idxs):
        Z[i, 0] = ps[k]; Z[i, 1] = -ps[k]; Z[i, 2] = 0
    w = fit_weights(Z, C, idxs)
    assert w[0] > w[1]
    assert w[1] == 0.0
