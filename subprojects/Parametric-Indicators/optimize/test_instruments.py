# optimize/test_instruments.py
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import instruments as I
from optimize import data as D


def test_tokens_and_point_values():
    assert I.TOKENS == ("NQ", "ES")
    assert I.point_value("NQ") == 20.0 and I.point_value("ES") == 50.0
    assert I.is_valid("NQ") and I.is_valid("ES") and not I.is_valid("QQQ-RTH")


def test_resolve_paths_nq_matches_current_data_module():
    dec, mn, box = I.resolve_paths("NQ", "4h")
    assert dec == str(D._RAW / "NQ_4h.csv")
    assert mn == str(D._RAW / "NQ_1m.csv")
    assert box == str(D._BOX_CSV)


def test_resolve_paths_es_exists_on_disk():
    dec, mn, box = I.resolve_paths("ES", "4h")
    assert os.path.exists(dec) and os.path.exists(mn) and os.path.exists(box)
    assert "ES" in dec


def test_scale_factor():
    assert I.scale_factor("NQ") == 1.0
    sf = I.scale_factor("ES")
    assert 0.0 < sf < 1.0           # ES (~6508) is a fraction of NQ (~23861)
