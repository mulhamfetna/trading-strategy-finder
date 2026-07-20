"""SIZING · Z3 — fixed-fractional vs VOLATILITY-TARGETING contract scaling.

Z2 settled the FRACTION (~quarter-half Kelly). Z3 asks the METHOD: should contract count be constant
(fixed-fractional — constant $ risk per trade) or scaled inversely to volatility (vol-targeting — constant
$ VOLATILITY per trade)?

A prior worth stating (then testing, per D4): our strategy uses a FIXED-POINT stop (40 pts), so each trade
already risks a constant $ amount (40 x contracts x pv) regardless of the current volatility — i.e. the
fixed approach is ALREADY vol-normalized. Scaling contracts by 1/sigma on top would make the $ risk per
trade VARY with vol (less when loud, more when quiet), which could DE-normalize it. Vol-targeting only helps
if high-vol trades have a worse risk-adjusted edge — but D4/S3 found the per-trade edge (stop-out rate) is
regime-INVARIANT. So the prior is: vol-targeting does not help here. Test it.

Compares, on the pooled edge-champion trades (4h/2h/1h/15m; 5m/2m have ~0 Kelly edge, Z1):
  * FIXED:       $ per trade proportional to pnl_points (constant contracts).
  * VOL-TARGET:  $ per trade = pnl_points x (target_sigma / sigma_at_entry), clipped to [0.25x, 4x].
Metrics: per-trade Sharpe (mean/sd), max drawdown of cumulative P&L, return/DD. Vol-targeting also incurs
extra rebalancing turnover (a cost the fixed approach avoids) — flagged.

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_vol_target.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, signals                               # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int   # noqa: E402
from perf._common import champion_preset                         # noqa: E402
from optimize.fundamentals.champion_params import champion_stops, describe  # noqa: E402
import pandas as pd                                              # noqa: E402

STOP = 40.0; LAM = 0.97
TFS = ["4h", "2h", "1h", "15m"]


def metrics(pnl):
    cum = np.cumsum(pnl)
    runmax = np.maximum.accumulate(np.concatenate([[0], cum]))[1:]
    dd = runmax - cum
    maxdd = dd.max() if len(dd) else 0.0
    sharpe = pnl.mean() / pnl.std() * np.sqrt(len(pnl)) if pnl.std() > 0 else 0.0   # annualized-ish per-trade
    ret_dd = cum[-1] / maxdd if maxdd > 0 else np.inf
    return cum[-1], maxdd, sharpe, ret_dd


def main() -> int:
    pnl_all, sig_all = [], []
    for tf in TFS:
        df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
        p = champion_preset(tf)
        _SS, _SH, _TP, _FL = champion_stops(p, tf)   # STRICT — a missing stop must raise, never default
        print(describe(p, tf), flush=True)
        s = signals_to_int(signals.decision_signals(df, box))
        gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
        MD = df1["Date"].to_numpy(); MC = df1["Close"].to_numpy(float); MO = df1["Open"].to_numpy(float)
        F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), s, gate,
                          MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float), MC,
                          _SS, _SH, _TP,
                          _FL, m_open=MO)
        dt = np.diff(MD).astype("timedelta64[s]").astype(np.int64)
        r = np.full(len(MC), np.nan); r[1:] = np.log(MC[1:] / MC[:-1]); r[1:][dt != 60] = np.nan
        cvar = pd.Series(np.where(np.isfinite(r), r, np.nan) ** 2).ewm(alpha=1 - LAM, adjust=False,
                                                                       min_periods=30).mean().shift(1).to_numpy()
        sig_pts = np.sqrt(cvar) * MC
        for t in F:
            e0 = int(np.searchsorted(MD, np.datetime64(t["entry_time"]), side="left"))
            if 1 <= e0 < len(MC) and np.isfinite(sig_pts[e0]):
                pnl_all.append(float(t["pnl_points"])); sig_all.append(float(sig_pts[e0]))

    pnl = np.array(pnl_all); sig = np.array(sig_all)
    tgt = np.median(sig)
    w_raw = np.clip(tgt / sig, 0.25, 4.0)
    w = w_raw / w_raw.mean()                                       # LEVERAGE-MATCH: E[w]=1, fair comparison
    tcost = 0.10 * np.abs(np.diff(w_raw, prepend=1.0))            # turnover cost ~0.1pt per unit size change

    corr = np.corrcoef(pnl, sig)[0, 1]
    print(f"\nNQ edge-champions · {len(pnl)} trades · median sigma {tgt:.1f} pts · "
          f"corr(pnl, sigma) = {corr:+.3f}")
    print(f"  vol-target is LEVERAGE-MATCHED (mean weight = 1) so totals are comparable; a turnover cost of")
    print(f"  ~0.1pt per unit size change is charged to vol-target (it rebalances every trade).\n")
    print(f"  {'method':<20} {'total(pts)':>11} {'maxDD(pts)':>11} {'Sharpe~':>9} {'return/DD':>10}")
    print("-" * 66)
    variants = (("FIXED", pnl), ("VOL-TARGET (matched)", pnl * w),
                ("VOL-TARGET − costs", pnl * w - tcost))
    for name, series in variants:
        tot, mdd, sh, rdd = metrics(series)
        print(f"  {name:<20} {tot:>11.0f} {mdd:>11.0f} {sh:>9.2f} {rdd:>10.2f}")

    # ROBUSTNESS: does the vol-target Sharpe edge hold in BOTH halves? (the fluke-window check)
    print("\n" + "=" * 66)
    print("ROBUSTNESS — Sharpe by chronological half (does the vol-target edge persist?)")
    print("=" * 66)
    h = len(pnl) // 2
    print(f"  {'half':<8} {'FIXED Sharpe':>13} {'VOL-TGT Sharpe':>15} {'edge':>8}")
    edges = []
    for nm, sl in (("1st", slice(0, h)), ("2nd", slice(h, None))):
        _, _, shf, _ = metrics(pnl[sl])
        _, _, shv, _ = metrics((pnl * w)[sl])
        edges.append(shv - shf)
        print(f"  {nm:<8} {shf:>13.2f} {shv:>15.2f} {shv-shf:>+8.2f}")
    stable = all(e > 0 for e in edges)

    print("\n" + "=" * 66)
    print("READ")
    print("=" * 66)
    print(f"  corr(pnl, sigma) = {corr:+.3f} — {'~zero, so there is NO vol-conditional edge to exploit' if abs(corr)<0.05 else 'a real pnl-vs-vol relation'}.")
    if abs(corr) < 0.05:
        print(f"  With no vol-edge, any leverage-matched Sharpe gain is a variance-shaping/sample artifact, not")
        print(f"  a durable edge. Vol-target {'held its Sharpe edge in BOTH halves' if stable else 'did NOT hold in both halves (flipped) => fluke-window artifact'}.")
    print(f"  Plus vol-target rebalances every trade (mean |size change| "
          f"{100*np.mean(np.abs(np.diff(w_raw))):.0f}%) — real turnover cost the FIXED method avoids.")
    print(f"  Verdict guidance: adopt vol-target ONLY if its Sharpe edge is (a) present after leverage-match,")
    print(f"  (b) stable across halves, and (c) survives costs — AND ideally backed by corr(pnl,sigma)<0.")
    print(f"  Otherwise keep FIXED (the fixed-point stop already normalizes risk, D4). Next: Z4 (PnL:DD).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
