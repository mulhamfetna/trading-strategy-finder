"""Phase-1 study: run the champion through the exact engine with intra-candle vetoed entry OFF (baseline) then
ON across a sweep of wait windows N. Report, per N: net entries added, the win-rate of the genuinely-NEW
(rescued) entries vs the 57.5% breakeven, payoff, total P/L, median hold-time, and max drawdown.

Not purely additive: a rescued mid-candle entry occupies the position and can reshape the later timeline, so we
report BOTH net entry change and the count/quality of genuinely-new entries."""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
from research.intracandle.champion_run import run_champion_exact  # noqa: E402
from research.kalman_fusion.metrics import payoff_ratio, max_drawdown  # noqa: E402

_BREAKEVEN = 0.575   # 1 / (1 + 0.74) — payoff pinned by exits
# payload["trades"] use dollar `pnl` (already x point-value) and epoch-second entry_time/exit_time.


def _hold_min(t):
    return (int(t["exit_time"]) - int(t["entry_time"])) / 60.0


def _metrics(trades, base_keys):
    pnls = np.array([t["pnl"] for t in trades], dtype=float)
    new = [t for t in trades if t["entry_time"] not in base_keys]
    npnl = np.array([t["pnl"] for t in new], dtype=float)
    wr_new = float((npnl > 0).mean()) if npnl.size else 0.0
    holds = [_hold_min(t) for t in trades]
    return {
        "entries_total": len(trades),
        "entries_new": len(new),                      # genuinely-new (rescued) intra-candle entries
        "win_rate_new": round(wr_new, 4),
        "breakeven_ok": bool(wr_new > _BREAKEVEN),
        "new_pnl": round(float(npnl.sum()), 2),       # P/L contributed by the new entries
        "payoff": round(payoff_ratio(pnls), 4),
        "total_pnl": round(float(pnls.sum()), 2),
        "median_hold_min": round(float(np.median(holds)), 1) if holds else 0.0,
        "max_dd": round(max_drawdown(pnls), 2),
    }


def sweep(tf="4h", Ns=(30, 60, 120, 240)):
    base, base_s = run_champion_exact(tf, intracandle_veto_entry=False)
    base_keys = {t["entry_time"] for t in base}
    base_total = float(sum(t["pnl"] for t in base))
    rows = []
    for N in Ns:
        more, _ = run_champion_exact(tf, intracandle_veto_entry=True, intracandle_max_wait=N)
        m = _metrics(more, base_keys)
        m["N"] = N
        m["entries_added_net"] = m["entries_total"] - len(base)
        m["pnl_delta_vs_champ"] = round(m["total_pnl"] - base_total, 2)
        rows.append(m)
    return rows


def _fmt(rows):
    hdr = f"{'N':>4} {'total':>6} {'net+':>5} {'new':>4} {'win%new':>8} {'bkeven':>6} {'medHold':>8} {'PnL':>11} {'dPnL':>10} {'maxDD':>9}"
    out = [f"champion baseline: 214 trades, $142,203 (4h)", hdr]
    for r in rows:
        out.append(f"{r['N']:>4} {r['entries_total']:>6} {r['entries_added_net']:>+5} {r['entries_new']:>4} "
                   f"{100*r['win_rate_new']:>7.1f}% {str(r['breakeven_ok']):>6} {r['median_hold_min']:>7.0f}m "
                   f"{r['total_pnl']:>11,.0f} {r['pnl_delta_vs_champ']:>+10,.0f} {r['max_dd']:>9,.0f}")
    return "\n".join(out)


if __name__ == "__main__":
    print(_fmt(sweep()))
