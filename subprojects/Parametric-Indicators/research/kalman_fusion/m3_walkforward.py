"""M3 walk-forward validation: expanding-window quarterly. Regime cut-points, the 3a exit map, and the 3b
admission set are ALL learned on train (bars before the test quarter) and scored forward. Reuses m2's fold
generator + the M3 regime mechanism. Off the production path.

3a is the decisive gate (regime-scaled exits on the champion's own trades). 3b (regime-gated admission of extra
dropped signals, exited via the 3a map) is scored only when 3a survives.
"""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.m2_walkforward import quarter_folds
from research.kalman_fusion.ceiling import eligible_dropped
from research.kalman_fusion import m3_regime as m3


def _masks(C, q_start, q_end):
    idx = np.arange(C["n"])
    return (idx < q_start), (q_start <= idx) & (idx < q_end)


def walk_forward_3a(C) -> dict:
    """Per-fold: freeze terciles + learn exit map on train, score M3 vs BASE(=champion) on the test quarter."""
    taken = cp.champion_taken_trades(C)
    folds = quarter_folds(C)
    rows = []; sm = sb = 0.0; wins = 0
    for f in folds:
        q_start, q_end = f["q_start"], f["q_end"]
        reg = m3.regime_labels(C["vf"], q_start)                 # cuts frozen on train slice
        train_mask, test_mask = _masks(C, q_start, q_end)
        exit_map = m3.learn_exit_map(C, taken, reg, train_mask)
        m3_pnl = m3.apply_exit_map(C, taken, reg, exit_map, test_mask)
        base = m3.base_pnl(C, taken, test_mask)                  # BASE == champion exits
        n_test = int(sum(1 for t in taken if test_mask[int(t["entry_idx"])]))
        rows.append({"q": f["q"], "exit_map": exit_map, "m3_pnl": m3_pnl, "base_pnl": base, "n": n_test})
        sm += m3_pnl; sb += base; wins += int(m3_pnl > base)
    survived = wins > len(folds) / 2 and sm > sb
    return {"rows": rows, "sum_m3": sm, "sum_base": sb, "folds_m3_wins": wins,
            "n_folds": len(folds), "survived": survived}


def walk_forward_3b(C) -> dict:
    """Per-fold: inherit 3a's exit map, ALSO admit eligible-dropped signals whose train native-direction
    win-rate clears breakeven, exit them under their regime scheme. Score vs BASE(=champion)."""
    taken = cp.champion_taken_trades(C)
    dropped = eligible_dropped(C)["idxs"]
    folds = quarter_folds(C)
    rows = []; sm = sb = 0.0; wins = 0
    for f in folds:
        q_start, q_end = f["q_start"], f["q_end"]
        reg = m3.regime_labels(C["vf"], q_start)
        train_mask, test_mask = _masks(C, q_start, q_end)
        exit_map = m3.learn_exit_map(C, taken, reg, train_mask)
        admitted = m3.admit_by_regime(C, reg, train_mask)
        # champion trades exited via the 3a map (inherits 3a) ...
        pnl = m3.apply_exit_map(C, taken, reg, exit_map, test_mask)
        # ... plus newly-admitted dropped signals in the test quarter, native dir, regime-scheme exit
        add_n = 0
        for i in dropped:
            if test_mask[i] and int(reg[i]) in admitted:
                pnl += m3.rescore_trade(C, {"entry_idx": i}, exit_map[int(reg[i])])
                add_n += 1
        base = m3.base_pnl(C, taken, test_mask)
        rows.append({"q": f["q"], "admitted": sorted(admitted), "m3_pnl": pnl, "base_pnl": base,
                     "added": add_n})
        sm += pnl; sb += base; wins += int(pnl > base)
    return {"rows": rows, "sum_m3": sm, "sum_base": sb, "folds_m3_wins": wins, "n_folds": len(folds)}
