#!/usr/bin/env python3
"""Load TimesFM ONCE, run the directional/calibration diagnostic on several (instrument, tf, horizon)
combos, caching each full-series forecast pass for later walk-forward reuse.

    python run_diag.py            # ES 1h + NQ 1h, horizon 24
"""
from __future__ import annotations

import sys

from diagnose import diagnose
from tfm.forecaster import get_forecaster

# (instrument, timeframe, horizon-in-bars). 1h already cached (instant reprint); 30m then 15m are
# the new passes. Horizon 24 bars = 12h on 30m, 6h on 15m — comparable holding windows.
COMBOS = [
    ("ES", "1h", 24),
    ("NQ", "1h", 24),
    ("ES", "30m", 24),
    ("NQ", "30m", 24),
    ("ES", "15m", 24),
    ("NQ", "15m", 24),
]

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    fc = get_forecaster("timesfm")  # loaded once, reused across all combos
    for inst, tf, h in COMBOS:
        print("\n" + "=" * 66)
        diagnose(inst, tf, h, fc=fc)
        print("=" * 66, flush=True)
