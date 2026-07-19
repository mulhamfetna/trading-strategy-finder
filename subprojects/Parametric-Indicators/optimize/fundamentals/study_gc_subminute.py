"""Task #20 — HOW FAST does gold price a macro release? (1-SECOND resolution)

THE QUESTION. The 1-minute study proved that 100% of gold's inverse macro reaction lands inside the
release MINUTE: the un-tradeable jump carries +$132/release (t=+7.13) and everything after the print is
+$5.37 (t=0.52, noise). But "inside one minute" was our MEASUREMENT FLOOR, not a fact about the world.
A minute is a long time. If the last of that move actually lands at +30 seconds, then someone reading
the number at +2s still has something to trade. If it is done in 2 seconds, the door is shut.

WHAT WE MEASURE. For each release we take the 1-second bars from T-10s to T+60s and build the
anti-signal position: SHORT gold on a positive surprise, LONG on a negative one (the direction the
1-minute study established). We then report the CUMULATIVE P&L of that position as a function of how
many seconds after the print you managed to get in.

  entry at +k seconds  =>  captures  close[T+60s] - close[T+k]   (times -sign(surprise))

If the curve is flat from k=1 onward, the move is already over by the first second and there is nothing
to trade at any achievable speed. If it decays gradually, the decay rate IS the execution budget.

CAUSALITY: the surprise is known at T (the print). We never enter before T. Entry at +k uses the close
of second k, so we pay for the move we did not see coming.

THE NULL: the same shuffle control used throughout — permute the surprises and recompute. A curve that
a random surprise reproduces is not a curve.

  python3 optimize/fundamentals/study_gc_subminute.py --instrument GC
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals import release_calendar as rc                # noqa: E402
from optimize.fundamentals.extended_data import load_1s_windows         # noqa: E402
from optimize.fundamentals.study_surprise import build_surprises        # noqa: E402

PRE_S = 10          # seconds of context before the print
POST_S = 60         # seconds after the print we track


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="GC")
    ap.add_argument("--n-shuffle", type=int, default=2000)
    ap.add_argument("--point-value", type=float, default=100.0, help="GC = $100/point")
    a = ap.parse_args()

    sur = build_surprises(rc.load_calendar())
    sur = sur.dropna(subset=["z"]) if "z" in sur.columns else sur
    print(f"\n{len(sur)} releases with a causal surprise")

    # One pass over the multi-GB 1-second file for ALL release windows.
    windows = [(t - pd.Timedelta(seconds=PRE_S), t + pd.Timedelta(seconds=POST_S))
               for t in pd.to_datetime(sur["Date"])]
    print(f"pulling {len(windows)} x {PRE_S + POST_S}s windows from the 1-second file "
          f"(one pass, byte-seek)...")
    sec = load_1s_windows(windows, instrument=a.instrument)
    print(f"  got {len(sec):,} one-second bars")

    idx = pd.Series(np.arange(len(sec)), index=sec["Date"].values)

    rows, zs = [], []
    for _, r in sur.iterrows():
        t = pd.Timestamp(r["Date"])
        z = float(r["z"])
        # closes at T+0 .. T+POST_S, second by second
        want = [t + pd.Timedelta(seconds=k) for k in range(POST_S + 1)]
        pos = idx.reindex(want)
        if pos.isna().any():          # a gap in the tape => skip, never interpolate a price
            continue
        closes = sec["Close"].values[pos.values.astype(int)]
        rows.append(closes)
        zs.append(z)

    if not rows:
        print("no releases with complete 1-second coverage")
        return 1

    C = np.asarray(rows, dtype=float)          # (n, POST_S+1) close prices
    z = np.asarray(zs, dtype=float)
    n = len(z)
    print(f"\n{n} releases with COMPLETE 1-second coverage across the window\n")

    final = C[:, POST_S]
    rng = np.random.default_rng(0)

    print("=" * 84)
    print(f"{a.instrument}: anti-signal P&L vs HOW LATE YOU GOT IN")
    print("  (short on a positive surprise / long on a negative one; hold to +60s)")
    print("=" * 84)
    print(f"{'entry':>8} | {'points':>8} | {'$/release':>11} | {'t-stat':>7} | {'shuffled $':>12}")
    print("-" * 84)

    for k in (0, 1, 2, 3, 5, 10, 15, 20, 30, 45):
        pnl = -np.sign(z) * (final - C[:, k])
        t = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(n)) if pnl.std(ddof=1) > 0 else 0.0
        sh = np.array([(-np.sign(rng.permutation(z)) * (final - C[:, k])).mean()
                       for _ in range(a.n_shuffle)])
        star = "  <-- CANNOT trade (before/at the print)" if k == 0 else ""
        print(f"{('T+' + str(k) + 's'):>8} | {pnl.mean():+8.3f} | {a.point_value * pnl.mean():+11.2f} "
              f"| {t:+7.2f} | {a.point_value * sh.mean():+7.2f}±{a.point_value * sh.std():.0f}{star}")

    # How much of the total 0->60s move is already done by second k?
    print("\n" + "=" * 84)
    print("PRICE DISCOVERY CURVE — what fraction of the full 60s move is complete by +k seconds?")
    print("=" * 84)
    move = -np.sign(z)[:, None] * (C - C[:, 0][:, None])       # anti-signal cum. move from T+0
    total = move[:, POST_S]
    denom = total.mean()
    for k in (1, 2, 3, 5, 10, 15, 20, 30, 45, 60):
        frac = move[:, k].mean() / denom if denom != 0 else float("nan")
        bar = "#" * max(0, min(50, int(round(50 * frac))))
        print(f"  +{k:>2}s  {100 * frac:6.1f}%  {bar}")

    print("\nREAD THIS AS: if the curve is already ~100% by +1s, the release is priced before any human")
    print("or system could react, and no execution speed recovers it. If it climbs gradually, the slope")
    print("is the execution budget — and the $/release column above is what that speed is worth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
