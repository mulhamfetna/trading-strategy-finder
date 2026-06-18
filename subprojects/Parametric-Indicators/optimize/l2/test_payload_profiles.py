import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import payload


def test_save_and_load_l2_profile_roundtrip():
    name = "_pytest_tmp_profile"
    preset = dict(sl_soft=120.0, sl_hard=140.0, tp=100.0, gate_pct=50.0, dd_limit=0.0,
                  cooldown=0, flip=True, k=1, ind_1min=False, indicators=[])
    try:
        profs = payload.save_l2_profile(name, preset)
        assert name in profs
        assert payload.load_l2_profiles()[name]["flip"] is True
    finally:
        # cleanup: drop the temp profile
        all_p = payload.load_l2_profiles()
        all_p.pop(name, None)
        payload._L2_PROFILES.write_text(__import__("json").dumps(all_p, indent=1))


def test_save_l2_profile_requires_name():
    import pytest
    with pytest.raises(ValueError):
        payload.save_l2_profile("  ", {})


def test_l2_config_has_schema_l1_and_profiles():
    c = payload.l2_config()
    assert "indicator_schema" in c and isinstance(c["indicator_schema"], (list, dict))
    assert "profiles" in c and isinstance(c["profiles"], dict)
    assert set(("dropped", "veto", "vol_gate", "flat_candidates", "n_trades")).issubset(c["l1"])
