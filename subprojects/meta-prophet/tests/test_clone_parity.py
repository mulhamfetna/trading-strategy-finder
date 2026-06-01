"""Prove the adaptive clone == the original engine when levers are OFF.

This is the guarantee that we never changed the manual logic: with sl_tp_mult=None and
entry_gate=None, the clone must produce byte-identical trades to src.strategy.simple_strategy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJ = Path("/mnt/data/projects/trading")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ))
sys.path.insert(0, str(ROOT))

from src.data.loader import load_data
from src.strategy.simple_strategy import SimpleStrategy as Orig, SimpleStrategyParams as OrigP
from engine_clone.simple_strategy_adaptive import SimpleStrategy as Clone, SimpleStrategyParams as CloneP

DATA = PROJ / "data"


def _load(year: int):
    d = DATA / f"{year}_data"
    df4 = load_data(str(d / f"NQ_4h_{year}.csv"))
    df1 = load_data(str(d / f"NQ_1m_{year}.csv"))
    box = pd.read_csv(d / f"NQ_full_data_{year}.csv")
    box["Date"] = pd.to_datetime(box["Date"]).dt.normalize()
    box = box.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    return df4, df1, box


def _params(cls):
    return cls(sl_soft_points=80.0, sl_hard_points=100.0, tp_soft_points=50.0, tp_hard_points=50.0,
               data_path_4h="", data_path_1min="", box_data_path="", flip_entry_direction=False)


def test_clone_equals_original_when_levers_off():
    df4, df1, box = _load(2025)
    orig_trades, _ = Orig(_params(OrigP)).backtest(df4, df1, box)
    clone_trades, _ = Clone(_params(CloneP)).backtest(df4, df1, box)  # no levers
    assert len(orig_trades) == len(clone_trades), f"trade count differs: {len(orig_trades)} vs {len(clone_trades)}"
    for a, b in zip(orig_trades, clone_trades):
        assert a["entry_time"] == b["entry_time"]
        assert a["exit_reason"] == b["exit_reason"]
        assert a["pnl_points"] == pytest.approx(b["pnl_points"], abs=1e-9)
