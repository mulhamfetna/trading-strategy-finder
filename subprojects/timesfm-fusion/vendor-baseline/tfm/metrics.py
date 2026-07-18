"""Performance metrics — matches the reference run_stats.py definitions so numbers are comparable.

Max drawdown uses the same global-high-water-mark underwater math on the chronological (by exit
time) net-P/L stream. Return/DD is the headline 'high profit + low drawdown' fitness.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .engine import Trade


@dataclass
class Stats:
    n: int
    pnl: float
    win: float
    pf: float
    max_dd: float
    ret_dd: float
    avg_w: float
    avg_l: float
    expectancy: float

    def as_row(self) -> dict:
        return dict(n=self.n, pnl=self.pnl, win=self.win, pf=self.pf,
                    max_dd=self.max_dd, ret_dd=self.ret_dd, avg_w=self.avg_w,
                    avg_l=self.avg_l, expectancy=self.expectancy)


def compute_stats(trades: list[Trade]) -> Stats:
    rows = sorted(trades, key=lambda r: r.exit_time)
    n = len(rows)
    if n == 0:
        return Stats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    pnls = np.array([r.pnl for r in rows], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    gross_w = float(wins.sum())
    gross_l = float(-losses.sum())
    pf = (gross_w / gross_l) if gross_l else float("inf")
    eq = np.cumsum(pnls)
    max_dd = float((np.maximum.accumulate(eq) - eq).max())
    pnl = float(pnls.sum())
    ret_dd = (pnl / max_dd) if max_dd else float("inf")
    return Stats(
        n=n, pnl=pnl,
        win=100.0 * len(wins) / n,
        pf=pf, max_dd=max_dd, ret_dd=ret_dd,
        avg_w=float(wins.mean()) if len(wins) else 0.0,
        avg_l=float(losses.mean()) if len(losses) else 0.0,
        expectancy=pnl / n,
    )


def fmt_stats(s: Stats, point_value: float | None = None) -> str:
    pf = "inf" if s.pf == float("inf") else f"{s.pf:.2f}"
    rd = "inf" if s.ret_dd == float("inf") else f"{s.ret_dd:.2f}"
    pts = f"   ({s.pnl / point_value:,.1f} pts)" if point_value else ""
    return (f"  trades {s.n:>4}   win {s.win:>5.1f}%   PF {pf:>5}\n"
            f"  net P/L      ${s.pnl:>12,.0f}{pts}\n"
            f"  max drawdown ${s.max_dd:>12,.0f}   return/DD {rd}\n"
            f"  avg win      ${s.avg_w:>12,.0f}   avg loss ${s.avg_l:,.0f}\n"
            f"  expectancy   ${s.expectancy:>12,.2f} / trade")
