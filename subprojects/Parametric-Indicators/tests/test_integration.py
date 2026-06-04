"""Integration — composite gate wiring on REAL data. The keystone parity guarantee:
with all indicators off, the composite gate equals the vol gate exactly, and the engine produces
identical trades to today's strategy. Skips if the market CSVs aren't present.
"""
import numpy as np
import pytest

import strategy
from engine import SimpleStrategy, SimpleStrategyParams
from indicators import library, runner
from indicators.base import IndicatorConfig


@pytest.fixture(scope="module")
def inputs():
    try:
        return strategy.load_inputs()
    except Exception as e:  # data not available in this environment
        pytest.skip(f"market data unavailable: {e}")


def _vol_gate(df4, vf, n2025, gate_pct=60.0):
    gthr = float(np.percentile(vf[:n2025], gate_pct))
    return vf <= gthr


def test_composite_gate_all_off_equals_vol_gate(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    gate, votes, active = runner.composite_gate(vg, df4, box, indicators=[], k=1)
    np.testing.assert_array_equal(gate, vg)


def test_composite_gate_disabled_indicator_equals_vol_gate(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    disabled = [library.build("rsi", IndicatorConfig(enabled=False)),
                library.build("ema_trend", IndicatorConfig(enabled=False))]
    gate, _, active = runner.composite_gate(vg, df4, box, indicators=disabled, k=1)
    assert active.tolist() == [False, False]
    np.testing.assert_array_equal(gate, vg)


def test_engine_trades_identical_when_indicators_off(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    sp = SimpleStrategyParams(sl_soft_points=30, sl_hard_points=40, tp_soft_points=60,
                              tp_hard_points=60, data_path_4h="", data_path_1min="",
                              box_data_path="", flip_entry_direction=False)
    base_trades, _ = SimpleStrategy(sp).backtest(df4, df1, box, entry_gate=vg)
    gate, _, _ = runner.composite_gate(vg, df4, box, indicators=[], k=1)
    comp_trades, _ = SimpleStrategy(sp).backtest(df4, df1, box, entry_gate=gate)
    assert len(base_trades) == len(comp_trades)
    for a, b in zip(base_trades, comp_trades):
        assert a["entry_time"] == b["entry_time"]
        assert a["exit_reason"] == b["exit_reason"]
        assert a.get("pnl_points") == b.get("pnl_points")


def test_enabled_indicator_gate_is_subset_of_vol_gate(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    rsi_on = [library.build("rsi", IndicatorConfig(enabled=True, mode="both"))]
    gate, votes, active = runner.composite_gate(vg, df4, box, indicators=rsi_on, k=1)
    assert active.tolist() == [True]
    # ANDed with a real confirmation mask ⇒ never opens MORE bars than the vol gate
    assert gate.sum() <= vg.sum()
    assert (gate <= vg).all()
