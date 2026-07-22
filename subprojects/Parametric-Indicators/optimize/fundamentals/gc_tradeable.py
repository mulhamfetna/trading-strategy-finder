import sys
sys.path.insert(0, ".")
import numpy as np
from scipy import stats
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals.extended_data import load_1m_extended
from optimize.fundamentals.study_surprise import build_surprises
from optimize.fundamentals.study_pattern import paths_for

sur = build_surprises(rc.load_calendar())
df1 = load_1m_extended("GC")
P, z, dates = paths_for(df1, sur)

# P[:, k] = cumulative move from close[T-1] to minute k of the post-release path.
# P[:,0] is the RELEASE BAR itself — the instantaneous jump, which we CANNOT trade:
# we only learn the number at T, so we cannot be positioned for the jump that prints at T.
jump = P[:, 0]
print("=" * 78)
print("SPLITTING THE EFFECT: un-tradeable jump vs tradeable drift")
print("=" * 78)

s = stats.spearmanr(z, P[:, 4])
print("\n  FULL move  close[T-1] -> T+5   spearman=%+.3f p=%.5f   <- what we measured" % (s[0], s[1]))
s = stats.spearmanr(z, jump)
print("  JUMP ONLY  close[T-1] -> T+0   spearman=%+.3f p=%.5f   <- CANNOT be traded" % (s[0], s[1]))

print("\n  --- what is left AFTER the print, entering at the close of the release bar ---")
for k, lab in ((1, "T+0 -> T+1"), (4, "T+0 -> T+5"), (9, "T+0 -> T+10"),
               (14, "T+0 -> T+15"), (29, "T+0 -> T+30")):
    drift = P[:, k] - jump
    s = stats.spearmanr(z, drift)
    pnl = -np.sign(z) * drift
    t = pnl.mean() / (pnl.std() / np.sqrt(len(pnl)))
    print("  %-12s spearman=%+.3f p=%.4f | anti-signal PnL %+.3f pts ($%+7.2f) t=%+.2f"
          % (lab, s[0], s[1], pnl.mean(), 100 * pnl.mean(), t))

print("\n  --- for reference: the un-tradeable jump traded perfectly ---")
pnl = -np.sign(z) * jump
print("  jump PnL  %+.3f pts ($%+.2f/release) t=%+.2f"
      % (pnl.mean(), 100 * pnl.mean(), pnl.mean() / (pnl.std() / np.sqrt(len(pnl)))))
