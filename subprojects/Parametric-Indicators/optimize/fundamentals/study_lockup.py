"""Task #8 — is 08:30 (PUBLICATION) really the market-moving instant, or does the lockup leak?

US macro data is handed to journalists EARLY under embargo — a "lockup", historically ~30 minutes
before publication. They write their stories inside a sealed room and the wire fires at exactly 08:30.

The user's claim: we care about 08:30, the PUBLICATION time, not any earlier internal release.

IF THE LOCKUP LEAKED, we would see volatility BEFORE 08:30 on release days — someone trading on
information the public does not have. If it does not leak, the market must be dead quiet right up to
08:30 and then explode.

This is a testable claim about market integrity, and our data can settle it.

Method: for RELEASE days only, measure the volatility ratio at each clock minute from 07:45 to 08:35,
and compare to the SAME clock minutes on NON-release days (the control). A leak shows up as elevated
volatility on release days BEFORE 08:30 that is absent on control days.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from optimize import data
from optimize.fundamentals import release_calendar as rc

_, df1, *_ = data.load_inputs("4h")
cal = rc.load_calendar()

close = df1["Close"].to_numpy(dtype=np.float64)
ret_bp = np.zeros(len(close))
ret_bp[1:] = np.abs(np.diff(close) / close[:-1]) * 10_000.0
baseline = float(ret_bp[1:].mean())

t = df1["Date"]
day = t.dt.normalize()
hhmm = t.dt.strftime("%H:%M")

# 08:30 release days only (the BLS/BEA/Census set — excludes the 14:00 FOMC)
rel_days = set(cal[cal["Date"].dt.strftime("%H:%M") == "08:30"]["Date"].dt.normalize())
is_rel = day.isin(rel_days).to_numpy()
# control: weekdays that are NOT release days
is_ctl = (~day.isin(rel_days) & (t.dt.weekday < 5)).to_numpy()

print(f"08:30 release days: {len(rel_days)}   ·   baseline = {baseline:.3f} bp/min\n")
print("THE LOCKUP TEST — is there ANY unusual activity before the number is published?")
print()
print(f"{'clock':>7} | {'RELEASE days':>14} | {'control days':>14} | {'ratio R/C':>10} | verdict")
print("-" * 74)

for m in ["07:45", "08:00", "08:05", "08:15", "08:20", "08:25", "08:28", "08:29",
          "08:30", "08:31", "08:35"]:
    sel = (hhmm == m).to_numpy()
    r = ret_bp[sel & is_rel]
    c = ret_bp[sel & is_ctl]
    if len(r) < 5 or len(c) < 5:
        continue
    rr, cc = r.mean() / baseline, c.mean() / baseline
    ratio = rr / cc if cc > 0 else float("nan")
    if m == "08:30":
        v = "<<< THE PRINT"
    elif ratio > 1.5:
        v = "!! ELEVATED — possible leak"
    elif ratio > 1.2:
        v = "mildly elevated"
    else:
        v = "normal"
    print(f"{m:>7} | {rr:>7.2f}x (n={len(r):>3}) | {cc:>7.2f}x (n={len(c):>4}) | {ratio:>9.2f}x | {v}")

print()
print("READ: 'ratio R/C' is how much more volatile that minute is on a RELEASE day than on an")
print("ordinary weekday. A value near 1.0 means release days are INDISTINGUISHABLE from normal days")
print("at that minute — i.e. nobody is trading on the number yet.")
