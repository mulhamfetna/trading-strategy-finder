import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest
from optimize.l2 import payload


def test_validate_accepts_permissive_and_sets_window_full():
    p = payload.validate_l2_params(dict(payload.PERMISSIVE))
    assert p["window"] == "full"
    assert p["sl_soft"] == 149.8 and p["tp"] == 120.2
    assert p["cooldown"] == 0 and p["k"] == 1 and p["flip"] is False
    assert p["indicators"] == []


def test_validate_rejects_bad_params():
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "sl_soft": -1})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "gate_pct": 150})
    with pytest.raises(payload.L2ParamError):
        payload.validate_l2_params({**payload.PERMISSIVE, "sl_soft": None})
    with pytest.raises(payload.L2ParamError):   # unknown indicator key -> from_specs raises -> wrapped
        payload.validate_l2_params({**payload.PERMISSIVE,
                                    "indicators": [{"key": "not_a_real_indicator", "enabled": True,
                                                    "mode": "both", "params": {}}]})


def test_l1_cache_returns_same_object():
    a = payload.run_l1_cached("4h")
    b = payload.run_l1_cached("4h")
    assert a is b
    assert len(a.ledger) == 255


def test_save_and_load_l2_profile_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "_PROFILES", tmp_path / "l2_profiles.json")
    profs = payload.save_l2_profile("mine", dict(payload.PERMISSIVE))
    assert "mine" in profs
    assert payload.load_l2_profiles()["mine"]["tp"] == 120.2
    with pytest.raises(payload.L2ParamError):
        payload.save_l2_profile("", dict(payload.PERMISSIVE))
