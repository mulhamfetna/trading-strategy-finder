"""How much statistical power do we actually have with 52 releases?

The pattern study returned null on magnitude, shape and persistence. Before calling that a NEGATIVE
result, we must ask: COULD we have detected a real effect of that size, if one existed?

If the answer is "no", then the null is not evidence of absence — it is evidence of a study too small
to see anything, and the correct action is to GET MORE DATA, not to abandon the idea.
"""
import numpy as np
from scipy import stats

ALPHA = 0.05
zc = stats.norm.ppf(1 - ALPHA / 2)          # 1.96


def power_for(r, n):
    """Power to detect a correlation r with n observations (Fisher z)."""
    if n <= 3:
        return 0.0
    zr = 0.5 * np.log((1 + r) / (1 - r))
    se = 1 / np.sqrt(n - 3)
    return float(stats.norm.sf(zc - abs(zr) / se))


def n_for(r, power=0.80):
    """Observations needed to detect r with the given power."""
    zr = 0.5 * np.log((1 + r) / (1 - r))
    zb = stats.norm.ppf(power)
    return int(np.ceil(((zc + zb) / abs(zr)) ** 2 + 3))


N_NOW = 52
print("POWER ANALYSIS — can 52 releases see anything at all?\n")
print(f"{'true effect r':>14} | {'power we HAVE':>14} | {'n needed for 80%':>17} | {'we have':>9}")
print("-" * 66)
for r in [0.05, 0.10, 0.11, 0.15, 0.20, 0.30, 0.40]:
    p = power_for(r, N_NOW)
    need = n_for(r)
    print(f"{r:>14.2f} | {100*p:>13.0f}% | {need:>17,} | {100*N_NOW/need:>8.0f}%")

print()
print("The magnitude effect we OBSERVED was r = +0.105 to +0.121 (consistently positive, 4/4 measures).")
r_obs = 0.11
print(f"  power to detect r = {r_obs} with n = {N_NOW}:  {100*power_for(r_obs, N_NOW):.0f}%")
print(f"  releases needed for 80% power:            {n_for(r_obs):,}")
print(f"  releases we have:                         {N_NOW}")
print()
print(f"  => Even if the effect is REAL at r = {r_obs}, we would fail to detect it "
      f"{100*(1-power_for(r_obs, N_NOW)):.0f}% of the time.")
print()
print("HOW MANY EVENTS COULD WE GET?")
print("-" * 66)
print("  The calendar is NOT the constraint — FRED has decades of releases.")
print("  Our PRICE DATA is: 2025-01-01 -> 2026-05-19 (~16.5 months).")
print()
yrs_now = 1.38
per_year = 52 / yrs_now
for yrs, label in [(1.38, "what we have now"), (5, "5 years of 1-min price data"),
                   (10, "10 years"), (17, "back to 2009")]:
    n = int(per_year * yrs)
    print(f"  {label:<32} ~{n:>4} releases   power at r=0.11: {100*power_for(0.11, n):>3.0f}%")
print()
print("  Adding TWO-STAR events (the user's own original plan) would roughly DOUBLE the rate again.")
