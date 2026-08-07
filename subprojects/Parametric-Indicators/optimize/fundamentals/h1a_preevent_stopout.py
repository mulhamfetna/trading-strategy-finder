"""WS-NEWS2 Phase 1, H1-A (#115) — can we survive the wait to a release?

THE QUESTION, in the owner's words: *"we may decide to enter and ride the news change and make huge
profit — but we will study that we don't hit the stops before the news time, so we don't benefit from
the news and we make only loss."*

If a position opened before a release is stopped out BEFORE the release fires, the news never helps and
the trade is a pure loss. **That risk is measurable today, with no consensus data at all** — it is pure
price behaviour — and if survival is poor, Phase 1 dies cheaply and direction never matters.

WHAT IS ALREADY KNOWN AND FRAMES THIS

  · Experiment #11 — the market goes QUIET before a release: **0.78x normal at −2 min**.
    ⇒ encouraging: a quiet market is a low stop-out environment.
  · Experiment #15 — there is NO information leak: 07:45–08:28 runs 0.81–0.89x vs control.
    ⇒ discouraging: nothing leaks, so a pre-positioned trade is NOT an informed trade unless
      `previous` and `forecast` themselves carry direction (that is H1-B/H1-C, and needs consensus).
  · Experiment #10 — the release itself is **8.32x** at offset 0.

⚠️ THE DUMB CONTROL IS NOT OPTIONAL HERE. "97% survive" means nothing on its own — an ordinary quiet
   minute would also survive. The question is whether the pre-release window is UNUSUALLY safe, so the
   identical measurement runs on matched non-release days at the SAME CLOCK TIME. Without that, the
   market's normal calm gets reported as a property of news.

⚠️ DIRECTION IS UNKNOWN, SO BOTH SIDES ARE MEASURED. We do not know which way we would enter, so the
   script reports the stop-out rate for a LONG and for a SHORT separately. Reporting only the kinder
   one would be choosing the answer.

    WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 optimize/fundamentals/h1a_preevent_stopout.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
CAL = HERE / "us_high_impact.csv"
# ⚠️ Per-instrument filename. A single fixed path meant running NQ then GC SILENTLY OVERWROTE the
# first result — the kind of loss that leaves no trace and is discovered only when a number looks odd.
def out_path(instrument: str) -> Path:
    return HERE / f"h1a_stopout_{instrument}.json"

# Pre-registered grid — this IS the whole search for H1-A (criterion P1-C3 in #115).
WAITS = [5, 15, 30, 60]          # minutes held BEFORE the release

# ⚠️ STOPS ARE IN PERCENT OF PRICE, NOT POINTS.
# The first version used absolute points, which is NOT comparable across instruments and produced a
# nonsense cross-instrument result: a 40-point stop is 0.13% of NQ at 29,880 but 1.3% of GC at ~3,000
# — ten times wider. GC therefore showed near-zero stop-outs and looked "calmer", when in truth its
# stop was effectively enormous. Percent of entry price makes the risk equivalent.
STOPS_PCT = [0.05, 0.10, 0.20, 0.40]
N_CELLS = len(WAITS) * len(STOPS_PCT)


def measure(df, stamps, waits, stops_pct, label, out):
    """Fraction of positions stopped out during [T−wait, T) — long side and short side separately."""
    import numpy as np
    import pandas as pd

    idx = pd.Index(df["Date"])
    hi = df["High"].to_numpy(float)
    lo = df["Low"].to_numpy(float)
    op = df["Open"].to_numpy(float)

    pos = idx.get_indexer(pd.DatetimeIndex(stamps).floor("min"))
    pos = pos[pos >= 0]
    print(f"\n  {label}: {len(pos)} events matched to a bar")
    if len(pos) == 0:
        return

    print(f"    {'wait':>6} {'stop':>6} {'n':>6} {'LONG stopped':>14} {'SHORT stopped':>15} "
          f"{'either':>9}   (stop in points)")
    for w in waits:
        starts = pos - w
        ok = starts >= 0
        s, e = starts[ok], pos[ok]
        entry = op[s]
        # worst excursion against each side during the wait
        adverse_long = np.array([entry[i] - lo[s[i]:e[i]].min() if e[i] > s[i] else 0.0
                                 for i in range(len(s))])
        adverse_short = np.array([hi[s[i]:e[i]].max() - entry[i] if e[i] > s[i] else 0.0
                                  for i in range(len(s))])
        for pct in stops_pct:
            stop = entry * (pct / 100.0)          # stop distance in POINTS, per-event, from % of price
            L = float((adverse_long >= stop).mean())
            S = float((adverse_short >= stop).mean())
            either = float(((adverse_long >= stop) | (adverse_short >= stop)).mean())
            print(f"    {w:>5}m {pct:>5.2f}% {len(s):>6} {L:>13.1%} {S:>14.1%} {either:>8.1%}"
                  f"   (median {float(np.median(stop)):.1f} pts)")
            out.append({"set": label, "wait_min": w, "stop_pct": pct,
                        "median_stop_pts": float(np.median(stop)), "n": int(len(s)),
                        "long_stopped": L, "short_stopped": S, "either_stopped": either,
                        "median_adverse_long": float(np.median(adverse_long)),
                        "median_adverse_short": float(np.median(adverse_short))})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ")
    a = ap.parse_args()

    import numpy as np
    import pandas as pd
    from optimize.fundamentals.extended_data import load_1m_extended

    cal = pd.read_csv(CAL, parse_dates=["Date"])
    df = load_1m_extended(a.instrument)
    print("=" * 96)
    print(f"WS-NEWS2 Phase 1 H1-A (#115) — pre-release stop-out risk, {a.instrument}")
    print("=" * 96)
    print(f"  releases        : {len(cal):,}  ({cal.Date.min():%Y-%m-%d} .. {cal.Date.max():%Y-%m-%d})")
    print(f"  price frame     : {df.Date.min()} -> {df.Date.max()}  ({len(df):,} bars)")
    print(f"  pre-registered  : waits {WAITS} min x stops {STOPS_PCT} % = {N_CELLS} cells (WHOLE SEARCH)")
    print(f"  ⚠️ both LONG and SHORT reported — direction is unknown, so neither side is chosen")

    out: list[dict] = []
    measure(df, cal["Date"], WAITS, STOPS_PCT, "RELEASES", out)

    # ---- dumb control: same clock times, days with NO release ----------------------------------
    rng = np.random.default_rng(20260807)
    real_days = set(pd.DatetimeIndex(cal["Date"]).normalize())
    lo_d, hi_d = df.Date.min(), df.Date.max()
    ctrl = []
    for t in cal["Date"]:
        for _ in range(40):
            shift = int(rng.integers(3, 500)) * (1 if rng.random() < 0.5 else -1)
            c = pd.Timestamp(t) - pd.Timedelta(days=shift)
            if c.normalize() in real_days or c < lo_d or c > hi_d or c.weekday() >= 5:
                continue
            ctrl.append(c)
            break
    print(f"\n  control timestamps drawn: {len(ctrl)} (same clock minutes, NO release that day)")
    measure(df, ctrl, WAITS, STOPS_PCT, "CONTROL", out)

    OUT = out_path(a.instrument)
    OUT.write_text(json.dumps({"instrument": a.instrument, "waits": WAITS, "stops_pct": STOPS_PCT,
                               "results": out}, indent=1))
    print(f"\nwrote -> {OUT}")

    # ---- the verdict, stated against the control, never on its own -----------------------------
    rel = {(r["wait_min"], r["stop_pct"]): r for r in out if r["set"] == "RELEASES"}
    ctl = {(r["wait_min"], r["stop_pct"]): r for r in out if r["set"] == "CONTROL"}
    print("\n" + "=" * 96)
    print("VERDICT — release window vs a matched ordinary window")
    print("=" * 96)
    print(f"  {'wait':>6} {'stop':>6} {'release either':>16} {'control either':>16} {'ratio':>8}")
    for w in WAITS:
        for s in STOPS_PCT:
            r, c = rel.get((w, s)), ctl.get((w, s))
            if not r or not c:
                continue
            ratio = r["either_stopped"] / c["either_stopped"] if c["either_stopped"] else float("nan")
            print(f"  {w:>5}m {s:>5.2f}% {r['either_stopped']:>15.1%} {c['either_stopped']:>15.1%} "
                  f"{ratio:>7.2f}x")
    print("\n  ratio < 1  ⇒ the pre-release window is SAFER than an ordinary one (consistent with the")
    print("               measured 0.78x pre-release quiet)")
    print("  ratio > 1  ⇒ it is MORE dangerous, and pre-positioning pays a premium for the privilege")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
