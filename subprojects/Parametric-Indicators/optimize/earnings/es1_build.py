#!/usr/bin/env python3
"""E-S1 — the earnings event-state dataset. Implements docs/ES1-DATASET-SPEC.md (frozen).

FU-9's builder reused (stance machinery + repaint falsifier + bracket outcomes) over the
earnings calendar; power context recomputed by E-P1's machinery and parity-anchored to the
committed ep1_events files (C1).

    WSH_16Y_ROOT=... python3 optimize/earnings/es1_build.py --instrument NQ \
        --bars-1s ~/Mulham/data_2010_1s/NQ_Continuous_Data/NQ_1s.csv
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PI_ROOT = HERE.parents[1]
FUND = PI_ROOT / "optimize" / "fundamentals"
REPO = PI_ROOT.parents[1]
for p_ in (str(PI_ROOT), str(FUND), str(REPO)):
    sys.path.insert(0, p_)

import p2_power_model as p2                                        # noqa: E402
from extended_data import load_1m_extended                         # noqa: E402
from indicators.library import REGISTRY, build                     # noqa: E402
from indicators.base import IndicatorConfig                        # noqa: E402
from optimize.fundamentals.fu9_build import (stance_rows, c2_causality,  # noqa: E402
                                             ride_outcomes)

TABLE = HERE / "data" / "earnings_timestamps_FINAL_16y.csv"


def event_table(df1: pd.DataFrame) -> pd.DataFrame:
    d = pd.read_csv(TABLE, usecols=["ticker", "event_et", "session"])
    d["event_et"] = pd.to_datetime(d.event_et)
    d = d.sort_values("event_et").reset_index(drop=True)
    rm = p2.realized_moves(df1, pd.DatetimeIndex(d.event_et))
    ev = pd.concat([d, rm.reset_index(drop=True)], axis=1)
    ev = ev.dropna(subset=["jump_pct"]).sort_values("event_et").reset_index(drop=True)
    ev["pred"] = p2.build_predictions(ev, ev.ticker, trailing=0)
    return ev.rename(columns={"event_et": "et", "ticker": "title"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=["NQ", "ES"])
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()
    inst = a.instrument
    t0 = time.time()
    print(f"[E-S1] build {inst} · spec docs/ES1-DATASET-SPEC.md (FU-9 conventions)",
          flush=True)
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    ev = event_table(df1)
    print(f"[E-S1] events with a bar: {len(ev)} · scored (pred): "
          f"{ev.pred.notna().sum()}", flush=True)

    # C1 — parity vs the committed E-P1 evidence
    ref = pd.read_csv(HERE / "data" / f"ep1_events_{inst}.csv",
                      parse_dates=["event_et"]).rename(
        columns={"event_et": "et", "ticker": "title"})
    j = ref.merge(ev[["et", "title", "pred", "jump_pct"]], on=["et", "title"],
                  how="left", suffixes=("_ref", ""))
    c1_ok = (len(j) == len(ref)
             and float((j.pred - j.pred_ref).abs().max()) < 1e-9
             and float((j.jump_pct - j.jump_pct_ref).abs().max()) < 1e-9)
    print(f"[E-S1] C1 power parity vs ep1_events: {'PASS' if c1_ok else 'FAIL'} "
          f"({len(j)} rows)", flush=True)

    inds = {k: build(k, IndicatorConfig(enabled=True)) for k in sorted(REGISTRY)}
    states, timing, handles = stance_rows(ev, df1, inds)
    top = sorted(timing.items(), key=lambda kv: -kv[1])[:5]
    print("[E-S1] top-5 indicator cost: " +
          ", ".join(f"{k} {v:.1f}s" for k, v in top), flush=True)

    rides = ride_outcomes(inst, ev, Path(a.bars_1s).expanduser())
    df = pd.concat([ev.assign(instrument=inst), rides, states], axis=1)

    gates = {"C1_power_parity": (c1_ok, f"{len(j)} committed rows exact")}
    gates["C2_causality"] = c2_causality(ev, df1, states, handles, inds)
    dup = int(df.duplicated(["instrument", "et", "title"]).sum())
    gates["C3_unique"] = (dup == 0, f"{dup} duplicates")
    have = int(df.ride_pnl_usd.notna().sum())
    gates["C4_coverage"] = (bool(have > 300), f"bracket outcomes {have}/{len(df)}")

    for g, (ok, msg) in gates.items():
        print(f"[E-S1] {g}: {'PASS' if ok else 'FAIL'} — {msg}", flush=True)
    all_ok = all(ok for ok, _ in gates.values())
    out = Path(a.out)
    if all_ok:
        dest = out / f"es1_event_state_{inst}.csv"
        df.to_csv(dest, index=False)
        print(f"[E-S1] WRITTEN {dest} rows={len(df)} cols={len(df.columns)}", flush=True)
    else:
        print("[E-S1] GATES FAILED — dataset NOT written", flush=True)
    manifest = {"instrument": inst, "version": "v1", "rows": int(len(df)),
                "cols": int(len(df.columns)), "scored_pred": int(ev.pred.notna().sum()),
                "bracket_outcomes": have,
                "gates": {k: {"pass": bool(ok), "msg": m} for k, (ok, m) in gates.items()},
                "wall_s": round(time.time() - t0, 1)}
    (out / f"es1_manifest_{inst}.json").write_text(json.dumps(manifest, indent=2))
    print(f"[E-S1] done {inst} in {manifest['wall_s']}s -> "
          f"{'OK' if all_ok else 'GATES-FAILED'}", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
