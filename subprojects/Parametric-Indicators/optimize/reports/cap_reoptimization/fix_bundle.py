"""Fix two bundle bugs found by the reproduction check.

1) POINT-VALUE SILENT DEFAULT. optimize/instruments.py listed only 6 markets and did
   `_POINT_VALUE.get(instrument, 20.0)` — so HG/CL/NG (added later) were quietly priced as the NASDAQ.
   Copper 15m came out as $33 instead of $41,588 (off by its 1,250x point-value ratio); Oil by 50x;
   Gas by 500x. An unknown token now RAISES instead of guessing.

2) OOS READ FROM THE WRONG FIELD. backtest.py took the headline from meta.boxes (the on-screen figure)
   but the 2026 number from meta.summary. Those differ for the shifted (non-NQ) instruments, so the two
   halves of every label came from different engines.
"""
import pathlib

B = pathlib.Path.home() / "Mulham/wsg-i/playbooks_backtester"

# ---- 1) point values
p = B / "optimize" / "instruments.py"
s = p.read_text()
old = '''_POINT_VALUE = {
    "NQ": 20.0,     # Nasdaq-100 E-mini
    "ES": 50.0,     # S&P 500 E-mini
    "GC": 100.0,    # Gold (COMEX, full)
    "SI": 5000.0,   # Silver (COMEX, full)
    "RTY": 50.0,    # Russell 2000 E-mini
    "YM": 5.0,      # Dow E-mini
}


def point_value(instrument: str = "NQ") -> float:
    return _POINT_VALUE.get(instrument, 20.0)'''

new = '''_POINT_VALUE = {
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
                       f"known: {sorted(_POINT_VALUE)}") from None'''

assert old in s, "point-value block not found"
p.write_text(s.replace(old, new, 1))
print("instruments shim: HG/CL/NG added; unknown token now raises")

# ---- 2) OOS source
b = B / "backtest.py"
t = b.read_text()
hits = [ln for ln in t.splitlines() if "oos_pnl" in ln and "summary" in ln]
for ln in hits:
    fixed = ln.replace('["meta"]["summary"]["pnl"]', '["meta"]["boxes"]["pnl"]')
    t = t.replace(ln, fixed, 1)
    print(f"backtest.py: OOS now from meta.boxes -> {fixed.strip()[:80]}")
if not hits:
    print("backtest.py: no summary-based oos_pnl line found (already fixed?)")
b.write_text(t)
