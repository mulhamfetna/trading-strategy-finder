import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from engine import SimpleStrategyParams  # noqa: E402


def test_intracandle_params_default_off():
    p = SimpleStrategyParams(sl_soft_points=1, sl_hard_points=2, tp_hard_points=3,
                             data_path_4h="x", data_path_1min="y", box_data_path="z")
    assert p.intracandle_veto_entry is False      # default OFF => parity
    assert p.intracandle_max_wait == 240          # one 4h candle of 1-min bars
