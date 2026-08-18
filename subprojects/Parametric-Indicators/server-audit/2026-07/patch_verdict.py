"""Verdict engine: flag 'technically positive but negligible' out-of-sample results.

A slot like CL 5m earned +$42 out-of-sample while exposing you to a $717 drawdown. The old rule only
flagged op < 0, so +$42 read as 'holds up out-of-sample' — misleading. New rule: if the out-of-sample
profit is smaller than 10% of the worst drawdown, it is noise, not edge → CAUTION with a plain reason.
"""
import os

p = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators/build_playbooks.py")
s = open(p).read()

old = """    if op is not None and op < 0:
        reasons.append(f"loses money out-of-sample in 2026 ({money(op)})")
"""
new = """    if op is not None and op < 0:
        reasons.append(f"loses money out-of-sample in 2026 ({money(op)})")
    elif op is not None and fdd and 0 <= op < 0.10 * fdd:
        # technically positive, but the 2026 profit is dwarfed by the drawdown you must sit through:
        # that is noise, not a tradeable edge. Say so rather than calling it "holds up".
        reasons.append(f"essentially flat out-of-sample in 2026 ({money(op)} against a "
                       f"${fdd:,.0f} drawdown) — no demonstrated edge on unseen data")
"""

if "essentially flat out-of-sample" in s:
    print("already patched")
else:
    assert old in s, "verdict OOS block not found"
    open(p, "w").write(s.replace(old, new, 1))
    print("verdict engine patched -> negligible-OOS now flagged as CAUTION")
