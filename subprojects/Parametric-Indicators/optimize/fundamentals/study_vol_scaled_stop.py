"""#7 · D4 — VOL-SCALED STOP: does a constant-sigma stop beat the fixed 40-pt stop?

D3 showed the fixed 40-pt stop is regime-blind: ~100 sigma away when quiet, <1 sigma of the tail when loud
(where a single 1-min move can blow through it). The proposed fix is a stop set as a constant number of
STANDARD DEVIATIONS (k x EWMA-sigma), so it is a constant stop-out probability across regimes rather than a
constant number of points.

This tests it OFFLINE on the champion entries (no engine change — prove it helps first). For each entry we
re-walk the 1-min path with a fixed -40 stop vs a -k*sigma stop (k chosen so the MEDIAN sigma-stop = 40, a
fair comparison), same TP (+60) and max-hold, and compare P/L, risk, and — the real question — whether the
stop-out rate is EQUALIZED across vol regimes.

HONEST CAVEAT baked into the read: D1 showed the backtest fills the stop exactly (0% beyond-stop), so a
WIDER sigma-stop in loud regimes ALLOWS bigger backtest losses — the sigma-stop's main benefit (avoiding
LIVE blow-through fills, and consistent risk) is partly invisible to a backtest. We report both and do not
overclaim a P/L win.

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_vol_scaled_stop.py --tf 1h
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments, signals                    # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int     # noqa: E402
from perf._common import champion_preset                           # noqa: E402
from optimize.fundamentals.champion_params import champion_stops, describe  # noqa: E402

LAM = 0.97; TP = 60.0; MAXHOLD = 1440    # 1 trading day of 1-min bars


def walk(mc, e0, ep, dirn, stop_pts, tp_pts, maxhold):
    """First-touch exit walking the 1-min path from e0. Returns (pnl_points, reason)."""
    hi = min(e0 + maxhold, len(mc) - 1)
    for t in range(e0 + 1, hi + 1):
        move = dirn * (mc[t] - ep)
        if move <= -stop_pts:
            return -stop_pts, "stop"
        if move >= tp_pts:
            return tp_pts, "tp"
    return dirn * (mc[hi] - ep), "cap"        # mark to market at max-hold


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--instrument", default="NQ")
    a = ap.parse_args()
    pv = instruments.point_value(a.instrument)

    df, df1, box, vf, n = data.load_inputs(a.tf, instrument=a.instrument)
    p = champion_preset(a.tf)
    _SS, _SH, _TP, _FL = champion_stops(p, a.tf)   # STRICT — a missing stop must raise, never default
    print(describe(p, a.tf), flush=True)
    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
    MD = df1["Date"].to_numpy(); MC = df1["Close"].to_numpy(float)
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float), MC,
                      _SS, _SH, TP, _FL)
    if not F:
        print("no trades"); return 1

    # causal EWMA sigma in POINTS on the 1-min frame
    dt = np.diff(MD).astype("timedelta64[s]").astype(np.int64)
    r = np.full(len(MC), np.nan); r[1:] = np.log(MC[1:] / MC[:-1]); r[1:][dt != 60] = np.nan
    cvar = pd.Series(np.where(np.isfinite(r), r, np.nan) ** 2).ewm(alpha=1 - LAM, adjust=False,
                                                                   min_periods=30).mean().shift(1).to_numpy()
    sig_pts = np.sqrt(cvar) * MC                                    # 1-sd 1-min move in points, per bar

    ent = []
    for t in F:
        e0 = int(np.searchsorted(MD, np.datetime64(t["entry_time"]), side="left"))
        if e0 < 1 or e0 >= len(MC) or not np.isfinite(sig_pts[e0]):
            continue
        ent.append((e0, float(t["entry_price"]), 1 if t["direction"] == "long" else -1, sig_pts[e0]))
    S = np.array([e[3] for e in ent])
    k = 40.0 / np.median(S)                                         # median sigma-stop == 40 pts (fair)
    print(f"\n{a.instrument} {a.tf} · {len(ent)} entries · EWMA sigma_pts median {np.median(S):.1f} "
          f"(10th {np.percentile(S,10):.1f} / 90th {np.percentile(S,90):.1f}) · k={k:.1f} "
          f"=> sigma-stop = {k:.1f}*sigma, median {k*np.median(S):.0f} pts\n")

    # regime buckets by entry sigma
    q33, q67 = np.percentile(S, [33, 67])
    def regime(s): return "quiet" if s < q33 else "loud" if s > q67 else "normal"

    res = {"FIXED-40": [], "sigma-scaled": []}
    reasons = {"FIXED-40": {}, "sigma-scaled": {}}
    byreg = {"FIXED-40": {}, "sigma-scaled": {}}
    for (e0, ep, dirn, s) in ent:
        for name, stop in (("FIXED-40", 40.0), ("sigma-scaled", max(5.0, k * s))):
            pnl, why = walk(MC, e0, ep, dirn, stop, TP, MAXHOLD)
            res[name].append(pnl)
            reasons[name][why] = reasons[name].get(why, 0) + 1
            rg = regime(s)
            byreg[name].setdefault(rg, []).append(why == "stop")

    print("=" * 88)
    print(f"{'stop rule':<14} {'total P/L':>12} {'$/trade':>9} {'win%':>6} {'stop%':>6} {'tp%':>5} "
          f"{'cap%':>5} {'worst':>8} {'sd':>7}")
    print("-" * 88)
    for name in ("FIXED-40", "sigma-scaled"):
        r_ = np.array(res[name]) * pv
        tot = len(res[name])
        st = 100 * reasons[name].get("stop", 0) / tot
        tp_ = 100 * reasons[name].get("tp", 0) / tot
        cp = 100 * reasons[name].get("cap", 0) / tot
        print(f"  {name:<12} ${r_.sum():>11,.0f} ${r_.mean():>+8,.0f} {100*(r_>0).mean():>5.1f}% "
              f"{st:>5.1f}% {tp_:>4.1f}% {cp:>4.1f}% ${r_.min():>+7,.0f} ${r_.std():>,.0f}")

    print("\n" + "=" * 88)
    print("THE REAL QUESTION — is the stop-out rate EQUALIZED across regimes? (the point of constant-sigma)")
    print("=" * 88)
    print(f"  {'regime':<8} {'n':>5} | {'FIXED-40 stop%':>15} | {'sigma-scaled stop%':>19}")
    for rg in ("quiet", "normal", "loud"):
        nq = len(byreg['FIXED-40'].get(rg, []))
        f_ = 100 * np.mean(byreg['FIXED-40'].get(rg, [0]))
        s_ = 100 * np.mean(byreg['sigma-scaled'].get(rg, [0]))
        print(f"  {rg:<8} {nq:>5} | {f_:>14.1f}% | {s_:>18.1f}%")

    print("\n" + "=" * 88)
    print("READ (honest)")
    print("=" * 88)
    print("  The point of the sigma-stop is CONSISTENCY: a constant stop-out probability across regimes,")
    print("  vs the fixed stop whose stop% swings by regime (tight & often-hit when loud, ~never-hit when")
    print("  quiet). If the fixed stop% column swings a lot and the sigma column is flat, the sigma-stop")
    print("  delivers consistent risk. P/L may be SIMILAR-or-worse in the BACKTEST (D1: the backtest caps")
    print("  losses at the stop, so a wider loud-regime sigma-stop just books bigger losses) — the real")
    print("  sigma-stop win is LIVE (no blow-through fills, consistent sizing), which a clean-fill backtest")
    print("  cannot show. Do NOT adopt on backtest P/L alone; adopt for risk consistency + live gap safety.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
