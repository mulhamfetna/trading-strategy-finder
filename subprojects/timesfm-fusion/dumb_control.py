#!/usr/bin/env python3
"""DUMB CONTROL: does a cheap volatility proxy replicate TimesFM's NQ vol-gate?

The teammate's gate vetoes an NQ entry when TimesFM's pre-entry forecast band (q90-q10)/price is in
the top ~15% of its causal history (p85), lifting Return/DD 9.36 -> 18.78 (DD -44%). The question our
SOP demands before integrating a 200M model: can a PLAIN volatility estimator do the same job?

We take the SAME 481-trade book (entry_time + pnl from the audit trail) and gate it with the IDENTICAL
causal p85 VolGate, but feeding it — instead of the TimesFM band — cheap proxies computed from NQ 1h
price at the bar BEFORE entry (causal):
  * ATR(n)/close           (Average True Range, the classic)
  * realized vol(n)        (std of last n log-returns)
  * rolling range(n)/close (high-low span over last n bars)
Each proxy is swept over several lookbacks n and we KEEP ITS BEST (steelman the dumb control). We also
report how many of TimesFM's 34 vetoed trades each proxy also vetoes (overlap) and the correlation
between the TimesFM band and each proxy.

If a cheap proxy ~matches TimesFM's Return/DD, we do NOT need the model. If TimesFM clearly wins, it
earns its keep.

Run:  python3 dumb_control.py <NQ_1h.csv>
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor-baseline"))
from gate_service import VolGate, _stats

BOOK = HERE / "vendor-baseline" / "nq_gated_book.csv"
LOOKBACKS = [14, 24, 50, 100]


def gate_stats(pnl, readings, pct=85.0):
    """Apply the exact causal VolGate to a per-trade reading series; return (stats, keep_mask)."""
    g = VolGate(pct=pct)
    keep = np.array([g.allow(r if np.isfinite(r) else None) for r in readings])
    return _stats(pnl[keep]), keep


def main():
    price_csv = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "vendor-baseline/NQ_1h.csv")
    book = pd.read_csv(BOOK)
    book["entry_time"] = pd.to_datetime(book["entry_time"])
    book = book.sort_values("entry_time").reset_index(drop=True)
    pnl = book["pnl"].to_numpy(float)
    tfm_band = book["rel_band"].to_numpy(float)
    tfm_keep_csv = book["kept"].astype(str).str.lower().isin(["true", "1"]).to_numpy()

    px = pd.read_csv(price_csv)
    px.columns = [c.strip().lower() for c in px.columns]
    px["datetime"] = pd.to_datetime(px["datetime"])
    px = px.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    idx = {t: k for k, t in enumerate(px["datetime"])}
    high, low, close = (px[c].to_numpy(float) for c in ("high", "low", "close"))

    # --- causal volatility proxies on the full 1h grid (value at bar i uses bars <= i) ---
    prev_close = np.concatenate([[np.nan], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    logret = np.concatenate([[np.nan], np.diff(np.log(close))])
    proxies = {}
    for n in LOOKBACKS:
        atr = pd.Series(tr).rolling(n).mean().to_numpy() / close
        rv = pd.Series(logret).rolling(n).std().to_numpy()
        rng = (pd.Series(high).rolling(n).max() - pd.Series(low).rolling(n).min()).to_numpy() / close
        proxies[f"ATR{n}"] = atr
        proxies[f"realvol{n}"] = rv
        proxies[f"range{n}"] = rng

    # --- map each entry to its pre-entry (k-1) proxy readings ---
    mapped = sum(1 for t in book["entry_time"] if t in idx)
    def readings_for(series):
        out = np.full(len(book), np.nan)
        for i, t in enumerate(book["entry_time"]):
            k = idx.get(t)
            if k is not None and k - 1 >= 0:
                out[i] = series[k - 1]
        return out

    base = _stats(pnl)
    tfm_stats, tfm_keep = gate_stats(pnl, tfm_band)

    print(f"price file: {price_csv}")
    print(f"entries mapped to bars: {mapped}/{len(book)}\n")
    hdr = f"  {'gate':16} {'trades':>6} {'P/L':>12} {'maxDD':>11} {'Ret/DD':>7} {'vsTFM_ovlp':>10} {'corr':>6}"
    print(hdr)
    print(f"  {'reference(all)':16} {base['n']:>6} {base['pnl']:>12,.0f} {base['dd']:>11,.0f} {base['ret_dd']:>7.2f} {'-':>10} {'-':>6}")
    print(f"  {'TimesFM p85':16} {tfm_stats['n']:>6} {tfm_stats['pnl']:>12,.0f} {tfm_stats['dd']:>11,.0f} {tfm_stats['ret_dd']:>7.2f} {'(self)':>10} {'1.00':>6}")

    # best proxy per family, plus every variant for the record
    rows = []
    for name, series in proxies.items():
        r = readings_for(series)
        st, keep = gate_stats(pnl, r)
        veto = ~keep
        ovlp = int((veto & (~tfm_keep)).sum())               # trades BOTH vetoed
        tfm_veto_n = int((~tfm_keep).sum())
        valid = np.isfinite(r) & np.isfinite(tfm_band)
        corr = float(np.corrcoef(r[valid], tfm_band[valid])[0, 1]) if valid.sum() > 5 else float("nan")
        rows.append((name, st, ovlp, tfm_veto_n, corr))

    for name, st, ovlp, tfm_veto_n, corr in sorted(rows, key=lambda x: -x[1]["ret_dd"]):
        print(f"  {name:16} {st['n']:>6} {st['pnl']:>12,.0f} {st['dd']:>11,.0f} {st['ret_dd']:>7.2f} "
              f"{str(ovlp)+'/'+str(tfm_veto_n):>10} {corr:>6.2f}")

    best = max(rows, key=lambda x: x[1]["ret_dd"])
    print(f"\nTimesFM Return/DD = {tfm_stats['ret_dd']:.2f}  |  best cheap proxy ({best[0]}) = {best[1]['ret_dd']:.2f}")
    verdict = ("CHEAP PROXY MATCHES/BEATS TimesFM -> the 200M model is NOT needed"
               if best[1]["ret_dd"] >= tfm_stats["ret_dd"] - 0.5 else
               "TimesFM clearly beats the best cheap proxy -> the model adds something")
    print("VERDICT:", verdict)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
