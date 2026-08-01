# optimize/l2/test_instrument_champion_default.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import payload

_CHAMP = {"4h": {"box": {"sl_soft": 41.0, "sl_hard": 46.0, "tp": 33.0, "gate_pct": 50.0,
                         "dd_limit": 1000.0, "cooldown": 0, "flip": False, "k": 1}, "indicators": {}}}


def test_es_default_uses_champion_when_present(tmp_path, monkeypatch):
    # isolate from the real results/ file: point the dashboard at a tmp champion
    cf = tmp_path / "wsh4_champions_full_ES.json"
    cf.write_text(json.dumps(_CHAMP))
    monkeypatch.setattr(payload, "_instrument_champions_path", lambda inst: cf)
    p = payload.instrument_l1_default("ES", "4h")
    assert p["sl_soft"] == 41.0 and p["ind_1min"] is True     # champion box, not scaled-permissive


def test_es_default_falls_back_when_champion_absent(tmp_path, monkeypatch):
    # no champion file → ES falls back to scaled-permissive (indicators empty, gate 0)
    monkeypatch.setattr(payload, "_instrument_champions_path", lambda inst: tmp_path / "nope.json")
    p = payload.instrument_l1_default("ES", "4h")
    assert p["indicators"] == [] and p["gate_pct"] == 0


def test_es_default_falls_back_for_tf_without_champion(tmp_path, monkeypatch):
    # champion file present but missing this TF → scaled-permissive for that TF
    cf = tmp_path / "wsh4_champions_full_ES.json"
    cf.write_text(json.dumps(_CHAMP))                          # only has 4h
    monkeypatch.setattr(payload, "_instrument_champions_path", lambda inst: cf)
    p = payload.instrument_l1_default("ES", "2m")
    assert p["indicators"] == [] and p["gate_pct"] == 0
