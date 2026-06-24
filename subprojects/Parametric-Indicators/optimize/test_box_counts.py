"""box_fire_stats — per-candle box-fire counts (the pre-collapse detail decision_signals discards).
Anchors are the validated figures from the 2026-06-24 multi-box data study (NQ 4h, 2,119 candles)."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize import signals, data as data_mod


def test_box_fire_stats_matches_research_anchors():
    df_dec, df1, box, vf, n_split = data_mod.load_inputs("4h")
    s = signals.box_fire_stats(df_dec, box)
    assert s["total_candles"] == 2119
    assert s["fired_candles"] == 829          # candles with >=1 level-pair firing
    assert s["multi_box_candles"] == 191      # candles with >=2 level-pairs firing
    assert s["both_tf_candles"] == 157        # >=1 weekly AND >=1 monthly pair fired
    assert s["total_fires"] == 1066           # sum of all per-candle pair-fires
    # internal consistency
    assert s["fired_candles"] >= s["multi_box_candles"] >= s["both_tf_candles"]
    assert s["total_fires"] >= s["fired_candles"]
