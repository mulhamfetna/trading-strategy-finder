"""Minimal self-contained instrument registry for the shareable bundle.

The full research registry also resolves per-instrument data paths; this bundle takes EXPLICIT CSV paths
(--decision/--minute/--box), so the only thing needed here is the point value per contract — a fallback
used when a champion preset omits "pv". Every champion in champions/ already carries its own "pv", so this
is belt-and-suspenders and keeps the bundle free of any external registry file.
"""

# USD value of one full point, per contract (1 contract).
_POINT_VALUE = {
    "NQ": 20.0,      # Nasdaq-100 E-mini
    "ES": 50.0,      # S&P 500 E-mini
    "GC": 100.0,     # Gold (COMEX, full)
    "SI": 5000.0,    # Silver (COMEX, full)
    "HG": 25000.0,   # Copper (COMEX, full - 25,000 lbs x $/lb)
    "CL": 1000.0,    # Crude Oil (NYMEX, full - 1,000 bbl x $/bbl)
    "NG": 10000.0,   # Natural Gas (NYMEX, full - 10,000 MMBtu x $/MMBtu)
    "RTY": 50.0,     # Russell 2000 E-mini
    "YM": 5.0,       # Dow E-mini
}


def point_value(instrument: str = "NQ") -> float:
    """USD per point for one contract.

    A SILENT-DEFAULT TRAP: this used to be `.get(instrument, 20.0)`, so any market missing from the
    table was quietly priced as the Nasdaq. HG/CL/NG were added to the bundle without being added
    here, and their P/L came out divided by their point-value ratio (Copper 15m: $41,588 -> $33).
    An unknown token now RAISES rather than guessing a wrong contract size.
    """
    try:
        return _POINT_VALUE[instrument]
    except KeyError:
        raise KeyError(f"no point value for instrument {instrument!r} - "
                       f"known: {sorted(_POINT_VALUE)}") from None
