"""FA-v2 · B3 — THE "ASSIST" (scale-in after a loss near news): does it have a real recovery edge?

The user's hypothesis: after a position takes a certain loss near a news event, price 'skyrockets', so
adding a second contract and waiting recovers both. The research (FAV2-02) is one-directional against
this: averaging down without a genuine positive edge is a documented route to ruin, and fat tails make it
worse. The ONLY thing that could rescue it is a real, positive, NEWS-CONDITIONAL recovery edge that our
(non-news) stop-loss martingale study did not see.

THE TEST — decisive because the "added contract" is just a fresh position entered AT THE LOSS POINT, so
its expectancy IS the whole question. On the 17-year NQ frame (full power):
  * anchor at each 08:30 release, reference price p0 = close[T-1] (causal).
  * simulate a hypothetical position (LONG and SHORT tested). Find the first bar within W minutes where it
    is down >= L points — the "loss point" t_loss (where the user would add a second contract).
  * the ADDED contract enters same-direction at close[t_loss]; its recovery over the next H minutes is the
    future return from t_loss. THAT expectancy decides everything.
  * DUMB CONTROL: the identical procedure at thousands of RANDOM non-news times. If a news-loss recovers no
    better than a matched non-news loss, there is no news edge — the assist is a fair bet at DOUBLE size.

PRE-DECLARED VERDICT (does not move):
  The assist has a real edge ONLY IF the added-contract future return after a NEWS loss is (a) significantly
  POSITIVE and (b) significantly BETTER than the non-news control. Otherwise it is REJECTED: doubling down
  on a fair-or-negative bet only multiplies exposure to the fat tail (#7) — the account-killer the research
  warns of. We also report the TAIL (worst outcomes) because that, not the mean, is what ruins the account.

  WSH_DATA_BASE=/home/dev/Mulham python3 -u optimize/fundamentals/study_assist.py --L 40
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals import release_calendar as rc            # noqa: E402
from optimize.fundamentals.extended_data import load_1m_extended    # noqa: E402


def loss_then_recover(close, anchors, L, W, H, direction):
    """For each anchor index a (reference = close[a-1]), find the first loss>=L within W bars; return the
    ADDED contract's future return over H bars from the loss point (same direction). direction: +1 long."""
    out = []
    for a in anchors:
        if a < 1 or a + W >= len(close):
            continue
        p0 = close[a - 1]
        seg = close[a:a + W]
        pnl = direction * (seg - p0)                      # position P/L path
        hit = np.flatnonzero(pnl <= -L)
        if not len(hit):
            continue
        t = a + int(hit[0])                               # the loss point
        if t + H >= len(close):
            continue
        add_ret = direction * (close[t + H] - close[t])   # added contract's recovery over H
        # also: does the ADDED contract get back to breakeven at any point in H?
        fut = direction * (close[t:t + H + 1] - close[t])
        recovered = bool((fut >= L).any())                # 'skyrocket' = added contract gains >= L
        out.append((add_ret, recovered))
    return out


