import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import numpy as np  # noqa: E402
from indicators.intracandle import build_resolver  # noqa: E402


def _gate(n, true_at, d=+1):
    a = np.zeros(n, dtype=bool)
    a[true_at] = True
    return {+1: a if d == +1 else np.zeros(n, bool), -1: a if d == -1 else np.zeros(n, bool)}


def test_enters_first_qualifying_flat_bar():
    g = _gate(100, [40], d=+1)                      # gate opens at global bar 40
    r = build_resolver(g, min_start=0, max_wait=240)
    # candle starts at global 10; gate opens at offset 30; flat everywhere
    assert r(+1, start_e=10, sub_len=50, is_flat=lambda o: True) == (30,)


def test_waits_until_flat():
    g = _gate(100, [40, 45], d=+1)                  # gate open at offsets 30 and 35
    r = build_resolver(g, min_start=0, max_wait=240)
    # not flat until offset 33 => first flat gate-open bar is offset 35
    assert r(+1, start_e=10, sub_len=50, is_flat=lambda o: o >= 33) == (35,)


def test_expires_past_max_wait():
    g = _gate(100, [40], d=+1)                      # gate open at offset 30
    r = build_resolver(g, min_start=0, max_wait=20)  # N=20 < 30 => never reached
    assert r(+1, start_e=10, sub_len=50, is_flat=lambda o: True) is None


def test_direction_isolated():
    g = _gate(100, [40], d=+1)                      # only LONG gate open
    r = build_resolver(g, min_start=0, max_wait=240)
    assert r(-1, start_e=10, sub_len=50, is_flat=lambda o: True) is None  # short never qualifies
