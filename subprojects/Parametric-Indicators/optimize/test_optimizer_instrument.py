# optimize/test_optimizer_instrument.py
import sys, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import optimizer as OPT
from optimize import instruments


def test_study_suffix():
    assert OPT._study_suffix("NQ") == ""
    assert OPT._study_suffix("ES") == "_ES"


def test_db_for_instrument_suffix():
    nq = OPT._db_for("4h", "wsh4_4h", "NQ")
    es = OPT._db_for("4h", "wsh4_4h_ES", "ES")
    assert nq.name == "wsh_4h.db"
    assert es.name == "wsh_4h_ES.db"


def test_bounds_scaled_for_es():
    b = {"sl_soft": [10.0, 200.0], "sl_hard": [10.0, 250.0], "tp": [10.0, 180.0]}
    nb, ndd = OPT._bounds_for(b, 5000.0, "NQ")
    assert nb == b and ndd == 5000.0                       # NQ unchanged
    sf = instruments.scale_factor("ES")
    eb, edd = OPT._bounds_for(b, 5000.0, "ES")
    assert abs(eb["sl_soft"][1] - 200.0 * sf) < 1e-6        # point bounds scaled
    assert abs(edd - 5000.0 * sf) < 1e-6                    # dd_limit max scaled


def test_run_accepts_instrument():
    assert "instrument" in inspect.signature(OPT.run).parameters
