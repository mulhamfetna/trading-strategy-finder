"""Isolated −1 business-day box shift for the 2024 window box (NQ_full_data_2024.csv).

Mirrors the FROZEN WS-AS.8 box-shift map exactly (`isolated_etf_box_shift.py`):
    new_Date = old_Date - 1 business day      (pandas BDay; weekends are the only holidays)
    Monday -> Friday(prev wk) · Tuesday -> Monday · Wednesday -> Tuesday
    Thursday -> Wednesday · Friday -> Thursday

Scope: ONLY the Parametric-Indicators 2024 box. The 2025/2026 boxes are NOT touched.
The original is backed up to NQ_full_data_2024.preshift.csv (reversible). Loud asserts
fail the run if the shift ever yields a weekend / a duplicate / a non-backward date
(NO silent fallback). Idempotency guard: refuses to run twice (a .shifted marker).

Usage:  python3 shift_2024_box.py            apply the shift (backup + overwrite)
        python3 shift_2024_box.py --revert    restore from the pre-shift backup
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

import config

_BOX = config.DATA_ROOT / "2024_data" / "NQ_full_data_2024.csv"
_BACKUP = config.DATA_ROOT / "2024_data" / "NQ_full_data_2024.preshift.csv"
_MARKER = config.DATA_ROOT / "2024_data" / ".box_shifted_minus1bday"


def revert() -> int:
    if not _BACKUP.exists():
        print(f"no backup at {_BACKUP} — nothing to revert"); return 1
    _BOX.write_bytes(_BACKUP.read_bytes())
    _MARKER.unlink(missing_ok=True)
    print(f"reverted {_BOX.name} from {_BACKUP.name}")
    return 0


def apply() -> int:
    if _MARKER.exists():
        print(f"REFUSING: {_MARKER.name} present — box already shifted. "
              f"Run with --revert first to re-apply."); return 1
    box = pd.read_csv(_BOX)
    old = pd.to_datetime(box["Date"]).dt.normalize()
    new = old - pd.offsets.BDay(1)
    # loud invariants (no silent fallback) — identical to the frozen WS-AS.8 script
    assert new.dt.dayofweek.max() <= 4, "shift produced a weekend date"
    assert not new.duplicated().any(), "shift produced duplicate dates (collision)"
    assert (new < old).all(), "some dates not moved backward"
    # backup the original first (reversible audit trail)
    _BACKUP.write_bytes(_BOX.read_bytes())
    box["Date"] = new.dt.strftime("%Y-%m-%d")
    box.to_csv(_BOX, index=False)
    _MARKER.write_text(f"box Date shifted -1 BDay; backup={_BACKUP.name}\n")
    print(f"shifted {len(box)} box rows -1 business day")
    print(f"  before: {old.min().date()} .. {old.max().date()}")
    print(f"  after:  {new.min().date()} .. {new.max().date()}")
    print(f"  backup: {_BACKUP}")
    print(f"  marker: {_MARKER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(revert() if "--revert" in sys.argv[1:] else apply())
