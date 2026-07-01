"""M2 walk-forward validation: expanding-window quarterly. theta selected on train, scored on the next test
quarter, vs the champion's same-quarter trades. Reuses M2 policy + Phase-1 rig. Off the production path."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion import rig
from research.kalman_fusion.m2_trend import policy
from research.kalman_fusion.ceiling import eligible_dropped
from research.kalman_fusion.metrics import payoff_ratio


def _quarter_key(dates):
    return (dates.dt.year * 10 + ((dates.dt.month - 1) // 3 + 1)).to_numpy()


def quarter_folds(C):
    key = _quarter_key(C["d"]["Date"])
    uniq = sorted(set(key.tolist()))
    folds = []
    for k in uniq:
        if sum(1 for u in uniq if u < k) < 2:        # need >= 2 prior quarters of train
            continue
        idx = np.where(key == k)[0]
        folds.append({"q": int(k), "q_start": int(idx[0]), "q_end": int(idx[-1] + 1)})
    return folds


def _entry_bar_idx(C, book):
    dec = C["d"]["Date"].to_numpy("datetime64[ns]")
    et = np.array([np.datetime64(t["entry_time"]) for t in book], dtype="datetime64[ns]")
    return np.searchsorted(dec, et, side="left")     # entry_time == a decision-bar date → exact index


def window_stats(C, z, theta, mode, lo, hi) -> dict:
    admit, direction = policy(C, z, theta, mode)
    book = rig.run_book(C, admit, direction)
    if not book:
        return {"pnl": 0.0, "n": 0, "win": 0.0, "payoff": 0.0}
    idx = _entry_bar_idx(C, book)
    pnls = np.array([book[k]["pnl"] for k in range(len(book)) if lo <= idx[k] < hi], dtype=float)
    n = int(pnls.size)
    return {"pnl": float(pnls.sum()), "n": n,
            "win": (float((pnls > 0).sum()) / n if n else 0.0), "payoff": payoff_ratio(pnls)}
