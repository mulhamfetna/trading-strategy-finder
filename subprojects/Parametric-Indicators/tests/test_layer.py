"""TDD — runner.veto_mask + build_layer (the Q5 gate/resolver split) on real data."""
import numpy as np
import pytest

import strategy
from indicators import library, runner
from indicators.base import IndicatorConfig


@pytest.fixture(scope="module")
def inputs():
    try:
        return strategy.load_inputs()
    except Exception as e:
        pytest.skip(f"market data unavailable: {e}")


def test_veto_mask_all_false_with_no_veto_indicators(inputs):
    df4, df1, box, vf, n2025 = inputs
    rsi = library.build("rsi", IndicatorConfig(enabled=True, mode="confirm"))  # not a veto
    vm = runner.veto_mask(df4, box, [rsi])
    assert vm.dtype == bool and len(vm) == len(df4)
    assert not vm.any()


def test_veto_mask_marks_some_bars_with_adx_veto(inputs):
    df4, df1, box, vf, n2025 = inputs
    adx = library.build("adx", IndicatorConfig(enabled=True, mode="veto",
                                               params={"threshold": 25}))
    vm = runner.veto_mask(df4, box, [adx])
    assert vm.any()          # ADX vetoes the no-trend bars
    assert vm[0] == False     # entry bar 0 never vetoes (no signal bar before it)


def test_build_layer_all_off_equals_vol_gate(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = (vf <= float(np.percentile(vf[:n2025], 60.0)))
    gate, resolver, vmask = runner.build_layer(df4, box, [], k=1, vol_gate=vg)
    np.testing.assert_array_equal(gate, vg)
    assert not vmask.any()
    assert callable(resolver)


def test_build_layer_veto_shrinks_gate(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = (vf <= float(np.percentile(vf[:n2025], 60.0)))
    adx = library.build("adx", IndicatorConfig(enabled=True, mode="veto", params={"threshold": 25}))
    gate, resolver, vmask = runner.build_layer(df4, box, [adx], k=1, vol_gate=vg)
    assert (gate <= vg).all()        # veto only ever removes eligibility
    assert gate.sum() < vg.sum()
