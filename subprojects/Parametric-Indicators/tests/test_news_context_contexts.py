"""Context labels must be CAUSAL -- computed only from information available before the release."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.news_context.contexts import (            # noqa: E402
    label_c1_policy_regime, label_c2_vol_regime, label_c3_trend,
)


def _sur(n=100, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "Date": pd.date_range("2015-01-02 08:30", periods=n, freq="7D"),
        "surprise_z": rng.normal(0, 1, n),
        "ret_30": rng.normal(0, 10, n),
    })


def test_c1_first_k_are_unlabelled():
    s = _sur(100)
    lab = label_c1_policy_regime(s, "ret_30", k=40)
    assert (lab[:40] == "").all(), "the first k releases cannot have a trailing window"
    assert set(np.unique(lab[40:])) <= {"POS", "NEG"}


def test_c1_is_causal_future_cannot_change_a_past_label():
    s = _sur(100)
    full = label_c1_policy_regime(s, "ret_30", k=40)
    truncated = label_c1_policy_regime(s.iloc[:60].copy(), "ret_30", k=40)
    # labels for the first 60 rows must be identical -- later data must not leak backwards
    assert list(full[:60]) == list(truncated)


def test_c1_detects_a_planted_sign_flip():
    n = 120
    rng = np.random.default_rng(1)
    z = rng.normal(0, 1, n)
    ret = np.empty(n)
    ret[:60] = z[:60] * 10 + rng.normal(0, 1, 60)     # positive relationship
    ret[60:] = -z[60:] * 10 + rng.normal(0, 1, 60)    # flipped
    s = pd.DataFrame({"Date": pd.date_range("2015-01-02 08:30", periods=n, freq="7D"),
                      "surprise_z": z, "ret_30": ret})
    lab = label_c1_policy_regime(s, "ret_30", k=30)
    assert lab[59] == "POS"        # trailing window still all-positive
    assert lab[-1] == "NEG"        # trailing window now all-flipped


def test_c1_k_must_be_positive():
    with pytest.raises(ValueError):
        label_c1_policy_regime(_sur(50), "ret_30", k=0)


def test_c3_trend_up_and_down():
    dates = pd.date_range("2015-01-01", periods=400, freq="D")
    df1 = pd.DataFrame({"Date": dates, "Close": np.arange(400, dtype=float) + 100})  # strictly rising
    s = pd.DataFrame({"Date": [dates[300] + pd.Timedelta(hours=8)], "surprise_z": [0.0]})
    lab = label_c3_trend(s, df1, ma_days=50)
    assert lab[0] == "UP"      # rising series is always above its trailing MA

    df1_down = pd.DataFrame({"Date": dates, "Close": (400 - np.arange(400)).astype(float) + 100})
    lab2 = label_c3_trend(s, df1_down, ma_days=50)
    assert lab2[0] == "DOWN"


def test_c3_ma_days_must_be_sane():
    dates = pd.date_range("2015-01-01", periods=10, freq="D")
    df1 = pd.DataFrame({"Date": dates, "Close": np.arange(10, dtype=float)})
    s = pd.DataFrame({"Date": [dates[5]], "surprise_z": [0.0]})
    with pytest.raises(ValueError):
        label_c3_trend(s, df1, ma_days=1)


def test_c2_maps_regimes_to_two_buckets(tmp_path):
    csv = tmp_path / "r.csv"
    pd.DataFrame({"date": pd.date_range("2015-01-01", periods=10, freq="D"),
                  "regime": [0, 0, 1, 1, 2, 2, 3, 3, 0, 3],
                  "n_regimes": 4}).to_csv(csv, index=False)
    # regimes by date: 01-01=0 01-02=0 01-03=1 01-04=1 01-05=2 01-06=2 01-07=3 01-08=3 01-09=0 01-10=3
    # median of [0,0,1,1,2,2,3,3,0,3] = 1.5  =>  regime <= 1.5 is CALM, above is TURBULENT
    s = pd.DataFrame({"Date": pd.to_datetime(["2015-01-01 08:30", "2015-01-09 08:30",
                                              "2015-01-08 08:30"]),
                      "surprise_z": [0.0, 0.0, 0.0]})
    lab = label_c2_vol_regime(s, csv)
    assert lab[0] == "CALM"          # 2015-01-01 -> regime 0
    assert lab[1] == "CALM"          # 2015-01-09 -> regime 0
    assert lab[2] == "TURBULENT"     # 2015-01-08 -> regime 3


def test_c2_unknown_date_is_unlabelled(tmp_path):
    csv = tmp_path / "r.csv"
    pd.DataFrame({"date": pd.date_range("2015-01-01", periods=3, freq="D"),
                  "regime": [0, 1, 3], "n_regimes": 4}).to_csv(csv, index=False)
    s = pd.DataFrame({"Date": pd.to_datetime(["2020-06-01 08:30"]), "surprise_z": [0.0]})
    assert label_c2_vol_regime(s, csv)[0] == ""
