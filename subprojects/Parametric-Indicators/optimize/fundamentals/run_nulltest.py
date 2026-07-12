"""Run the veto rule against the REAL calendar and against N FAKE ones. Print a verdict.

THE POINT: everything else in this milestone could work perfectly and still be worthless. If a FAKE
calendar -- same event count, same times of day, random release-free dates -- improves performance as
much as the real one, then we have not discovered "news matters". We have discovered "flattening
trades sometimes helps", which is a fact about our stop placement, not about the world.

  python3 optimize/fundamentals/run_nulltest.py --tf 4h --n 30
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import core, data, instruments, signals            # noqa: E402
from optimize import timeframes as TF                            # noqa: E402
from optimize.fast_engine import signals_to_int                  # noqa: E402
from optimize.fundamentals import nulltest                       # noqa: E402
from optimize.fundamentals import release_calendar as rc         # noqa: E402
from perf._common import champion_preset                         # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--n", type=int, default=30, help="number of fake calendars")
    ap.add_argument("--pre", type=int, default=0, help="measured: 0")
    ap.add_argument("--post", type=int, default=12, help="measured: 12")
    ap.add_argument("--mult", type=float, default=1.0, help="profit-exemption multiple")
    a = ap.parse_args()

    df_dec, df1, box, vf, n_split = data.load_inputs(a.tf, instrument=a.instrument)
    sig = signals_to_int(signals.decision_signals(df_dec, box))
    bar_td = TF.get(a.tf).bar_td
    pv = instruments.point_value(a.instrument)
    base = dict(champion_preset(a.tf))
    cal = rc.load_calendar()

    def run(**over):
        core._clear_caches()
        return core.backtest_metrics(df_dec, df1, box, vf, n_split,
                                     {**base, **over}, bar_td, sig_int=sig, pv=pv)

    veto = dict(news_veto=True, news_pre_min=a.pre, news_post_min=a.post,
                news_profit_exempt_mult=a.mult)

    off = run(news_veto=False)
    on = run(**veto)
    real_delta = on["pnl"] - off["pnl"]

    print(f"{a.instrument} {a.tf}   window pre={a.pre} post={a.post}   exempt={a.mult}x stop")
    print(f"  calendar: {len(cal)} real events\n")
    print(f"  baseline (veto off) : ${off['pnl']:>12,.0f}   trades={off['n_taken']:>4}   "
          f"DD ${off['max_dd']:>10,.0f}")
    print(f"  REAL calendar       : ${on['pnl']:>12,.0f}   trades={on['n_taken']:>4}   "
          f"DD ${on['max_dd']:>10,.0f}   delta=${real_delta:+,.0f}")
    print(f"\n  running {a.n} fake calendars...\n")

    deltas = []
    for s in range(a.n):
        fake = nulltest.fake_calendar(cal, df1, seed=s)
        res = run(**veto, _news_calendar_override=fake)
        d = res["pnl"] - off["pnl"]
        deltas.append(d)
        print(f"    fake seed {s:>2d}: ${res['pnl']:>12,.0f}  trades={res['n_taken']:>4}  "
              f"delta=${d:+,.0f}")

    deltas = np.array(deltas, dtype=float)
    better = int((deltas >= real_delta).sum())
    p = (better + 1) / (len(deltas) + 1)          # +1/+1: the standard permutation-test estimator

    print(f"\n  fake delta: mean=${deltas.mean():+,.0f}  sd=${deltas.std():,.0f}  "
          f"min=${deltas.min():+,.0f}  max=${deltas.max():+,.0f}")
    print(f"  real delta: ${real_delta:+,.0f}")
    print(f"  {better}/{len(deltas)} fake calendars did AT LEAST AS WELL as the real one")
    print(f"  empirical p-value = {p:.3f}\n")

    if p < 0.05:
        print("  VERDICT: REAL EFFECT (p < 0.05) — the real calendar beats chance.")
        return 0
    print("  VERDICT: *** INDISTINGUISHABLE FROM CHANCE — DO NOT SHIP ***")
    print("           The rule is not reading news; it is just flattening trades.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
