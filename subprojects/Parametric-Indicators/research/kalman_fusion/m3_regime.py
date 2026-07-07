"""M3 vol-regime mechanism: realized-vol terciles (from HAR-RV vf) drive (3a) per-regime exit scaling and
(3b) per-regime admission. Off the production path; reuses the Phase-1 rig + isolated re-simulation.

Regime causality: tercile cut-points are frozen on the TRAIN slice only (vf[:train_hi]) and applied forward.
Exit re-scoring is per-trade ISOLATED (research.counterfactual_pause.simulate_one_custom) — only the exit lines
move, so there is never look-ahead beyond a trade's own forward 1-minute path.
"""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped, _dirval

# a-priori exit schemes: fixed multipliers on the champion (sl_soft, sl_hard, tp). BASE == the champion (null).
EXIT_SCHEMES = {"TIGHT": 0.75, "BASE": 1.0, "WIDE": 1.5}
REGIMES = (0, 1, 2)                       # LO / MID / HI realized-vol tercile


def regime_labels(vf, train_hi: int) -> np.ndarray:
    """Per-bar vol-regime label {0,1,2} using tercile cut-points FROZEN on vf[:train_hi] (causal)."""
    vf = np.asarray(vf, dtype=float)
    lo, hi = np.quantile(vf[:int(train_hi)], [1.0 / 3.0, 2.0 / 3.0])
    return (vf > lo).astype(int) + (vf > hi).astype(int)


def rescore_trade(C, trade, scheme: str) -> float:
    """Re-simulate `trade` in isolation with the champion's exits scaled by `scheme`. Returns dollars.
    BASE (x1.0) reproduces the champion's own P/L (locked by test_base_rescore_identity)."""
    m = EXIT_SCHEMES[scheme]
    p = C["params"]
    t = cp.simulate_one_custom(C, int(trade["entry_idx"]),
                               float(p["sl_soft"]) * m, float(p["sl_hard"]) * m, float(p["tp"]) * m,
                               bool(p["flip"]))
    return float(t["pnl_points"]) * C["pv"] if t is not None else 0.0


def learn_exit_map(C, trades, regimes, train_mask) -> dict:
    """On TRAIN trades only, pick the P/L-maximising scheme per regime. Returns {regime: scheme}.
    A trade is train iff train_mask[entry_idx] is True — test-region trades are never read."""
    train_mask = np.asarray(train_mask, dtype=bool)
    out = {}
    for r in REGIMES:
        sub = [t for t in trades if train_mask[int(t["entry_idx"])] and int(regimes[int(t["entry_idx"])]) == r]
        if not sub:
            out[r] = "BASE"
            continue
        best, best_pnl = "BASE", -1e18
        for scheme in EXIT_SCHEMES:                       # dict order TIGHT,BASE,WIDE — BASE wins ties over WIDE
            pnl = sum(rescore_trade(C, t, scheme) for t in sub)
            if pnl > best_pnl:
                best_pnl, best = pnl, scheme
        out[r] = best
    return out


def apply_exit_map(C, trades, regimes, exit_map, test_mask) -> float:
    """Total dollars over TEST trades, each exited under its regime's learned scheme."""
    test_mask = np.asarray(test_mask, dtype=bool)
    return float(sum(rescore_trade(C, t, exit_map[int(regimes[int(t["entry_idx"])])])
                     for t in trades if test_mask[int(t["entry_idx"])]))


def base_pnl(C, trades, mask) -> float:
    """Total dollars over masked trades under BASE everywhere (the champion null)."""
    mask = np.asarray(mask, dtype=bool)
    return float(sum(rescore_trade(C, t, "BASE") for t in trades if mask[int(t["entry_idx"])]))


# ---- 3b admission -------------------------------------------------------------------------------
def admit_regimes_from_winrates(winrates: dict, breakeven: float = 0.575) -> set:
    """Pure gate: admit a regime iff its native-direction win-rate strictly clears the payoff breakeven."""
    return {r for r, w in winrates.items() if w > breakeven}


def _native_win(C, idx: int) -> int:
    """1 if the dropped signal at idx, taken in its NATIVE box direction, wins; else 0 (None-close -> 0)."""
    box = int(np.sign(C["sig"][idx - 1]))
    if box == 0:
        return 0
    p = C["params"]
    t = cp.simulate_one_custom(C, idx, float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"]),
                               bool(p["flip"]))
    if t is None:
        return 0
    got = _dirval(t["direction"])
    # champion flip already applied inside the engine; native win = realised side matches box AND pnl>0
    return int(got == box and t["pnl_points"] > 0)


def regime_native_winrates(C, regimes, train_mask) -> dict:
    """Native-direction win-rate of eligible-dropped signals per regime, on train."""
    train_mask = np.asarray(train_mask, dtype=bool)
    idxs = [i for i in eligible_dropped(C)["idxs"] if train_mask[i]]
    out = {}
    for r in REGIMES:
        sub = [i for i in idxs if int(regimes[i]) == r]
        wins = sum(_native_win(C, i) for i in sub)
        out[r] = (wins / len(sub)) if sub else 0.0
    return out


def admit_by_regime(C, regimes, train_mask, breakeven: float = 0.575) -> set:
    """Regimes whose train native-direction win-rate clears breakeven."""
    return admit_regimes_from_winrates(regime_native_winrates(C, regimes, train_mask), breakeven)
