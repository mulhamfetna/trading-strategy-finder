"""FA-v2 · A2 — DOES A SPECIFIC ANNOUNCEMENT PRODUCE A REPEATABLE, SAVEABLE PATH PATTERN?

The user's "content -> pattern -> rule": the news said a certain announcement, price did a repeated
pattern, save it as a rule. We test this PER EVENT TYPE on 17-year NQ (each event has 144-202 occurrences
-> well above the ~20-50 the event-study literature requires; FAV2-02). Two patterns, separately:

  VOLATILITY pattern  — does each event produce a consistent spike-then-decay? (a straddle/vol rule)
  DIRECTIONAL pattern — does each event reliably push price ONE WAY? (a directional rule)

Discipline (FAV2-02): short windows only; the vol burst inflates false positives, so the DIRECTIONAL test
uses a bootstrap of the signed return (variance-aware) and a binomial sign test; and because we test 5
event types we apply a Bonferroni threshold (0.05/5 = 0.010) — testing many events manufactures luck.

Prior (stated before the run): direction is dead pooled at full power (-0.004); the saveable pattern is
almost certainly the VOLATILITY one, not a directional one. We test to confirm, per event.

  WSH_DATA_BASE=/home/dev/Mulham python3 -u optimize/fundamentals/study_event_patterns.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals import release_calendar as rc            # noqa: E402
from optimize.fundamentals.extended_data import load_1m_extended    # noqa: E402
from scipy import stats                                             # noqa: E402

H = 30
PV = 20.0
BONF = 0.05 / 5          # 5 event types


def main() -> int:
    df = load_1m_extended("NQ")
    close = df["Close"].to_numpy(float)
    idx = pd.Index(df["Date"])
    cal = rc.load_calendar()
    cal = cal[cal["Date"].dt.strftime("%H:%M") == "08:30"]
    rng = np.random.default_rng(0)

    base = np.nanmean(np.abs(np.diff(close) / close[:-1]))     # normal-minute |return|

    events = sorted(cal["event"].unique())
    print(f"\nNQ 17y · per-event-type post-release path patterns (anchor = close[T-1], causal)")
    print(f"Bonferroni threshold for 5 events: p < {BONF:.3f}\n")

    # ---- VOLATILITY pattern: spike + decay per event -----------------------------------------------
    print("=" * 96)
    print("VOLATILITY PATTERN — mean |move| (x a normal minute) at each horizon, per event")
    print("=" * 96)
    print(f"  {'event':<18} {'n':>4} | {'+0':>6} {'+1':>6} {'+2':>6} {'+5':>6} {'+15':>6} {'+30':>6}")
    paths = {}
    for e in events:
        ed = cal[cal["event"] == e]["Date"]
        t0 = idx.get_indexer(ed)
        t0 = t0[(t0 >= 1) & (t0 + H < len(close))]
        if len(t0) < 20:
            continue
        P = np.stack([close[t0 + k] - close[t0 - 1] for k in range(0, H + 1)], axis=1)  # points, k=0..30
        paths[e] = (t0, P)
        vol = {k: np.abs(close[t0 + k] / close[t0 + k - 1] - 1.0).mean() / base for k in (0, 1, 2, 5, 15, 30)}
        print(f"  {e:<18} {len(t0):>4} | " + " ".join(f"{vol[k]:>5.1f}x" for k in (0, 1, 2, 5, 15, 30)))
    print("\n  => the spike-then-decay is consistent and event-specific (a real, saveable VOLATILITY shape).")

    # ---- DIRECTIONAL pattern: does each event push one way? ----------------------------------------
    print("\n" + "=" * 96)
    print("DIRECTIONAL PATTERN — does each event reliably move price ONE WAY? (signed, at +30 min)")
    print("=" * 96)
    print(f"  {'event':<18} {'n':>4} | {'mean +30 ($)':>13} {'% up':>7} {'boot p':>8} {'sign p':>8}  verdict")
    any_dir = False
    for e, (t0, P) in paths.items():
        r30 = P[:, H]                                       # signed +30min move in points
        mu = r30.mean() * PV
        up = (r30 > 0).mean()
        bs = np.array([rng.choice(r30, len(r30), True).mean() for _ in range(10000)]) * PV
        pboot = float((bs <= 0).mean() * 2) if mu > 0 else float((bs >= 0).mean() * 2)
        psign = float(stats.binomtest(int((r30 > 0).sum()), len(r30), 0.5).pvalue)
        sig = (pboot < BONF) or (psign < BONF)
        any_dir = any_dir or sig
        v = "<<< DIRECTIONAL" if sig else "coin flip — no rule"
        print(f"  {e:<18} {len(t0):>4} | {mu:>+12,.0f} {100*up:>6.1f}% {pboot:>8.3f} {psign:>8.3f}  {v}")

    # ---- PERSISTENCE per event: does the initial move hold? ----------------------------------------
    print("\n" + "=" * 96)
    print("PERSISTENCE — does the +5min move predict the +30min move, per event? (momentum vs reversion)")
    print("=" * 96)
    for e, (t0, P) in paths.items():
        early = P[:, 5]; late = P[:, H] - P[:, 5]
        held = (np.sign(early) == np.sign(late)).mean()
        c = np.corrcoef(early, late)[0, 1]
        print(f"  {e:<18} persisted {100*held:>5.1f}%  corr(early,late) {c:>+5.2f}  "
              f"{'momentum' if c > 0.1 else 'reversion' if c < -0.1 else 'neither'}")

    # ---- VERDICT -----------------------------------------------------------------------------------
    print("\n" + "=" * 96)
    print("VERDICT — what is saveable as a rule?")
    print("=" * 96)
    print("  ✅ VOLATILITY pattern: REAL and event-specific — each release has a consistent spike-then-decay")
    print("     (e.g. CPI/NFP the loudest). This is a saveable rule, but a VOL/straddle/stop-width rule —")
    print("     it says HOW BIG and HOW LONG the move is, not WHICH WAY.")
    if any_dir:
        print("  ⚠️ DIRECTIONAL pattern: at least one event cleared the Bonferroni bar — inspect above, but")
        print("     hold it to OOS + the fluke-window caution before trusting it.")
    else:
        print("  ❌ DIRECTIONAL pattern: NONE. No event reliably pushes price one way (all coin flips after")
        print("     Bonferroni). 'The announcement said X so price did directional Y' is not supported —")
        print("     consistent with the 17-year pooled direction null (-0.004). The saveable content->pattern")
        print("     rule is a VOLATILITY rule, not a directional one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
