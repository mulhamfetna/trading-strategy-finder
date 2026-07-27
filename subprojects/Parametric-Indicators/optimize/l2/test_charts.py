"""STEP 4 — per-layer engine chart producers (optimize/l2/charts.py) derived from ONE causal run.
Asserts the series are well-formed and CONSISTENT with the books (equity endpoint == layer P/L), so the
unified dashboard's L2/Combined engine charts cannot drift from their boxes."""
import json
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest

from optimize.l2 import logbook, payload, charts
from volatility import gate_threshold

_TF = "4h"
_EXPECT = {"L1": 151655, "L2": 24498, "combined": 176154}   # l2v2 re-lock 2026-06-22 (reverse-entry-only)


@pytest.fixture(scope="module")
def cc():
    l1p = payload.l1_default_params(_TF)
    l2p = json.loads((_PI / "optimize" / "results" / "l2v2_4h_champion.json").read_text())["params"]
    res = logbook.run_causal(l1p, l2p, _TF)
    l1 = payload.run_l1_cached(_TF)
    return res, l1


@pytest.mark.parametrize("layer", ["L1", "L2", "combined"])
def test_charts_shapes_and_consistency(cc, layer):
    res, l1 = cc
    c = charts.charts_for_layer(res, l1, layer)
    # vol = one point per candle, in time order
    assert len(c["vol"]) == res.n
    ts = [p["time"] for p in c["vol"]]
    assert ts == sorted(ts)
    # the layer's equity endpoint must equal its P/L (charts derived from the SAME book as the boxes)
    assert c["equity"], f"{layer}: no equity points"
    assert round(c["equity"][-1]["value"]) == _EXPECT[layer]
    # equally many drawdown points; all dd >= 0
    assert len(c["drawdown"]) == len(c["equity"])
    assert all(p["value"] >= -1e-6 for p in c["drawdown"])
    # events: one ENTRY per taken trade at least
    n_entry = sum(1 for e in c["events"] if e["type"] == "ENTRY")
    assert n_entry == len(c["equity"])
    # state has a +1 per entry
    assert sum(1 for s in c["state"] if s["value"] == 1) == n_entry


def test_gate_threshold_is_window_correct_seed(cc):
    """gate_thr must be the percentile of the IN-SAMPLE prefix (l1.vf_seed), the STEP 3b fix —
    not of the full/windowed vf."""
    res, l1 = cc
    c = charts.charts_for_layer(res, l1, "L1")
    gp = float(res.l1_params["gate_pct"])
    if gp > 0:
        assert abs(c["gate_thr"] - round(gate_threshold(l1.vf_seed, len(l1.vf_seed), gp), 1)) < 1e-6
