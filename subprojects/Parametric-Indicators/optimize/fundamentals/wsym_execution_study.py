#!/usr/bin/env python3
"""RQ-7 (#147) — the YM CPI execution study: the four ACQ layers.

Implements `docs/WS-YMCPI-EXECUTION-PREREGISTRATION.md` (commit 6d12509, filed BEFORE any
measurement). Fill machinery imported from the parity-proven executor; events = the deployed
schedule's CPI rows (the exact set every prior YM number used).

    python3 wsym_execution_study.py --bars-1s ~/Mulham/data_2010_1s/YM_Continuous_Data/YM_1s.csv

Outputs: wsym_exec_events.csv · wsym_exec_result.json (committed evidence).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from src.deploy.release_executor import (   # noqa: E402
    ENTRY_TOL_S, EXIT_S, LEAD_S, Leg, load_1s_windows, run_bracket,
)
from wsescpi_study import cpi_schedule_events   # noqa: E402

PV, COST, TICK = 5.0, 22.50, 5.0
# the a-priori PASS lines (pre-registered — do not edit after results)
ACQ1_MED_S, ACQ1_P95_S = 30.0, 60.0
ACQ2_MIN_NET = 50.0
ACQ3_MIN_WINDOW_VOL = 20
ACQ4_MIN_SECONDS, ACQ4_MIN_VOL = 300, 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args()
    bars_path = Path(a.bars_1s)

    with bars_path.open("rb") as f:
        f.seek(-4096, 2)
        data_end = pd.Timestamp(f.read().splitlines()[-1].split(b",")[0].decode())
    cpi = cpi_schedule_events(data_end)
    print(f"RQ-7 execution study: {len(cpi)} CPI events; pre-reg 6d12509")

    windows = [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
               for t in cpi]
    bars = load_1s_windows(bars_path, windows, keep_volume=True)
    print(f"1s bars loaded: {len(bars):,}")
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    vol = bars["Volume"].to_numpy(float)

    rows = []
    for t in cpi:
        t0 = np.datetime64(t)
        t_ent = t0 - np.timedelta64(LEAD_S, "s")
        i_ent = int(np.searchsorted(idx, t_ent, side="right")) - 1
        i_rel = int(np.searchsorted(idx, t0, side="left"))
        i_end = int(np.searchsorted(idx, t0 + np.timedelta64(EXIT_S, "s"), side="right")) - 1
        if i_ent < 0 or i_end <= i_ent or i_rel <= i_ent or i_end >= len(idx):
            continue
        age_s = float((t_ent - idx[i_ent]) / np.timedelta64(1, "s"))
        if age_s > ENTRY_TOL_S:
            continue                                   # the executor would skip it too

        base = run_bracket(idx, op, hi, lo, cl, t, Leg("long", 1), PV, "base")
        # ACQ-2 harsher fill: entry at the OPEN of the FIRST traded bar AFTER rel-300s
        nxt = None
        if i_ent + 1 < i_rel:                          # a pre-release bar exists to fill on
            nxt = run_bracket(idx, op, hi, lo, cl, t, Leg("long", 1), PV, "nextopen",
                              entry_price=float(op[i_ent + 1]), walk_from=i_ent + 2)
        i_w0 = int(np.searchsorted(idx, t0 - np.timedelta64(LEAD_S, "s"), side="left"))
        rows.append({
            "et": t, "entry_bar_age_s": age_s,
            "next_gap_s": float((idx[i_ent + 1] - t_ent) / np.timedelta64(1, "s")),
            "entry_bar_vol": float(vol[i_ent]),
            "window_vol": float(vol[i_w0:i_rel].sum()),
            "window_seconds": int(i_rel - i_w0),
            "post_seconds": int(i_end - i_rel + 1),
            "post_vol": float(vol[i_rel:i_end + 1].sum()),
            "pnl_base": base.pnl_usd if base else np.nan,
            "pnl_nextopen": nxt.pnl_usd if nxt else (base.pnl_usd if base else np.nan),
            "entry_base": base.entry if base else np.nan,
            "entry_nextopen": nxt.entry if nxt else np.nan,
        })
    d = pd.DataFrame(rows)
    print(f"events measured: {len(d)}")

    acq1_med = d.entry_bar_age_s.median()
    acq1_p95 = d.entry_bar_age_s.quantile(0.95)
    acq1 = bool(acq1_med <= ACQ1_MED_S and acq1_p95 <= ACQ1_P95_S)

    net_base = d.pnl_base.mean() - COST
    net_next = d.pnl_nextopen.mean() - COST
    acq2 = bool(net_next > ACQ2_MIN_NET)

    acq3_med = d.window_vol.median()
    acq3 = bool(acq3_med >= ACQ3_MIN_WINDOW_VOL)

    acq4_sec, acq4_vol = d.post_seconds.median(), d.post_vol.median()
    acq4 = bool(acq4_sec >= ACQ4_MIN_SECONDS and acq4_vol >= ACQ4_MIN_VOL)

    slip = (d.entry_nextopen - d.entry_base).dropna()
    print(f"ACQ-1 fill staleness : median {acq1_med:.1f}s p95 {acq1_p95:.1f}s "
          f"(lines {ACQ1_MED_S}/{ACQ1_P95_S}) -> {'PASS' if acq1 else 'FAIL'}")
    print(f"ACQ-2 slippage       : base net ${net_base:+.2f} -> next-open net ${net_next:+.2f} "
          f"(line >${ACQ2_MIN_NET}) · realized entry shift mean {slip.mean():+.2f} pts "
          f"({slip.mean()/1.0:+.1f} ticks) -> {'PASS' if acq2 else 'FAIL'}")
    print(f"ACQ-3 entry depth    : median window vol {acq3_med:.0f} (line >={ACQ3_MIN_WINDOW_VOL}) "
          f"· median entry-bar vol {d.entry_bar_vol.median():.0f} -> {'PASS' if acq3 else 'FAIL'}")
    print(f"ACQ-4 exit tape      : median post seconds {acq4_sec:.0f}/900, vol {acq4_vol:.0f} "
          f"(lines {ACQ4_MIN_SECONDS}/{ACQ4_MIN_VOL}) -> {'PASS' if acq4 else 'FAIL'}")
    for k in (2, 4):                                   # flat adverse-tick stress (reported)
        print(f"  stress: entry {k} ticks adverse -> net ${net_base - k * TICK:+.2f}/event")

    verdict = "ACQUIRE" if (acq1 and acq2 and acq3 and acq4) else "NOT-ACQUIRED"
    print(f"\nVERDICT: {verdict}")

    d.to_csv(Path(a.out_dir) / "wsym_exec_events.csv", index=False)
    result = {"prereg_commit": "6d12509", "n": len(d),
              "acq1": {"median_s": float(acq1_med), "p95_s": float(acq1_p95), "pass": acq1},
              "acq2": {"net_base": float(net_base), "net_nextopen": float(net_next),
                       "entry_shift_ticks_mean": float(slip.mean()), "pass": acq2},
              "acq3": {"window_vol_median": float(acq3_med),
                       "entry_bar_vol_median": float(d.entry_bar_vol.median()), "pass": acq3},
              "acq4": {"post_seconds_median": float(acq4_sec),
                       "post_vol_median": float(acq4_vol), "pass": acq4},
              "verdict": verdict}
    (Path(a.out_dir) / "wsym_exec_result.json").write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
