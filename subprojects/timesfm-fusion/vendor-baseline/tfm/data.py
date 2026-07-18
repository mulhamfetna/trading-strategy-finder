"""Data loading + train/test (walk-forward) splitting for NQ / ES OHLCV candles.

Reads the same CSVs the reference backtester uses (datetime,open,high,low,close,volume).
Point at your data tree with the FUTURES_DATA_DIR env var; defaults to the reference bundle.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Where the raw {INST}_{TF}.csv files live. Override: set FUTURES_DATA_DIR.
DEFAULT_DATA_DIR = Path(os.environ.get(
    "FUTURES_DATA_DIR",
    r"C:\Users\Abd Ulfatah Esper\Downloads\Telegram Desktop"
    r"\mtf_layer_fusion_backtester\mtf_layer_fusion_backtester",
))


@dataclass(frozen=True)
class Instrument:
    """Per-contract economics + realistic frictions (round-trip)."""
    name: str
    point_value: float      # USD per index point per contract
    tick: float             # min price increment (points)
    commission_rt: float    # round-trip commission ($) per contract
    slippage_ticks: float   # assumed slippage per fill (ticks), applied on entry AND exit

    @property
    def cost_dollars(self) -> float:
        """All-in round-trip cost of one trade, in $ (commission + 2 fills of slippage)."""
        return self.commission_rt + 2.0 * self.slippage_ticks * self.tick * self.point_value


INSTRUMENTS = {
    "ES": Instrument("ES", point_value=50.0, tick=0.25, commission_rt=4.0, slippage_ticks=1.0),
    "NQ": Instrument("NQ", point_value=20.0, tick=0.25, commission_rt=4.0, slippage_ticks=1.0),
}


def load_ohlcv(instrument: str, tf: str = "1h", data_dir: Path | None = None) -> pd.DataFrame:
    """Load one instrument/timeframe as a clean OHLCV DataFrame indexed by datetime."""
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    path = data_dir / f"{instrument.upper()}_{tf}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Candle file not found: {path}")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df[["datetime", "open", "high", "low", "close", "volume"]]


# Timeframes we have as native CSVs; everything else is resampled from 1m.
NATIVE_TFS = {"1m", "1h", "4h"}
_UNIT_TO_PANDAS = {"m": "min", "h": "h"}


def _tf_to_freq(tf: str) -> str:
    """'5m' -> '5min', '30m' -> '30min', '2h' -> '2h'. Used for resampling from 1m."""
    tf = tf.strip().lower()
    num = "".join(ch for ch in tf if ch.isdigit()) or "1"
    unit = "".join(ch for ch in tf if ch.isalpha())
    if unit not in _UNIT_TO_PANDAS:
        raise ValueError(f"unsupported timeframe unit in {tf!r} (use m or h)")
    return f"{num}{_UNIT_TO_PANDAS[unit]}"


def resample_from_1m(df1m: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Aggregate 1-minute OHLCV to an arbitrary timeframe on a fixed grid anchored at the data
    start. Empty buckets (maintenance breaks / weekends) are dropped, so bars stay contiguous."""
    freq = _tf_to_freq(tf)
    g = (df1m.set_index("datetime")
         .resample(freq, origin="start", label="left", closed="left")
         .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
              close=("close", "last"), volume=("volume", "sum")))
    g = g.dropna(subset=["open", "high", "low", "close"]).reset_index()
    return g[["datetime", "open", "high", "low", "close", "volume"]]


def load_tf(instrument: str, tf: str, data_dir: Path | None = None) -> pd.DataFrame:
    """Load ANY timeframe: native CSV when available (1m/1h/4h), else resampled from 1m.
    Supports 1m, 2m, 5m, 15m, 30m, 1h, 2h, 4h, ... — anything expressible as <n>m or <n>h."""
    tf = tf.strip().lower()
    if tf in NATIVE_TFS:
        return load_ohlcv(instrument, tf, data_dir)
    df1m = load_ohlcv(instrument, "1m", data_dir)
    return resample_from_1m(df1m, tf)


def split_walk_forward(df: pd.DataFrame, train_frac: float = 0.70) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological split: first `train_frac` = TRAIN (tune thresholds), rest = OOS TEST.

    Returns (train, test) as row-contiguous copies with a fresh RangeIndex. The split is by
    row count, so both halves are contiguous in time — no leakage from future into past.
    """
    n = len(df)
    cut = int(round(n * train_frac))
    train = df.iloc[:cut].reset_index(drop=True).copy()
    test = df.iloc[cut:].reset_index(drop=True).copy()
    return train, test


def summarize_split(train: pd.DataFrame, test: pd.DataFrame) -> str:
    def span(d):
        return f"{d['datetime'].iloc[0]} -> {d['datetime'].iloc[-1]}  ({len(d)} bars)"
    return f"TRAIN: {span(train)}\nTEST : {span(test)}"


if __name__ == "__main__":
    for inst in ("ES", "NQ"):
        df = load_ohlcv(inst, "1h")
        tr, te = split_walk_forward(df)
        print(f"=== {inst} 1h ===")
        print(summarize_split(tr, te))
        print()
