import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import instruments as inst


def test_tokens_include_comex():
    assert inst.TOKENS == ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM")   # COMEX metals + NYMEX energy + CME


def test_point_values():
    assert inst.point_value("GC") == 100.0
    assert inst.point_value("SI") == 5000.0
    assert inst.point_value("HG") == 25000.0   # Copper, COMEX full (25,000 lbs · $/lb)
    assert inst.point_value("CL") == 1000.0    # Crude Oil, NYMEX full (1,000 bbl · $/bbl)
    assert inst.point_value("NG") == 10000.0   # Natural Gas, NYMEX full (10,000 MMBtu · $/MMBtu)


def test_resolve_paths_use_shifted_box():
    # GC/SI/HG/CL/NG (and ES) backtester must read the -1-workday-SHIFTED box, not the raw one.
    for tok in ("GC", "SI", "HG", "CL", "NG"):
        dec, minute, box = inst.resolve_paths(tok, "4h")
        assert dec.endswith(f"{tok}_4h.csv") and os.path.exists(dec)
        assert minute.endswith(f"{tok}_1m.csv") and os.path.exists(minute)
        assert box.endswith(f"{tok}_full_data_shifted.csv"), f"{tok} backtester must read the SHIFTED box"
        assert os.path.exists(box)


def test_es_repointed_to_shifted_box():
    _, _, box = inst.resolve_paths("ES", "4h")
    assert box.endswith("ES_full_data_shifted.csv"), "ES must now read the shifted box (raw retired 2026-07-06)"
    assert os.path.exists(box)
