"""cap_1min added as an optimizer search dimension (L1 + L2) + threaded to the engine."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import optimizer as OPT


def test_cap_1min_is_a_counted_dimension():
    assert OPT.CAP_1MIN_MAX == 1440
    d = OPT.search_dims(split_sltp=False)
    assert d["base_int"] == 3                      # cooldown, k, cap_1min
    assert d["total"] == sum(v for k, v in d.items() if k != "total")
    assert OPT.recommended_trials(False, per_dim=200) == d["total"] * 200
