"""#7 · D2 — THE TAIL INDEX OF RAW NQ 1-MINUTE RETURNS (where the genuine fat tail lives).

D1 showed the champion's per-trade P&L is TRUNCATED by the stop (bounded, light-tailed). The real fat tail
is in the RAW returns — the gaps/slippage that could blow THROUGH the stop live. This estimates how heavy
that tail actually is on 17 years of NQ 1-minute data, following the DIST-01 discipline:

  * BOTH tails separately (loss = left, gain = right) — they need not be equally heavy.
  * TWO methods — Hill estimator and GPD peaks-over-threshold — at SEVERAL thresholds, reported as a RANGE.
    A single Hill/GPD point estimate is unreliable (Bank of Canada 2019); we show the range + diagnostics.
  * PER SESSION — loss-tail heaviness in the loud RTH vs the quiet overnight (S3 found risk is
    session-dependent; expect a heavier tail when the tape is loud).

Tail index alpha: smaller = heavier. alpha>2 => mean & variance exist; alpha<4 => 4th moment may not.
Gaussian would be alpha=infinity. Research expectation: intraday alpha ~2-4 (heavier than daily's ~4-5).

  WSH_DATA_BASE=/home/dev/Mulham python3 -u optimize/fundamentals/study_tail_index.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals.extended_data import load_1m_extended    # noqa: E402
from scipy import stats                                             # noqa: E402


def hill(mag_desc, k):
    """Hill tail-index estimate from the top-k order statistics (mag sorted DESCENDING)."""
    if k < 10 or k + 1 >= len(mag_desc):
        return np.nan
    xk = mag_desc[k]
    if xk <= 0:
        return np.nan
    return 1.0 / np.mean(np.log(mag_desc[:k] / xk))


def gpd_alpha(mag, thr_q):
    """alpha = 1/xi from a GPD peaks-over-threshold fit (xi>0 => heavy). Returns (alpha, xi, n_exc)."""
    u = np.percentile(mag, thr_q)
    exc = mag[mag > u] - u
    if len(exc) < 50:
        return np.nan, np.nan, len(exc)
    xi, loc, beta = stats.genpareto.fit(exc, floc=0)
    alpha = (1.0 / xi) if xi > 1e-6 else np.inf
    return alpha, xi, len(exc)


def tail_report(r, label):
    """Hill (range over k) + GPD (range over threshold) for the loss and gain tails of returns r."""
    print(f"\n{'='*92}\n{label}   (n={len(r):,} returns)\n{'='*92}")
    for side, mag in (("LOSS tail (left)", -r[r < 0]), ("GAIN tail (right)", r[r > 0])):
        mag = np.sort(mag[np.isfinite(mag) & (mag > 0)])[::-1]      # descending magnitudes
        n = len(mag)
        print(f"  {side}  (n={n:,})")
        # Hill across a range of k (fractions of the tail)
        hs = []
        print(f"     Hill:  " + "  ".join(
            f"k={int(f*n)}({int(f*1000)/10}%):{hill(mag, int(f*n)):.2f}"
            for f in (0.001, 0.005, 0.01, 0.02) if int(f*n) >= 10))
        for f in (0.001, 0.005, 0.01, 0.02):
            a = hill(mag, int(f*n))
            if np.isfinite(a):
                hs.append(a)
        # GPD across thresholds
        gp = []
        gstr = []
        for thr in (99.9, 99.5, 99.0, 98.0):
            a, xi, ne = gpd_alpha(mag, thr)
            gstr.append(f"{thr}%:a={a:.2f}(xi={xi:+.2f},n={ne})")
            if np.isfinite(a):
                gp.append(a)
        print(f"     GPD:   " + "  ".join(gstr))
        allr = [x for x in hs + gp if np.isfinite(x)]
        if allr:
            print(f"     => tail index alpha RANGE [{min(allr):.2f}, {max(allr):.2f}]  "
                  f"({'HEAVY, higher moments may not exist' if min(allr) < 4 else 'moderate'})")


def main() -> int:
    df = load_1m_extended("NQ")
    d = df["Date"].to_numpy(); close = df["Close"].to_numpy(float)
    # gap-aware 1-min log returns (exclude halt/weekend steps)
    dt_s = np.diff(d).astype("timedelta64[s]").astype(np.int64)
    r = np.full(len(close), np.nan)
    r[1:] = np.log(close[1:] / close[:-1])
    r[1:][dt_s != 60] = np.nan
    hh = pd.DatetimeIndex(df["Date"]).hour + pd.DatetimeIndex(df["Date"]).minute / 60.0
    rr = r[np.isfinite(r)]
    print(f"\nNQ 17y · {len(rr):,} gap-clean 1-min log returns · "
          f"excess-kurtosis {stats.kurtosis(rr):+.1f} (Gaussian=0), skew {stats.skew(rr):+.2f}")

    tail_report(rr, "ALL SESSIONS")

    # per session (ET): RTH loud vs overnight quiet (S1 definitions)
    rth = np.isfinite(r) & (hh >= 9.5) & (hh < 16)
    onh = np.isfinite(r) & ((hh >= 18) | (hh < 2))
    tail_report(r[rth], "RTH (09:30-16:00 ET, the loud session)")
    tail_report(r[onh], "OVERNIGHT (18:00-02:00 ET, the quiet session)")

    print(f"\n{'='*92}\nREAD\n{'='*92}")
    print("  The RAW-return tail index is the genuine fat tail (D1: the trade P&L is truncated by the stop).")
    print("  A low alpha (<4) in a session = a heavier tail = bigger gap risk of a fill THROUGH the stop")
    print("  there. Compare loss vs gain (asymmetry) and RTH vs overnight (session risk). This sets, per")
    print("  session/event, how much room the stop needs. Next: D3 = McNeil-Frey (GARCH filter -> GPD on")
    print("  residuals) to condition the tail on volatility state and de-cluster it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
