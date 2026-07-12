"""Does the post-release move PERSIST or REVERSE? A descriptive study — no strategy, nothing tuned.

THE QUESTION (the user's own, from the brainstorm): after the print, "do the direction stayed as the
pre and while news said, so we continue in the open trade, or it reversed itself?"

THE POINT: this needs NO consensus, NO actual, NO content model, NO vendor. Just the validated release
timestamps (free) and NQ's own price. If the first k minutes of post-release movement predict the next
h minutes, then "enter at T+k in the direction of the initial move" is a tradeable ENTRY at the most
violent minutes of the month — which is the standing project direction (increase entries), and the
opposite of the veto we just killed.

CAUSALITY. For a release at minute T:
    reaction    = close[T+k] / close[T-1] - 1      known at T+k
    followthru  = close[T+h] / close[T+k] - 1      happens AFTER T+k
T-1 is the last bar BEFORE the print (the same causal anchor the NEWS_VETO exit uses). We enter at
T+k using only the reaction, and we are scored on the follow-through. Nothing peeks.

HONESTY. Sweeping k x h is a grid, and with only ~103 events some cells WILL look brilliant by chance.
So every statistic is also computed on N FAKE calendars (same count, same times of day, random
release-free dates — optimize/fundamentals/nulltest.py). A cell only means something if the real value
stands outside the fake distribution. Same discipline that killed the veto.

  python3 optimize/fundamentals/study_postrelease.py --n-fake 50
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data                                     # noqa: E402
from optimize.fundamentals import nulltest                    # noqa: E402
from optimize.fundamentals import release_calendar as rc      # noqa: E402

KS = [1, 2, 3, 5, 10, 15]              # minutes after the print at which we would enter
HS = [15, 30, 60, 120, 240]            # minutes we would then hold
POINT_VALUE_NQ = 20.0                  # $/point, optimize/instruments.py


def _stats(df1: pd.DataFrame, cal: pd.DataFrame, k: int, h: int) -> dict | None:
    """Reaction (T-1 -> T+k) vs follow-through (T+k -> T+h), over every release in `cal`."""
    idx = pd.Index(df1["Date"])
    close = df1["Close"].to_numpy(dtype=np.float64)
    n = len(close)

    t0 = idx.get_indexer(cal["Date"])                 # the release minute; -1 if that bar is absent
    ok = t0 >= 0
    t0 = t0[ok]
    anchor, entry, exit_ = t0 - 1, t0 + k, t0 + h
    good = (anchor >= 0) & (exit_ < n)
    anchor, entry, exit_ = anchor[good], entry[good], exit_[good]
    if len(entry) < 20:
        return None

    reaction = close[entry] / close[anchor] - 1.0
    followthru = close[exit_] / close[entry] - 1.0

    side = np.sign(reaction)                          # +1 momentum long, -1 momentum short
    live = side != 0
    side, reaction, followthru = side[live], reaction[live], followthru[live]
    if len(side) < 20:
        return None

    # P/L in $ of: enter at T+k in the direction of the reaction, 1 contract, exit at T+h.
    pnl = side * followthru * close[entry[live]] * POINT_VALUE_NQ

    return {
        "k": k, "h": h, "n": int(len(side)),
        "corr": float(np.corrcoef(reaction, followthru)[0, 1]),
        "hit": float((np.sign(followthru) == side).mean()),      # >0.5 = momentum, <0.5 = reversal
        "pnl_per_trade": float(pnl.mean()),
        "pnl_total": float(pnl.sum()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h", help="only used to load the 1-min frame")
    ap.add_argument("--n-fake", type=int, default=50)
    a = ap.parse_args()

    _, df1, *_ = data.load_inputs(a.tf)
    cal = rc.load_calendar()
    print(f"NQ 1-min · {len(cal)} releases · {df1['Date'].iloc[0]} -> {df1['Date'].iloc[-1]}\n")

    # h must be strictly beyond k, or entry and exit land on the same bar (zero-length hold).
    real = [r for k in KS for h in HS if h > k and (r := _stats(df1, cal, k, h))]

    # the same grid on fake calendars — the noise floor
    fakes: dict[tuple[int, int], list[dict]] = {(r["k"], r["h"]): [] for r in real}
    for s in range(a.n_fake):
        fc = nulltest.fake_calendar(cal, df1, seed=s)
        for k, h in fakes:
            if (r := _stats(df1, fc, k, h)):
                fakes[(k, h)].append(r)

    print(f"{'k':>3} {'h':>4} {'n':>4} | {'corr':>6} {'hit%':>6} {'$/trade':>9} {'$ total':>10} "
          f"| {'fake $/trade':>14} | {'p':>5}")
    print("-" * 84)

    rows = []
    for r in real:
        f = fakes[(r["k"], r["h"])]
        fpt = np.array([x["pnl_per_trade"] for x in f]) if f else np.array([0.0])
        # two-sided: is the real |edge| bigger than a fake one?
        better = int((np.abs(fpt) >= abs(r["pnl_per_trade"])).sum())
        p = (better + 1) / (len(fpt) + 1)
        rows.append({**r, "fake_mean": float(fpt.mean()), "fake_sd": float(fpt.std()), "p": p})
        star = " <<<" if p < 0.05 else ""
        print(f"{r['k']:>3} {r['h']:>4} {r['n']:>4} | {r['corr']:>+6.2f} {100*r['hit']:>5.1f}% "
              f"{r['pnl_per_trade']:>+9.0f} {r['pnl_total']:>+10.0f} "
              f"| {fpt.mean():>+8.0f} ±{fpt.std():>4.0f} | {p:>5.3f}{star}")

    print()
    best = max(rows, key=lambda r: abs(r["pnl_per_trade"]))
    sig = [r for r in rows if r["p"] < 0.05]
    print(f"strongest cell: k={best['k']} h={best['h']}  "
          f"${best['pnl_per_trade']:+,.0f}/trade over {best['n']} releases  "
          f"(hit {100*best['hit']:.1f}%, p={best['p']:.3f})")
    print(f"cells with p<0.05: {len(sig)} of {len(rows)}  "
          f"(expect ~{0.05*len(rows):.1f} by chance alone — that is the multiple-comparisons floor)")
    print()
    if not sig:
        print("VERDICT: no post-release structure. The initial move does NOT predict the follow-through.")
        print("         A content/surprise model would have to carry the direction entirely alone.")
    else:
        print("VERDICT: candidate structure found. NOT yet a strategy — next step is out-of-sample")
        print("         (measure on 2025, confirm on 2026) before believing any of it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
