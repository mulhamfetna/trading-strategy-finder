"""FA-v2 · A1 — DOES GOLD (GC) REACT TO US MACRO, AND HOW DOES IT COMPARE TO NQ?

The new workstream narrows to NQ + GC. Before any GC news study, the foundational question: does gold even
respond to scheduled US macro releases, how strongly, and is there a directional tilt? This is a
MEASUREMENT (an 8x volatility spike is an 8x spike regardless of sample size) — but any DIRECTIONAL /
signed claim on GC rests on only 2025-2026 data (~100 releases, the fluke window), so those are flagged
underpowered and pre-registered, per the silver lesson.

Both markets are measured on the SAME 2025-2026 window (wsg-i) for a fair head-to-head. NQ's 17-year spike
(8.3x) is already known; here NQ is the same-window yardstick for GC.

  WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 -u optimize/fundamentals/study_news_reaction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data                                          # noqa: E402
from optimize.fundamentals import release_calendar as rc           # noqa: E402
from scipy import stats                                            # noqa: E402


def reaction(df1: pd.DataFrame, cal: pd.DataFrame, rng):
    """Release-minute reaction stats for one market."""
    d = df1["Date"].to_numpy()
    close = df1["Close"].to_numpy(float)
    # gap-aware |1-min return| baseline
    dt_s = np.diff(d).astype("timedelta64[s]").astype(np.int64)
    is_1m = np.concatenate([[False], dt_s == 60])
    ret = np.concatenate([[np.nan], close[1:] / close[:-1] - 1.0])
    ret[~is_1m] = np.nan
    base = np.nanmean(np.abs(ret))

    idx = pd.Index(df1["Date"])
    t0 = idx.get_indexer(cal["Date"])
    ok = t0 >= 1
    t0 = t0[ok]
    ev = cal["event"].to_numpy()[ok]

    # spike multiplier at offset 0 (the release minute), and the offset profile
    prof = {}
    for off in range(-2, 6):
        ii = t0 + off
        ii = ii[(ii >= 1) & (ii < len(close))]
        prof[off] = float(np.nanmean(np.abs(close[ii] / close[ii - 1] - 1.0)) / base)

    # signed return at the release minute (directional tilt?) with a sign-test + bootstrap
    rr = close[t0] / close[t0 - 1] - 1.0
    rr = rr[np.isfinite(rr)]
    mean_signed = float(rr.mean())
    up_frac = float((rr > 0).mean())
    # bootstrap p that mean signed != 0
    bs = np.array([rng.choice(rr, len(rr), replace=True).mean() for _ in range(10000)])
    p_signed = float((bs <= 0).mean() * 2 if mean_signed > 0 else (bs >= 0).mean() * 2)

    return {"base": base, "n": len(rr), "prof": prof, "mean_signed": mean_signed,
            "up_frac": up_frac, "p_signed": p_signed, "rr": rr, "t0": t0, "ev": ev,
            "close": close}


def main() -> int:
    rng = np.random.default_rng(0)
    cal = rc.load_calendar()
    cal830 = cal[cal["Date"].dt.strftime("%H:%M") == "08:30"]

    out = {}
    for inst in ("NQ", "GC"):
        _, df1, *_ = data.load_inputs("4h", instrument=inst)
        out[inst] = reaction(df1, cal830, rng)
        print(f"{inst}: {df1['Date'].iloc[0]} -> {df1['Date'].iloc[-1]}  "
              f"({len(df1):,} 1-min)  matched {out[inst]['n']} of {len(cal830)} 08:30 releases")

    print("\n" + "=" * 78)
    print("REACTION PROFILE — |1-min return| around the 08:30 release, x a normal minute")
    print("=" * 78)
    print(f"{'offset':>7} {'clock':>7} | {'NQ':>8} | {'GC':>8}")
    for off in range(-2, 6):
        clock = (pd.Timestamp('2000-01-01 08:30') + pd.Timedelta(minutes=off)).strftime('%H:%M')
        print(f"{off:>7} {clock:>7} | {out['NQ']['prof'][off]:>7.2f}x | {out['GC']['prof'][off]:>7.2f}x"
              + ("   <== release minute" if off == 0 else ""))

    print("\n" + "=" * 78)
    print("HEAD-TO-HEAD at the release minute")
    print("=" * 78)
    nq0, gc0 = out['NQ']['prof'][0], out['GC']['prof'][0]
    print(f"  NQ spike: {nq0:.2f}x normal    GC spike: {gc0:.2f}x normal    "
          f"GC/NQ = {gc0/nq0:.2f}")
    print(f"  => GOLD {'DOES' if gc0 > 2 else 'does NOT clearly'} react to US macro releases "
          f"({'strongly' if gc0 > 4 else 'moderately' if gc0 > 2 else 'weakly'}).")

    print("\n" + "=" * 78)
    print("DIRECTIONAL TILT at the release minute — is there a systematic sign? (underpowered: 2025-2026)")
    print("=" * 78)
    for inst in ("NQ", "GC"):
        o = out[inst]
        pw = 0.0
        # power to see a mean/sd effect of ~0.15 sd at this n (rough)
        print(f"  {inst}: mean signed return {o['mean_signed']*1e4:>+6.2f} bp   "
              f"up {100*o['up_frac']:.1f}%   bootstrap p={o['p_signed']:.3f}   "
              f"{'<-- tilt?' if o['p_signed'] < 0.05 else '(no directional tilt — as expected)'}")
    print(f"  NOTE: n≈{out['GC']['n']} on 2025-2026 only. A directional GC claim here is UNDERPOWERED and")
    print(f"  frozen/pre-registered — the silver lesson. The |move| spike above is a real measurement; the")
    print(f"  SIGN is not yet decidable without long GC history.")

    print("\n" + "=" * 78)
    print("PER-EVENT-TYPE reaction (which announcements move GC most?) — |move| x normal at release min")
    print("=" * 78)
    for inst in ("NQ", "GC"):
        o = out[inst]
        print(f"  {inst}:")
        for e in sorted(set(o['ev'])):
            m = o['ev'] == e
            ii = o['t0'][m]
            ii = ii[(ii >= 1) & (ii < len(o['close']))]
            if len(ii) < 5:
                continue
            mult = float(np.nanmean(np.abs(o['close'][ii] / o['close'][ii-1] - 1.0)) / o['base'])
            print(f"     {e:<18} n={len(ii):>3}  {mult:>6.2f}x")

    print("\nMEASUREMENT — the |move| spike is real regardless of sample; SIGN/direction on GC is frozen.")
    print("Next (A2/B): per-event-type PATH patterns, and news-conditional trade decisions (close/enter/assist).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
