"""Reusable 2-state local-level+trend Kalman (constant-velocity). Forward filter → causal per-bar velocity
+ its variance → a unitless z-score trend strength. No fitting; q/r are fixed knobs."""
from __future__ import annotations
import numpy as np


def velocity_z(log_prices, q=1e-5, r=1.0):
    y = np.asarray(log_prices, dtype=float)
    n = y.size
    vel = np.zeros(n); var = np.zeros(n)
    if n == 0:
        return np.zeros(0), vel, var
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([1.0, 0.0])
    # continuous white-noise-acceleration process covariance (dt=1), scaled by q
    Q = q * np.array([[1.0 / 3.0, 1.0 / 2.0], [1.0 / 2.0, 1.0]])
    x = np.array([y[0], 0.0]); P = np.eye(2)
    for t in range(n):
        x = F @ x; P = F @ P @ F.T + Q                       # predict
        S = float(H @ P @ H + r)                             # innovation variance
        K = (P @ H) / S                                      # gain
        x = x + K * (y[t] - float(H @ x))                    # update
        P = P - np.outer(K, H) @ P
        vel[t] = x[1]; var[t] = P[1, 1]
    z = vel / np.sqrt(np.maximum(var, 1e-12))
    return z, vel, var
