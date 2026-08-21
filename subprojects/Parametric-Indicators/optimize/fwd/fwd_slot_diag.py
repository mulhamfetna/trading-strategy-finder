"""WS-FWD Phase 4 support (#176) — per-slot WHY diagnostics.

For every `best` slot: the dropped-signal mix (veto vs vol-gate) lifetime and over the final
60 days of the book, entry/exit-reason mix, the last entry date vs data end (darkness), and
the gate-share drift — the raw material for the owner's why-positive/why-negative report.
Runs on the warm L1 cache (fast); output one JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
PI = HERE.parents[2]
sys.path.insert(0, str(PI))

TFS = ("4h", "2h", "1h", "15m", "5m", "2m")
TOKENS = ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM")


def diag(tok: str, tf: str) -> dict:
    from optimize.l2 import payload as P
    champs = json.loads(P._instrument_champions_path(tok, "best").read_text())
    if tf not in champs:
        return {"status": "no_champion"}
    l1p = P._champion_layer_params(tf, champs[tf])
    l1 = P.run_l1_cached(tf, params=l1p, instrument=tok)
    led = pd.DataFrame(l1.ledger)
    drops = pd.DataFrame(l1.dropped_signals)
    data_end = pd.Timestamp(l1.df_dec["Date"].iloc[-1])
    out = {"status": "ok", "gate_pct": l1p.get("gate_pct"), "k": l1p.get("k"),
           "dd_limit": l1p.get("dd_limit"), "cap_mode": l1p.get("cap_mode"),
           "n_indicators": len(l1p.get("indicators") or []), "data_end": str(data_end)}
    if len(led):
        led["entry_time"] = pd.to_datetime(led["entry_time"])
        last_entry = led["entry_time"].max()
        out["last_entry"] = str(last_entry)
        out["idle_days_at_end"] = int((data_end - last_entry).days)
        out["exit_reasons"] = Counter(led["exit_reason"]).most_common()
        out["n_entries"] = len(led)
    if len(drops):
        drops["ts"] = pd.to_datetime(drops["ts"])
        out["drops_lifetime"] = Counter(drops["reason"]).most_common()
        t60 = data_end - pd.Timedelta(days=60)
        d60 = drops[drops["ts"] > t60]
        e60 = int((led["entry_time"] > t60).sum()) if len(led) else 0
        out["last60d"] = {"entries": e60, "drops": Counter(d60["reason"]).most_common()}
        tot_life = len(drops) + out.get("n_entries", 0)
        tot_60 = len(d60) + e60
        out["entry_rate_lifetime"] = round(out.get("n_entries", 0) / tot_life, 4) if tot_life else None
        out["entry_rate_last60d"] = round(e60 / tot_60, 4) if tot_60 else None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    res = {}
    for tok in TOKENS:
        for tf in TFS:
            key = f"{tok}_{tf}"
            try:
                res[key] = diag(tok, tf)
            except Exception as e:  # noqa: BLE001
                res[key] = {"status": f"ERROR: {type(e).__name__}: {e}"}
            print(key, res[key].get("status"), res[key].get("entry_rate_lifetime"),
                  res[key].get("entry_rate_last60d"), res[key].get("idle_days_at_end"), flush=True)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print(f"DIAG DONE -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
