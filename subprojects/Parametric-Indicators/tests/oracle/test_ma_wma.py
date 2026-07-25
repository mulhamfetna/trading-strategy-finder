import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd

from indicators.calc.ma import wma
from tests.oracle.fixture import ohlcv


def test_wma_matches_independent_pandas_oracle():
    x = ohlcv(300)["close"]
    n = 10
    w = np.arange(1, n + 1)
    oracle = pd.Series(x).rolling(n).apply(lambda s: np.dot(s, w) / w.sum(), raw=True).to_numpy()
    got = wma(x, n)
    m = ~np.isnan(oracle)
    assert np.allclose(got[m], oracle[m], atol=1e-9)
    assert np.isnan(got[:n - 1]).all()      # causal warm-up


def test_wma_weights_recent_more():
    # ramp input: WMA must exceed SMA (recent-weighted) and trail the latest value
    x = np.arange(1.0, 21.0)
    n = 5
    got = wma(x, n)
    sma5 = pd.Series(x).rolling(n).mean().to_numpy()
    assert got[-1] > sma5[-1] and got[-1] < x[-1]
