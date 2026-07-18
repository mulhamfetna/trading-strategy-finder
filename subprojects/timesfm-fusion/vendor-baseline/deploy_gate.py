#!/usr/bin/env python3
"""Production runner: apply the TimesFM volatility gate to the reference strategy and emit the final
gated strategy — stats + a full audit CSV of every trade (kept/vetoed, its forecast vol, its P/L).

    python deploy_gate.py NQ          # -> nq_gated_book.csv + printed stats
    python deploy_gate.py NQ --pct 80

This is the deployable artifact: the same causal rule proven in overlay.py, packaged via
gate_service.VolGate so the identical object can run live.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from gate_service import gate_reference_book
from tfm.data import DEFAULT_DATA_DIR, INSTRUMENTS, load_tf
from tfm.forecast_cache import forecast_arrays
from tfm.forecaster import get_forecaster
from tfm.strategy import _DECILE_SPAN_SIGMAS

LOG_NAME = {"ES": "es_run_mtf_log.csv", "NQ": "nq_run_mtf_log.csv"}


def _fmt(s, tag):
    rd = "inf" if s["ret_dd"] == float("inf") else f"{s['ret_dd']:.2f}"
    return (f"  {tag:20} trades={s['n']:>4}  P/L=${s['pnl']:>10,.0f}  "
            f"maxDD=${s['dd']:>9,.0f}  Return/DD={rd:>6}  win={s['win']:.0f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instrument", nargs="?", default="NQ", choices=["ES", "NQ"])
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--horizon", type=int, default=24)
    ap.add_argument("--pct", type=float, default=85.0)
    args = ap.parse_args()
    inst = INSTRUMENTS[args.instrument]

    df = load_tf(args.instrument, args.tf)
    close = df["close"].to_numpy(float)
    idx = {pd.Timestamp(t): k for k, t in enumerate(df["datetime"])}
    med, qlo, qhi = forecast_arrays(df, get_forecaster("timesfm"), 512, args.horizon,
                                    cache_key=f"{args.instrument}_{args.tf}_full")
    rel = (qhi - qlo) / _DECILE_SPAN_SIGMAS / close  # stationary forecast band

    log = pd.read_csv(DEFAULT_DATA_DIR / LOG_NAME[args.instrument])
    ent = log[log["decision"] == "entry"].copy()
    ent["datetime"] = pd.to_datetime(ent["datetime"])
    ent = ent.sort_values("datetime").reset_index(drop=True)

    bands = np.full(len(ent), np.nan)
    for i, t in enumerate(ent["datetime"]):
        k = idx.get(pd.Timestamp(t))
        if k is not None and k - 1 >= 0 and not np.isnan(rel[k - 1]):
            bands[i] = rel[k - 1]  # forecast from the bar BEFORE entry (causal)

    keep, base, gated, rows = gate_reference_book(
        ent["datetime"].tolist(), ent["pnl"].to_numpy(float), bands, pct=args.pct)

    out = pd.DataFrame(rows)
    out["direction"] = ent["direction"].values
    out["decision"] = np.where(out["kept"], "TAKE", "VETO")
    path = f"{args.instrument.lower()}_gated_book.csv"
    out.to_csv(path, index=False)

    print(f"=== {args.instrument} {args.tf} + TimesFM vol gate (p{args.pct:.0f}) ===")
    print(_fmt(base, "reference (all)"))
    print(_fmt(gated, "+ vol gate"))
    dropped = out[~out["kept"]]
    print(f"\n  vetoed {len(dropped)} trades netting ${dropped['pnl'].sum():,.0f} "
          f"(win {100*(dropped['pnl']>0).mean():.0f}%)  ->  audit trail written to {path}")


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
