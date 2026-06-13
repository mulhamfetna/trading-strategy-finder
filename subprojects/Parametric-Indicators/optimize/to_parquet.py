"""Tier 4 — convert input CSVs to Parquet siblings (<csv>.parquet).

Each sibling is written from the EXACT post-load CSV frame (`loader.load_data` with parquet-read disabled),
so loading with WSH_USE_PARQUET=1 returns a byte-identical DataFrame — same float64, same datetime64 — just
faster to read and smaller on disk. Opt-in: nothing reads parquet unless WSH_USE_PARQUET is set.

  python3 optimize/to_parquet.py Full_Canldes_Data/<RAW_DIR>/NQ_1m.csv  data/full_data/NQ_full_data.csv ...
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


def convert(csv_path: str) -> Path:
    os.environ.pop("WSH_USE_PARQUET", None)   # force the CSV path while building the sibling
    from loader import load_data
    df = load_data(str(csv_path))
    out = Path(str(csv_path) + ".parquet")
    df.to_parquet(out, index=False)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("csvs", nargs="+")
    for c in ap.parse_args().csvs:
        print("wrote", convert(c))
