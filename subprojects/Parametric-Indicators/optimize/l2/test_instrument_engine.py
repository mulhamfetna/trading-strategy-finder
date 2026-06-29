# optimize/l2/test_instrument_engine.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimize.l2 import l1_runner
from optimize import instruments


def _es_perm():
    sf = instruments.scale_factor("ES")
    return {"indicators": [], "k": 1, "gate_pct": 0, "flip": False, "ind_1min": False, "cooldown": 0,
            "sl_soft": 149.8 * sf, "sl_hard": 167.1 * sf, "tp": 120.2 * sf, "dd_limit": 0.0}


def test_run_l1_es_carries_instrument_and_pv():
    r = l1_runner.run_l1("4h", params=_es_perm(), instrument="ES")
    assert r.instrument == "ES"
    # ES book exists and its $ pnl uses pv=50 (sanity: non-empty ledger)
    assert len(r.df_dec) > 0


def test_run_l1_nq_default_instrument():
    r = l1_runner.run_l1("4h")
    assert r.instrument == "NQ"
