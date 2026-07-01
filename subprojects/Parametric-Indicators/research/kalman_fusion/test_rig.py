import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.rig import evaluate


def test_rig_reproduces_champion_metrics():
    C = cp.load_champion("4h")
    taken = cp.champion_taken_trades(C)                 # the engine's own trade list
    champ_pnls = [t["pnl_points"] * C["pv"] for t in taken]
    n_taken = len(taken)

    m = evaluate(C, cp._engine_gate(C), direction=None)  # rig, same gate
    assert m.n_entries == n_taken
    assert abs(m.total_pnl - sum(champ_pnls)) < 1e-6      # byte-for-byte P/L
