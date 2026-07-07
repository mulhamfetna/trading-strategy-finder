import research.kalman_fusion  # noqa: F401  (triggers the sys.path insert)
from optimize import counterfactual_pause as cp


def test_load_champion_returns_expected_context():
    C = cp.load_champion("4h")
    for key in ("d", "d1", "box", "n", "sig", "vol_gate", "veto", "confirm", "params", "pv"):
        assert key in C, f"missing {key}"
    assert C["n"] > 2000           # NQ 4h ~2119 decision bars
    assert C["pv"] > 0
    # engine gate is a boolean mask of length n
    g = cp._engine_gate(C)
    assert g.shape == (C["n"],)
    assert g.dtype == bool
