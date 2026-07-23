"""The daily (D*) box zones that box_lookup.py discards at load time.

Mirrors box_lookup._WEEKLY_LEVELS exactly, tier letter swapped W -> D. Note the sub-zone column ORDER is
asymmetric in the weekly list and is reproduced verbatim: the TH sub-zone is ('*TH2', '*TH1') while the TL
sub-zone is ('*TL1', '*TL2').
"""
from __future__ import annotations

from typing import List, Tuple

# (upper_col, lower_col, label) — same shape as box_lookup._WEEKLY_LEVELS
DAILY_LEVELS: List[Tuple[str, str, str]] = [
    ('DTHU', 'DTHD', 'D-TH'),
    ('DTH2', 'DTH1', 'D-TH sub'),
    ('DRHU', 'DRHD', 'D-RH'),
    ('DIHU', 'DIHD', 'D-IH'),
    ('DILU', 'DILD', 'D-IL'),
    ('DRLU', 'DRLD', 'D-RL'),
    ('DTLU', 'DTLD', 'D-TL'),
    ('DTL1', 'DTL2', 'D-TL sub'),
]
