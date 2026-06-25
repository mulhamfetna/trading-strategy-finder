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


def test_native_seed_carries_cap_1min():
    b = {"sl_soft": [10, 200], "sl_hard": [0, 400], "tp": [10, 300]}
    box0 = {"sl_soft": 100, "sl_hard": 150, "tp": 120, "gate_pct": 0, "dd_limit": 0,
            "cooldown": 0, "flip": False, "k": 1}
    s0 = OPT._native_seed(box0, {}, split_sltp=False, b=b)
    assert s0["cap_1min"] == 0                                   # absent → 0 (reproduces prior champ)
    s1 = OPT._native_seed({**box0, "cap_1min": 5000}, {}, split_sltp=False, b=b)
    assert s1["cap_1min"] == OPT.CAP_1MIN_MAX                    # clamped to bound
