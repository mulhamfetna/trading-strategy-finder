"""Fix the stale 6-instrument lists inside the bundle (backtest.py docstring + data/README.txt).
The bundle now ships 9 markets; both places still claimed {NQ,ES,GC,SI,RTY,YM}."""
import os
from pathlib import Path

B = Path(os.path.expanduser("~/Mulham/wsg-i/playbooks_backtester"))
NEW = "NQ,ES,GC,SI,HG,CL,NG,RTY,YM"

edits = [
    (B / "backtest.py", "INST ∈ {NQ,ES,GC,SI,RTY,YM}", f"INST ∈ {{{NEW}}}"),
    (B / "data" / "README.txt", "INST in {NQ,ES,GC,SI,RTY,YM}", f"INST in {{{NEW}}}"),
]

for path, old, new in edits:
    s = path.read_text()
    if new in s:
        print(f"{path.name}: already patched")
    elif old in s:
        path.write_text(s.replace(old, new))
        print(f"{path.name}: patched -> {NEW}")
    else:
        print(f"{path.name}: PATTERN NOT FOUND (manual check needed)")
