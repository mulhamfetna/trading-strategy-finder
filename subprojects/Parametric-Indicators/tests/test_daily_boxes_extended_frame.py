"""The M3 extension must be a clean, assertion-guarded concatenation - or fail loudly."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.extended_frame import _concat_checked, load_extended   # noqa: E402


def test_concat_rejects_overlapping_dates():
    a = pd.DataFrame({"Date": pd.to_datetime(["2024-01-01", "2024-01-02"]), "v": [1, 2]})
    b = pd.DataFrame({"Date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "v": [3, 4]})
    with pytest.raises(ValueError, match="duplicate"):
        _concat_checked(a, b, "test")


def test_concat_rejects_schema_mismatch():
    a = pd.DataFrame({"Date": pd.to_datetime(["2024-01-01"]), "v": [1]})
    b = pd.DataFrame({"Date": pd.to_datetime(["2024-01-02"]), "w": [2]})
    with pytest.raises(ValueError, match="schema"):
        _concat_checked(a, b, "test")


def test_concat_sorts_and_preserves_all_rows():
    a = pd.DataFrame({"Date": pd.to_datetime(["2024-01-03", "2024-01-01"]), "v": [3, 1]})
    b = pd.DataFrame({"Date": pd.to_datetime(["2024-01-02"]), "v": [2]})
    out = _concat_checked(a, b, "test")
    assert len(out) == 3
    assert out["v"].tolist() == [1, 2, 3]
    assert out["Date"].is_monotonic_increasing


def test_load_extended_real_data_spans_2024_to_2026():
    """Reads only daily/4h CSVs (a few thousand rows) — cheap enough to run anywhere."""
    try:
        df_dec, box = load_extended("4h")
    except FileNotFoundError as e:
        pytest.skip(f"real data not present: {e}")
    assert df_dec["Date"].min().year == 2024
    assert df_dec["Date"].max().year == 2026
    assert len(df_dec) == 3663, f"expected 3663 4h bars, got {len(df_dec)}"
    assert {"Open", "High", "Low", "Close"}.issubset(df_dec.columns)


def test_main_candles_come_from_the_PRODUCTION_raw_dir():
    """Regression guard: decision candles must resolve exactly where optimize/data.py resolves them.

    They live under $WSH_DATA_BASE/<RAW_DIR>/, NOT under $WSG_DATA_ROOT/full_data/. Those two happen to
    both contain NQ_4h.csv, so a wrong path silently 'works' on 4h and then fails on 1h.
    """
    from optimize.data import _RAW
    if not Path(_RAW).is_dir():
        pytest.skip(f"market data not present (server-only): {_RAW}")
    for tf in ("4h", "1h", "2h"):
        assert (Path(_RAW) / f"NQ_{tf}.csv").exists(), f"production candle path missing for {tf}"


def test_load_extended_works_for_1h_not_only_4h():
    """1h has no NQ_1h.csv under full_data/ — this fails if the loader uses the wrong root."""
    try:
        df_dec, _box = load_extended("1h")
    except FileNotFoundError as e:
        pytest.skip(f"real data not present: {e}")
    assert df_dec["Date"].min().year == 2024
    assert df_dec["Date"].max().year == 2026
    assert len(df_dec) > 3663, "1h must have more bars than 4h"
