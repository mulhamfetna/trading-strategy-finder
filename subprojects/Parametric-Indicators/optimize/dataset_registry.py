"""Tier 4 — dataset registry for reproducibility across the instruments × timeframes × windows matrix.

Records, per input file: absolute path, sha256(content), byte size, mtime. A run can stamp the registry of
the exact data it consumed so any result is traceable to a precise dataset version. Pure stdlib; no heavy
deps; safe to call anywhere.

  python3 optimize/dataset_registry.py NQ_1m.csv NQ_4h.csv --out optimize/results/dataset_registry.json
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def file_sha256(path, _buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_buf), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(path) -> dict:
    p = Path(path)
    st = p.stat()
    return {"path": str(p.resolve()), "sha256": file_sha256(p), "bytes": st.st_size, "mtime": int(st.st_mtime)}


def register(paths, out=None) -> dict:
    """Build {'datasets': [describe(p) …]}; write JSON to `out` if given. Returns the record."""
    rec = {"datasets": [describe(p) for p in paths]}
    if out:
        Path(out).write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    print(json.dumps(register(a.paths, a.out), indent=1))
