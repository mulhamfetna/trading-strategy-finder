"""M3 vol-regime tests (TDD, written first). Off production path; golden untouched.

Covers: regime causality, tercile balance, BASE re-sim identity, no look-ahead, exit-map train-only,
breakeven gate. See docs/superpowers/specs/2026-07-02-kalman-m3-regime-design.md §6.
"""
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion import m3_regime as m3

_C = None


def champ():
    global _C
    if _C is None:
        _C = cp.load_champion("4h")
    return _C


# --- 1. regime labels are causal: train-region labels depend only on vf[:train_hi] -----------------
def test_regime_labels_causal():
    vf = np.linspace(1.0, 4.0, 400)
    hi = 200
    lab = m3.regime_labels(vf, hi)
    vf2 = vf.copy(); vf2[hi:] = 999.0            # perturb ONLY the future
    lab2 = m3.regime_labels(vf2, hi)
    assert np.array_equal(lab[:hi], lab2[:hi])   # train-region labels unchanged
    assert set(np.unique(lab[:hi]).tolist()) <= {0, 1, 2}


# --- 2. terciles split the train slice ~1/3 each -------------------------------------------------
def test_tercile_balance_on_train():
    rng_vals = np.linspace(0.0, 1.0, 900)
    hi = 900
    lab = m3.regime_labels(rng_vals, hi)[:hi]
    counts = [int((lab == r).sum()) for r in (0, 1, 2)]
    assert all(abs(c - 300) <= 5 for c in counts), counts


# --- 3. BASE (x1.0) re-simulation reproduces the champion trade's own P/L -------------------------
def test_base_rescore_identity():
    C = champ()
    taken = cp.champion_taken_trades(C)
    for t in taken[:8]:
        got = m3.rescore_trade(C, t, "BASE")
        assert abs(got - t["pnl_points"] * C["pv"]) < 1e-6, t["entry_idx"]


# --- 4. rescored P/L uses only that trade's own forward path (no look-ahead) ----------------------
def test_no_lookahead_truncate_after_exit():
    C = champ()
    t = next(x for x in cp.champion_taken_trades(C) if x["exit_reason"] != "OPEN")
    full = m3.rescore_trade(C, t, "BASE")
    xt = np.datetime64(t["exit_time"])
    Ct = dict(C)
    keep = C["d1"]["Date"].to_numpy("datetime64[ns]") <= xt   # drop all 1-min bars AFTER the exit
    Ct["d1"] = C["d1"][keep]
    trunc = m3.rescore_trade(Ct, t, "BASE")
    assert abs(full - trunc) < 1e-6


# --- 5. learn_exit_map reads train-masked trades only ---------------------------------------------
def test_exit_map_train_only():
    C = champ()
    taken = cp.champion_taken_trades(C)
    reg = m3.regime_labels(C["vf"], C["n_split"])
    K = 40
    idxs = np.array([t["entry_idx"] for t in taken])
    # mask A: a per-bar mask True only where one of the FIRST K trades enters
    mask_first = np.zeros(C["n"], dtype=bool); mask_first[idxs[:K]] = True
    map_masked = m3.learn_exit_map(C, taken, reg, mask_first)          # full trade list, masked to first K
    map_subset = m3.learn_exit_map(C, taken[:K], reg, np.ones(C["n"], dtype=bool))  # only first K, all-True
    assert map_masked == map_subset                                   # test-region trades were ignored


# --- 6. breakeven gate: 60% regime admits, 55% doesn't -------------------------------------------
def test_breakeven_gate():
    adm = m3.admit_regimes_from_winrates({0: 0.60, 1: 0.55, 2: 0.50}, breakeven=0.575)
    assert adm == {0}
