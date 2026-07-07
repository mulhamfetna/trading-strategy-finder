"""Run the champion through the EXACT engine (strategy.build_payload — the same path the golden gate uses),
with the intra-candle vetoed-entry flag toggled. Off => byte-identical to the golden baseline."""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_PERF = _ROOT / "perf"
if str(_PERF) not in sys.path:
    sys.path.insert(0, str(_PERF))

import strategy  # noqa: E402
from _common import load_bundle  # noqa: E402  (perf/_common.py)


def run_champion_exact(tf: str = "4h", intracandle_veto_entry: bool = False,
                       intracandle_max_wait: int = 240, intracandle_force_close: bool = False):
    """Return (trades, summary) for the champion at `tf`, optionally with intra-candle vetoed entry on
    (and optionally the force-close variant: a normal entry force-closes an open rescued trade)."""
    df_dec, df1, box, vf, n2025, preset = load_bundle(tf)
    preset = dict(preset)
    preset["intracandle_veto_entry"] = bool(intracandle_veto_entry)
    preset["intracandle_max_wait"] = int(intracandle_max_wait)
    preset["intracandle_force_close"] = bool(intracandle_force_close)
    payload = strategy.build_payload(df_dec, df1, box, vf, n2025, preset)
    return payload["trades"], payload["meta"]["summary"]
