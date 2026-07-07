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


def select_theta_train(C, z, mode, train_hi) -> float:
    idxs_tr = [i for i in eligible_dropped(C)["idxs"] if i < train_hi]
    if not idxs_tr:
        return 1e9
    grid = list(np.quantile(np.abs(z[idxs_tr]), [0.0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95])) + [1e9]
    best_th, best_pnl = 1e9, -1e18
    for th in grid:
        pnl = window_stats(C, z, float(th), mode, 0, train_hi)["pnl"]
        if pnl > best_pnl:
            best_pnl, best_th = pnl, float(th)
    return best_th


def evaluate_quarter(C, z, theta, mode, q_start, q_end):
    m2 = window_stats(C, z, theta, mode, q_start, q_end)
    champ = window_stats(C, z, 1e9, mode, q_start, q_end)     # theta=inf => champion book only
    return m2, champ


def walk_forward(C, z, mode) -> dict:
    rows = []; sm = sc = 0.0; wins = 0
    folds = quarter_folds(C)
    for f in folds:
        th = select_theta_train(C, z, mode, f["q_start"])
        m2, champ = evaluate_quarter(C, z, th, mode, f["q_start"], f["q_end"])
        rows.append({"q": f["q"], "theta": th, "m2": m2, "champ": champ})
        sm += m2["pnl"]; sc += champ["pnl"]; wins += int(m2["pnl"] > champ["pnl"])
    return {"rows": rows, "sum_m2_pnl": sm, "sum_champ_pnl": sc,
            "folds_m2_wins": wins, "n_folds": len(folds)}
