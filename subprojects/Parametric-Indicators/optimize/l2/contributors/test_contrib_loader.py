# optimize/l2/contributors/test_contrib_loader.py
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pandas as pd
from optimize.l2.contributors import loader


def test_load_es_inputs_shapes_and_columns():
    es = loader.load_contributor_inputs("ES", "4h")
    assert es.token == "ES"
    assert es.tick_threshold == 0.75
    # decision frame: OHLCV with a parsed Date column, ~2119 bars (measured)
    for col in ("Date", "Open", "High", "Low", "Close", "Volume"):
        assert col in es.df_dec.columns
    assert pd.api.types.is_datetime64_any_dtype(es.df_dec["Date"])
    assert len(es.df_dec) > 2000
    assert es.df_dec["Date"].is_monotonic_increasing
    # 1-minute frame is much larger and also datetime-parsed
    assert len(es.df1) > len(es.df_dec) * 50
    assert pd.api.types.is_datetime64_any_dtype(es.df1["Date"])
    # box frame: normalized Date index (midnight), no duplicate dates
    assert es.box.index.name == "Date"
    assert (es.box.index == es.box.index.normalize()).all()
    assert not es.box.index.duplicated().any()
    # delivery: only long/short rows (2_holds_dropped), datetime parsed
    assert set(es.delivery["signal"].unique()) <= {"long", "short"}
    assert pd.api.types.is_datetime64_any_dtype(es.delivery["datetime"])
