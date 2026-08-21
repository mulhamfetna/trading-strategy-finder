"""WS-FWD Phase 0 (#176) — data-currency audit.

The deployed champions' books end mid-May 2026; the owner says the tape now reaches August.
Before ANY forward run, this prints — per instrument, through the repo's OWN path resolver
(optimize.instruments.resolve_paths, so we audit exactly what the engine would load) — the
first/last timestamp of the 1-minute frame, each decision-TF frame, and the box CSV.
No verdicts here; this is the census the runs stand on (verify-don't-assume).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PI = HERE.parents[2]                      # subprojects/Parametric-Indicators
sys.path.insert(0, str(PI))

from optimize import instruments as INST          # noqa: E402
from optimize import timeframes as TF             # noqa: E402

TFS = ("4h", "2h", "1h", "15m", "5m", "2m")


def _first_last(path: str) -> tuple[str, str, int]:
    """(first_line, last_line, approx_bytes) without loading the file."""
    p = Path(path)
    if not p.exists():
        return ("<MISSING>", "<MISSING>", 0)
    size = p.stat().st_size
    with open(p, "rb") as f:
        f.readline()                              # header
        first = f.readline().decode(errors="replace").strip()
        back = min(size, 4096)
        f.seek(size - back)
        tail = f.read().decode(errors="replace").strip().splitlines()
        last = tail[-1] if tail else "<EMPTY>"
    return (first, last, size)


def main() -> None:
    print(f"# WS-FWD phase 0 data audit — roots: WSH_DATA_BASE={os.environ.get('WSH_DATA_BASE')!r} "
          f"WSG_DATA_ROOT={os.environ.get('WSG_DATA_ROOT')!r}")
    for tok in INST.TOKENS:
        print(f"\n== {tok} ==")
        try:
            dec4, minute, box = INST.resolve_paths(tok, "4h")
        except Exception as e:  # noqa: BLE001 — audit must report, not die
            print(f"  RESOLVE FAILED: {type(e).__name__}: {e}")
            continue
        f, l, sz = _first_last(minute)
        print(f"  1m    {minute}\n        first={f[:64]}  last={l[:64]}  ({sz/1e6:.1f} MB)")
        for tf in TFS:
            dec, _, _ = INST.resolve_paths(tok, tf)
            f, l, sz = _first_last(dec)
            print(f"  {tf:<4}  last={l[:64]}  ({sz/1e6:.1f} MB)")
        f, l, sz = _first_last(box)
        print(f"  box   {box}\n        first={f[:64]}  last={l[:64]}  ({sz/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
