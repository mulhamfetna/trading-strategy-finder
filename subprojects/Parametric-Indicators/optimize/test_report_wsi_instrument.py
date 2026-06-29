# optimize/test_report_wsi_instrument.py
import sys, os, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_report_wsi_instrument_suffix():
    os.environ["WSI_INSTRUMENT"] = "ES"
    import optimize.report_wsi as rw
    importlib.reload(rw)
    assert rw._SUF == "_ES"
    assert rw._db_for("4h", "wsh4_4h_ES").name == "wsh_4h_ES.db"
    os.environ["WSI_INSTRUMENT"] = "NQ"; importlib.reload(rw)
    assert rw._SUF == "" and rw._db_for("4h", "wsh4_4h").name == "wsh_4h.db"


def test_build_champions_reads_suffixed_csv():
    os.environ["WSI_INSTRUMENT"] = "ES"
    import optimize.build_champions_from_pareto as bc
    importlib.reload(bc)
    assert bc._SUF == "_ES"
    assert "_ES.csv" in str(bc._RESULTS / f"2h_wsi_pareto{bc._SUF}.csv")
    os.environ["WSI_INSTRUMENT"] = "NQ"; importlib.reload(bc)
    assert bc._SUF == ""
