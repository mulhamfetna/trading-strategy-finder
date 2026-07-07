import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped, simulate_dir, signal_outcomes, ceiling_report


def test_eligible_dropped_shape_and_counts():
    C = cp.load_champion("4h")
    e = eligible_dropped(C)
    assert e["n_taken"] > 150                       # champion ~214 trades
    assert len(e["idxs"]) > 0                       # there ARE blocked-while-flat signals
    assert set(e["by_reason"]) <= {"vol_gated", "vetoed", "confirm<K"}
    assert e["n_eligible"] == e["n_taken"] + len(e["idxs"])
    assert e["n_taken"] / e["n_eligible"] < 0.5     # entry-rate today is well under half


def test_simulate_dir_matches_native_simulate_one():
    C = cp.load_champion("4h")
    idx = eligible_dropped(C)["idxs"][0]
    native_trade = cp.simulate_one(C, idx)             # engine's native-direction isolated trade
    assert native_trade is not None
    got = simulate_dir(C, idx, native_trade["direction"])
    assert abs(got - native_trade["pnl_points"] * C["pv"]) < 1e-6


def test_oracle_dominates_native():
    C = cp.load_champion("4h")
    idxs = eligible_dropped(C)["idxs"][:200]
    o = signal_outcomes(C, idxs)
    res = ~np.isnan(o["oracle"])
    assert res.any()
    assert np.all(o["oracle"][res] >= o["native"][res] - 1e-6)


def test_ceiling_report_structure_and_bounds():
    C = cp.load_champion("4h")
    rep = ceiling_report(C)
    assert "champion" in rep and "all" in rep
    base = rep["champion"]; allc = rep["all"]
    assert 0.0 < base["entry_rate"] < 0.5
    assert allc["oracle"]["entry_rate"] > base["entry_rate"]
    assert allc["oracle"]["total_pnl"] >= allc["native"]["total_pnl"] - 1e-6
    for r in ("vol_gated", "vetoed", "confirm<K"):
        assert r in rep
