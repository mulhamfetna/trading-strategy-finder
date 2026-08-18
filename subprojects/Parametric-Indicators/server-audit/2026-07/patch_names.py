"""Add HG/CL/NG to the playbook builder's NAMES map (they were falling back to the bare ticker)."""
import os

p = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators/build_playbooks.py")
s = open(p).read()

old = ('NAMES = {"NQ": "Nasdaq-100 (NQ)", "ES": "S&P 500 (ES)", "GC": "Gold (GC)",\n'
       '         "SI": "Silver (SI)", "RTY": "Russell 2000 (RTY)", "YM": "Dow (YM)"}')
new = ('NAMES = {"NQ": "Nasdaq-100 (NQ)", "ES": "S&P 500 (ES)", "GC": "Gold (GC)",\n'
       '         "SI": "Silver (SI)", "RTY": "Russell 2000 (RTY)", "YM": "Dow (YM)",\n'
       '         "HG": "Copper (HG)", "CL": "Crude Oil (CL)", "NG": "Natural Gas (NG)"}')

if new in s:
    print("already patched")
else:
    assert old in s, "NAMES block not found"
    open(p, "w").write(s.replace(old, new))
    print("NAMES patched -> HG / CL / NG added")
