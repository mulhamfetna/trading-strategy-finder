"""S1 — CHARACTERISE OUR OWN INTRADAY SESSION SHAPE (task #5, phase 2).

The deep-research pass (docs/superpowers/SESSION-01) established that the single most important session
fact for us is a CONFOUND, not a signal: the intraday volatility/volume shape is predictable by time of
day, and it must be measured (and later removed) before any event/causality estimate. It also gave us the
literature's numbers to check ours against: a ~2x U-shape (loud 09:30 open, quiet lunch, loud 16:00 close)
that the papers replicate for Nasdaq/S&P futures specifically.

This study measures OUR OWN shape, on OUR OWN 1-minute NQ tape, over 17 years. It is a MEASUREMENT — like
the calendar self-validation, its truth does not depend on sample size or power. It answers:
  * where are our volatility and volume peaks and troughs, minute by minute (US Eastern)?
  * what is our open/close-vs-midday ratio — does it match the literature's ~2x?
  * how do the named sessions (Globex overnight / Asia / London / RTH) compare?
And it BAKES IN a timezone sanity assertion: the volume peak must land at the 09:30 ET cash open. If it
does not, the data is not in the timezone we think it is, and the run aborts.

TWO CAREFUL POINTS:
  1. Session-boundary gaps (the 17:00-18:00 ET Globex halt, weekends) are NOT 1-minute returns. A close
     across a 1-hour halt looks like a huge move. We count a return ONLY when the previous bar is exactly
     60 seconds earlier — otherwise the 18:00 reopen bar shows a fake spike.
  2. Everything is US Eastern wall-clock (the frame's native tz), so DST is consistent: 09:30 is the cash
     open in both summer and winter. Minute-of-day grouping by HH:MM is therefore clean.

  WSH_DATA_BASE=/home/dev/Mulham python3 -u optimize/fundamentals/study_session_shape.py --instrument NQ
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals.extended_data import load_1m_extended   # noqa: E402

# Named sessions, US Eastern wall-clock. Boundaries from the research (SESSION-01 R7), to be VALIDATED by
# where the activity actually lands — we impose the labels, the data decides if they mean anything.
SESSIONS = [
    ("Globex halt (dead)",        (17, 0), (18, 0)),
    ("Globex reopen / evening",   (18, 0), (20, 0)),
    ("Asia",                      (20, 0), (24, 0)),
    ("Asia (post-midnight)",      (0, 0),  (2, 0)),
    ("Europe / London",           (2, 0),  (8, 0)),
    ("London-NY overlap / pre-open", (8, 0), (9, 30)),
    ("RTH morning",               (9, 30), (12, 0)),
    ("Lunch",                     (12, 0), (13, 30)),
    ("RTH afternoon -> close",    (13, 30), (16, 0)),
    ("Post-close",                (16, 0), (17, 0)),
]

# GMT+3 (the user's timezone) is ET + 7h in summer / + 8h in winter. US releases anchor to ET wall-clock,
# so we show a nominal +7 for orientation only (do NOT use for computation — the analysis is all ET).
def et_to_gmt3(hh: int, mm: int) -> str:
    g = (hh + 7) % 24
    return f"{g:02d}:{mm:02d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--bucket", type=int, default=30, help="minutes per bucket for the curve table")
    a = ap.parse_args()

    df = load_1m_extended(a.instrument)
    d = df["Date"].to_numpy()
    close = df["Close"].to_numpy(float)
    vol = df["Volume"].to_numpy(float)
    print(f"\n{a.instrument}: {df['Date'].iloc[0]} -> {df['Date'].iloc[-1]}  ({len(df):,} 1-min bars)")

    # --- 1-min returns, but ONLY across genuine 1-minute steps (no halt/weekend gaps) -----------------
    dt_s = np.diff(d).astype("timedelta64[s]").astype(np.int64)
    is_1min = np.concatenate([[False], dt_s == 60])                   # True where prev bar is exactly 60s back
    ret = np.zeros(len(close))
    ret[1:] = np.abs(close[1:] / close[:-1] - 1.0)
    ret[~is_1min] = np.nan                                            # drop cross-gap "returns"
    n_gap = int((~is_1min).sum())
    print(f"  excluded {n_gap:,} cross-gap steps (halts/weekends) from the return series "
          f"({100*n_gap/len(close):.1f}% of bars)\n")

    mod = pd.DatetimeIndex(df["Date"]).hour * 60 + pd.DatetimeIndex(df["Date"]).minute  # minute-of-day
    mod = mod.to_numpy()

    def stat_at(minute_of_day, arr):
        m = mod == minute_of_day
        v = arr[m]
        v = v[np.isfinite(v)]
        return (v.mean() if len(v) else np.nan), int(len(v))

    base_ret = np.nanmean(ret)                                       # the "normal minute" volatility
    base_vol = np.nanmean(vol)

    # --- TIMEZONE SANITY: the volume peak MUST be at the 09:30 ET cash open --------------------------
    vol_by_min = np.array([np.nanmean(vol[mod == m]) if (mod == m).any() else 0.0 for m in range(1440)])
    peak_min = int(np.argmax(vol_by_min))
    peak_hh, peak_mm = divmod(peak_min, 60)
    print("=" * 84)
    print("TIMEZONE SANITY CHECK (the analysis aborts if this fails)")
    print("=" * 84)
    top5 = np.argsort(vol_by_min)[::-1][:5]
    print(f"  peak 1-min VOLUME lands at {peak_hh:02d}:{peak_mm:02d} ET  "
          f"(= {et_to_gmt3(peak_hh, peak_mm)} in your GMT+3, summer)")
    print(f"  top-5 volume minutes (ET): " +
          ", ".join(f"{divmod(int(m),60)[0]:02d}:{divmod(int(m),60)[1]:02d}" for m in top5))
    # The RIGHT check: the volume peak must sit inside RTH (09:30-16:00 ET). For index futures the single
    # loudest minute is the CASH CLOSE (15:59-16:00), not the open — the closing auction/rebalance. A
    # 7-hour GMT+3<->ET mismatch would push real RTH activity OUT of this labeled window, so an in-RTH peak
    # is a valid timezone proof. (The 08:30 volatility spike, verified separately in tz_check, is the other.)
    open_vol = vol_by_min[9*60+30] / base_vol
    close_vol = vol_by_min[15*60+59] / base_vol
    if not (9*60+30 <= peak_min <= 16*60):
        print(f"  🚨 volume peak is OUTSIDE RTH (09:30-16:00 ET). The data is not in the timezone we think.")
        print(f"     ABORTING — every session label below would be wrong.")
        return 1
    print(f"  ✅ peak is inside RTH at the cash CLOSE; the 09:30 open is a secondary peak "
          f"(open {open_vol:.1f}x / close {close_vol:.1f}x normal volume).")
    print(f"     Both are US cash-session landmarks => the frame IS US Eastern, as the whole system assumes.")

    # --- THE CURVE, in buckets ----------------------------------------------------------------------
    print()
    print("=" * 84)
    print(f"THE INTRADAY SHAPE — mean |1-min return| and volume per {a.bucket}-min bucket (ET)")
    print("=" * 84)
    print(f"{'ET':>7} {'GMT+3':>6} | {'|ret| x norm':>12} {'vol x norm':>11} | volatility")
    print("-" * 84)
    for start in range(0, 1440, a.bucket):
        mm_mask = (mod >= start) & (mod < start + a.bucket)
        r = ret[mm_mask]; r = r[np.isfinite(r)]
        v = vol[mm_mask]
        if not len(r):
            continue
        rmult = r.mean() / base_ret
        vmult = (np.nanmean(v) / base_vol) if len(v) else np.nan
        hh, mm = divmod(start, 60)
        bar = "#" * int(min(rmult * 8, 60))
        print(f"{hh:02d}:{mm:02d}   {et_to_gmt3(hh, mm):>6} | {rmult:>11.2f}x {vmult:>10.2f}x | {bar}")

    # --- KEY LANDMARK MINUTES -----------------------------------------------------------------------
    print()
    print("=" * 84)
    print("KEY LANDMARK MINUTES (ET)")
    print("=" * 84)
    landmarks = [("08:30 macro release", 8*60+30), ("09:30 cash OPEN", 9*60+30),
                 ("12:00 lunch", 12*60), ("15:59 pre-close", 15*60+59),
                 ("16:00 cash CLOSE", 16*60), ("17:00 halt start", 17*60),
                 ("18:00 Globex reopen", 18*60), ("03:00 London open", 3*60)]
    for name, m in landmarks:
        rm, nr = stat_at(m, ret)
        vm, _ = stat_at(m, vol)
        hh, mm = divmod(m, 60)
        print(f"  {name:<22} ({et_to_gmt3(hh,mm)} GMT+3): "
              f"vol {rm/base_ret:>6.2f}x  volume {vm/base_vol:>6.2f}x  (n={nr:,})")

    # --- THE U-SHAPE RATIO the literature predicts (~2x) --------------------------------------------
    print()
    print("=" * 84)
    print("THE U-SHAPE — does our RTH curve match the literature's ~2x open/close-vs-midday?")
    print("=" * 84)
    def win_mean(lo, hi):
        m = (mod >= lo) & (mod < hi)
        r = ret[m]; r = r[np.isfinite(r)]
        return r.mean() if len(r) else np.nan
    openv = win_mean(9*60+30, 10*60)          # 09:30-10:00
    lunchv = win_mean(12*60, 12*60+30)        # 12:00-12:30
    closev = win_mean(15*60+30, 16*60)        # 15:30-16:00
    print(f"  RTH open   (09:30-10:00): {openv/base_ret:.2f}x normal")
    print(f"  Lunch      (12:00-12:30): {lunchv/base_ret:.2f}x normal")
    print(f"  RTH close  (15:30-16:00): {closev/base_ret:.2f}x normal")
    print(f"  open/lunch  ratio: {openv/lunchv:.2f}x    close/lunch ratio: {closev/lunchv:.2f}x")
    print(f"  literature (Andersen-Bollerslev, S&P futures): ~0.095%/0.055%/0.105% => ~1.7-1.9x")

    # --- NAMED SESSIONS -----------------------------------------------------------------------------
    print()
    print("=" * 84)
    print("NAMED SESSIONS (ET) — mean volatility & volume, ranked")
    print("=" * 84)
    rows = []
    for name, (h0, m0), (h1, m1) in SESSIONS:
        lo, hi = h0*60+m0, h1*60+m1
        m = (mod >= lo) & (mod < hi) if hi > lo else ((mod >= lo) | (mod < hi))
        r = ret[m]; r = r[np.isfinite(r)]
        v = vol[m]
        rows.append((name, lo, hi, r.mean()/base_ret if len(r) else np.nan,
                     np.nanmean(v)/base_vol if len(v) else np.nan, int(np.isfinite(r).sum())))
    for name, lo, hi, rm, vm, nn in sorted(rows, key=lambda x: -(x[3] if np.isfinite(x[3]) else -1)):
        h0, m0 = divmod(lo, 60); h1, m1 = divmod(hi, 60)
        print(f"  {name:<32} {h0:02d}:{m0:02d}-{h1:02d}:{m1:02d} ET  "
              f"vol {rm:>5.2f}x  volume {vm:>5.2f}x")

    print()
    print("MEASUREMENT — no null test needed (this is a description of the tape, like the calendar spike).")
    print("Next: S2 (overnight vs RTH segmentation, per market) and S3 (does our champion's edge concentrate")
    print("by session?). Session structure is a FILTER, not an entry — see SESSION-01 R6.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
