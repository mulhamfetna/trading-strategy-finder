"""INSIDE THE MINUTE — what actually happened at 08:30 on 2025-03-07?

The most-quoted bar in this whole investigation:

    08:30  open 20107.50  HIGH 20249.00  LOW 20061.50  close 20218.25   range 187.5 pts, 5,069 contracts

It went DOWN 46 points AND UP 141 points inside sixty seconds. And a 1-minute OHLC candle CANNOT tell
you which happened first. That single fact may be WHY the "trade the reaction" study found nothing —
a data-resolution artifact, not market efficiency. We have never been able to tell those apart.

Now we have 1-SECOND data. Let's look inside.

THE QUESTION THAT MATTERS: if you had to decide direction from the first few SECONDS, could you? Or
does the market whipsaw so violently that even a second-by-second view is unusable?
"""
import sys
sys.path.insert(0, ".")
import pandas as pd
from optimize.fundamentals.extended_data import load_1s

T = pd.Timestamp("2025-03-07 08:30:00")
print(f"Loading 1-second bars around {T} (chunked read of a 7.8 GB file)...\n")
d = load_1s(start=T - pd.Timedelta(minutes=2), end=T + pd.Timedelta(minutes=3))
if d.empty:
    print("  no data in that window")
    raise SystemExit(1)

ep = float(d[d.Date < T].Close.iloc[-1])          # the last price BEFORE the print
print(f"last price before the print (08:29:59): {ep}\n")

print("=" * 84)
print("THE RELEASE MINUTE, SECOND BY SECOND  (08:30:00 -> 08:30:59)")
print("=" * 84)
w = d[(d.Date >= T) & (d.Date < T + pd.Timedelta(minutes=1))]
print(f"{'time':>10} {'open':>10} {'high':>10} {'low':>10} {'close':>10} {'vol':>7} "
      f"{'vs entry':>9}  path")
print("-" * 84)
run_hi, run_lo = -1e9, 1e9
for _, r in w.iterrows():
    run_hi = max(run_hi, r.High)
    run_lo = min(run_lo, r.Low)
    delta = r.Close - ep
    bar = ("+" if delta >= 0 else "-") + "#" * min(int(abs(delta) / 4), 40)
    print(f"{r.Date.strftime('%H:%M:%S'):>10} {r.Open:>10.2f} {r.High:>10.2f} {r.Low:>10.2f} "
          f"{r.Close:>10.2f} {int(r.Volume):>7} {delta:>+9.2f}  {bar}")

print()
print("=" * 84)
print("WHAT THE 1-MINUTE CANDLE HID")
print("=" * 84)
lo_t = w.loc[w.Low.idxmin(), "Date"]
hi_t = w.loc[w.High.idxmax(), "Date"]
print(f"  the LOW  (20061.50) happened at {lo_t.strftime('%H:%M:%S')}")
print(f"  the HIGH (20249.00) happened at {hi_t.strftime('%H:%M:%S')}")
print()
if lo_t < hi_t:
    print("  ⇒ It went DOWN FIRST, then up. A long would have been STOPPED OUT before the rally.")
else:
    print("  ⇒ It went UP FIRST, then down. A long would have been fine; a SHORT would have been killed.")
print()
print("  The 1-minute candle records BOTH extremes and gives you NO WAY to know the order.")
print("  A backtest on 1-min bars must GUESS — and whichever it guesses, it is wrong half the time.")

print()
print("=" * 84)
print("COULD YOU HAVE TRADED IT? — the direction at each second, vs where it ended")
print("=" * 84)
final = float(w.Close.iloc[-1])
print(f"  price at the end of the release minute: {final:.2f}  ({final-ep:+.2f} vs entry)\n")
for s in (1, 2, 3, 5, 10, 15, 30):
    sub = w[w.Date < T + pd.Timedelta(seconds=s)]
    if sub.empty:
        continue
    px = float(sub.Close.iloc[-1])
    early = px - ep
    right = (early > 0) == (final - ep > 0)
    print(f"    after {s:>2}s: {px:>9.2f} ({early:>+7.2f})  "
          f"=> following it would have been {'RIGHT' if right else 'WRONG'}")
