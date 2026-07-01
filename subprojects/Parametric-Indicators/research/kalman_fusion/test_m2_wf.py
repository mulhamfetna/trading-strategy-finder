import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z
from research.kalman_fusion.m2_walkforward import quarter_folds, window_stats


def test_quarter_folds_causal_expanding():
    C = cp.load_champion("4h")
    folds = quarter_folds(C)
    assert len(folds) >= 3
    starts = [f["q_start"] for f in folds]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)   # strictly expanding
    for f in folds:
        assert 0 < f["q_start"] < f["q_end"] <= C["n"]                    # train non-empty, precedes test


def test_window_partition_equals_full():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    full = window_stats(C, z, 1e9, "redirect", 0, C["n"])                 # theta=inf → champion book, whole span
    d = C["d"]["Date"]; key = (d.dt.year * 10 + ((d.dt.month - 1) // 3 + 1)).to_numpy()
    tot = 0.0
    for k in sorted(set(key.tolist())):
        idx = np.where(key == k)[0]
        tot += window_stats(C, z, 1e9, "redirect", int(idx[0]), int(idx[-1] + 1))["pnl"]
    assert abs(tot - full["pnl"]) < 1e-6


from research.kalman_fusion.m2_walkforward import select_theta_train, evaluate_quarter, walk_forward


def test_evaluate_quarter_champion_is_theta_inf():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    f = quarter_folds(C)[0]
    m2_inf, champ = evaluate_quarter(C, z, 1e9, "redirect", f["q_start"], f["q_end"])
    assert m2_inf == champ                              # theta=inf admits nothing => M2==champion


def test_select_theta_uses_train_only():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"].copy()
    f = quarter_folds(C)[0]
    th0 = select_theta_train(C, z, "redirect", f["q_start"])
    z[f["q_end"] - 1] = 999.0                           # perturb a TEST-quarter signal's z
    th1 = select_theta_train(C, z, "redirect", f["q_start"])
    assert th0 == th1                                   # theta* depends on train only


def test_walk_forward_aggregate_shape():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    wf = walk_forward(C, z, "redirect")
    assert wf["n_folds"] == len(quarter_folds(C))
    assert len(wf["rows"]) == wf["n_folds"]
    assert 0 <= wf["folds_m2_wins"] <= wf["n_folds"]
