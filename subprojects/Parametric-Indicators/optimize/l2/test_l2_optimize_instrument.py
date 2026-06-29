# optimize/l2/test_l2_optimize_instrument.py
import sys, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import optimize as l2opt


def test_run_and_export_accept_instrument():
    assert "instrument" in inspect.signature(l2opt.run).parameters
    assert "instrument" in inspect.signature(l2opt._export_champion).parameters


def test_export_champion_es_filename(tmp_path):
    champ = {"params": {"sl_soft": 40}, "in_sample": {"pnl": 1.0, "n": 5}, "oos": {"pnl": 1.0, "n": 5}}
    p = l2opt._export_champion(champ, "4h", tmp_path, prefix="l2v1", instrument="ES")
    assert p.name == "l2v1_4h_ES_champion.json"
    nq = l2opt._export_champion(champ, "4h", tmp_path, prefix="l2v1", instrument="NQ")
    assert nq.name == "l2v1_4h_champion.json"
