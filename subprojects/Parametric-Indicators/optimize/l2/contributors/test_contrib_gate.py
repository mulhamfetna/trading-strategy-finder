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


def _synth_es(n=8, closes=None):
    d = pd.date_range("2025-01-01 18:00", periods=n, freq="4h")
    if closes is None:
        closes = np.array([10, 11, 13, 16, 15, 12, 14, 17], dtype=float)[:n]
    df = pd.DataFrame({"Date": d, "Open": closes, "High": closes + 1.0,
                       "Low": closes - 1.0, "Close": closes})
    return SimpleNamespace(df_dec=df.copy(), df1=df.copy(), box=None,
                           delivery=None, tick_threshold=0.75)


def _cfg_committee():
    return {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch",
            "signal": {"encoding": "none"},
            "committee": [{"key": "ema_trend", "enabled": True, "mode": "confirm",
                           "params": {"fast": 1, "slow": 2}}]}


def test_committee_channel_shapes_dtypes_and_entry_shift(monkeypatch):
    from optimize.l2.contributors import loader as _loader
    es = _synth_es()
    monkeypatch.setattr(_loader, "load_contributor_inputs", lambda token, tf="4h": es)
    l1 = _fake_l1(8)
    l1.sig_int = np.array([1, 1, 1, -1, -1, 1, 1, -1], dtype=np.int8)
    veto, cc = gate.contributor_gate_masks(_cfg_committee(), l1)
    assert veto.dtype == bool and cc.dtype == np.int64
    assert len(veto) == len(cc) == 8
    assert cc[0] == 0                                   # entry-shift identity at idx0 (no future leak)
    assert (cc < gate.NO_CONFIRM_CONSTRAINT).all()      # real confirm source => real counts, not sentinel
    assert cc.max() <= 1                                # one confirm indicator => count in {0,1}


def test_committee_lookahead_guard_future_bars_dont_change_earlier(monkeypatch):
    from optimize.l2.contributors import loader as _loader
    k = 4                                               # freeze NQ bars [0..k]
    base = _synth_es()
    es2 = _synth_es()
    es2.df_dec.loc[k + 1:, "Close"] += 99.0             # mutate ONLY future ES bars
    es2.df_dec.loc[k + 1:, ["Open", "High", "Low"]] += 99.0
    es2.df1 = es2.df_dec.copy()
    l1 = _fake_l1(8); l1.sig_int = np.array([1, 1, 1, -1, -1, 1, 1, -1], dtype=np.int8)

    monkeypatch.setattr(_loader, "load_contributor_inputs", lambda token, tf="4h": base)
    v1, c1 = gate.contributor_gate_masks(_cfg_committee(), l1)
    monkeypatch.setattr(_loader, "load_contributor_inputs", lambda token, tf="4h": es2)
    v2, c2 = gate.contributor_gate_masks(_cfg_committee(), l1)
    assert np.array_equal(v1[:k + 1], v2[:k + 1])       # earlier NQ-bar masks unaffected by future ES
    assert np.array_equal(c1[:k + 1], c2[:k + 1])


_NQ_DIR = np.array([1, 1, 1, -1, -1, 1, 1, -1], dtype=np.int8)
_ES_STATE = np.array([1, 1, -1, -1, 1, 1, -1, -1], dtype=np.int8)


def _patch_state(monkeypatch, arr=_ES_STATE):
    from optimize.l2.contributors import state as _state, loader as _loader
    monkeypatch.setattr(_loader, "load_contributor_inputs", lambda token, tf="4h": _synth_es())
    monkeypatch.setattr(_state, "touch_state", lambda df_dec, delivery: arr)


def test_signal_only_stance_both_matches_signal_stance(monkeypatch):
    from optimize.l2.contributors import votes
    _patch_state(monkeypatch)
    l1 = _fake_l1(8); l1.sig_int = _NQ_DIR
    cfg = {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch",
           "committee": [], "signal": {"encoding": "stance", "mode": "both"}}
    veto, cc = gate.contributor_gate_masks(cfg, l1)
    exp_cvote, exp_veto = votes.signal_stance(_NQ_DIR, _ES_STATE, "both")
    assert np.array_equal(veto, exp_veto)
    assert np.array_equal(cc, exp_cvote.astype(np.int64))   # committee empty => cc = signal confirm
    assert (cc < gate.NO_CONFIRM_CONSTRAINT).all()          # stance 'both' is a confirm source


def test_signal_veto_only_has_no_confirm_source_sentinel(monkeypatch):
    from optimize.l2.contributors import votes
    _patch_state(monkeypatch)
    l1 = _fake_l1(8); l1.sig_int = _NQ_DIR
    cfg = {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch",
           "committee": [], "signal": {"encoding": "stance", "mode": "veto"}}
    veto, cc = gate.contributor_gate_masks(cfg, l1)
    _, exp_veto = votes.signal_stance(_NQ_DIR, _ES_STATE, "veto")
    assert np.array_equal(veto, exp_veto)
    assert (cc == gate.NO_CONFIRM_CONSTRAINT).all()         # no confirm source anywhere => sentinel


def test_truthtable_with_confirm_cell_is_a_confirm_source(monkeypatch):
    _patch_state(monkeypatch)
    l1 = _fake_l1(8); l1.sig_int = _NQ_DIR
    cfg = {"token": "ES", "enabled": True, "tf": "4h", "state_def": "touch", "committee": [],
           "signal": {"encoding": "truthtable", "table": {("long", "long"): "confirm"}}}
    veto, cc = gate.contributor_gate_masks(cfg, l1)
    assert (cc < gate.NO_CONFIRM_CONSTRAINT).all()          # a 'confirm' cell => real confirm source
    assert not veto.any()                                   # table has no 'veto' cell
