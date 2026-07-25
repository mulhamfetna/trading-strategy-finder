import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from tests.oracle.fixture import ohlcv


def test_fixture_is_deterministic_and_valid():
    a, b = ohlcv(300), ohlcv(300)
    for k in ("open", "high", "low", "close", "volume"):
        assert np.array_equal(a[k], b[k])
    assert np.all(a["high"] >= a["low"])
    assert np.all(a["high"] >= a["close"]) and np.all(a["close"] >= a["low"])
    assert np.all(a["high"] >= a["open"]) and np.all(a["open"] >= a["low"])
    assert np.all(a["volume"] > 0)
    assert len(a["close"]) == 300
