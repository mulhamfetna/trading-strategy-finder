"""THE GATE: does the MAGNITUDE signal survive out-of-sample?

The direction signal looked real in-sample (corr -0.43, p=0.021, a perfect economic story) and
EVAPORATED out of sample. It was a Fed regime, not an edge. That is the trap this project exists to
avoid, and it caught me once already today.

So the magnitude signal gets the SAME gate, pre-declared:

  Fit the relationship on 2024 + 2025. Apply it, UNCHANGED, to 2026.
  If the sign flips or the correlation collapses, it is dead. No re-slicing, no horizon shopping.

Also reported: the POWER at each stage — because a null on 20 OOS events means nothing, and I am not
going to make that mistake twice.
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

measures = {
    "|move| at +5m": np.abs(P[:, 4]),
    "|move| at +30m": np.abs(P[:, H - 1]),
    "path RANGE": P.max(axis=1) - P.min(axis=1),
    "path VOL (std)": P.std(axis=1),
}

print(f"\n{len(z)} releases  ·  years {sorted(set(yr))}")
print(f"  2024: {(yr==2024).sum()}   2025: {(yr==2025).sum()}   2026: {(yr==2026).sum()}\n")

IS = yr <= 2025          # fit here
OOS = yr == 2026         # test here, untouched

print("=" * 92)
print("OUT-OF-SAMPLE GATE — fit on 2024+2025, apply UNCHANGED to 2026")
print("=" * 92)
print(f"{'measure':<16} | {'IS corr':>8} {'IS p':>7} {'IS pow':>7} | "
      f"{'OOS corr':>9} {'OOS p':>7} {'OOS pow':>8} | {'HOLDS?':>7}")
print("-" * 92)

rng = np.random.default_rng(0)
for name, m in measures.items():
    a_, m_a = np.abs(z[IS]), m[IS]
    b_, m_b = np.abs(z[OOS]), m[OOS]
    if len(b_) < 8:
        print(f"{name:<16} | too few OOS events ({len(b_)})")
        continue
    ci = float(np.corrcoef(a_, m_a)[0, 1])
    co = float(np.corrcoef(b_, m_b)[0, 1])
    pi = float((np.array([abs(np.corrcoef(rng.permutation(a_), m_a)[0, 1]) for _ in range(2000)])
                >= abs(ci)).mean())
    po = float((np.array([abs(np.corrcoef(rng.permutation(b_), m_b)[0, 1]) for _ in range(2000)])
                >= abs(co)).mean())
    holds = "YES" if (np.sign(ci) == np.sign(co) and abs(co) > 0.5 * abs(ci)) else "no"
    print(f"{name:<16} | {ci:>+8.3f} {pi:>7.3f} {100*power_for(ci,int(IS.sum())):>6.0f}% | "
          f"{co:>+9.3f} {po:>7.3f} {100*power_for(co,int(OOS.sum())):>7.0f}% | {holds:>7}")

print()
print("  'HOLDS?' = the 2026 correlation kept the SAME SIGN and retained at least HALF the strength.")
print()
print("  ⚠ OOS power is LOW by construction (few 2026 events). A weak OOS result is therefore NOT")
print("    strong evidence against — but a SIGN FLIP would be, and that is what killed the direction")
print("    signal. Read the sign first, the magnitude second, the p-value last.")
