import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals.extended_data import load_1s_windows, sixteen_year_path
from optimize.fundamentals.study_surprise import build_surprises

PRE_S, POST_S, PV = 10, 60, 100.0
sur = build_surprises(rc.load_calendar()).dropna(subset=["surprise_z"])
sur = sur.assign(Date=pd.to_datetime(sur["Date"]))
first_ts = pd.Timestamp(pd.read_csv(sixteen_year_path("GC", "1s"), nrows=1)["datetime"][0])
sur = sur[sur["Date"] >= first_ts + pd.Timedelta(seconds=PRE_S)]

windows = [(t - pd.Timedelta(seconds=PRE_S), t + pd.Timedelta(seconds=POST_S)) for t in sur["Date"]]
sec = load_1s_windows(windows, instrument="GC", verbose=False)
cl = pd.Series(sec["Close"].values, index=sec["Date"].values)
hi = pd.Series(sec["High"].values, index=sec["Date"].values)
lo = pd.Series(sec["Low"].values, index=sec["Date"].values)

rows, zs, spreads = [], [], []
for _, r in sur.iterrows():
    t = r["Date"]
    want = pd.date_range(t, periods=POST_S + 1, freq="s")
    seg = cl.reindex(cl.index.union(want)).ffill().reindex(want)
    if seg.isna().any():
        continue
    rows.append(seg.to_numpy(dtype=float))
    zs.append(float(r["surprise_z"]))
    # proxy for how violent the tape is right at entry: the high-low range of second +1
    h = hi.reindex(hi.index.union([t + pd.Timedelta(seconds=1)])).ffill().reindex([t + pd.Timedelta(seconds=1)])
    l = lo.reindex(lo.index.union([t + pd.Timedelta(seconds=1)])).ffill().reindex([t + pd.Timedelta(seconds=1)])
    spreads.append(float(h.iloc[0] - l.iloc[0]))

C = np.asarray(rows); z = np.asarray(zs); n = len(z)
sp = np.asarray(spreads)
final = C[:, POST_S]

print("=" * 80)
print("NOISE + COST CHECK — the T+1s entry, the only one worth costing")
print("=" * 80)
pnl = -np.sign(z) * (final - C[:, 1])
print(f"  n releases              : {n}")
print(f"  mean                    : {pnl.mean():+.3f} pts = ${PV*pnl.mean():+.2f}")
print(f"  std (per-trade swing)   :  {pnl.std(ddof=1):.3f} pts = ${PV*pnl.std(ddof=1):.0f}")
print(f"  t-stat                  : {pnl.mean()/(pnl.std(ddof=1)/np.sqrt(n)):+.2f}")
print(f"  win rate                :  {100*np.mean(pnl>0):.1f}%")
print(f"  releases per year       :  {n/16.1:.0f}")
print(f"  gross $/yr (1 contract) : ${PV*pnl.mean()*n/16.1:+,.0f}")

print("\n  --- the tape AT entry (second +1), which is what you must cross ---")
print(f"  median 1-sec high-low range : {np.median(sp):.2f} pts = ${PV*np.median(sp):.0f}")
print(f"  mean                        : {sp.mean():.2f} pts = ${PV*sp.mean():.0f}")

print("\n  --- BREAKEVEN: how much round-trip cost kills it? ---")
be = PV * pnl.mean()
print(f"  edge per release            : ${be:.2f}")
print(f"  GC commission (rt, ~$5)     : ${be-5:.2f} left")
for ticks in (1, 2, 3, 5):
    c = 5 + ticks * 10.0          # GC tick = 0.10 pt = $10
    print(f"  + {ticks} tick slippage (${ticks*10:.0f}) => ${be-c:+.2f} per release"
          f"{'   <-- DEAD' if be-c <= 0 else ''}")
