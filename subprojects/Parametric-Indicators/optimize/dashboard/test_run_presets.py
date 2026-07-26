import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import run_presets


def test_preset_crud_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(run_presets, "_STORE", tmp_path / "rp.json")
    run_presets.save("nq-warm", {"instrument": "NQ", "reference": "ES", "timeframes": ["4h"]})
    run_presets.save("gc-cold", {"instrument": "GC", "cold_start": True})
    assert run_presets.list_names() == ["gc-cold", "nq-warm"]
    assert run_presets.get("nq-warm")["reference"] == "ES"
    run_presets.delete("nq-warm")
    assert run_presets.list_names() == ["gc-cold"]
    assert run_presets.get("nq-warm") is None


def test_missing_store_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(run_presets, "_STORE", tmp_path / "none.json")
    assert run_presets.list_names() == [] and run_presets.get("x") is None
