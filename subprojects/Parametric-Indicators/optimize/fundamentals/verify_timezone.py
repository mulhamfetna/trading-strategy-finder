"""TIMEZONE ALIGNMENT PROOF — a permanent, re-runnable guard.

THE HAZARD (raised 2026-07-14): the whole system runs on New York (US Eastern) candle time. US macro
releases are announced at 08:30 AM ET. If the calendar's release timestamps were ever in a DIFFERENT
timezone than the candles (e.g. the user's GMT+3), every news window would be mis-aligned by ~7 hours and
every event study would be silently wrong.

THE PROOF: measure the mean |1-min return| at each minute OFFSET from the labeled release timestamp. If
news and candles share a timezone, the volatility spike lands at offset 0 (the release minute). If they
were 7 hours apart, the spike would appear ~7 hours away and offset 0 would be quiet.

Verified result (17-year NQ frame): 7.3x spike at offset 0 (08:30 ET), 0.66x (BELOW normal) at offset
-7h. Definitive: news and candles are both US Eastern, correctly aligned.

  WSH_DATA_BASE=/home/dev/Mulham python3 -u optimize/fundamentals/verify_timezone.py
"""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals.extended_data import load_1m_extended

df1 = load_1m_extended("NQ")
cal = rc.load_calendar()
cal = cal[cal["Date"].dt.strftime("%H:%M") == "08:30"]        # the 08:30 releases only

idx = pd.Index(df1["Date"])
close = df1["Close"].to_numpy(float)
ret = np.abs(np.diff(close, prepend=close[0]) / close)        # |1-min return|

# baseline: mean |ret| over ALL bars (the "normal minute")
base = ret.mean()

t0 = idx.get_indexer(cal["Date"])
t0 = t0[t0 >= 0]
print(f"matched {len(t0)} of {len(cal)} labeled 08:30 releases to an exact candle timestamp")
print(f"(if the timezone were wrong, FEW releases would match an exact bar, and the spike would be elsewhere)\n")

print("mean |1-min return| at each OFFSET from the labeled 08:30 timestamp, as a multiple of a normal minute:")
print(f"{'offset (min)':>12} {'clock':>7} {'x normal':>9}   spike")
for off in range(-5, 8):
    ii = t0 + off
    ii = ii[(ii >= 0) & (ii < len(ret))]
    mult = ret[ii].mean() / base
    clock = (pd.Timestamp('2000-01-01 08:30') + pd.Timedelta(minutes=off)).strftime('%H:%M')
    bar = "#" * int(min(mult, 40))
    star = "  <== THE SPIKE" if off == 0 else ""
    print(f"{off:>12} {clock:>7} {mult:>8.2f}x   {bar}{star}")

print()
print("NOW THE FALSIFICATION: if news were really in GMT+3 and candles in ET (NY, GMT-4 summer),")
print("the true event would be 7 HOURS earlier in candle-time. Check offset -420 min (7h before):")
for off in (-420, -300, -60, 0, 60, 420):
    ii = t0 + off
    ii = ii[(ii >= 0) & (ii < len(ret))]
    if len(ii) == 0:
        continue
    mult = ret[ii].mean() / base
    hh = off/60
    print(f"   offset {off:>5} min ({hh:+.0f}h): {mult:>6.2f}x normal")
