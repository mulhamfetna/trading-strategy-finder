import sys
from pathlib import Path
from types import SimpleNamespace

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
import pytest

from optimize.l2.contributors import gate


def _fake_l1(n=5):
    dates = pd.date_range("2025-01-01 18:00", periods=n, freq="4h")
    return SimpleNamespace(df_dec=pd.DataFrame({"Date": dates}),
                           df1=pd.DataFrame({"Date": dates}),
                           bar_td=pd.Timedelta("4h"),
                           sig_int=np.array([1, -1, 0, 1, -1], dtype=np.int8)[:n])


def test_disabled_contributor_is_noop():
    l1 = _fake_l1()
    veto, cc = gate.contributor_gate_masks({"token": "ES", "enabled": False}, l1)
    assert veto.dtype == bool and not veto.any()
    assert cc.dtype == np.int64 and (cc == gate.NO_CONFIRM_CONSTRAINT).all()
    assert len(veto) == len(cc) == 5


def test_assert_unique_keys_raises_on_dup():
    with pytest.raises(ValueError, match="duplicate"):
        gate._assert_unique_keys([{"key": "macd", "enabled": True},
                                  {"key": "macd", "enabled": True}])
    gate._assert_unique_keys([{"key": "macd", "enabled": True},
                              {"key": "cci", "enabled": True}])  # no raise
