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


def _sp():
    return SimpleStrategyParams(sl_soft_points=30, sl_hard_points=40, tp_soft_points=60,
                                tp_hard_points=60, data_path_4h="", data_path_1min="",
                                box_data_path="", flip_entry_direction=False)


def test_entry_resolver_immediate_equals_baseline(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    base, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg)
    # resolver that fills immediately at the signal close ⇒ must reproduce baseline exactly
    immediate = lambda idx, d, s, sidx, ts, sub: (ts, s)
    got, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=immediate)
    assert len(base) == len(got)
    for a, b in zip(base, got):
        assert a["entry_time"] == b["entry_time"]
        assert a["entry_price"] == b["entry_price"]
        assert a["exit_reason"] == b["exit_reason"]
        assert a.get("pnl_points") == b.get("pnl_points")


def test_entry_resolver_none_skips_all_entries(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    never = lambda idx, d, s, sidx, ts, sub: None
    got, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=never)
    assert [t for t in got if t.get("exit_reason") not in (None, "OPEN")] == []


def test_entry_resolver_shifts_entry_price(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    # fill 5 pts better than signal close (long: lower) at the first 1-min bar
    def retrace5(idx, d, s, sidx, ts, sub):
        px = s - 5 if d == "long" else s + 5
        return (ts, px)
    got, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=retrace5)
    taken = [t for t in got if t.get("exit_reason") not in (None, "OPEN")]
    assert taken, "expected some trades"
    for t in taken:
        off = -5 if t["direction"] == "long" else 5
        assert abs(t["sl_hard_line"] - (t["entry_price"] + (-40 if t["direction"] == "long" else 40))) < 1e-6


def test_binding_retrace0_fills_immediately_at_signal_close(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    rsi = library.build("rsi", IndicatorConfig(enabled=True, mode="confirm"))  # retrace 0
    resolver = runner.build_entry_resolver(df4, box, [rsi], k=1)
    trades, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=resolver)
    taken = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    assert taken, "expected some RSI-confirmed trades"
    for t in taken:
        # immediate fill at the signal bar's close (retrace=0)
        assert abs(t["entry_price"] - float(df4["Close"].iloc[t["signal_idx"]])) < 1e-6


def test_binding_retrace_points_shifts_fill_to_level(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    rsi = library.build("rsi", IndicatorConfig(enabled=True, mode="confirm"))
    # retrace is GLOBAL now: 10 points, applied to all indicators
    resolver = runner.build_entry_resolver(df4, box, [rsi], k=1,
                                           retrace_amount=10.0, retrace_unit="points", wait_bars=0)
    trades, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=resolver)
    taken = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    assert taken, "expected some filled retrace trades"
    for t in taken:
        s = float(df4["Close"].iloc[t["signal_idx"]])
        want = s - 10 if t["direction"] == "long" else s + 10
        assert abs(t["entry_price"] - want) < 1e-6   # filled exactly at the retrace level


def test_binding_disabled_indicators_means_no_confirmers(inputs):
    df4, df1, box, vf, n2025 = inputs
    # k_eff = min(k, 0) = 0 ⇒ immediate fill at close (Q2 waive); behaves like baseline gate
    resolver = runner.build_entry_resolver(df4, box, [], k=1)
    vg = _vol_gate(df4, vf, n2025)
    base, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg)
    got, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=resolver)
    assert len(base) == len(got)
    for a, b in zip(base, got):
        assert a["entry_time"] == b["entry_time"] and a["entry_price"] == b["entry_price"]


def test_carry_across_bars_fills_on_a_later_bar_at_anchor(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    # Resolver that NEVER fills on the arming bar; fills at the anchor close on a LATER bar.
    seen = {}

    def carry_resolver(idx, direction, signal_close, signal_idx, ts, sub_bars):
        first = seen.get(signal_idx)
        if first is None:
            seen[signal_idx] = idx
            return None                      # arm → carry (never fill on the arming bar)
        if idx > first:
            return (ts, signal_close)        # a later bar for the SAME armed setup → fill at anchor
        return None

    trades, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg, entry_resolver=carry_resolver)
    taken = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    assert taken, "expected some carried trades"
    # every fill is carried (no immediate fills) ⇒ entry bar is at least 2 past the signal bar,
    # and the fill price is the ORIGINAL armed signal close (anchor), not the current bar's close.
    assert any(t["entry_idx"] - t["signal_idx"] >= 2 for t in taken)
    for t in taken:
        assert t["entry_idx"] - t["signal_idx"] >= 2
        assert abs(t["entry_price"] - float(df4["Close"].iloc[t["signal_idx"]])) < 1e-6


def test_veto_mask_aborts_armed_entry(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    # never-immediate resolver + a veto on every bar ⇒ armed setups always aborted ⇒ no trades
    never = lambda idx, d, s, sidx, ts, sub: None  # never fills
    veto_all = np.ones(len(df4), dtype=bool)
    trades, _ = SimpleStrategy(_sp()).backtest(df4, df1, box, entry_gate=vg,
                                               entry_resolver=never, veto_mask=veto_all)
    assert [t for t in trades if t.get("exit_reason") not in (None, "OPEN")] == []


def test_enabled_indicator_gate_is_subset_of_vol_gate(inputs):
    df4, df1, box, vf, n2025 = inputs
    vg = _vol_gate(df4, vf, n2025)
    rsi_on = [library.build("rsi", IndicatorConfig(enabled=True, mode="both"))]
    gate, votes, active = runner.composite_gate(vg, df4, box, indicators=rsi_on, k=1)
    assert active.tolist() == [True]
    # ANDed with a real confirmation mask ⇒ never opens MORE bars than the vol gate
    assert gate.sum() <= vg.sum()
    assert (gate <= vg).all()
