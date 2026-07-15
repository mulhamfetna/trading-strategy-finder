#!/usr/bin/env python3
"""Cross-timeframe vol gate: gate the reference strategy's 1h trades using a FINER-timeframe
TimesFM volatility band (e.g. 30m), which may read the entry-time regime more sharply than the 1h
band. Fully causal: for a 1h entry at time T we use the finer bar that CLOSES strictly before T.

    python overlay_xtf.py NQ 30m     # gate NQ 1h trades with the 30m band
Requires (INST)_1h_full and (INST)_(gate_tf)_full forecast caches.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from tfm.data import DEFAULT_DATA_DIR, INSTRUMENTS, load_tf
from tfm.forecast_cache import forecast_arrays
from tfm.forecaster import get_forecaster
from tfm.strategy import _DECILE_SPAN_SIGMAS

LOG_NAME = {"ES": "es_run_mtf_log.csv", "NQ": "nq_run_mtf_log.csv"}


def _stats(pnls):
    n = len(pnls)
    if n == 0:
        return dict(n=0, pnl=0.0, dd=0.0, ret_dd=0.0, win=0.0)
    eq = np.cumsum(pnls)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    wins = pnls[pnls > 0]
    return dict(n=n, pnl=float(pnls.sum()), dd=dd,
                ret_dd=float(pnls.sum() / dd) if dd else float("inf"),
                win=100.0 * len(wins) / n)


def _fmt(s, tag):
    rd = "inf" if s["ret_dd"] == float("inf") else f"{s['ret_dd']:.2f}"
    return (f"  {tag:26} n={s['n']:>4}  pnl=${s['pnl']:>10,.0f}  maxDD=${s['dd']:>9,.0f}  "
            f"ret/DD={rd:>6}  win={s['win']:.0f}%")


def build_relsigma(inst_name, tf, horizon=24):
    df = load_tf(inst_name, tf)
    med, qlo, qhi = forecast_arrays(df, get_forecaster("timesfm"), 512, horizon,
                                    cache_key=f"{inst_name}_{tf}_full")
    close = df["close"].to_numpy(float)
    rel = (qhi - qlo) / _DECILE_SPAN_SIGMAS / close
    times = df["datetime"].to_numpy()  # sorted
    return times, rel


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    inst_name = (sys.argv[1] if len(sys.argv) > 1 else "NQ").upper()
    gate_tf = sys.argv[2] if len(sys.argv) > 2 else "30m"
    inst = INSTRUMENTS[inst_name]

    g_times, g_rel = build_relsigma(inst_name, gate_tf)

    log = pd.read_csv(DEFAULT_DATA_DIR / LOG_NAME[inst_name])
    ent = log[log["decision"] == "entry"].copy()
    ent["datetime"] = pd.to_datetime(ent["datetime"])
    ent = ent.sort_values("datetime").reset_index(drop=True)

    # for each 1h entry, causal finer-bar sigma = the gate bar that closes strictly before entry
    g_ts = pd.DatetimeIndex(g_times)
    sig = np.full(len(ent), np.nan)
    for i, t in enumerate(ent["datetime"]):
        pos = g_ts.searchsorted(pd.Timestamp(t), side="left") - 1  # last bar with time < t
        if pos >= 0 and not np.isnan(g_rel[pos]):
            sig[i] = g_rel[pos]
    pnl = ent["pnl"].to_numpy(float)

    print(f"=== CROSS-TF gate — {inst_name} 1h trades gated by {gate_tf} TimesFM band ===")
    print(f"  {len(ent)} trades, {np.isnan(sig).sum()} without a finer-bar reading\n")

    for pct in (85, 80, 75, 65):
        keep = np.ones(len(ent), bool)
        for j in range(len(ent)):
            hist = sig[:j][~np.isnan(sig[:j])]
            if not np.isnan(sig[j]) and len(hist) >= 40:
                keep[j] = sig[j] <= np.percentile(hist, pct)
        print(_fmt(_stats(pnl[keep]), f"causal {gate_tf}-vol<=p{pct}"))
    print(_fmt(_stats(pnl), "baseline (all)"))


if __name__ == "__main__":
    main()
