"""M2 — Kalman trend-state director for the champion's dropped 4h signals. Continuous price (4h + 1-min
frames, equal-weight z, NO fitting). Two decision modes (re-direct / trend-filter). Reuses Phase-1 rig +
M0 eligibility. Causal; exits fixed (payoff pinned)."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion.kalman_trend import velocity_z

_MIN = np.timedelta64(1, "m")


def trend_z(C, frames=("4h", "1m"), q=1e-5, r=1.0):
    n = int(C["n"]); out = {}
    if "4h" in frames:
        z4, _, _ = velocity_z(np.log(C["d"]["Close"].to_numpy(float)), q, r)
        col = np.zeros(n); col[1:] = z4[:n - 1]              # z as of the signal bar i-1
        out["4h"] = col
    if "1m" in frames:
        d1 = C["d1"]
        z1, _, _ = velocity_z(np.log(d1["Close"].to_numpy(float)), q, r)
        m1_close = d1["Date"].to_numpy("datetime64[ns]") + _MIN     # 1-min bar close
        dec_start = C["d"]["Date"].to_numpy("datetime64[ns]")[:n]   # 4h bar i start == bar i-1 close
        j = np.searchsorted(m1_close, dec_start, side="right") - 1  # last 1-min closed <= signal close
        out["1m"] = np.where(j >= 0, z1[np.clip(j, 0, len(z1) - 1)], 0.0)
    out["combined"] = sum(out[f] for f in frames)
    return out


from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped


def policy(C, z, theta, mode):
    n = int(C["n"])
    admit = np.asarray(cp._engine_gate(C)).copy()
    direction = np.zeros(n, dtype=np.int8)
    box = np.sign(np.asarray(C["sig"]).astype(int))
    for i in eligible_dropped(C)["idxs"]:
        if abs(z[i]) <= theta:
            continue
        zdir = int(np.sign(z[i]))
        if zdir == 0:
            continue
        if mode == "redirect":
            admit[i] = True; direction[i - 1] = zdir
        elif mode == "filter":
            bdir = int(box[i - 1])
            if bdir != 0 and zdir == bdir:
                admit[i] = True; direction[i - 1] = bdir
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return admit, direction
