import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research.intracandle.l2_sweep import sweep  # noqa: E402


def test_sweep_rows():
    rows = sweep("4h", Ns=(60,))
    r = rows[0]
    assert r["N"] == 60
    assert "combined_pnl" in r and "combined_dd" in r and "dd_not_worse" in r
