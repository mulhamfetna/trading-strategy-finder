# optimize/test_folds_instrument.py
import sys, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize import folds


def test_score_walkforward_accepts_pv():
    assert "pv" in inspect.signature(folds.score_walkforward).parameters
