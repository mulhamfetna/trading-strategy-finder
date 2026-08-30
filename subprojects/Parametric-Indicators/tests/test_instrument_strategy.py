# tests/test_instrument_strategy.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import strategy

_BASE = {"sl_soft": 40, "sl_hard": 45, "tp": 33, "gate_pct": 0, "dd_limit": 0,
         "cooldown": 0, "flip": False, "window": "full", "k": 1}


def test_get_bundle_accepts_instrument():
    try:
        nq = strategy.get_bundle("4h")           # default NQ
    except FileNotFoundError as e:                # market data is server-only (2026-08-22)
        pytest.skip(f"market data not present: {e}")
    es = strategy.get_bundle("4h", instrument="ES")
    assert nq is not None and es is not None
    assert nq[0]["Close"].median() != es[0]["Close"].median()   # distinct candle frames


def test_validate_params_pv_defaults_per_instrument():
    assert strategy.validate_params(dict(_BASE))["pv"] == 20.0                       # NQ default
    assert strategy.validate_params(dict(_BASE), instrument="ES")["pv"] == 50.0      # ES default
    # an explicit pv in params still wins over the instrument default
    assert strategy.validate_params({**_BASE, "pv": 7}, instrument="ES")["pv"] == 7.0
