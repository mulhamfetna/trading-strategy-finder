"""Load an arbitrary contributor's inputs (candles + boxes + delivered touch signal).

Mirrors optimize/data.load_inputs + load_box for a registry-declared instrument. Pure data loading —
no alignment, no state, no votes (those are align.py / state.py / votes.py)."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from loader import load_data                                      # noqa: E402
from optimize.l2.contributors.registry import get_contributor    # noqa: E402


def load_contributor_box(box_csv: str) -> pd.DataFrame:
    """Load a contributor's unified box frame, normalized Date index (same shape as optimize/data.load_box
    and box_lookup expectations)."""
    c = pd.read_csv(box_csv)
    c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    return c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)


def load_delivery_signal(delivery_csv: str) -> pd.DataFrame:
    """Load the delivered Stage-1 touch signal stream (2_holds_dropped: only long/short rows, one per
    (candle × box)). Columns: datetime, open, high, low, close, volume, signal, box_id, box_upper,
    box_lower (per ES_SIGNALS_DELIVERY/README.md)."""
    d = pd.read_csv(delivery_csv)
    d["datetime"] = pd.to_datetime(d["datetime"])
    return d


@dataclass
class ContributorInputs:
    token: str
    df_dec: pd.DataFrame    # decision-TF OHLCV (Date/Open/High/Low/Close/Volume)
    df1: pd.DataFrame       # 1-minute OHLCV (shared exit resolution analogue)
    box: pd.DataFrame       # unified box frame (normalized Date index)
    delivery: pd.DataFrame  # delivered touch signal stream
    tick_threshold: float


def load_contributor_inputs(token: str, tf: str = "4h") -> ContributorInputs:
    """Return the full input bundle for a contributor + timeframe (preset 'full')."""
    c = get_contributor(token)
    df_dec = load_data(c.candle_csv(tf)).sort_values("Date").reset_index(drop=True)
    df1 = load_data(c.candle_csv("1m")).sort_values("Date").reset_index(drop=True)
    box = load_contributor_box(c.box_csv)
    delivery = load_delivery_signal(c.delivery_csv(tf, "full"))
    return ContributorInputs(token=c.token, df_dec=df_dec, df1=df1, box=box,
                             delivery=delivery, tick_threshold=c.tick_threshold)
