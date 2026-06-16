import numpy as np

from optimize import counterfactual_pause as CP


def test_attribute_partition():
    # engine convention: entry bar idx uses sig[idx-1] for the box signal and the masks AT idx for the gate.
    sig = np.array([1, 1, 0, 1, 1, 1, 0], dtype=int)       # box signal per bar (sig[idx-1] feeds entry idx)
    vol_gate = np.array([1, 1, 0, 1, 1, 1, 1], dtype=bool)  # idx2 vol-gated
    veto = np.array([0, 0, 0, 0, 1, 0, 0], dtype=bool)      # idx4 vetoed
    confirm = np.array([1, 1, 1, 1, 1, 0, 1], dtype=bool)   # idx5 confirm<K
    cause = CP.attribute(sig, vol_gate, veto, confirm)     # one label per ENTRY bar idx
    assert list(cause[1:]) == ["would_enter", "vol_gated", "box_silence",
                               "vetoed", "confirm<K", "would_enter"]


def test_attribute_every_bar_one_label():
    rng = np.random.default_rng(0)
    n = 200
    sig = rng.integers(-1, 2, n)
    vg = rng.random(n) > .3
    ve = rng.random(n) > .8
    cf = rng.random(n) > .2
    cause = CP.attribute(sig, vg, ve, cf)
    assert set(cause[1:]) <= {"box_silence", "vol_gated", "vetoed", "confirm<K", "would_enter"}
    assert all(c is not None for c in cause[1:])


def test_isolated_sim_matches_real_taken_trade():
    """The isolated simulator must reproduce a really-taken trade's P/L exactly (isolated exit == engine exit)."""
    C = CP.load_champion("4h")
    taken = CP.champion_taken_trades(C)        # real fast_backtest run with the champion gate
    assert taken, "champion produced no trades"
    t0 = taken[len(taken) // 2]                # a mid-sample real trade
    sim = CP.simulate_one(C, int(t0["entry_idx"]))
    assert sim is not None
    assert abs(float(sim["pnl_points"]) - float(t0["pnl_points"])) < 1e-6
    assert sim["exit_reason"] == t0["exit_reason"]
