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


def test_l1_disk_cache_survives_memory_clear():
    payload.run_l1_cached("4h")                       # warms in-memory + disk
    assert payload._l1_cache_file("4h").exists()      # persisted to the disk cache
    payload._L1_CACHE.clear()                          # drop the in-process memo
    r = payload.run_l1_cached("4h")                    # must reload from disk (no recompute)
    assert len(r.ledger) == 255


def test_save_and_load_l2_profile_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "_PROFILES", tmp_path / "l2_profiles.json")
    profs = payload.save_l2_profile("mine", dict(payload.PERMISSIVE))
    assert "mine" in profs
    assert payload.load_l2_profiles()["mine"]["tp"] == 120.2
    with pytest.raises(payload.L2ParamError):
        payload.save_l2_profile("", dict(payload.PERMISSIVE))


def test_build_l2_payload_permissive_matches_metrics():
    out = payload.build_l2_payload(dict(payload.PERMISSIVE))
    for key in ("meta", "candles", "l1_spans", "dropped", "l2_trades",
                "l2_equity", "l1_equity", "combined_equity"):
        assert key in out, key
    m = out["meta"]
    assert m["l1"]["n_trades"] == 255
    assert round(m["l1"]["pnl"]) == 149989
    s = m["summary"]["l2"]
    assert s["n"] == 349 and s["n_l1_entry_exits"] == 52
    assert round(s["pnl"]) == -64299
    g = m["summary"]["combined"]
    assert g["dd_not_worse"] is False
    assert round(g["max_dd"]) == 50574 and round(g["l1_only_dd"]) == 15491
    assert m["dropped_counts"] == {"veto": 286, "vol_gate": 206, "total": 492, "flat_candidates": 410}
    assert len(out["candles"]) > 0 and len(out["dropped"]) == 492
    for ser in ("l2_equity", "l1_equity", "combined_equity"):
        ts = [pt["time"] for pt in out[ser]]
        assert ts == sorted(ts) and len(ts) == len(set(ts)), ser
    longs = [t for t in out["l2_trades"] if t["direction"] == "long"]
    assert longs, "expected at least one long L2 trade"
    t = longs[0]
    assert abs(t["sl_hard_line"] - (t["entry_price"] - 167.1)) < 1e-6
    assert abs(t["tp_hard_line"] - (t["entry_price"] + 120.2)) < 1e-6


def test_derive_lines_short_mirrors_long():
    line = payload._derive_lines(
        {"entry_price": 1000.0, "direction": "short"},
        {"sl_soft": 10.0, "sl_hard": 20.0, "tp": 30.0})
    assert line == {"sl_hard_line": 1020.0, "sl_soft_line": 1010.0, "tp_hard_line": 970.0}


def test_dedupe_keeps_last_and_sorts():
    out = payload._dedupe([{"time": 3, "value": 1}, {"time": 1, "value": 2}, {"time": 3, "value": 9}])
    assert out == [{"time": 1, "value": 2}, {"time": 3, "value": 9}]
