import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.dashboard import queue


def test_matrix_expands_to_per_study_configs():
    got = queue.expand({"instruments": ["NQ", "ES"], "timeframes": ["4h", "1h"],
                        "trials_mode": "one", "trials": 5000, "reference": "ES"})
    keys = {(c["instrument"], c["timeframe"], c["trials"]) for c in got}
    assert keys == {("NQ", "4h", 5000), ("NQ", "1h", 5000), ("ES", "4h", 5000), ("ES", "1h", 5000)}
    # per-study cfg carries the shared settings + a single-tf timeframes list for the launcher
    assert all(c["reference"] == "ES" and c["timeframes"] == [c["timeframe"]] for c in got)


def test_auto_trials_mode_sets_flag():
    got = queue.expand({"instruments": ["NQ"], "timeframes": ["4h"], "trials_mode": "auto"})
    assert got[0]["auto_trials"] is True and "trials" not in got[0]


def test_per_item_trials_mode():
    got = queue.expand({"instruments": ["NQ", "GC"], "timeframes": ["4h"], "trials_mode": "per",
                        "per_trials": {"NQ:4h": 8000, "GC:4h": 3000}})
    by = {c["instrument"]: c["trials"] for c in got}
    assert by == {"NQ": 8000, "GC": 3000}


def test_defaults_single_instrument_and_tf():
    got = queue.expand({"instrument": "NQ", "trials_mode": "auto"})
    assert len(got) == 1 and got[0]["instrument"] == "NQ" and got[0]["timeframe"] == "4h"
