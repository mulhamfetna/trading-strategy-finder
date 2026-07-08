"""Minimal self-contained instrument registry for the shareable bundle.

The full research registry also resolves per-instrument data paths; this bundle takes EXPLICIT CSV paths
(--decision/--minute/--box), so the only thing needed here is the point value per contract — a fallback
used when a champion preset omits "pv". Every champion in champions/ already carries its own "pv", so this
is belt-and-suspenders and keeps the bundle free of any external registry file.
"""

# USD value of one full point, per contract (1 contract).
_POINT_VALUE = {
    "NQ": 20.0,     # Nasdaq-100 E-mini
    "ES": 50.0,     # S&P 500 E-mini
    "GC": 100.0,    # Gold (COMEX, full)
    "SI": 5000.0,   # Silver (COMEX, full)
    "RTY": 50.0,    # Russell 2000 E-mini
    "YM": 5.0,      # Dow E-mini
}


def point_value(instrument: str = "NQ") -> float:
    return _POINT_VALUE.get(instrument, 20.0)
