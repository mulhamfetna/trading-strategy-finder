# optimize/l2/contributors/test_contrib_committee.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize.l2.contributors import votes
from indicators.base import CONFIRM


def _rising_es(n=60):
    """A monotonically rising ES decision frame ⇒ EMA(fast)>EMA(slow), stance = +1 (bullish) on warm bars."""
    dates = pd.date_range("2025-01-01T18:00", periods=n, freq="4h")
    close = np.linspace(100.0, 200.0, n)
    return pd.DataFrame({"Date": dates, "Open": close, "High": close + 1,
                         "Low": close - 1, "Close": close, "Volume": np.ones(n)})


def test_es_long_committee_vote_confirms_only_nq_long():
    """ES is bullish (rising). With box_dir = +1 (NQ-long) the ES EMA-trend confirms; with box_dir = -1
    (NQ-short) it must NOT confirm. Orientation: +1 always means 'agrees with NQ' (Spec §5b)."""
    es = _rising_es(60)
    n = len(es)
    j_es = np.arange(n, dtype=np.int64)                # identity grid
    specs = [{"key": "ema_trend", "enabled": True, "mode": "confirm",
              "params": {"fast": 3, "slow": 8}}]
    nq_long = np.ones(n, dtype=np.int8)
    nq_short = -np.ones(n, dtype=np.int8)
    v_long, inds = votes.committee_votes(es.df_dec if hasattr(es, "df_dec") else es, j_es, nq_long, specs)
    v_short, _ = votes.committee_votes(es, j_es, nq_short, specs)
    ind_id = next(iter(v_long))
    warm = 8                                            # slow EMA warm-up
    assert (v_long[ind_id][warm:] == CONFIRM).all()    # ES-long confirms NQ-long
    assert not (v_short[ind_id][warm:] == CONFIRM).any()  # ES-long never confirms NQ-short


def test_committee_masks_are_identity_when_no_specs_enabled():
    es = _rising_es(20)
    n = len(es)
    j_es = np.arange(n, dtype=np.int64)
    v, inds = votes.committee_votes(es, j_es, np.ones(n, dtype=np.int8), specs=[])
    assert v == {}
    veto = votes.committee_veto_mask(v, inds, n)
    confirm = votes.committee_confirm_mask(v, inds, k=1, n=n)
    assert not veto.any()                              # no veto ⇒ all-False identity
    assert confirm.all()                               # no confirmer ⇒ all-True identity (Spec §8.1)


def test_committee_confirm_mask_threshold_and_alignment():
    es = _rising_es(40)
    n = len(es)
    j_es = np.arange(n, dtype=np.int64)
    specs = [{"key": "ema_trend", "enabled": True, "mode": "confirm", "params": {"fast": 3, "slow": 8}}]
    nq_long = np.ones(n, dtype=np.int8)
    v, inds = votes.committee_votes(es, j_es, nq_long, specs)
    confirm = votes.committee_confirm_mask(v, inds, k=1, n=n)
    assert confirm.dtype == bool and len(confirm) == n
    assert confirm[0]                                  # idx0 is identity-True (entry-bar alignment)
    assert confirm[-1]                                 # late warm bars confirm ⇒ gate open
