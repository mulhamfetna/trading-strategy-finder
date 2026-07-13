"""ROBUSTNESS — the user's challenge: "you proved a single scenario of failure. Take 20+ samples and
redo the test. Would the results be the same?"

Fair challenge. Every headline result so far rests on ONE dataset (NQ, 2025-01 -> 2026-05). That is
exactly the kind of single-sample claim this project has spent its whole life attacking in others.

So we re-test three ways:

  1. BOOTSTRAP (N resamples). Resample the surprise events WITH REPLACEMENT and recompute the
     correlation. Gives a confidence interval instead of a point estimate. If the in-sample -0.322
     has a CI straddling zero, it was never real. If the 2026 death has a CI straddling zero, the
     death itself is uncertain and we must say so.

  2. NINE MARKETS. We already own NQ, ES, YM, RTY (equity indices), GC, SI, HG (metals), CL, NG
     (energy). US macro moves ALL of them. If the surprise signal is real it should appear SOMEWHERE.
     If it dies on all nine, the negative result is far stronger than one market could ever make it.
     And the SIGNS are informative: a strong jobs number should plausibly be bearish for equities
     (hawkish Fed) but BULLISH for copper (real demand). If our signal is just an "alarm detector",
     every market moves the same way — which is the falsification test from spec section 3.4, now run
     on nine instruments instead of one.

  3. SPLIT-HALF. Fit on 2025, test on 2026 — per market, not just pooled.

  python3 optimize/fundamentals/robustness.py --n-boot 400
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments                       # noqa: E402
from optimize.fundamentals import release_calendar as rc     # noqa: E402
from optimize.fundamentals.study_surprise import build_surprises, HS   # noqa: E402

H_MAIN = 5          # the horizon that was "significant" in-sample (corr -0.322, p=0.021)


def outcomes_for(df1: pd.DataFrame, sur: pd.DataFrame, h: int):
    """Return (surprise_z, return, year) aligned — only releases this market actually has bars for."""
    idx = pd.Index(df1["Date"])
    close = df1["Close"].to_numpy(dtype=np.float64)
    t0 = idx.get_indexer(sur["Date"])
    ok = (t0 >= 1) & (t0 + h < len(close))
    t0v = t0[ok]
    ret = close[t0v + h] / close[t0v - 1] - 1.0
    return (sur["surprise_z"].to_numpy()[ok], ret, sur["Date"].dt.year.to_numpy()[ok])


def boot_ci(z, ret, n_boot: int, rng) -> tuple[float, float, float]:
    """(point estimate, 2.5th pct, 97.5th pct) of the correlation, by resampling EVENTS."""
    if len(z) < 10:
        return float("nan"), float("nan"), float("nan")
    point = float(np.corrcoef(z, ret)[0, 1])
    n = len(z)
    cs = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        zi, ri = z[i], ret[i]
        if zi.std() == 0 or ri.std() == 0:
            continue
        cs.append(np.corrcoef(zi, ri)[0, 1])
    cs = np.array(cs)
    return point, float(np.percentile(cs, 2.5)), float(np.percentile(cs, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=400)
    ap.add_argument("--h", type=int, default=H_MAIN)
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    cal = rc.load_calendar()
    print("Pulling ALFRED point-in-time surprises (once — macro data is market-independent)...\n")
    sur = build_surprises(cal)
    print(f"\n{len(sur)} releases with a causal surprise\n")
    print("=" * 96)
    print(f"TEST ACROSS ALL 9 MARKETS  ·  horizon h={a.h} min  ·  {a.n_boot} bootstrap resamples")
    print("=" * 96)
    print(f"{'mkt':<5} {'n':>4} | {'FULL corr':>10} {'95% CI':>18} {'real?':>6} | "
          f"{'2025':>8} {'2026':>8} {'held?':>6}")
    print("-" * 96)

    rows = []
    for tok in instruments.TOKENS:
        try:
            _, df1, *_ = data.load_inputs("4h", instrument=tok)
        except Exception as e:                                # noqa: BLE001
            print(f"{tok:<5} UNAVAILABLE ({str(e)[:40]})")
            continue
        z, ret, yr = outcomes_for(df1, sur, a.h)
        if len(z) < 20:
            print(f"{tok:<5} {len(z):>4} | too few releases priced")
            continue

        pt, lo, hi = boot_ci(z, ret, a.n_boot, rng)
        # "real?" = does the 95% bootstrap CI EXCLUDE zero?
        real = "YES" if (lo > 0 or hi < 0) else "no"

        m25, m26 = yr == 2025, yr == 2026
        c25 = float(np.corrcoef(z[m25], ret[m25])[0, 1]) if m25.sum() >= 10 else float("nan")
        c26 = float(np.corrcoef(z[m26], ret[m26])[0, 1]) if m26.sum() >= 10 else float("nan")
        held = "YES" if (not np.isnan(c25) and not np.isnan(c26)
                         and np.sign(c25) == np.sign(c26)) else "no"

        rows.append({"mkt": tok, "n": len(z), "pt": pt, "lo": lo, "hi": hi,
                     "real": real, "c25": c25, "c26": c26, "held": held})
        print(f"{tok:<5} {len(z):>4} | {pt:>+10.3f} [{lo:>+6.3f},{hi:>+6.3f}] {real:>6} | "
              f"{c25:>+8.3f} {c26:>+8.3f} {held:>6}")

    print()
    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    n_real = sum(r["real"] == "YES" for r in rows)
    n_held = sum(r["held"] == "YES" for r in rows)
    print(f"  markets where the FULL-sample correlation is real (95% CI excludes 0): "
          f"{n_real} of {len(rows)}")
    print(f"  markets where the 2025 sign SURVIVED into 2026:                        "
          f"{n_held} of {len(rows)}")
    print()

    # The alarm-detector falsification (spec 3.4), now on 9 markets instead of 1.
    signs = {r["mkt"]: np.sign(r["pt"]) for r in rows}
    same = len(set(signs.values())) == 1
    print(f"  sign of the correlation per market: "
          f"{ {k: ('+' if v > 0 else '-') for k, v in signs.items()} }")
    if same:
        print("  ⚠ ALL markets move the SAME way on a surprise. That is what an ALARM DETECTOR looks")
        print("    like, not a news reader — a strong jobs number cannot be bearish for everything.")
    else:
        print("  markets disagree on sign — consistent with genuine content (e.g. hawkish-Fed bearish")
        print("    for equities but demand-bullish for industrial metals).")
    print()
    if n_real == 0:
        print("  ⇒ NO market shows a real full-sample correlation. The negative result HOLDS,")
        print("    and it now rests on NINE independent markets rather than one.")
    else:
        print(f"  ⇒ {n_real} market(s) show a real correlation — investigate before concluding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
