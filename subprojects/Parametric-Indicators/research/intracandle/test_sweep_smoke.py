import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.intracandle.run_sweep import sweep  # noqa: E402


def test_sweep_returns_rows_for_each_N():
    rows = sweep("4h", Ns=(60,))
    r = rows[0]
    assert r["N"] == 60
    assert r["entries_new"] >= 0
    assert 0.0 <= r["win_rate_new"] <= 1.0
    assert "breakeven_ok" in r
    assert "entries_added_net" in r
