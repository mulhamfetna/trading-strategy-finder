import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from indicators import library, runner


def _frame(n=40):
    d = pd.date_range("2025-01-01 18:00", periods=n, freq="4h")
    c = np.linspace(100, 120, n)
    df = pd.DataFrame({"Date": d, "Open": c, "High": c + 1, "Low": c - 1, "Close": c})
    box = pd.DataFrame({"Date": d}).set_index("Date")
    return df, box


def test_confirm_count_matches_confirm_mask():
    df, box = _frame()
    inds = library.from_specs([
        {"key": "ema_trend", "enabled": True, "mode": "confirm", "params": {"fast": 3, "slow": 8}},
        {"key": "rsi", "enabled": True, "mode": "confirm", "params": {"n": 5, "lower": 40, "upper": 60}}])
    cc_entry, n_conf = runner.confirm_count(df, box, inds)
    assert cc_entry.dtype == np.int64 and len(cc_entry) == len(df) and cc_entry[0] == 0 and n_conf == 2
    for k in (1, 2, 3):
        mask = runner.confirm_mask(df, box, inds, k)
        k_eff = min(k, n_conf)
        expect = np.ones(len(df), dtype=bool)
        expect[1:] = cc_entry[1:] >= k_eff
        assert np.array_equal(mask, expect), f"mismatch at k={k}"


def test_confirm_count_no_confirmers_is_zero():
    df, box = _frame()
    inds = library.from_specs([
        {"key": "adx", "enabled": True, "mode": "veto", "params": {"n": 5, "threshold": 20}}])
    cc_entry, n_conf = runner.confirm_count(df, box, inds)
    assert n_conf == 0 and not cc_entry.any()
