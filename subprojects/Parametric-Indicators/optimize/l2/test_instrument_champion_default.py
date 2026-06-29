# optimize/l2/test_instrument_champion_default.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import payload

_ES_CH = Path(__file__).resolve().parents[1] / "results" / "wsh4_champions_full_ES.json"


def test_es_default_uses_champion_when_present():
    created = not _ES_CH.exists()
    if created:
        _ES_CH.write_text(json.dumps({"4h": {"box": {"sl_soft": 41.0, "sl_hard": 46.0, "tp": 33.0,
            "gate_pct": 50.0, "dd_limit": 1000.0, "cooldown": 0, "flip": False, "k": 1}, "indicators": {}}}))
    try:
        p = payload.instrument_l1_default("ES", "4h")
        assert p["sl_soft"] == 41.0 and p["ind_1min"] is True     # champion box, not scaled-permissive
    finally:
        if created:
            _ES_CH.unlink()


def test_es_default_falls_back_when_absent():
    # with no champion for a TF, ES falls back to scaled-permissive (indicators empty, gate 0)
    p = payload.instrument_l1_default("ES", "2m")
    if not _ES_CH.exists():
        assert p["indicators"] == [] and p["gate_pct"] == 0
