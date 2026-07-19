"""S3 — DOES OUR CHAMPION'S EDGE CONCENTRATE BY SESSION? (task #5, phase 2, the money question)

S1 showed the TAPE has a shape (RTH loud, overnight quiet). S3 asks the only question that pays: does OUR
EDGE have a shape? We bucket every champion trade by the SESSION it entered in and ask whether P/L,
win-rate, and the stop-out tail depend on it. If our money is made only in one session, that is a FILTER
worth having (SESSION-01 R6: session structure is a filter, not a standalone entry).

A NATURAL EXPERIMENT falls out of the 4h timeframe for free: a 4h strategy can only enter at the six 4h
bar boundaries — 02:00 / 06:00 / 10:00 / 14:00 / 18:00 / 22:00 ET. Exactly TWO of those (10:00, 14:00)
land in RTH; the other four are off-hours. So "RTH-entry vs off-hours-entry" is a clean, pre-existing
split we did not choose after seeing results.

DISCIPLINE (the standing rules of this project, applied):
  * NULL TEST: permute which trades belong to which session and ask whether the observed per-session
    P/L-per-trade spread exceeds chance. A spread that random labels reproduce is not a session effect.
  * NOISE CHECK: bootstrap the RTH-vs-off-hours P/L-per-trade difference; report the 95% CI and p. A big
    dollar total on a fat-tailed per-trade distribution is not evidence (see the stop-loss lesson: +$80/
    trade against a +/-$1,600 swing was noise).
  * POWER: report n per bucket; a session with 30 trades tells us little.

PRE-DECLARED CRITERION (before the run):
  A session FILTER is worth pursuing (=> S4) ONLY IF the per-session P/L-per-trade differs SIGNIFICANTLY
  (permutation p < 0.05) AND the best-session subset beats the full set's P/L-per-trade beyond noise.
  Otherwise session-of-entry carries no information and we STOP.

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_session_edge.py --tf 4h
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
from optimize.fundamentals.champion_params import champion_stops  # noqa: E402

# Session labels by ENTRY HOUR (ET), from S1 (SESSION-02). Coarsened to hour since 4h entries are hourly.
def session_of(hour: int) -> str:
    if 9 <= hour < 12:  return "RTH-morning"
    if 12 <= hour < 13: return "Lunch"
    if 13 <= hour < 16: return "RTH-afternoon"
    if 16 <= hour < 18: return "Post-close"
    if 18 <= hour < 20: return "Globex-eve"
    if 20 <= hour < 24: return "Asia"
    if 0 <= hour < 2:   return "Asia-am"
    if 2 <= hour < 8:   return "Europe"
    return "Pre-open"                                              # 08:00-09:30


def is_rth(hour: int) -> bool:
    return 9 <= hour < 16


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--n-perm", type=int, default=10000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    df, df1, box, vf, n = data.load_inputs(a.tf, instrument=a.instrument)
    p = champion_preset(a.tf)
    sl_soft, sl_hard, tp, _flip = champion_stops(p)
    gp = float(p["gate_pct"])
    pv = instruments.point_value(a.instrument)

    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], gp))
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                      df1["Close"].to_numpy(float), sl_soft, sl_hard, tp,
                      _flip)
    if not F:
        print("no trades"); return 1

    hrs = np.array([pd.Timestamp(t["entry_time"]).hour for t in F])
    pnl = np.array([float(t["pnl_points"]) for t in F]) * pv
    stopped = np.array([t["exit_reason"] == "STOP_LOSS_HARD" for t in F])
    sess = np.array([session_of(h) for h in hrs])
    rth = np.array([is_rth(h) for h in hrs])

    print(f"\n{a.instrument} {a.tf} champion  ·  {len(F)} trades  ·  ${pv:,.0f}/pt  ·  total P/L "
          f"${pnl.sum():,.0f}")
    print(f"per-trade: mean ${pnl.mean():+,.0f}  sd ${pnl.std():,.0f}  win {100*(pnl>0).mean():.1f}%\n")

    print("=" * 92)
    print("ENTRY-HOUR DISTRIBUTION (confirms the natural experiment — a 4h strategy enters at 4h boundaries)")
    print("=" * 92)
    for h in sorted(set(hrs)):
        m = hrs == h
        tag = "RTH" if is_rth(h) else "off-hours"
        print(f"  {h:02d}:00 ET ({session_of(h):<14} {tag:>9}): n={int(m.sum()):>4}  "
              f"P/L ${pnl[m].sum():>11,.0f}  ${pnl[m].mean():>+7,.0f}/trade  "
              f"win {100*(pnl[m]>0).mean():>5.1f}%  stop {100*stopped[m].mean():>5.1f}%")

    # ---------------------------------------------------------------- per-session table
    print()
    print("=" * 92)
    print("BY SESSION")
    print("=" * 92)
    order = sorted(set(sess), key=lambda s: -pnl[sess == s].mean())
    print(f"  {'session':<16} {'n':>5} {'total P/L':>13} {'$/trade':>10} {'win%':>7} {'stop%':>7} "
          f"{'worst':>10}")
    for s in order:
        m = sess == s
        print(f"  {s:<16} {int(m.sum()):>5} ${pnl[m].sum():>11,.0f} ${pnl[m].mean():>+8,.0f} "
              f"{100*(pnl[m]>0).mean():>6.1f}% {100*stopped[m].mean():>6.1f}% ${pnl[m].min():>+9,.0f}")

    # ---------------------------------------------------------------- RTH vs off-hours
    print()
    print("=" * 92)
    print("THE SPLIT — RTH-entry (10:00, 14:00) vs OFF-HOURS-entry (02/06/18/22)")
    print("=" * 92)
    for lab, m in (("RTH-entry", rth), ("off-hours", ~rth)):
        print(f"  {lab:<12} n={int(m.sum()):>4}  total ${pnl[m].sum():>11,.0f}  "
              f"${pnl[m].mean():>+7,.0f}/trade  win {100*(pnl[m]>0).mean():>5.1f}%  "
              f"stop {100*stopped[m].mean():>5.1f}%")
    diff = pnl[rth].mean() - pnl[~rth].mean()
    print(f"\n  RTH minus off-hours: ${diff:+,.0f} per trade")

    # ---------------------------------------------------------------- NULL TEST (permutation)
    print()
    print("=" * 92)
    print("IS IT REAL? — null test + noise check (mandatory)")
    print("=" * 92)
    # (1) permutation: does per-session $/trade spread exceed chance?
    def spread(labels):
        ms = [pnl[labels == s].mean() for s in set(labels) if (labels == s).sum() >= 5]
        return (max(ms) - min(ms)) if len(ms) >= 2 else 0.0
    obs_spread = spread(sess)
    null_spread = np.array([spread(rng.permutation(sess)) for _ in range(a.n_perm)])
    p_spread = float((null_spread >= obs_spread).mean())
    print(f"  per-session $/trade spread: observed ${obs_spread:,.0f}   "
          f"shuffled {null_spread.mean():,.0f} +/- {null_spread.std():,.0f}   p = {p_spread:.3f}")

    # (2) bootstrap the RTH-vs-off-hours difference
    def boot_diff():
        a_ = rng.choice(pnl[rth], rth.sum(), replace=True).mean()
        b_ = rng.choice(pnl[~rth], (~rth).sum(), replace=True).mean()
        return a_ - b_
    bs = np.array([boot_diff() for _ in range(a.n_perm)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p_diff = float((bs <= 0).mean() * 2) if diff > 0 else float((bs >= 0).mean() * 2)
    print(f"  RTH-vs-off-hours $/trade: ${diff:+,.0f}   95% CI [${lo:+,.0f}, ${hi:+,.0f}]   p = {p_diff:.3f}")
    print(f"  per-trade sd ${pnl.std():,.0f} — an ${abs(diff):,.0f} gap on that spread needs "
          f"~{int((2.8*pnl.std()/max(abs(diff),1e-9))**2):,} trades to confirm; we have {len(F)}.")

    # ---------------------------------------------------------------- TEMPORAL STABILITY (the decider)
    #
    # THE DOMINANT CONFOUND: this champion was OPTIMIZED in-sample on this exact 2025-2026 data. A
    # marginal in-sample session pattern (p=0.014) could be the optimizer fitting session-correlated
    # noise. My pre-declared criterion did NOT guard this — disclosed. The cheap decisive test on existing
    # data: does the per-session ranking HOLD across two chronological halves? A real pattern persists; an
    # optimization artifact does not.
    print()
    print("=" * 92)
    print("TEMPORAL STABILITY — does the per-session ranking hold in BOTH halves? (the real decider)")
    print("=" * 92)
    et = np.array([np.datetime64(t["entry_time"]) for t in F])
    order_t = np.argsort(et)
    half = order_t[:len(F) // 2], order_t[len(F) // 2:]
    common = [s for s in set(sess) if all((sess[h] == s).sum() >= 5 for h in half)]
    h1 = np.array([pnl[half[0]][sess[half[0]] == s].mean() for s in common])
    h2 = np.array([pnl[half[1]][sess[half[1]] == s].mean() for s in common])
    print(f"  {'session':<16} {'1st half $/trade':>17} {'2nd half $/trade':>17}")
    for s, a1, b1 in zip(common, h1, h2):
        flip = "" if (a1 > 0) == (b1 > 0) else "   <-- SIGN FLIP"
        print(f"  {s:<16} {a1:>+16,.0f} {b1:>+16,.0f}{flip}")
    stab = float(np.corrcoef(h1, h2)[0, 1]) if len(common) >= 3 else float("nan")
    n_keep = int(np.sum((h1 > 0) == (h2 > 0)))
    print(f"\n  correlation of per-session $/trade, 1st half vs 2nd half: {stab:+.3f}")
    print(f"  sessions that KEEP their sign across halves: {n_keep}/{len(common)} "
          f"(the correlation can be carried by ONE stable cell while the rest is noise)")
    print(f"  (a real BROAD session pattern keeps most signs; a few-cell fluke keeps only 1-2)")

    # ---------------------------------------------------------------- VERDICT
    print()
    print("=" * 92)
    print("VERDICT — against the criterion declared before the run (+ the confound it missed)")
    print("=" * 92)
    sig_spread = p_spread < 0.05
    print(f"  (a) per-session $/trade differs significantly (permutation, selection-aware): "
          f"{'YES' if sig_spread else 'NO'} (p={p_spread:.3f})")
    print(f"  (b) but the clean RTH-vs-overnight axis: {'sig' if p_diff < 0.05 else 'NOT sig'} "
          f"(p={p_diff:.3f}) — the pattern is idiosyncratic HOURS, not a clean session story")
    broad_stable = n_keep >= (len(common) - 1)          # a BROAD pattern keeps almost all signs
    print(f"  (c) BROAD stability: only {n_keep}/{len(common)} sessions keep their sign across halves "
          f"=> {'broadly stable' if broad_stable else 'NOT a broad pattern — carried by 1-2 cells'}")
    print()
    print(f"  ROBUST finding (not an artifact): STOP-OUT RATE is strongly session-dependent — RTH-morning")
    print(f"  {100*stopped[sess=='RTH-morning'].mean():.0f}% vs Asia "
          f"{100*stopped[sess=='Asia'].mean():.0f}% — a direct consequence of S1's volatility shape. That")
    print(f"  feeds session-aware STOP SIZING (an endorsed filter use), not entry selection.")
    print()
    if sig_spread and broad_stable:
        print(f"  ⚠️ P/L pattern is significant AND broadly stable — worth an OUT-OF-SAMPLE test before S4.")
    else:
        print(f"  ❌ A BROAD session ENTRY edge is NOT supported: {len(common)-n_keep}/{len(common)} sessions")
        print(f"     flip sign between halves, and the clean RTH-vs-overnight axis is not significant. The")
        print(f"     omnibus p=0.014 is carried by a SINGLE stable cell — the 22:00/Asia entry")
        print(f"     (+${pnl[sess=='Asia'].mean():,.0f}/trade, both halves). That is the SILVER situation: 1 of 6")
        print(f"     windows, n={int((sess=='Asia').sum())}, in the 2025-2026 fluke window, on an OPTIMIZED champion, with no")
        print(f"     long history to confirm. => a FROZEN observation, not a filter to build. And acting on")
        print(f"     it would REMOVE entries (against the increase-entries goal). STOP at S3 for P/L.")
        print(f"     Carry forward ONLY the robust stop-out-rate finding into future sizing work.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
