import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from optimize import vote_cache as vc


def test_round_trip_identity(tmp_path):
    vc.set_cache_dir(tmp_path); vc._clear_disk_cache()
    arr = np.array([1, -1, 0, 1, 0, -1], dtype=np.int8)
    k = vc.disk_key(("sig",), True, "ifvg", "confirm", ())
    assert vc.get(k) is None                       # cold
    vc.put(k, arr)
    got = vc.get(k)
    assert got is not None and np.array_equal(got, arr) and got.dtype == arr.dtype


def test_key_isolation():
    base = ("sigA",)
    k1 = vc.disk_key(base, True, "breaker", "confirm", (("swing_l", 5),))
    k2 = vc.disk_key(base, True, "breaker", "confirm", (("swing_l", 6),))   # diff params
    k3 = vc.disk_key(("sigB",), True, "breaker", "confirm", (("swing_l", 5),))  # diff slice
    k4 = vc.disk_key(base, False, "breaker", "confirm", (("swing_l", 5),))  # diff use1
    assert len({k1, k2, k3, k4}) == 4
    # version participates in the key
    old = vc.CACHE_VERSION
    try:
        vc.CACHE_VERSION = "DIFFERENT"
        assert vc.disk_key(base, True, "breaker", "confirm", (("swing_l", 5),)) != k1
    finally:
        vc.CACHE_VERSION = old


def test_best_effort_no_raise(tmp_path):
    vc.set_cache_dir(tmp_path / "does/not/exist/yet")    # put() must create it; get() on missing → None
    assert vc.get(vc.disk_key(("s",), True, "x", "m", ())) is None
    vc.put(vc.disk_key(("s",), True, "x", "m", ()), np.zeros(3, np.int8))  # must not raise
