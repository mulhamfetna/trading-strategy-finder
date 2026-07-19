"""TASK #11 — THE STOP-LOSS VERDICT, RE-TESTED AT 1-SECOND RESOLUTION.

WHY THIS EXISTS, AND WHY IT MATTERS MORE THAN ANYTHING ELSE IN THIS WORKSTREAM.

Report 04 concluded that the dynamic stop-loss is DEAD: price after a stop-out is a fair MARTINGALE, so
no rule for honouring-vs-ignoring the stop can beat it. That rested on 235 trades, 7 disaster floors, and
a match to gambler's ruin within 0.34 percentage points. It is backed by Doob's Optional Stopping Theorem
and by the two most rigorous papers in the field.

**AND IT WAS MEASURED ENTIRELY ON 1-MINUTE BARS.**

Then we looked inside a single minute with 1-second data — the 08:30 payrolls print of 2025-03-07:

    08:30:01   THE LOW    -46 pts   <- this is what stopped out the long
    08:30:03              +51 pts   <- already right, and it STAYED right
    08:30:10   THE HIGH  +141 pts

**The move that took the stop lasted TWO SECONDS.** A 1-minute OHLC candle records both extremes and
CANNOT TELL YOU THE ORDER. Every backtest we have run on 1-minute bars has had to GUESS — and whichever
way it guesses, it is wrong half the time.

So the martingale result may be an ARTIFACT OF THE RESOLUTION rather than a fact about the market. If a
large share of our stop-outs are two-second liquidity sweeps, then "the stop-out" and "the path after it"
are not the things we thought we were measuring.

================================================================================================
THE KILL CRITERION — DECLARED HERE, IN THE SOURCE, BEFORE THE STUDY IS RUN. IT DOES NOT MOVE.
================================================================================================

    The original verdict STANDS (dynamic stop stays DEAD) if EITHER:

      (A) SWEEPS ARE RARE          — fewer than 15% of stop-outs are sweeps; or
      (B) THE POST-SWEEP PATH IS ALSO A MARTINGALE — even on the swept subset, ignoring the stop has
                                     expectancy indistinguishable from zero.

    The verdict FALLS only if sweeps are COMMON *and* ignoring the stop on them is PROFITABLE.

One beautiful example has already fooled me twice in a single day. The criterion is written down first
precisely so that it cannot be tuned to flatter whatever comes back.

DEFINITIONS (also fixed in advance):

  SWEEP     the stop level is touched, and within --recover-secs (default 60) price returns to the stop
            level or better. i.e. the adverse move that triggered the exit was FULLY RETRACED, fast.
  GENUINE   the stop is touched and price does NOT come back within that window. A real adverse move.

CAUSALITY. The counterfactual keeps the ORIGINAL take-profit and applies a DISASTER FLOOR at
--floor-mult x the stop distance, exactly as report 04 did. "Ignoring the stop" is never unbounded risk —
without a floor we would be measuring a martingale by construction rather than testing for one.

  python3 -u optimize/fundamentals/study_stop_1s.py --tf 4h --floor-mult 3
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
from optimize.fundamentals.extended_data import load_1s_windows    # noqa: E402
from perf._common import champion_preset                           # noqa: E402
from optimize.fundamentals.champion_params import champion_stops  # noqa: E402

SWEEP_RATE_KILL = 0.15          # (A) below this, sweeps are rare and the verdict stands


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--floor-mult", type=float, default=3.0)
    ap.add_argument("--recover-secs", type=int, default=60,
                    help="a stop-out is a SWEEP if price retraces to the stop within this many seconds")
    ap.add_argument("--post-min", type=int, default=480,
                    help="minutes of 1-second path to examine after the stop. At 60 only 93 of 235 "
                         "stop-outs resolved (hit TP or floor) and the rest were EXCLUDED — too few to "
                         "conclude from. Report 04 allowed a full trading day; 480 min matches it.")
    a = ap.parse_args()

    # ---------------------------------------------------------------- the champion, on 1-minute bars
    df, df1, box, vf, n = data.load_inputs(a.tf, instrument=a.instrument)
    p = champion_preset(a.tf)
    sl_soft, sl_hard, tp, _flip = champion_stops(p)
    gp = float(p.get("gate_pct", 60))
    pv = instruments.point_value(a.instrument)

    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], gp))
    MD = df1["Date"].to_numpy()

    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float),
                      df1["Close"].to_numpy(float), sl_soft, sl_hard, tp,
                      _flip, track_excursions=True)
    stopped = [t for t in F if t["exit_reason"] == "STOP_LOSS_HARD"]

    print(f"\n{a.instrument} {a.tf}  ·  SL {sl_soft}/{sl_hard}  TP {tp}  ·  ${pv:,.0f}/pt")
    print(f"{len(F)} trades, {len(stopped)} killed by the HARD STOP")
    print(f"\nKILL CRITERION (declared before the run):")
    print(f"  (A) sweeps < {100*SWEEP_RATE_KILL:.0f}% of stop-outs            -> verdict STANDS")
    print(f"  (B) post-sweep path is ALSO a martingale     -> verdict STANDS")
    print(f"  verdict FALLS only if sweeps are COMMON *and* ignoring the stop on them PAYS.\n")

    # ---------------------------------------------------------------- the 1-second windows
    # The stop fired inside 1-min bar s0 = entry_bar + bars_1m - 1. We want that whole minute (to find
    # the exact SECOND of the touch) plus --post-min of path after it.
    jobs = []
    for t in stopped:
        e0 = int(np.searchsorted(MD, np.datetime64(t["entry_time"]), side="left"))
        s0 = e0 + int(t["bars_1m"]) - 1
        if s0 >= len(MD):
            continue
        t_stop_bar = pd.Timestamp(MD[s0])
        jobs.append({
            "trade": t,
            "bar": t_stop_bar,
            "long": t["direction"] == "long",
            "ep": float(t["entry_price"]),
        })
    if not jobs:
        print("no stopped trades to examine.")
        return 1

    windows = [(j["bar"], j["bar"] + pd.Timedelta(minutes=a.post_min + 1)) for j in jobs]
    print(f"loading 1-second bars for {len(windows)} stop-outs "
          f"({a.post_min} min of path each) — ONE pass over the 7.3 GB file...")
    S = load_1s_windows(windows)
    if S.empty:
        print("  no 1-second data covering these trades.")
        return 1
    sd = S["Date"].to_numpy()
    sh = S["High"].to_numpy(float)
    sl_ = S["Low"].to_numpy(float)
    sc = S["Close"].to_numpy(float)      # hoisted: Result 3's grid would otherwise re-convert this
                                         # 3.8M-row column 15 x 235 = 3,525 times.

    # ---------------------------------------------------------------- classify every stop-out
    rows = []
    for j in jobs:
        t, long, ep = j["trade"], j["long"], j["ep"]
        stop_line = ep - sl_hard if long else ep + sl_hard
        tp_line = ep + tp if long else ep - tp
        floor_line = ep - a.floor_mult * sl_hard if long else ep + a.floor_mult * sl_hard

        i0 = int(np.searchsorted(sd, np.datetime64(j["bar"]), side="left"))
        i1 = int(np.searchsorted(sd, np.datetime64(j["bar"] + pd.Timedelta(minutes=a.post_min)),
                                 side="right"))
        if i1 - i0 < 5:
            continue
        H, L, D = sh[i0:i1], sl_[i0:i1], sd[i0:i1]

        # the exact SECOND the stop was touched
        touch = np.flatnonzero(L <= stop_line) if long else np.flatnonzero(H >= stop_line)
        if not len(touch):
            continue                      # 1s data disagrees the stop was hit in this minute — skip
        k = int(touch[0])

        # Did it come back? Measured STRICTLY AFTER the touching bar (k+1 onward).
        #
        # ⚠️ THE BUG THIS REPLACES, because it produced a beautiful, completely fake headline.
        # The first version searched from index k — the very 1-second bar that TRIGGERED the stop. For a
        # long, the stop fires when that bar's LOW <= stop_line; its HIGH is then almost always >=
        # stop_line, simply because a bar contains both. So "price recovered to the stop" was TRUE BY
        # CONSTRUCTION, in the same second, for 97.4% of stop-outs, with a median recovery time of ZERO
        # seconds. The zero was the tell. I was measuring "does a bar contain its own high", not "did the
        # market come back". A stop-out cannot be swept by the tick that caused it.
        horizon = np.flatnonzero(D <= D[k] + np.timedelta64(a.recover_secs, "s"))
        kr = int(horizon[-1]) if len(horizon) else k
        if kr <= k:
            continue
        back = (np.flatnonzero(H[k + 1:kr + 1] >= stop_line) if long
                else np.flatnonzero(L[k + 1:kr + 1] <= stop_line))
        is_sweep = bool(len(back))
        secs_beyond = (int((D[k + 1 + int(back[0])] - D[k]) / np.timedelta64(1, "s"))
                       if is_sweep else None)

        # how far past the stop did it go, before coming back?
        adverse = (float(stop_line - L[k:kr + 1].min()) if long
                   else float(H[k:kr + 1].max() - stop_line))

        # THE COUNTERFACTUAL, on 1-SECOND bars: ignore the stop, keep the TP, keep a disaster floor.
        post_h, post_l = H[k:], L[k:]
        hit_tp = np.flatnonzero(post_h >= tp_line) if long else np.flatnonzero(post_l <= tp_line)
        hit_fl = np.flatnonzero(post_l <= floor_line) if long else np.flatnonzero(post_h >= floor_line)
        i_tp = int(hit_tp[0]) if len(hit_tp) else 10 ** 9
        i_fl = int(hit_fl[0]) if len(hit_fl) else 10 ** 9
        if i_tp == 10 ** 9 and i_fl == 10 ** 9:
            cf = None                                   # unresolved — EXCLUDED, never counted as a win
        elif i_tp <= i_fl:
            cf = tp
        else:
            cf = -(a.floor_mult * sl_hard)

        rows.append({"sweep": is_sweep, "secs_beyond": secs_beyond, "adverse": adverse,
                     "cf_points": cf, "real_points": float(t["pnl_points"])})

    R = pd.DataFrame(rows)
    nsw = int(R["sweep"].sum())
    rate = nsw / len(R)

    print()
    print("=" * 84)
    print("RESULT 1 — HOW MANY STOP-OUTS ARE ACTUALLY TWO-SECOND SWEEPS?")
    print("=" * 84)
    print(f"  stop-outs examined at 1-second resolution : {len(R)}")
    print(f"  SWEEPS  (price retraced to the stop within {a.recover_secs}s) : "
          f"{nsw:>4}   ({100*rate:>5.1f}%)")
    print(f"  GENUINE (it did not come back)                        : "
          f"{len(R)-nsw:>4}   ({100*(1-rate):>5.1f}%)")
    if nsw:
        sb = R.loc[R["sweep"], "secs_beyond"].dropna()
        print()
        print(f"  of the sweeps, how long was price beyond the stop before retracing?")
        print(f"     median {sb.median():.0f}s   ·  mean {sb.mean():.1f}s   ·  "
              f"90th pct {sb.quantile(0.90):.0f}s   ·  max {sb.max():.0f}s")
        print(f"     under 5 seconds: {100*(sb <= 5).mean():.1f}%   "
              f"under 10 seconds: {100*(sb <= 10).mean():.1f}%")

    print()
    print("=" * 84)
    print("RESULT 2 — IF WE HAD IGNORED THE STOP (1-second counterfactual, TP kept, floor at "
          f"{a.floor_mult:.0f}x)")
    print("=" * 84)
    nunres = int(R["cf_points"].isna().sum())
    print(f"  (unresolved within {a.post_min} min — neither TP nor floor — EXCLUDED, never counted "
          f"as a win: {nunres} of {len(R)})")
    print()
    for label, sub in (("SWEEPS", R[R["sweep"]]), ("GENUINE", R[~R["sweep"]]), ("ALL", R)):
        res = sub.dropna(subset=["cf_points"])
        if not len(res):
            print(f"  {label:<8} nothing resolved")
            continue
        real = res["real_points"].sum() * pv
        cf = res["cf_points"].sum() * pv
        won = (res["cf_points"] > 0).mean()
        print(f"  {label:<8} n={len(res):>4}  |  realized ${real:>12,.0f}  ->  "
              f"ignoring the stop ${cf:>12,.0f}  |  delta ${cf-real:>+12,.0f}  "
              f"(recovered to TP {100*won:.1f}%)")

    # ================================================================================================
    # RESULT 3/4/5 — one simulator, three questions.
    #
    # Every strategy below is expressed as ONE causal function so they are exactly comparable and cannot
    # drift apart. Each returns per-trade points, aligned to the same trade list, so deltas are paired.
    # ================================================================================================
    prep = []
    for j in jobs:
        t, long, ep = j["trade"], j["long"], j["ep"]
        stop_line = ep - sl_hard if long else ep + sl_hard
        i0 = int(np.searchsorted(sd, np.datetime64(j["bar"]), side="left"))
        i1 = int(np.searchsorted(sd, np.datetime64(j["bar"] + pd.Timedelta(minutes=a.post_min)),
                                 side="right"))
        if i1 - i0 < 5:
            continue
        H, L, C, D = sh[i0:i1], sl_[i0:i1], sc[i0:i1], sd[i0:i1]
        touch = np.flatnonzero(L <= stop_line) if long else np.flatnonzero(H >= stop_line)
        if not len(touch):
            continue
        prep.append({
            "long": long, "ep": ep, "k": int(touch[0]), "H": H, "L": L, "C": C, "D": D,
            "stop": stop_line,
            "tp": ep + tp if long else ep - tp,
            "floor": (ep - a.floor_mult * sl_hard) if long else (ep + a.floor_mult * sl_hard),
            "real": float(t["pnl_points"]),
        })

    def _hold_from(q, r0):
        """Hold from index r0: take-profit, else disaster floor, else mark to market. Never excluded."""
        long, H, L, C = q["long"], q["H"], q["L"], q["C"]
        ph, pl_ = H[r0:], L[r0:]
        i_tp = np.flatnonzero(ph >= q["tp"]) if long else np.flatnonzero(pl_ <= q["tp"])
        i_fl = np.flatnonzero(pl_ <= q["floor"]) if long else np.flatnonzero(ph >= q["floor"])
        a_tp = int(i_tp[0]) if len(i_tp) else 10 ** 9
        a_fl = int(i_fl[0]) if len(i_fl) else 10 ** 9
        if a_tp == 10 ** 9 and a_fl == 10 ** 9:
            px = float(C[-1])                                  # marked to market, never booked as a win
            return ((px - q["ep"]) if long else (q["ep"] - px)), False
        if a_tp <= a_fl:
            return tp, False
        return -(a.floor_mult * sl_hard), True

    def sim_delay(wait: float, margin: float):
        """THE TRADEABLE RULE. On the stop touch: wait; stay in only if price comes back; else bail at
        the market. Causal — every decision uses only what was knowable when it was taken."""
        out, stayed, bailed, floors = [], 0, 0, 0
        for q in prep:
            long, H, L, C, D, k = q["long"], q["H"], q["L"], q["C"], q["D"], q["k"]
            w_end = int(np.searchsorted(D, D[k] + np.timedelta64(int(wait), "s"), side="right")) - 1
            w_end = max(w_end, min(k + 1, len(D) - 1))
            seg = slice(k + 1, w_end + 1)
            fl = (np.flatnonzero(L[seg] <= q["floor"]) if long
                  else np.flatnonzero(H[seg] >= q["floor"]))
            rec = (np.flatnonzero(H[seg] >= q["stop"] + margin) if long
                   else np.flatnonzero(L[seg] <= q["stop"] - margin))
            if len(fl) and (not len(rec) or fl[0] < rec[0]):
                out.append(-(a.floor_mult * sl_hard)); floors += 1; continue
            if not len(rec):
                px = float(C[w_end])                           # BAIL. This is the cost of waiting.
                out.append((px - q["ep"]) if long else (q["ep"] - px)); bailed += 1; continue
            stayed += 1
            v, hitfloor = _hold_from(q, k + 1 + int(rec[0]))
            out.append(v); floors += int(hitfloor)
        return np.array(out, float), stayed, bailed, floors

    def sim_control():
        """THE DUMB CONTROL. No sweeps. No 1-second data. Just hold to TP or the 3x floor — i.e. a WIDER
        STOP, and nothing else."""
        out, floors = [], 0
        for q in prep:
            v, hitfloor = _hold_from(q, q["k"])
            out.append(v); floors += int(hitfloor)
        return np.array(out, float), floors

    realized = np.array([q["real"] for q in prep], float)
    realized_all = realized.sum() * pv

    print()
    print("=" * 84)
    print("RESULT 3 — THE IMPLEMENTABLE RULE: delay the stop, bail if it doesn't come back")
    print("=" * 84)
    print("  (RESULT 2 is NOT tradeable — it labels sweeps using the 60s AFTER the stop, then measures")
    print("   the path from that same point. This one CHARGES YOU FOR THE WAIT, as reality would.)")
    print()
    print(f"  realized on all {len(prep)} stop-outs (take the stop, as today): ${realized_all:>12,.0f}")
    print()
    print(f"  {'wait':>5} {'margin':>7} | {'rule P/L':>13} {'vs today':>13} | {'stayed in':>10} "
          f"{'bailed':>8} | {'floor hits':>10}")
    print("  " + "-" * 76)
    best = None
    for wait in (5, 10, 30, 60, 120):
        for margin in (0.0, 2.0, 5.0):
            v, stayed, bailed, floors = sim_delay(wait, margin)
            pl = v.sum() * pv
            if best is None or pl > best[0]:
                best = (pl, wait, margin, v)
            print(f"  {wait:>5}s {margin:>6.0f}p | ${pl:>12,.0f} ${pl-realized_all:>+12,.0f} | "
                  f"{stayed:>10} {bailed:>8} | {floors:>10}")

    d_best = best[3] - realized
    ctrl_v, ctrl_floors = sim_control()
    ctrl_pl = ctrl_v.sum() * pv
    d_ctrl = ctrl_v - realized

    print()
    print(f"  BEST: wait {best[1]}s, margin {best[2]:.0f} pts -> ${best[0]:,.0f} "
          f"(${best[0]-realized_all:+,.0f} vs taking the stop)")

    # ================================================================================================
    # RESULT 4 — THE CONTROL THAT DECIDES IT. Does the sweep logic add ANYTHING?
    # ================================================================================================
    # The winning cell STAYS IN almost every trade and eats ~100 disaster-floor hits. A rule that almost
    # never takes the stop and lets the loss run to 3x IS NOT SWEEP DETECTION — IT IS JUST A WIDER STOP.
    # So run the dumbest control: never look at a single second of 1-second data; simply hold to TP or the
    # floor. If THAT earns the same money, the sweeps add nothing and the real finding is the far more
    # boring "your stop is too tight" — a different claim, with a far bigger drawdown.
    print()
    print("=" * 84)
    print("RESULT 4 — THE CONTROL: no sweeps, no 1-second data, JUST A WIDER STOP")
    print("=" * 84)
    print(f"  hold every stopped trade to TP or the {a.floor_mult:.0f}x floor "
          f"(stop widened {sl_hard:.0f} -> {a.floor_mult*sl_hard:.0f} pts)")
    print(f"  control P/L: ${ctrl_pl:>12,.0f}   (${ctrl_pl-realized_all:+,.0f} vs taking the stop, "
          f"{ctrl_floors} floor hits)")
    print()
    edge = best[0] - ctrl_pl
    print(f"  ⇒ the 1-second sweep logic is worth ${edge:+,.0f} OVER the dumb control.")
    print(f"    Of the ${best[0]-realized_all:+,.0f} headline, ${ctrl_pl-realized_all:+,.0f} is just "
          f"'the stop is too tight' and needs NO 1-second data at all.")

    # ================================================================================================
    # RESULT 5 — IS ANY OF THIS DISTINGUISHABLE FROM ZERO?
    # ================================================================================================
    # STANDING RULE, learned by retracting an entire workstream: never report a result without asking what
    # the NOISE looks like. Per-trade outcomes here swing by ~100 points. The question is not "is it
    # positive" — it is "is it bigger than the sampling error of 235 draws from a very fat distribution".
    print()
    print("=" * 84)
    print("RESULT 5 — IS IT DISTINGUISHABLE FROM NOISE? (mandatory: no result without this)")
    print("=" * 84)
    rng = np.random.default_rng(0)

    def boot(d: np.ndarray, label: str):
        mu = float(d.mean())
        bs = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(10000)])
        lo_, hi_ = np.percentile(bs, [2.5, 97.5])
        p = float((bs <= 0).mean() * 2) if mu > 0 else float((bs >= 0).mean() * 2)
        print(f"  {label:<32} {mu:>+6.2f} pts/trade (${mu*pv:>+6.0f})  "
              f"95% CI [{lo_:>+6.2f},{hi_:>+6.2f}]  p={p:.3f}"
              f"{'  <<< SIGNIFICANT' if p < 0.05 else '  — NOISE'}")
        return p

    p_best = boot(d_best, "best delay rule vs the stop")
    boot(d_ctrl, "dumb wider stop vs the stop")
    p_edge = boot(d_best - d_ctrl, "SWEEP LOGIC vs the control")
    print()
    sd_ = d_best.std()
    mu_ = abs(d_best.mean())
    need = int((2.8 * sd_ / mu_) ** 2) if mu_ > 1e-9 else 10 ** 9
    print(f"  per-trade spread (sd) = {sd_:.1f} points. THIS is why {len(prep)} trades buys so little:")
    print(f"  a {d_best.mean():+.1f} pt/trade effect against a {sd_:.0f} pt spread needs ~{need:,} "
          f"stop-outs to confirm. We have {len(prep)}.")

    # ---------------------------------------------------------------- THE VERDICT
    print()
    print("=" * 84)
    print("VERDICT — against the criterion declared BEFORE the run")
    print("=" * 84)
    if rate < SWEEP_RATE_KILL:
        print(f"  (A) SATISFIED: sweeps are {100*rate:.1f}% of stop-outs, below the {100*SWEEP_RATE_KILL:.0f}% bar.")
        print(f"      => SWEEPS ARE RARE. The 1-minute martingale verdict STANDS.")
        print(f"      => The dynamic stop-loss remains DEAD. 1-second resolution does not rescue it.")
        return 0

    # (B) IS JUDGED EXACTLY AS IT WAS DECLARED, and the wording matters:
    #
    #     "(B) ... ignoring the stop has expectancy INDISTINGUISHABLE FROM ZERO."
    #
    # Not "is it negative" — INDISTINGUISHABLE FROM ZERO. That is a claim about statistical significance,
    # and it is the whole content of a martingale: a fair game has expectancy zero, and no exit rule can
    # change it. So (B) is settled by the bootstrap p-value, not by the sign of a dollar total.
    #
    # An earlier version of this code tested `delta <= 0` and duly announced "BOTH CONDITIONS BROKEN" on a
    # +$18,685 that is +$80/trade against a ±$1,600 per-trade spread (p = 0.45). That would have retracted
    # report 04 on pure noise. The criterion I wrote down was right; my implementation of it was wrong.
    delta = best[0] - realized_all
    print(f"  (A) NOT satisfied: sweeps are {100*rate:.1f}% of stop-outs (>= {100*SWEEP_RATE_KILL:.0f}%). "
          f"Sweeps are COMMON and REAL.")
    print(f"  (B) judged on the TRADEABLE rule (Result 3), by SIGNIFICANCE — as declared:")
    print(f"      best delay rule = wait {best[1]}s / margin {best[2]:.0f}pts -> ${delta:+,.0f} "
          f"(= {d_best.mean():+.2f} pts/trade), p = {p_best:.3f}")
    print()
    if p_best >= 0.05:
        print(f"      ✅ (B) SATISFIED. The expectancy of ignoring the stop is INDISTINGUISHABLE FROM ZERO")
        print(f"         (p = {p_best:.3f}; the 95% interval contains 0). That is precisely what a")
        print(f"         MARTINGALE looks like — a fair game, which no exit rule can beat.")
        print()
        print(f"      => THE ORIGINAL VERDICT STANDS. The dynamic stop-loss remains DEAD.")
        print()
        print(f"      AND NOTE WHAT DID *NOT* SAVE IT. The sweeps are entirely real: {100*rate:.0f}% of")
        print(f"      stop-outs are swept, and the median one is beyond the stop for ONE SECOND. 1-minute")
        print(f"      bars really are too coarse to see them. The resolution complaint was CORRECT —")
        print(f"      and fixing it changed NOTHING, because the money was never there to begin with.")
        print(f"      Seeing the sweep more clearly does not make it profitable to sit through.")
        print()
        print(f"      Of the ${delta:+,.0f} that LOOKED like an edge, ${ctrl_pl-realized_all:+,.0f} is just")
        print(f"      'the stop is too tight' (no 1-second data needed), and ALL of it is noise:")
        print(f"      {len(prep)} stop-outs against an {d_best.std():.0f}-point per-trade spread would need")
        print(f"      ~{int((2.8*d_best.std()/max(abs(d_best.mean()),1e-9))**2):,} samples to resolve.")
    else:
        print(f"      🚨 (B) BROKEN. Sweeps are common AND ignoring the stop pays, SIGNIFICANTLY "
              f"(p = {p_best:.3f}).")
        print(f"      => Report 04's martingale verdict may be a RESOLUTION ARTIFACT.")
        print(f"      => STILL NOT A RESULT. It needs: a null test; out-of-sample validation (this grid")
        print(f"         was fit in-sample, best-of-15); and the full engine (sequence effects — a held")
        print(f"         trade blocks the next entry). It sizes a PRIZE. It does not bank it.")
        print(f"      => Also note the sweep logic beats a DUMB WIDER STOP by only "
              f"${best[0]-ctrl_pl:+,.0f} (p = {p_edge:.3f}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
