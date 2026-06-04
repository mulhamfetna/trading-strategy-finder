"""TDD — build_payload indicator wiring: parity when off, behaviour when on, strict validation."""
import copy
import pytest

import strategy
from strategy import ParamError


@pytest.fixture(scope="module")
def inputs():
    try:
        return strategy.load_inputs()
    except Exception as e:
        pytest.skip(f"market data unavailable: {e}")


BASE = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=60, dd_limit=2000,
            cooldown=20, flip=False, window="full")


def _run(inputs, **over):
    p = copy.deepcopy(BASE); p.update(over)
    return strategy.build_payload(*inputs, params=p)


def test_no_indicators_key_is_unchanged(inputs):
    base = _run(inputs)
    with_empty = _run(inputs, indicators=[], k=1)
    assert base["meta"]["summary"] == with_empty["meta"]["summary"]


def test_disabled_indicator_matches_baseline(inputs):
    base = _run(inputs)
    off = _run(inputs, indicators=[{"key": "rsi", "enabled": False}], k=1)
    assert base["meta"]["summary"]["n_taken"] == off["meta"]["summary"]["n_taken"]
    assert base["meta"]["summary"]["pnl"] == off["meta"]["summary"]["pnl"]


def test_enabled_veto_reduces_or_equals_trades(inputs):
    base = _run(inputs)
    veto = _run(inputs, indicators=[{"key": "adx", "enabled": True, "mode": "veto",
                                     "params": {"threshold": 25}}], k=1)
    assert veto["meta"]["summary"]["n_taken"] <= base["meta"]["summary"]["n_taken"]


def test_k_exceeds_confirmers_raises(inputs):
    with pytest.raises(ParamError):
        _run(inputs, indicators=[{"key": "rsi", "enabled": True, "mode": "confirm"}], k=3)


def test_unknown_indicator_key_raises(inputs):
    with pytest.raises(ParamError):
        _run(inputs, indicators=[{"key": "nope", "enabled": True}], k=1)


def test_bad_k_raises(inputs):
    with pytest.raises(ParamError):
        _run(inputs, indicators=[], k=0)


def test_smc_indicator_produces_generation_report(inputs):
    out = _run(inputs, indicators=[{"key": "fvg", "enabled": True, "mode": "confirm"}], k=1,
               gen={"swing_l": 2, "golf_n": 3})
    rep = out["meta"]["gen_report"]
    assert rep is not None and rep["params"] == {"swing_l": 2, "golf_n": 3}
    assert "n_bull_fvg" in rep and rep["bars"] > 0
