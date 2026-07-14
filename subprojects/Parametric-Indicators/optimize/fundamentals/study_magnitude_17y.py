"""THE DECIDING TEST — magnitude signal, year by year, on 17 years of data.

At n=117 (2024-2026) the magnitude signal was +0.19, p=0.027, SIGNIFICANT.
At n=871 (2010-2026) it is -0.018, p=0.347, NOTHING.

Two possible explanations, and they demand opposite actions:

  A) IT WAS NEVER REAL. The +0.19 was a small-sample artifact. With 871 events we now have ~100% power
     to detect r=0.19 — we looked properly and found nothing. DEAD. Accept it.

  B) IT IS A REGIME. The effect exists in recent years and not historically, so pooling 17 years dilutes
     it to zero. That is exactly what the DIRECTION signal did. Not a discovery — but not a refutation
     either, and it would mean the effect is real but unstable.

Year-by-year is the only way to tell them apart.

Also reports the true power: what is our chance of detecting r=0.19 at each sample size? That is the
number that decides whether a null MEANS anything.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from scipy import stats
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals.extended_data import load_1m_extended
from optimize.fundamentals.study_surprise import build_surprises
from optimize.fundamentals.study_pattern import paths_for

H = 30
R_CLAIMED = 0.19          # the effect we previously claimed at n=117


def power_for(r, n):
    if n <= 3 or r == 0:
        return 0.0
    zr = 0.5 * np.log((1 + abs(r)) / (1 - abs(r)))
    return float(stats.norm.sf(stats.norm.ppf(0.975) - zr * np.sqrt(n - 3)))


df1 = load_1m_extended("NQ")
sur = build_surprises(rc.load_calendar())
P, z, dates = paths_for(df1, sur, H)
yr = np.array([int(str(d)[:4]) for d in dates])
absz = np.abs(z)
mag = np.abs(P[:, 4])                       # |move| at +5 min — the headline measure

print(f"\n{len(z)} releases, {yr.min()}-{yr.max()}\n")
print("=" * 78)
print("THE POWER QUESTION FIRST — does our null MEAN anything now?")
print("=" * 78)
for n in (117, 400, 871):
    print(f"  power to detect r={R_CLAIMED} with n={n:>3}: {100*power_for(R_CLAIMED, n):>5.1f}%")
print()
print(f"  => At n=871 we would find r={R_CLAIMED} essentially every time. We found r=-0.018.")
print("     THIS NULL IS REAL EVIDENCE, not a blind spot. (Unlike the 12%-power null that I retracted.)")

print()
print("=" * 78)
print("YEAR BY YEAR — is it a REGIME (recent only) or was it NEVER REAL?")
print("=" * 78)
print(f"{'year':>6} {'n':>5} | {'corr':>8} | {'power@0.19':>11} | bar")
print("-" * 78)
rows = []
for y in range(yr.min(), yr.max() + 1):
    s = yr == y
    if s.sum() < 8:
        continue
    r = float(np.corrcoef(absz[s], mag[s])[0, 1])
    rows.append((y, int(s.sum()), r))
    bar = "#" * int(abs(r) * 60)
    sign = "+" if r >= 0 else "-"
    print(f"{y:>6} {int(s.sum()):>5} | {r:>+8.3f} | {100*power_for(R_CLAIMED, int(s.sum())):>10.0f}% | {sign}{bar}")

rs = np.array([r for _, _, r in rows])
pos = int((rs > 0).sum())
print()
print(f"  positive years: {pos}/{len(rs)}   mean r = {rs.mean():+.3f}   sd = {rs.std():.3f}")
print()

# The pooled estimate over the LONG history vs the RECENT window
recent = yr >= 2024
old = yr < 2024
r_recent = float(np.corrcoef(absz[recent], mag[recent])[0, 1])
r_old = float(np.corrcoef(absz[old], mag[old])[0, 1])
print("=" * 78)
print("RECENT vs HISTORICAL")
print("=" * 78)
print(f"  2024-2026 (what we tested before): n={int(recent.sum()):>3}  r = {r_recent:+.3f}  "
      f"power = {100*power_for(abs(r_recent), int(recent.sum())):.0f}%")
print(f"  2010-2023 (the new data):          n={int(old.sum()):>3}  r = {r_old:+.3f}  "
      f"power = {100*power_for(R_CLAIMED, int(old.sum())):.0f}% to see 0.19")
print()
if abs(r_old) < 0.05 and r_recent > 0.10:
    print("  => The effect is present ONLY in the recent window, and ABSENT across 14 years where we")
    print("     have overwhelming power to see it. That is a REGIME at best — and far more likely a")
    print("     SMALL-SAMPLE ARTIFACT, because a 3-year window is exactly where flukes live.")
elif pos >= 0.7 * len(rs):
    print("  => Positive in most years — worth another look.")
else:
    print("  => No consistent sign across years. The signal was never there.")
