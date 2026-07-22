"""FA-v2 · B1 — CLOSE/TRIM AN OPEN POSITION BEFORE A NEWS RELEASE?

The research (FAV2-02) says this is the one decision idea with a real mechanism: volatility is forecastable
and DECOUPLED from returns, so trimming exposure into a scheduled release gives up variance you can predict
— not return you can't. BUT net-of-cost profitability is contested, so it must be validated on our ledgers.

THE CLEAN, COST-NEUTRAL TEST. For every champion trade that is OPEN across an 08:30 release, compare:
  * HELD-THROUGH   = the trade's actual P/L (it rode through the release).
  * CLOSE-BEFORE   = close at the last 1-min bar before the release (08:29), realize that P/L, stop.
The difference (GIVE-UP = held - close_before) is exactly the P/L earned from 08:29 to the real exit — the
part you forgo by closing early. Closing before news does NOT add a round-trip (it replaces the exit, not
adds one), so this version is COST-NEUTRAL.

THE DECISION (pre-declared):
  * If GIVE-UP is ~zero-mean but HIGH-variance  -> closing before news removes variance FOR FREE. B1 WORKS
    (risk-adjusted), exactly the Moreira-Muir mechanism.
  * If GIVE-UP is significantly POSITIVE          -> holding through EARNS money; closing costs return. B1 fails.
  * If GIVE-UP is significantly NEGATIVE          -> holding through LOSES; closing helps P/L too. B1 wins outright.
Judged by SIGNIFICANCE (bootstrap), not the sign of a dollar total — the standing rule.

  WSH_DATA_BASE=/home/dev/Mulham/wsg-h python3 -u optimize/fundamentals/study_close_on_news.py --tf 4h
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
from optimize.fundamentals import release_calendar as rc           # noqa: E402
from perf._common import champion_preset                           # noqa: E402
from optimize.fundamentals.champion_params import champion_stops  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--n-boot", type=int, default=10000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    df, df1, box, vf, n = data.load_inputs(a.tf, instrument=a.instrument)
    p = champion_preset(a.tf)
    sl_soft, sl_hard, tp, _flip = champion_stops(p)
    gp = float(p["gate_pct"])
    pv = instruments.point_value(a.instrument)

    sig = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], gp))
    MD = df1["Date"].to_numpy(); MC = df1["Close"].to_numpy(float); MO = df1["Open"].to_numpy(float)
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float), MC,
                      sl_soft, sl_hard, tp, _flip, m_open=MO)
    if not F:
        print("no trades"); return 1

    cal = rc.load_calendar()
    rel = cal[cal["Date"].dt.strftime("%H:%M") == "08:30"]["Date"].to_numpy()

    tot_pnl = sum(t["pnl_points"] for t in F) * pv
    print(f"\n{a.instrument} {a.tf} champion · {len(F)} trades · total P/L ${tot_pnl:,.0f} · ${pv:,.0f}/pt")

    rows = []
    for t in F:
        et = np.datetime64(t["entry_time"]); xt = np.datetime64(t["exit_time"])
        long = t["direction"] == "long"
        ep = float(t["entry_price"])
        # first 08:30 release strictly inside (entry_time, exit_time)
        spanning = rel[(rel > et) & (rel < xt)]
        if not len(spanning):
            continue
        ri = int(np.searchsorted(MD, spanning[0], side="left"))
        if ri < 1 or ri >= len(MC):
            continue
        close_before = float(MC[ri - 1])                             # the 08:29 bar
        closed_pnl = (close_before - ep) if long else (ep - close_before)
        held_pnl = float(t["pnl_points"])
        rows.append({"held": held_pnl, "closed": closed_pnl, "giveup": held_pnl - closed_pnl})

    R = pd.DataFrame(rows)
    n_span = len(R)
    print(f"\ntrades OPEN across an 08:30 release: {n_span} of {len(F)} "
          f"({100*n_span/len(F):.1f}%)  — the rest are already flat at release time")
    if n_span < 5:
        print("too few spanning trades to say anything. (Consistent with 'already flat for ~77%'.)")
        return 0

    give = R["giveup"].to_numpy() * pv
    held = R["held"].to_numpy() * pv
    closed = R["closed"].to_numpy() * pv

    print("\n" + "=" * 84)
    print("GIVE-UP — P/L earned from 08:29 (close-before point) to the real exit, per spanning trade")
    print("=" * 84)
    print(f"  total give-up (held − closed) : ${give.sum():>+12,.0f}")
    print(f"  mean per trade                : ${give.mean():>+12,.0f}   sd ${give.std():>,.0f}")
    mu = give.mean()
    bs = np.array([rng.choice(give, len(give), replace=True).mean() for _ in range(a.n_boot)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    pv_ = float((bs <= 0).mean() * 2) if mu > 0 else float((bs >= 0).mean() * 2)
    print(f"  95% CI [${lo:+,.0f}, ${hi:+,.0f}]   bootstrap p = {pv_:.3f}")

    # variance saved vs return given up
    print("\n" + "=" * 84)
    print("THE RISK-ADJUSTED READ (the Moreira-Muir mechanism)")
    print("=" * 84)
    print(f"  holding through the release contributed ${give.sum():+,.0f} of the ${tot_pnl:,.0f} total P/L")
    print(f"  ...at a per-trade sd of ${give.std():,.0f} across {n_span} trades "
          f"(std of the through-release P/L we'd remove by closing).")
    print(f"  closing before news (no re-entry) is COST-NEUTRAL — it moves the exit, adds no round-trip.")

    print("\n" + "=" * 84)
    print("VERDICT — is closing before news worth it?")
    print("=" * 84)
    if pv_ >= 0.05:
        print(f"  ✅ GIVE-UP is INDISTINGUISHABLE FROM ZERO (p={pv_:.3f}) but carries real variance")
        print(f"     (sd ${give.std():,.0f}/trade). => Holding through the release earns ~nothing on average")
        print(f"     while adding risk. Closing before news is a FREE variance reduction — the mechanism holds.")
        print(f"     WORTH a risk-adjusted implementation, BUT note n={n_span} is small (already flat for most")
        print(f"     releases), so the total risk removed is modest. Confirm on GC + more TFs before building.")
    elif mu > 0:
        print(f"  ❌ GIVE-UP is significantly POSITIVE (${give.sum():+,.0f}, p={pv_:.3f}): holding through the")
        print(f"     release EARNS money on average. Closing before news would COST return. Do NOT close.")
    else:
        print(f"  ⚠️ GIVE-UP is significantly NEGATIVE (${give.sum():+,.0f}, p={pv_:.3f}): holding through")
        print(f"     LOSES on average — closing before news would improve BOTH P/L and risk. Strong for B1,")
        print(f"     but check this isn't just the fat tail (a few big through-release losses) before acting.")
    print(f"\n  Also reported: held ${held.sum():+,.0f} vs close-before ${closed.sum():+,.0f} on the {n_span}")
    print(f"  spanning trades. Next: re-entry variant (close 08:29, re-enter after the burst) + GC champion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
