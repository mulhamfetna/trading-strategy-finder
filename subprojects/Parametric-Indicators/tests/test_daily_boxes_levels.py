"""DAILY_LEVELS must mirror the weekly level structure exactly and name only real CSV columns."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from box_lookup import _WEEKLY_LEVELS                       # noqa: E402
from research.daily_boxes.levels import DAILY_LEVELS        # noqa: E402


def test_daily_levels_mirror_weekly_shape():
    assert len(DAILY_LEVELS) == len(_WEEKLY_LEVELS) == 8
    for (du, dl, dlab), (wu, wl, wlab) in zip(DAILY_LEVELS, _WEEKLY_LEVELS):
        assert du == "D" + wu[1:], f"{du} should mirror {wu}"
        assert dl == "D" + wl[1:], f"{dl} should mirror {wl}"
        assert dlab == "D" + wlab[1:], f"{dlab} should mirror {wlab}"


def test_daily_level_columns_all_exist_in_real_box_csv():
    import config
    box_csv = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"
    if not box_csv.exists():
        pytest.skip(f"box csv not present: {box_csv}")
    cols = set(pd.read_csv(box_csv, nrows=1).columns)
    missing = [c for u, l, _ in DAILY_LEVELS for c in (u, l) if c not in cols]
    assert not missing, f"columns missing from box CSV: {missing}"
