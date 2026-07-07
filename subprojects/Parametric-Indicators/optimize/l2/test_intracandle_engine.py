import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.l2 import l1_runner, engine  # noqa: E402
from optimize.l2.payload import validate_layer_params  # noqa: E402

# PERMISSIVE-style L2 (no gate/indicators) so every flat dropped signal is a candidate → the vetoed
# stream is exercised. Own exits.
_L2 = dict(sl_soft=30, sl_hard=40, tp=60, gate_pct=0, dd_limit=0, cooldown=0, k=1,
           flip=False, ind_1min=False, indicators=[])

_L1 = None


def _l1():
    global _L1
    if _L1 is None:
        _L1 = l1_runner.run_l1("4h")
    return _L1


def _run(over):
    p = validate_layer_params({**_L2, **over})
    return engine.run_l2(_l1(), p).ledger


def test_off_is_identical():
    base = _run({"l2_intracandle": False})
    again = _run({"l2_intracandle": False})
    assert len(base) > 0
    assert [t["entry_time"] for t in base] == [t["entry_time"] for t in again]


def test_on_moves_vetoed_entries():
    off = _run({"l2_intracandle": False})
    on = _run({"l2_intracandle": True, "l2_intracandle_max_wait": 240})
    # vetoed candidates now enter mid-candle (not the 4h close) ⇒ the entry-time set changes
    assert {t["entry_time"] for t in on} != {t["entry_time"] for t in off}
