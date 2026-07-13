"""IS THE MAGNITUDE SIGNAL A REGIME, LIKE THE DIRECTION SIGNAL WAS?

The direction signal ("good news is bad news") was strong in 2025 (-0.43) and GONE in 2026. It was a
property of the Fed's stance, not a law of markets. That is the single most instructive failure of this
whole project.

The magnitude signal grew from +0.11 (52 events) to +0.22 (94 events) when 2024 was added. A STABLE
effect should have a STABLE correlation as you add data — the p-value sharpens, but r stays put. r
GROWING is a warning sign: it can mean 2024 simply had a stronger effect, i.e. we are looking at a
regime again.

So: compute r YEAR BY YEAR. If it is stable across 2024/2025/2026, it is an effect. If it lives in one
year, it is a regime and it will die exactly like the last one did.
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

measures = {
    "|move| +5m": np.abs(P[:, 4]),
    "|move| +30m": np.abs(P[:, H - 1]),
    "path RANGE": P.max(axis=1) - P.min(axis=1),
    "path VOL": P.std(axis=1),
}

print("\nIS IT AN EFFECT, OR A REGIME? — correlation of |surprise| with move size, YEAR BY YEAR")
print("(the direction signal lived ONLY in 2025 and died in 2026. Does this one do the same?)\n")
print(f"{'measure':<14} | " + " | ".join(f"{y:>16}" for y in [2024, 2025, 2026]) + " | verdict")
print("-" * 88)

for name, m in measures.items():
    cells, rs = [], []
    for y in (2024, 2025, 2026):
        s = yr == y
        if s.sum() < 10:
            cells.append(f"{'n<10':>16}")
            rs.append(np.nan)
            continue
        r = float(np.corrcoef(absz[s], m[s])[0, 1])
        rs.append(r)
        cells.append(f"{r:>+7.3f} (n={int(s.sum()):>2}) ")
    ok = [r for r in rs if not np.isnan(r)]
    same_sign = all(np.sign(r) == np.sign(ok[0]) for r in ok)
    if same_sign and min(abs(np.array(ok))) > 0.08:
        v = "STABLE — present every year"
    elif same_sign:
        v = "same sign, one year weak"
    else:
        v = "!! SIGN FLIPS — regime, like the last one"
    print(f"{name:<14} | " + " | ".join(cells) + f" | {v}")

print()
n_by_year = {y: int((yr == y).sum()) for y in (2024, 2025, 2026)}
print(f"  events per year: {n_by_year}")
print(f"  power to see r=0.22 with n=42 (2024): {100*power_for(0.22, 42):.0f}%")
print(f"  power to see r=0.22 with n=52 (2025): {100*power_for(0.22, 52):.0f}%")
print(f"  power to see r=0.22 with n=23 (2026): {100*power_for(0.22, 23):.0f}%")
print()
print("  ⚠ Each individual YEAR is far too small to be significant on its own. What we are reading")
print("    here is the SIGN and the rough SIZE — not significance. A sign that holds in all three")
print("    years is meaningful; a sign that flips is fatal, and it is exactly what killed direction.")
