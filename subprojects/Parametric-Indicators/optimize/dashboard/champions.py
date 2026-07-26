"""Champion leaderboard source for the Reporting panel (#22).

Reads the deployed champion set — optimize/results/best_champions_full{_INST}.json, one file per
instrument, keyed by timeframe → {median_pnl, full_pnl, full_dd, win, box, indicators}. Flattens to one
row per (instrument, tf) for the leaderboard, newest metrics as stored (LOCAL is the source of truth).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_RESULTS = Path(__file__).resolve().parent.parent.parent / "optimize" / "results"


def _instrument_of(name: str) -> str:
    m = re.match(r"best_champions_full(?:_(\w+))?\.json$", name)
    return (m.group(1) if m and m.group(1) else "NQ")


def load_all(results_dir: Path | None = None) -> list[dict]:
    base = Path(results_dir) if results_dir else _RESULTS
    rows = []
    for path in sorted(base.glob("best_champions_full*.json")):
        inst = _instrument_of(path.name)
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for tf, c in data.items():
            if not isinstance(c, dict):
                continue
            inds = c.get("indicators", {}) or {}
            rows.append({
                "instrument": inst, "tf": tf,
                "pnl": c.get("full_pnl"), "dd": c.get("full_dd"),
                "median_pnl": c.get("median_pnl"), "win": c.get("win"),
                "n_indicators": len(inds),
                "indicators": sorted(inds.keys()),
                "box": c.get("box", {}),
                "deployed": True,          # best_champions_full = the current deployed set
            })
    rows.sort(key=lambda r: (r["pnl"] if r["pnl"] is not None else -1e18), reverse=True)
    return rows


def leaderboard() -> dict:
    rows = load_all()
    return {"ok": True, "count": len(rows),
            "instruments": sorted({r["instrument"] for r in rows}),
            "champions": rows}
