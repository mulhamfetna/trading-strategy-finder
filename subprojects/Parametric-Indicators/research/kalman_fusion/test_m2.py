import numpy as np
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion.kalman_trend import velocity_z


def test_velocity_positive_on_uptrend():
    y = np.arange(500, dtype=float) * 0.1     # steady up-trend, slope 0.1 (z scales with slope)
    z, vel, var = velocity_z(y)
    assert z.shape == y.shape
    assert vel[-1] > 0 and z[-1] > 3.0        # clearly positive trend, high z
    yf = np.full(400, 5.0)                    # flat
    zf, velf, _ = velocity_z(yf)
    assert abs(velf[-1]) < 1e-2 and abs(zf[-1]) < 1.0
    assert z[-1] > 5.0 * abs(zf[-1]) or abs(zf[-1]) < 0.5   # trend clearly separates from flat


def test_filter_is_causal():
    rng = np.arange(600, dtype=float)
    y = np.log(1000.0 + rng + np.sin(rng / 7.0))
    _, vfull, _ = velocity_z(y)
    _, vtrunc, _ = velocity_z(y[:400])
    assert np.allclose(vtrunc, vfull[:400], atol=0, rtol=0)


from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_trend import trend_z


def test_trend_z_shape_and_keys():
    C = cp.load_champion("4h")
    z = trend_z(C, frames=("4h", "1m"))
    assert set(z) == {"4h", "1m", "combined"}
    assert all(v.shape == (C["n"],) for v in z.values())
    assert np.allclose(z["combined"], z["4h"] + z["1m"])


def test_trend_z_is_causal():
    C = cp.load_champion("4h")
    zf = trend_z(C, frames=("4h",))["4h"]
    m = 1400
    Ct = dict(C); Ct["d"] = C["d"].iloc[:m].copy(); Ct["sig"] = np.asarray(C["sig"])[:m]; Ct["n"] = m
    zt = trend_z(Ct, frames=("4h",))["4h"]
    assert np.allclose(zt, zf[:m])


from research.kalman_fusion.m2_trend import policy
from research.kalman_fusion.ceiling import eligible_dropped


def test_policy_high_theta_reproduces_champion():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    admit, direction = policy(C, z, theta=1e9, mode="redirect")
    assert np.array_equal(admit, cp._engine_gate(C))
    assert int((direction != 0).sum()) == 0


def test_redirect_flips_and_filter_skips_on_disagreement():
    C = cp.load_champion("4h")
    i = eligible_dropped(C)["idxs"][0]
    box = int(np.sign(C["sig"][i - 1]))
    z = np.zeros(C["n"]); z[i] = -5.0 * (box if box != 0 else 1)   # trend OPPOSES the box direction
    a_r, d_r = policy(C, z, theta=1.0, mode="redirect")
    a_f, d_f = policy(C, z, theta=1.0, mode="filter")
    assert a_r[i] and d_r[i - 1] == int(np.sign(z[i]))            # re-direct admits + flips
    assert not a_f[i]                                             # filter skips the disagreement


from research.kalman_fusion.m2_trend import evaluate_m2


def test_evaluate_high_theta_is_champion():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    is_m, oos_m = evaluate_m2(C, z, theta=1e9, mode="redirect")
    champ = sum(t["pnl_points"] * C["pv"] for t in cp.champion_taken_trades(C))
    assert abs((is_m.total_pnl + oos_m.total_pnl) - champ) < 1e-6


def test_entry_rate_non_increasing_in_theta_m2():
    C = cp.load_champion("4h")
    z = trend_z(C)["combined"]
    rates = []
    for th in (0.0, 1.0, 2.0, 1e9):
        is_m, oos_m = evaluate_m2(C, z, theta=th, mode="redirect")
        rates.append(is_m.n_entries + oos_m.n_entries)
    assert all(rates[k] >= rates[k + 1] for k in range(len(rates) - 1))
