import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import pytest
from optimize.l2.contributors import registry


def test_es_contributor_paths_resolve_from_instruments_registry():
    c = registry.get_contributor("ES")
    assert c.token == "ES"
    assert c.align == "identity"                       # ES = exact grid (Spec §3.2)
    assert c.tick_threshold == 0.75
    assert c.candle_csv("4h").endswith("ES_Continuous_Data/ES_4h.csv")
    assert c.candle_csv("1m").endswith("ES_Continuous_Data/ES_1m.csv")
    # Non-NQ instruments read the -1-workday-SHIFTED box: instruments.py marks the raw box
    # "retired" (2026-07-06) so delivered signals and the backtest share one box. This
    # assertion still pinned the retired path (#66).
    assert c.box_csv.endswith("shifted_boxes/ES_full_data_shifted.csv")
    assert c.delivery_csv("4h", "full").endswith("ES_SIGNALS_DELIVERY/2_holds_dropped/ES_4h_full.csv")
    # every resolved path must actually exist on disk (no typo'd path silently accepted)
    for p in (c.candle_csv("4h"), c.candle_csv("1m"), c.box_csv, c.delivery_csv("4h", "full")):
        assert Path(p).exists(), p


def test_unknown_contributor_raises():
    with pytest.raises(KeyError):
        registry.get_contributor("DOGE")