def summarize(rows, pv, label, rng):
    if not rows:
        print(f"  {label:<10} no loss events"); return None
    r = np.array([x[0] for x in rows]) * pv
    rec = np.array([x[1] for x in rows])
    mu = r.mean()
    bs = np.array([rng.choice(r, len(r), replace=True).mean() for _ in range(10000)])
    p = float((bs <= 0).mean() * 2) if mu > 0 else float((bs >= 0).mean() * 2)
    print(f"  {label:<10} n={len(r):>4}  added-contract E[return] ${mu:>+7,.0f}/trade  "
          f"p={p:.3f}  skyrocket {100*rec.mean():>4.1f}%  worst ${r.min():>+8,.0f}  sd ${r.std():>,.0f}")
    return {"mu": mu, "p": p, "r": r, "n": len(r)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=float, default=40.0, help="loss in points that triggers the assist")
    ap.add_argument("--W", type=int, default=30, help="minutes within which the loss must occur")
    ap.add_argument("--H", type=int, default=60, help="minutes to hold the added contract for recovery")
    ap.add_argument("--pv", type=float, default=20.0, help="$/point (NQ)")
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    df = load_1m_extended("NQ")
    close = df["Close"].to_numpy(float)
    idx = pd.Index(df["Date"])
    cal = rc.load_calendar()
    rel = cal[cal["Date"].dt.strftime("%H:%M") == "08:30"]["Date"]
    news_anchor = idx.get_indexer(rel)
    news_anchor = news_anchor[news_anchor >= 1]

    # control anchors: random bars during RTH-ish hours, away from any release (>= 2h)
    reld = idx[news_anchor].values.astype("datetime64[m]")
    all_bars = np.arange(1, len(close))
    # cheap 'away from news': drop bars within 120 min of any news anchor
    mask = np.ones(len(close), dtype=bool)
    for na in news_anchor:
        mask[max(0, na - 120):na + 120] = False
    ctrl_pool = all_bars[mask[all_bars]]
    ctrl_anchor = rng.choice(ctrl_pool, size=min(4000, len(ctrl_pool)), replace=False)

    print(f"\nNQ 17y · {len(close):,} bars · L={a.L:.0f}pt loss, within {a.W}min, hold added contract {a.H}min")
    print(f"news anchors: {len(news_anchor)} releases · control anchors: {len(ctrl_anchor)} random non-news bars\n")

    res = {}
    for dname, dirn in (("LONG (down-move then add long)", +1), ("SHORT (up-move then add short)", -1)):
        print("=" * 92)
        print(f"{dname}")
        print("=" * 92)
        news = loss_then_recover(close, news_anchor, a.L, a.W, a.H, dirn)
        ctrl = loss_then_recover(close, ctrl_anchor, a.L, a.W, a.H, dirn)
        rn = summarize(news, a.pv, "NEWS", rng)
        rc_ = summarize(ctrl, a.pv, "control", rng)
        res[dirn] = (rn, rc_)
        print()

    # ---------------------------------------------------------------- VERDICT
    print("=" * 92)
    print("VERDICT — the pre-declared criterion (does NOT move)")
    print("=" * 92)
    any_edge = False
    for dirn, name in ((+1, "LONG"), (-1, "SHORT")):
        rn, rc_ = res[dirn]
        if rn is None or rc_ is None:
            continue
        news_pos = rn["mu"] > 0 and rn["p"] < 0.05
        # news better than control (bootstrap of the difference)
        diff = rn["mu"] - rc_["mu"]
        bs = np.array([rng.choice(rn["r"], rn["n"], True).mean() - rng.choice(rc_["r"], rc_["n"], True).mean()
                       for _ in range(10000)])
        pdiff = float((bs <= 0).mean() * 2) if diff > 0 else float((bs >= 0).mean() * 2)
        better = diff > 0 and pdiff < 0.05
        print(f"  {name}: added-contract after a NEWS loss = ${rn['mu']:+,.0f}/trade (p={rn['p']:.3f}); "
              f"control ${rc_['mu']:+,.0f}; news−control ${diff:+,.0f} (p={pdiff:.3f})")
        if news_pos and better:
            any_edge = True
            print(f"       -> significantly POSITIVE and BETTER than control. A real news recovery edge (rare!).")
        else:
            print(f"       -> {'not positive' if not news_pos else 'positive'} / "
                  f"{'not better than control' if not better else 'better'} => NO edge on this side.")
    print()
    if any_edge:
        print("  ⚠️ A news-conditional recovery edge SURVIVED on at least one side. Do NOT rush to build:")
        print("     next it needs out-of-sample confirmation, a cost model, and — critically — a tail /")
        print("     risk-of-ruin analysis, because the assist DOUBLES exposure to the fat tail (#7).")
    else:
        print("  ❌ REJECTED. The added contract after a news loss has NO positive, control-beating edge.")
        print("     Adding a second contract is therefore a fair-or-negative bet at DOUBLE size — it only")
        print("     multiplies exposure to the fat per-trade tail (the ±$1,600 swing that defeated every")
        print("     edge in this project). This is exactly the averaging-down-into-ruin the research warns")
        print("     of. The 'assist' must NOT be built. (Consistent with our stop-loss martingale finding:")
        print("     post-loss price is a FAIR game; the news condition does not rescue it.)")
    print("\n  NOTE THE TAIL: read the 'worst' column above — one such loss into a DOUBLED position is the")
    print("  account-killer, and it is not hypothetical (see the 1-second sweep / 80-pt per-trade sd).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
