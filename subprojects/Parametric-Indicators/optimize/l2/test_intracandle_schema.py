import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.l2.payload import validate_layer_params  # noqa: E402

_BASE = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=0, dd_limit=0, cooldown=0, k=1)


def test_intracandle_defaults_off():
    p = validate_layer_params(dict(_BASE))
    assert p["l2_intracandle"] is False
    assert p["l2_intracandle_max_wait"] == 240


def test_intracandle_roundtrip():
    p = validate_layer_params({**_BASE, "l2_intracandle": True, "l2_intracandle_max_wait": 60})
    assert p["l2_intracandle"] is True and p["l2_intracandle_max_wait"] == 60
