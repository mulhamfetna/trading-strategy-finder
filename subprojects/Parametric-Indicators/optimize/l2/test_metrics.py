import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import types
from optimize.l2 import metrics


def _stub(pnls, times):
    return types.SimpleNamespace(
        ledger=[{"pnl": p, "exit_time": t} for p, t in zip(pnls, times)],
        n_l1_entry_exits=0)


def test_equity_dd_basic():
    total, dd = metrics._equity_dd([100.0, -40.0, -30.0, 50.0])
    assert total == 80.0
    assert dd == 70.0          # peak 100 -> trough 30


def test_score_standalone():
    l2 = _stub([100.0, -40.0, -30.0, 50.0],
               ["2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"])
    s = metrics.score(l2)
    assert s["pnl"] == 80.0
    assert s["max_dd"] == 70.0
    assert s["n"] == 4
    assert s["win"] == 50.0     # 2 of 4 > 0


def test_combined_guardrail_orders_by_exit_time():
    # L1: +100 then -50 (dd 50). L2 a losing -80 interleaved in the middle worsens combined dd.
    l1 = _stub([100.0, -50.0], ["2025-01-01", "2025-01-10"])
    l2 = _stub([-80.0], ["2025-01-05"])
    c = metrics.combined(l1, l2)
    # merged by time: +100 (peak 100), -80 (eq 20), -50 (eq -30) -> dd 130
    assert c["pnl"] == -30.0
    assert c["max_dd"] == 130.0
    assert c["l1_only_dd"] == 50.0
    assert c["dd_not_worse"] is False
