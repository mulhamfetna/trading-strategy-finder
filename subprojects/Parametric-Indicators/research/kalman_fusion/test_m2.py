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
