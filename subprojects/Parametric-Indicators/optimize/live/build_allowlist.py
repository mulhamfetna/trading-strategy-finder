"""#195 — derive the live allowlist from the committed round-2 evidence, exactly per the pre-registered
rule in docs/LIVE-ALLOWLIST-PREREGISTRATION.md. Deterministic; re-running must reproduce the JSON."""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PI = Path(__file__).resolve().parents[2]
D = PI / "optimize" / "fwd" / "data_r2"
PRE = {"NQ": "2026-05-19 19:59:00", "ES": "2026-05-19 19:59:00", "GC": "2026-07-02 19:59:00",
       "SI": "2026-07-02 19:59:00", "HG": "2026-07-07 19:59:00", "CL": "2026-07-08 19:59:00",
       "NG": "2026-07-08 19:59:00", "RTY": "2026-07-05 19:59:00", "YM": "2026-07-05 19:59:00"}
COST = 25.0


def slot_row(f: str) -> dict:
    slot = Path(f).stem[9:]
    tok = slot.split("_")[0]
    b = pd.read_csv(f)
    b["et"] = pd.to_datetime(pd.to_numeric(b["entry_time"]), unit="s")
    fr = b[b["et"] > pd.Timestamp(PRE[tok])]
    return dict(slot=slot, full_n=len(b), full_gross_per_trade=round(float(b["pnl"].mean()), 2),
                full_net25=round(float((b["pnl"] - COST).sum()), 2),
                fresh_n=len(fr), fresh_net25=round(float((fr["pnl"] - COST).sum()), 2))


def main() -> None:
    diag = json.load(open(D / "fwd_slot_diag.json"))
    rows = [slot_row(f) for f in sorted(glob.glob(str(D / "fwd_book_*.csv")))]
    for r in rows:
        dg = diag.get(r["slot"], {})
        r["entry_rate_lifetime"] = dg.get("entry_rate_lifetime")
        r["entry_rate_last60d"] = dg.get("entry_rate_last60d")
        r["rule"] = {"fresh_net25>0": r["fresh_net25"] > 0, "fresh_n>=10": r["fresh_n"] >= 10,
                     "gross>=2xfriction": r["full_gross_per_trade"] >= 2 * COST,
                     "full_net25>0": r["full_net25"] > 0,
                     "not_gate_dark": (r["entry_rate_lifetime"] or 0) >= 0.05 and (r["entry_rate_last60d"] or 0) >= 0.01}
        r["allowed"] = all(r["rule"].values())
    allowed = sorted(r["slot"] for r in rows if r["allowed"])
    rng = np.random.default_rng(195)
    fresh = {r["slot"]: r["fresh_net25"] for r in rows}
    draws = [round(float(sum(fresh[s] for s in rng.choice(list(fresh), size=len(allowed), replace=False))), 2)
             for _ in range(20)]
    real = round(float(sum(fresh[s] for s in allowed)), 2)
    out = {"preregistration": "docs/LIVE-ALLOWLIST-PREREGISTRATION.md", "issue": "#195",
           "evidence": "optimize/fwd/data_r2/ (round-2 books + slot diag)", "cost_rt": COST,
           "allowed": allowed, "n_allowed": len(allowed),
           "fresh_net25_allowed_total": real,
           "control": {"seed": 195, "draws": draws, "p95": round(float(np.percentile(draws, 95)), 2),
                       "beats_p95": bool(real > float(np.percentile(draws, 95)))},
           "per_slot": rows}
    p = PI / "optimize" / "live" / "live_allowlist.json"
    p.write_text(json.dumps(out, indent=1))
    h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    print(f"allowed {len(allowed)}: {allowed}")
    print(f"fresh net@25 total {real:,.2f} vs control p95 {out['control']['p95']:,.2f} beats={out['control']['beats_p95']}")
    print(f"sha256[:16] {h} -> {p}")


if __name__ == "__main__":
    main()
