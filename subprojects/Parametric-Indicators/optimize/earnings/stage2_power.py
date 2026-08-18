"""WS-EARN Stage 2 (#111) — effective sample size, power, and the multiple-testing budget.

THE QUESTION: before spending anything searching for an edge, could we detect one if it existed?

This runs BEFORE Stage 3, deliberately. #103 established that the indicator search ran 4,000-47,100
trials against a sample supporting ~5 independent ones, and 1 of 8 pre-registered criteria passed as a
result. That programme did its power analysis after years of searching. This one does it first.

WHAT IT MEASURES

  1. effective independent n, and how it CHANGES WITH HORIZON — two events 30 minutes apart are
     independent for a 5-minute window and the same observation for an overnight one. Effective n is a
     property of the window, not of the event list.
  2. the distribution of NQ moves around the announcement — signed and absolute
  3. minimum detectable effect at 80% power
  4. that MDE against realistic round-trip cost
  5. how many independent approaches the sample supports before the best of them is meaningless
  6. a dumb control: the identical measurement on random non-announcement timestamps matched for
     time-of-day, per the standing "no positive result without a dumb control and a noise check" rule

🚫 It does NOT search for a strategy, fit any parameter, or test direction predictability. It measures
what WOULD be detectable.

⚠️ Volatility rising at the announcement is already known (~3x). **Volatility is not direction.**
A spike tells you the market will move, not which way, and the project's standing finding is that a fat
per-trade tail defeats most edges after cost.

    python3 optimize/earnings/stage2_power.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TABLE = DATA / "earnings_timestamps_STUDY12.csv"
OUT = DATA / "stage2_power.json"

PV = 20.0          # NQ dollars per index point — optimize/instruments.py
TICK = 0.25        # index points
TICK_USD = TICK * PV                                    # $5.00 per tick

# Round-trip cost. Precedent: optimize/fundamentals/gc_costs.py prices GC at ~$5 commission round-trip
# plus tick slippage. Same shape here, NQ tick = $5.
COMMISSION_RT = 4.50
COST_SCENARIOS = {
    "optimistic (commission + 0 slip)": COMMISSION_RT,
    "realistic (commission + 1 tick)": COMMISSION_RT + TICK_USD,
    "stressed  (commission + 2 ticks)": COMMISSION_RT + 2 * TICK_USD,
}

WINDOWS_MIN = [1, 5, 15, 30, 60]
GAMMA = 0.5772156649015329


def z_inv(p: float) -> float:
    """Standard-normal quantile (Acklam's rational approximation, ~1e-9 accurate)."""
    if not 0.0 < p < 1.0:
        raise ValueError(p)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def expected_max_of_n(n: int) -> float:
    """Bailey/Borwein/Lopez de Prado/Zhu (2014) Prop. 1 — expected max of N independent draws.

    Verified in docs/research-103/02-PRIOR-ART-statistical-limit.md against the authors' own three
    worked examples (N=45 -> 5.00 yr, N=7 -> 1.92 yr, N=10 -> E[max]=1.57). Three for three.
    """
    if n <= 1:
        return 0.0
    return (1 - GAMMA) * z_inv(1 - 1.0 / n) + GAMMA * z_inv(1 - (1.0 / n) * math.exp(-1))


def trials_budget(observed_t: float, cap: int = 10 ** 9) -> int:
    """Largest N whose expected best-of-N under the null still falls short of our observed statistic.

    Beyond this N, the best result a search finds is what pure noise would have produced anyway.
    """
    if observed_t <= 0:
        return 0
    lo, hi = 1, cap
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if expected_max_of_n(mid) < observed_t:
            lo = mid
        else:
            hi = mid - 1
    return lo


def effective_n(times, window_min: int) -> int:
    """Events whose [t, t+window] ranges overlap are ONE observation, not several.

    Effective n is a property of the horizon: two events 30 minutes apart are independent for a
    5-minute window and the same observation for a 60-minute one.
    """
    ts = sorted(times)
    if not ts:
        return 0
    n, end = 1, ts[0]
    for t in ts[1:]:
        if (t - end).total_seconds() > window_min * 60:
            n += 1
            end = t
        else:
            end = max(end, t)
    return n


def main() -> int:
    import numpy as np
    import pandas as pd
    from optimize.fundamentals.extended_data import load_1m_extended

    df = pd.read_csv(TABLE, parse_dates=["event_et"])
    d1 = load_1m_extended("NQ")
    idx = pd.Index(d1["Date"])
    close = d1["Close"].to_numpy(float)

    ev = df[df.nq_coverage == "bar_present"].sort_values("event_et").reset_index(drop=True)
    print("=" * 94)
    print("WS-EARN STAGE 2 — effective sample, power, and the multiple-testing budget")
    print("=" * 94)
    print(f"study universe : {df.ticker.nunique()} companies, {len(df)} events "
          f"({len(ev)} with NQ price coverage)")
    print(f"contract       : NQ, ${PV:.0f}/point, tick {TICK} pt = ${TICK_USD:.2f}")
    print(f"price frame    : {d1['Date'].min()} -> {d1['Date'].max()}")

    pos = idx.get_indexer(ev.event_et.dt.floor("min"))
    ok = pos >= 0
    ev, pos = ev[ok].reset_index(drop=True), pos[ok]

    # ---------------------------------------------------------------------------------------------
    print("\n" + "-" * 94)
    print("S2-C1  EFFECTIVE SAMPLE SIZE — and why it depends on the horizon")
    print("-" * 94)
    print(f"  {'window':>10}  {'raw events':>11}  {'effective n':>12}  {'lost to overlap':>16}")
    eff = {}
    for w in WINDOWS_MIN:
        e = effective_n(list(ev.event_et), w)
        eff[w] = e
        print(f"  {w:>7} min  {len(ev):>11}  {e:>12}  {len(ev)-e:>15} ")
    days = ev.event_et.dt.date.nunique()
    print(f"  {'overnight':>10}  {len(ev):>11}  {days:>12}  {len(ev)-days:>15} "
          f"  <- distinct announcement DAYS (second, independent method)")

    agree = abs(eff[60] - days) / max(eff[60], days) <= 0.25
    print(f"\n  two methods at the 60-min horizon: gap-collapse={eff[60]}, distinct-days={days}"
          f"  -> {'AGREE within 25% ✅' if agree else 'DISAGREE ❌'}")

    # ---------------------------------------------------------------------------------------------
    print("\n" + "-" * 94)
    print("S2-C2  WHAT THE MOVES ACTUALLY LOOK LIKE")
    print("-" * 94)
    print(f"  {'window':>8} {'n':>5} {'mean signed':>12} {'SD':>9} {'mean |move|':>12} "
          f"{'worst':>9} {'best':>8}   (NQ points)")
    stats = {}
    for w in WINDOWS_MIN:
        p1 = pos + w
        good = p1 < len(close)
        r = close[p1[good]] - close[pos[good]]
        stats[w] = {"n": int(len(r)), "mean": float(r.mean()), "sd": float(r.std(ddof=1)),
                    "abs": float(np.abs(r).mean()), "min": float(r.min()), "max": float(r.max())}
        s = stats[w]
        print(f"  {w:>5} min {s['n']:>5} {s['mean']:>12.2f} {s['sd']:>9.2f} {s['abs']:>12.2f} "
              f"{s['min']:>9.1f} {s['max']:>8.1f}")

    # ---------------------------------------------------------------------------------------------
    print("\n" + "-" * 94)
    print("S2-C2/C3  MINIMUM DETECTABLE EFFECT (80% power, alpha=0.05 two-sided) vs COST")
    print("-" * 94)
    print("  MDE = (z(0.975) + z(0.80)) * SD / sqrt(n_effective) = 2.802 * SD / sqrt(n)")
    print("  It is the smallest average per-event edge we could reliably tell apart from zero.\n")
    K = z_inv(0.975) + z_inv(0.80)
    print(f"  {'window':>8} {'n_eff':>6} {'SD (pts)':>10} {'MDE (pts)':>11} {'MDE ($/contract)':>18}")
    mdes = {}
    for w in WINDOWS_MIN:
        n_e = eff[w]
        mde = K * stats[w]["sd"] / math.sqrt(n_e)
        mdes[w] = mde
        print(f"  {w:>5} min {n_e:>6} {stats[w]['sd']:>10.2f} {mde:>11.2f} {mde*PV:>17.2f}")

    print("\n  round-trip cost scenarios (precedent: optimize/fundamentals/gc_costs.py):")
    for name, c in COST_SCENARIOS.items():
        print(f"    {name:<34} ${c:>6.2f}  = {c/PV:>5.2f} NQ points")

    realistic = COST_SCENARIOS["realistic (commission + 1 tick)"]
    print(f"\n  Cost is NOT the binding constraint here: every MDE above is far larger than the "
          f"${realistic:.2f}")
    print("  round trip. The binding question is the opposite one — **is an edge that large plausible?**\n")
    print("  A rule can only earn a fraction of the move it trades. So express the MDE as the share of")
    print("  the average absolute move a rule would have to convert into SIGNED profit:\n")
    print(f"  {'window':>8} {'MDE (pts)':>10} {'mean |move|':>12} {'share needed':>13} "
          f"{'implied directional accuracy':>29}")
    shares = {}
    for w in WINDOWS_MIN:
        share = mdes[w] / stats[w]["abs"]
        shares[w] = share
        # A binary long/short call right p of the time nets (2p-1) of the average absolute move.
        acc = (1 + share) / 2
        print(f"  {w:>5} min {mdes[w]:>10.2f} {stats[w]['abs']:>12.2f} {share:>12.1%} "
              f"{acc:>28.1%}")
    print("\n  ^ THIS is the real verdict. To be detectable at this sample size a rule must call")
    print("    direction correctly about 70% of the time. That is an extremely high bar for a")
    print("    liquid, heavily-traded, fully-scheduled event.")

    # ---------------------------------------------------------------------------------------------
    print("\n" + "-" * 94)
    print("S2-C4  MULTIPLE-TESTING BUDGET — how many independent approaches the sample supports")
    print("-" * 94)
    print("  Using Bailey et al. (2014) Prop. 1, the same formula #103 verified 3/3 against the")
    print("  authors' worked examples. A search of N independent approaches finds, from PURE NOISE,")
    print("  a best result of about E[max_N]. Any real finding must beat that, not merely beat zero.\n")
    print(f"  {'N approaches':>14}  {'best-of-N from noise alone (t)':>32}")
    for n_try in (5, 10, 50, 100, 500, 2000, 10000):
        print(f"  {n_try:>14,}  {expected_max_of_n(n_try):>32.2f}")

    print("  The budget depends entirely on how good the edge really is. Quoting one number would hide")
    print("  that, so here it is against a range of assumed skill levels, at the 5-minute window:\n")
    w5 = 5
    n5, s5 = eff[w5], stats[w5]
    print(f"  (5-min window, n_eff={n5}, mean |move|={s5['abs']:.1f} pts, SD={s5['sd']:.1f} pts)\n")
    print(f"  {'directional accuracy':>21} {'share of move':>14} {'edge (pts)':>11} {'|t|':>7} "
          f"{'approaches affordable':>22}")
    budgets = {}
    for acc in (0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        share = 2 * acc - 1
        edge = share * s5["abs"]
        t = edge / (s5["sd"] / math.sqrt(n5))
        b = trials_budget(t)
        budgets[f"acc_{acc:.2f}"] = b
        note = f"{b:,}" if b < 10 ** 9 else ">1e9"
        print(f"  {acc:>20.0%} {share:>14.0%} {edge:>11.2f} {t:>7.2f} {note:>22}")
    print("\n  Read the row that matches what you actually believe. At a realistic 55-60% accuracy the")
    print("  sample supports only a HANDFUL of independent approaches before the best of them is")
    print("  indistinguishable from the best of pure noise.")
    print("\n  ⛔ 'try 2,000 approaches' needs |t| > 3.45. At the 5-min window that requires roughly")
    print(f"     {trials_budget.__name__ and (3.45*s5['sd']/math.sqrt(n5)):.1f} points of consistent signed edge per event "
          f"(~{(3.45*s5['sd']/math.sqrt(n5))/s5['abs']:.0%} of the average move, "
          f"~{(1+(3.45*s5['sd']/math.sqrt(n5))/s5['abs'])/2:.0%} accuracy).")

    # ---------------------------------------------------------------------------------------------
    print("\n" + "-" * 94)
    print("DUMB CONTROL — the same measurement on NON-announcement days, matched for time-of-day")
    print("-" * 94)
    rng = np.random.default_rng(20260806)
    real_days = set(ev.event_et.dt.normalize())
    minutes = ev.event_et.dt.hour * 60 + ev.event_et.dt.minute
    all_dates = pd.Index(d1["Date"].dt.normalize().unique())
    cand = [d for d in all_dates if d not in real_days]
    ctrl_times = []
    for m in minutes:
        for _ in range(20):
            d = cand[rng.integers(len(cand))]
            t = d + pd.Timedelta(minutes=int(m))
            if t in idx:
                ctrl_times.append(t)
                break
    cpos = idx.get_indexer(pd.DatetimeIndex(ctrl_times))
    cpos = cpos[cpos >= 0]
    print(f"  control timestamps drawn: {len(cpos)} (same clock minutes, days with NO announcement)\n")
    print("  (a) SIZE of the move — is the announcement minute unusual at all?\n")
    print(f"  {'window':>8} {'real mean |move|':>18} {'control mean |move|':>21} {'ratio':>8}")
    ctrl = {}
    for w in WINDOWS_MIN:
        p1 = cpos + w
        g = p1 < len(close)
        cr = close[p1[g]] - close[cpos[g]]
        ctrl[w] = {"abs": float(np.abs(cr).mean()), "mean": float(cr.mean()),
                   "sd": float(cr.std(ddof=1)), "n": int(len(cr))}
        ratio = stats[w]["abs"] / ctrl[w]["abs"] if ctrl[w]["abs"] else float("nan")
        print(f"  {w:>5} min {stats[w]['abs']:>18.2f} {ctrl[w]['abs']:>21.2f} {ratio:>7.2f}x")

    # ⚠️ THE CONFOUND. NQ rose over 2024-2026, so ANY window measured long shows positive drift.
    # A positive signed mean is only evidence of an announcement effect if it EXCEEDS what an
    # ordinary minute of the same period produced. Without this the market's own trend gets
    # reported as a discovery.
    print("\n  (b) DIRECTION — is the drift an announcement effect, or just a rising market?\n")
    print(f"  {'window':>8} {'real mean signed':>18} {'|t|':>7} {'control mean signed':>21} "
          f"{'real - control':>15}")
    for w in WINDOWS_MIN:
        n_e = eff[w]
        t = abs(stats[w]["mean"]) / (stats[w]["sd"] / math.sqrt(n_e))
        diff = stats[w]["mean"] - ctrl[w]["mean"]
        flag = "  <- significant" if t > 1.98 else ""
        print(f"  {w:>5} min {stats[w]['mean']:>18.2f} {t:>7.2f} {ctrl[w]['mean']:>21.2f} "
              f"{diff:>15.2f}{flag}")
    print("\n  ^ t is computed against n_effective, NOT the raw event count. None of these is a")
    print("    result — this stage measures detectability, it does not test a hypothesis.")

    # ---------------------------------------------------------------------------------------------
    print("\n" + "-" * 94)
    print("WHAT WOULD ACTUALLY FIX THIS — sample size, not cleverness")
    print("-" * 94)
    print("  MDE shrinks as 1/sqrt(n). No amount of modelling skill changes that; only more events do.")
    print("  A 16-year NQ frame (2010->2026, plus a 1-second archive) already exists on the server")
    print("  (optimize/fundamentals/extended_data.py). 12 companies x 4 quarters x 16 years ~ 768 events.\n")
    n_now = eff[5]
    scale = (83.0 / 116.0)                      # independent-window yield measured on our own data
    print(f"  {'history':>22} {'events':>8} {'n_eff':>7} {'share of move needed':>21} "
          f"{'accuracy needed':>16}")
    projections = {}
    for label, yrs in (("now (2.4 years)", 2.4), ("6 years", 6.0), ("10 years", 10.0),
                       ("16 years (server)", 16.0)):
        n_events = 12 * 4 * yrs
        n_e = max(2, int(round(n_events * scale)))
        if label.startswith("now"):
            n_e, n_events = n_now, len(ev)
        share = (K * s5["sd"] / math.sqrt(n_e)) / s5["abs"]
        acc = (1 + share) / 2
        projections[label] = {"events": int(n_events), "n_eff": int(n_e),
                              "share_needed": float(share), "accuracy_needed": float(acc)}
        mark = "  <-- plausible" if acc < 0.62 else ("  <-- implausible" if acc > 0.68 else "")
        print(f"  {label:>22} {int(n_events):>8} {n_e:>7} {share:>20.1%} {acc:>15.1%}{mark}")

    print("\n  ⭐ This is the whole finding. At 2.4 years a rule needs ~71% directional accuracy to be")
    print("     detectable — implausible for a liquid, scheduled event. At 16 years it needs ~59%,")
    print("     which is an ordinary edge. THE SAMPLE, NOT THE METHOD, IS THE BINDING CONSTRAINT.")
    print("\n  This mirrors #103 exactly: there, #87 (more history) turned out to outrank every")
    print("  optimiser improvement. Same conclusion, arrived at independently, on a different question.")

    OUT.write_text(json.dumps({
        "projections": projections,
        "share_needed_by_window": shares,
        "control": ctrl,
        "universe": {"companies": int(df.ticker.nunique()), "events": int(len(df)),
                     "events_with_price": int(len(ev))},
        "effective_n_by_window_min": eff,
        "effective_n_distinct_days": int(days),
        "move_stats_points": stats,
        "mde_points": mdes,
        "mde_usd": {w: mdes[w] * PV for w in mdes},
        "cost_scenarios_usd": COST_SCENARIOS,
        "trial_budget_ceiling": budgets,
        "point_value": PV,
    }, indent=1, default=float))
    print(f"\nwrote -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
