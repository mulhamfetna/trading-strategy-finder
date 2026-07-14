"""Build a champions JSON (dashboard preset source) from the per-TF feasible-Pareto CSVs.

Each `optimize/results/<tf>_wsi_pareto.csv` is already sorted by median fold P/L (desc), so row 0 is
that timeframe's champion. We convert that row into the dashboard's champion schema:

    {tf: {"median_pnl": float, "full_pnl": float, "full_dd": float, "win": float,
          "box": {sl_soft, sl_hard, tp, gate_pct, dd_limit, cooldown, flip, k},
          "indicators": {<key>: {<param>: <typed value>, ...}, ...}}}

Indicator params come from the `<key>_<param>` columns, kept only for the enabled indicators (the
`indicators` cell, ';'-separated), and cast int/float per the library schema. Enables a faithful,
reproducible rebuild of the preset source from the pulled artifacts — no manual transcription.

Run:  python3 optimize/build_champions_from_pareto.py <out.json> [tf ...]
      (default TFs: 4h 2h 1h 15m 5m 2m — the wsh4 sweep set; 1m was excluded from that sweep)
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
from indicators import library  # noqa: E402
from optimize.report_wsi import _sig  # noqa: E402  — ONE definition of "how we persist a price param"

_RESULTS = _HERE / "results"
_DEFAULT_TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
_INSTRUMENT = os.environ.get("WSI_INSTRUMENT", "NQ")   # NQ (default) reads the bare pareto CSVs; ES → _ES
_SUF = "" if _INSTRUMENT == "NQ" else f"_{_INSTRUMENT}"

# per-indicator param name → caster (int/float), derived from the schema defaults
_CAST = {key: {p["name"]: type(p["default"]) for p in library.SCHEMA[key].get("params", [])}
         for key in library.REGISTRY}


def _num(s: str):
    """Parse a CSV numeric cell to float (blank → None)."""
    s = (s or "").strip()
    return None if s == "" else float(s)


def champion_for(tf: str) -> dict | None:
    csv_path = _RESULTS / f"{tf}_wsi_pareto{_SUF}.csv"
    if not csv_path.exists():
        print(f"  {tf}: no pareto CSV ({csv_path.name})", flush=True)
        return None
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print(f"  {tf}: empty pareto CSV", flush=True)
        return None
    r = rows[0]                                   # champion = top row (sorted by median P/L desc)
    enabled = [k for k in (r.get("indicators") or "").split(";") if k]
    inds: dict[str, dict] = {}
    for key in enabled:
        params = {}
        for pname, caster in _CAST.get(key, {}).items():
            v = _num(r.get(f"{key}_{pname}"))
            if v is not None:
                params[pname] = caster(v)          # int(...) or float(...) per schema
        inds[key] = params
    # Time caps. cap_mode is a STRING (none|bars|eod|both) — never route it through _num(), which coerces
    # to float. Legacy pareto CSVs have no cap_mode column ⇒ a non-zero cap_1min always meant a bars cap.
    _cap_n = int(_num(r.get("cap_1min")) or 0)
    _cap_mode = (r.get("cap_mode") or "").strip() or ("bars" if _cap_n > 0 else "none")
    box = dict(
        # ⚠️ SIGNIFICANT DIGITS, NEVER DECIMAL PLACES — and note this was the SECOND copy of that bug.
        # report_wsi wrote the pareto CSV with round(x, 4); this re-rounded the CSV back down to 4 dp, so
        # fixing report_wsi alone changed nothing. Price scales here span four orders of magnitude (Dow
        # $44,452, natural gas $3.57), so 4 dp leaves ONE significant digit on an NG stop of 0.0008 — a 1.1%
        # distortion that flipped NG 5m from +$38,079 to -$1,714 and had us blaming the optimizer for lying.
        # _sig is imported, not re-implemented, so a third copy cannot drift out of step with the other two.
        sl_soft=_sig(_num(r["sl_soft"])), sl_hard=_sig(_num(r["sl_hard"])),
        tp=_sig(_num(r["tp"])), gate_pct=_sig(_num(r["gate_pct"])),
        dd_limit=_sig(_num(r["dd_limit"])), cooldown=int(_num(r["cooldown"])),
        flip=str(r["flip"]).strip().lower() == "true", k=int(_num(r["k"])),
        # a bars count is meaningless unless the bars cap is armed — zero it so it cannot be misread
        cap_1min=(_cap_n if _cap_mode in ("bars", "both") else 0),
        cap_mode=_cap_mode,
    )
    return dict(median_pnl=_num(r["median_pnl"]), full_pnl=_num(r["full_pnl"]),
                full_dd=_num(r["full_dd"]), win=_num(r["win"]), box=box, indicators=inds)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__); return 2
    out_path = Path(sys.argv[1])
    tfs = sys.argv[2:] or _DEFAULT_TFS
    champs = {}
    for tf in tfs:
        c = champion_for(tf)
        if c:
            champs[tf] = c
            print(f"  {tf}: median ${c['median_pnl']:,.0f}  full ${c['full_pnl']:,.0f} "
                  f"DD {100*c['full_dd']/c['full_pnl']:.1f}%  +{len(c['indicators'])}ind", flush=True)
    out_path.write_text(json.dumps(champs, indent=1))
    print(f"wrote {out_path}  ({len(champs)} timeframes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
