"""#7 · D3 — THE CONDITIONAL TAIL (McNeil-Frey): how big is a 1-minute tail move GIVEN the regime?

D2 measured the tail SHAPE (alpha~3, heavier overnight) but shape is scale-free — it does not tell you how
many POINTS a stop must clear. D3 gives the magnitude, conditioned on the current volatility state, via the
McNeil-Frey pipeline:

  1. filter volatility with an EWMA/RiskMetrics conditional variance (a McNeil-Frey variant — a special
     case of the GARCH family; full GARCH MLE on 5.3M 1-min points is impractical and the de-clustering
     mechanism is identical). CAUSAL: sigma[t] uses only returns up to t-1.
  2. standardize: z[t] = r[t] / sigma[t]. The residuals z are approximately i.i.d. but (per the research)
     STILL fat-tailed — so we fit the tail to THEM, not to raw returns.
  3. the ABSOLUTE conditional tail move at bar t = z_q * sigma[t] * price[t]  (in points), for the fitted
     deep quantile z_q. Report it by regime (quiet/normal/loud/event) and by session, and flag where a
     single 1-min move can blow THROUGH the 40-pt stop.

  WSH_DATA_BASE=/home/dev/Mulham python3 -u optimize/fundamentals/study_conditional_tail.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals.extended_data import load_1m_extended    # noqa: E402
from scipy import stats                                             # noqa: E402

LAM = 0.97          # EWMA decay for 1-min conditional variance (slower than daily RiskMetrics 0.94)
STOP = 40.0         # the champion hard stop, in points


def main() -> int:
    df = load_1m_extended("NQ")
    d = df["Date"].to_numpy(); close = df["Close"].to_numpy(float)
    dt_s = np.diff(d).astype("timedelta64[s]").astype(np.int64)
    r = np.full(len(close), np.nan)
    r[1:] = np.log(close[1:] / close[:-1])
    r[1:][dt_s != 60] = np.nan                                       # gap-clean

    # ---- EWMA conditional variance, CAUSAL (predict sigma[t] from returns up to t-1) ----------------
    r2 = pd.Series(np.where(np.isfinite(r), r, np.nan) ** 2)
    cvar = r2.ewm(alpha=1 - LAM, adjust=False, min_periods=50).mean().shift(1).to_numpy()
    sigma = np.sqrt(cvar)                                            # conditional sd (return units), causal
    ok = np.isfinite(r) & np.isfinite(sigma) & (sigma > 0)
    z = np.full(len(r), np.nan)
    z[ok] = r[ok] / sigma[ok]

    zz = z[np.isfinite(z)]
    print(f"\nNQ 17y · EWMA(lambda={LAM}) conditional-vol filter · {len(zz):,} standardized residuals")
    print(f"  raw returns excess-kurtosis {stats.kurtosis(r[np.isfinite(r)]):+.1f}  ->  "
          f"standardized residuals excess-kurtosis {stats.kurtosis(zz):+.1f}")
    print(f"  (de-clustering removes MUCH of the fat tail, but the residual is STILL fat — as the research")
    print(f"   predicted: volatility clustering explains part, not all, of the tail.)")

    # ---- residual tail: GPD + empirical deep quantiles ---------------------------------------------
    print("\n" + "=" * 92)
    print("RESIDUAL TAIL — GPD on |z| (both sides) + the deep quantiles used to scale the tail move")
    print("=" * 92)
    az = np.abs(zz)
    for thr in (99.0, 99.5):
        u = np.percentile(az, thr); exc = az[az > u] - u
        xi, _, beta = stats.genpareto.fit(exc, floc=0)
        print(f"  GPD @ {thr}%:  xi={xi:+.3f} ({'heavy' if xi>0.05 else 'light'})  beta={beta:.3f}  n_exc={len(exc)}")
    zq = {q: float(np.percentile(az, q)) for q in (99.0, 99.9, 99.99)}
    print(f"  |z| quantiles:  99%={zq[99.0]:.2f}  99.9%={zq[99.9]:.2f}  99.99%={zq[99.99]:.2f}  "
          f"(a Gaussian would be 2.58 / 3.29 / 3.89)")

    # ---- ABSOLUTE conditional tail move, in POINTS, by regime --------------------------------------
    sig_pts = sigma * close                                          # 1-sd 1-min move in points, per bar
    sp = sig_pts[ok]
    hh = (pd.DatetimeIndex(df["Date"]).hour + pd.DatetimeIndex(df["Date"]).minute / 60.0).to_numpy()[ok]
    print("\n" + "=" * 92)
    print("ABSOLUTE 1-MINUTE TAIL MOVE BY REGIME (points) — z_q x sigma_pts, and vs the 40-pt stop")
    print("=" * 92)
    print(f"  {'regime (vol pctile)':<26} {'1sd(pts)':>9} {'99% move':>9} {'99.9% move':>11} {'99.99%':>8}")
    for name, pct in (("quiet (10th)", 10), ("normal (50th)", 50), ("loud (90th)", 90),
                      ("very loud (99th)", 99), ("extreme (99.9th)", 99.9)):
        s = np.percentile(sp, pct)
        print(f"  {name:<26} {s:>9.1f} {zq[99.0]*s:>9.1f} {zq[99.9]*s:>10.1f} {zq[99.99]*s:>8.1f}"
              + ("   <= a single 1-min move can BLOW THROUGH the 40-pt stop" if zq[99.9]*s > STOP else ""))

    # ---- by session -------------------------------------------------------------------------------
    print("\n" + "=" * 92)
    print("BY SESSION — the 99.9% conditional 1-min move (points); blow-through fraction vs 40-pt stop")
    print("=" * 92)
    rth = (hh >= 9.5) & (hh < 16); onh = (hh >= 18) | (hh < 2)
    for nm, m in (("RTH (loud)", rth), ("OVERNIGHT (quiet)", onh), ("ALL", np.ones(len(sp), bool))):
        s = sp[m]
        move999 = zq[99.9] * s
        med = np.median(move999); p90 = np.percentile(move999, 90)
        frac = np.mean(move999 > STOP)
        print(f"  {nm:<20} median 99.9% move {med:>6.1f} pts   90th {p90:>6.1f} pts   "
              f"blow-through {100*frac:>4.1f}% of bars")

    print("\n" + "=" * 92)
    print("READ")
    print("=" * 92)
    print("  This is the number a stop must respect: in a QUIET regime a 40-pt stop is many sigma away")
    print("  (safe); in a LOUD/EVENT regime a single 1-min move can exceed it (blow-through). The stop's")
    print("  real safety is CONDITIONAL on the vol state — so stop distance / size should scale with the")
    print("  EWMA sigma (and the A2 event-volatility burst). Next: D4 = turn this into a concrete")
    print("  vol-scaled stop-distance / sizing rule (the Kelly half still needs its own research).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
