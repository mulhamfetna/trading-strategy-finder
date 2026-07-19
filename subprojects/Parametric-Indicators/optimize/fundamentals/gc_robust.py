import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from scipy import stats
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals.extended_data import load_1m_extended
from optimize.fundamentals.study_surprise import build_surprises
from optimize.fundamentals.study_pattern import paths_for

MEI = 0.15
sur = build_surprises(rc.load_calendar())
print("PRE-DECLARED MEI = 0.15 (the same bar the NQ battery used)\n")

# ---- 1. Both instruments, rank correlation at +5 min -------------------------------------
for inst in ("GC", "NQ"):
    df1 = load_1m_extended(inst)
    P, z, dates = paths_for(df1, sur)
    m = P[:, 4]
    s = stats.spearmanr(z, m)
    verdict = "CLEARS MEI" if abs(s[0]) >= MEI else "below MEI 0.15"
    print("===== %s  n=%d  +5min =====" % (inst, len(z)))
    print("  spearman = %+.3f  p=%.5f   %s" % (s[0], s[1], verdict))

# ---- 2. GC robustness --------------------------------------------------------------------
df1 = load_1m_extended("GC")
P, z, dates = paths_for(df1, sur)
m = P[:, 4]
d = pd.to_datetime(pd.Series(dates))

print("\n===== GC ROBUSTNESS: does it hold in BOTH halves? =====")
mid = d.median()
for lab, msk in (("first half  (2010-2018)", (d <= mid).values),
                 ("second half (2018-2026)", (d > mid).values)):
    s = stats.spearmanr(z[msk], m[msk])
    print("  %-24s n=%4d  spearman=%+.3f  p=%.4f" % (lab, msk.sum(), s[0], s[1]))

print("\n===== GC per-YEAR (is it one era, or persistent?) =====")
neg = 0
tot = 0
for y in sorted(d.dt.year.unique()):
    msk = (d.dt.year == y).values
    if msk.sum() < 25:
        continue
    s = stats.spearmanr(z[msk], m[msk])
    tot += 1
    neg += 1 if s[0] < 0 else 0
    print("  %d  n=%3d  spearman=%+.3f  p=%.3f%s"
          % (y, msk.sum(), s[0], s[1], "  <-- negative" if s[0] < 0 else ""))
print("  => negative in %d of %d years" % (neg, tot))

# ---- 3. Economic size: the NOISE CHECK ---------------------------------------------------
print("\n===== NOISE CHECK: is the effect big enough to trade? =====")
# Trade the anti-signal: short gold on a positive surprise, long on a negative one.
pnl = -np.sign(z) * m                      # points per release, +5min hold
print("  mean move captured : %+.3f points/release" % pnl.mean())
print("  std of that move   :  %.3f points  (the per-trade swing)" % pnl.std())
print("  t-stat             : %+.2f" % (pnl.mean() / (pnl.std() / np.sqrt(len(pnl)))))
print("  GC point value $100 => $%+.2f per release, swing +-$%.0f"
      % (100 * pnl.mean(), 100 * pnl.std()))
