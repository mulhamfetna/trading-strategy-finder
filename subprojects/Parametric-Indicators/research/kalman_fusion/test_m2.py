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
