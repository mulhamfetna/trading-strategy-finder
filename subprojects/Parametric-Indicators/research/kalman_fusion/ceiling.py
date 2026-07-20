"""M0 — the counterfactual CEILING. Reuses counterfactual_pause's champion context + fast_backtest.
Deliberately an ORACLE (peeks at realized outcome to pick the better direction): an UPPER BOUND on what
admitting the dropped flow could earn, not a deployable policy."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from optimize.fast_engine import fast_backtest
from optimize.l2.l1_runner import build_state_timeline
from research.kalman_fusion.metrics import summarize

_BLOCKED = ("vol_gated", "vetoed", "confirm<K")


def eligible_dropped(C) -> dict:
    """Blocked box signals that fired while the champion was FLAT (the honest 'could we have taken it?'
    denominator). Excludes bars the champion was already in a trade."""
    taken = cp.champion_taken_trades(C)
    dec_dates = C["d"]["Date"].to_numpy()
    in_pos = build_state_timeline(taken, dec_dates, C["n"])          # bool[n], True = in a trade
    cause = cp.attribute(C["sig"], C["vol_gate"], C["veto"], C["confirm"])
    by_reason = {r: [] for r in _BLOCKED}
    idxs = []
    for i in range(1, C["n"]):
        if cause[i] in _BLOCKED and not in_pos[i]:
            by_reason[cause[i]].append(i)
            idxs.append(i)
    n_taken = len(taken)
    return {"idxs": idxs, "by_reason": by_reason,
            "n_taken": n_taken, "n_eligible": n_taken + len(idxs)}


def _dirval(direction) -> int:
    """Normalise a direction to +1/-1. Accepts +1/-1 (or any signed number) or 'long'/'short'."""
    if isinstance(direction, str):
        return 1 if direction.strip().lower().startswith("l") else -1
    return 1 if float(direction) > 0 else -1


def simulate_dir(C, entry_idx: int, direction):
    """Isolated trade at entry_idx FORCED to `direction` (+1/-1 or 'long'/'short'), champion exits.
    Returns dollars, or None if it never closes."""
    dv = _dirval(direction)
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = cp._bt_args(C)
    si = np.asarray(si).copy()
    # engine reads the box signal at idx-1 and applies `flip`; undo flip so `direction` is the REALISED side.
    si[entry_idx - 1] = -dv if flip else dv
    gate = np.zeros(C["n"], dtype=bool); gate[int(entry_idx)] = True
    trades = fast_backtest(dd, cl, si, gate, md, mh, ml, mc, sls, slh, tp, flip, m_open=mo)
    if not trades:
        return None
    return float(trades[0]["pnl_points"]) * C["pv"]


def signal_outcomes(C, idxs) -> dict:
    """Per-idx native(+1) / opposite(-1) / oracle dollar P/L. NaN where the trade never closes."""
    native = np.full(len(idxs), np.nan); opposite = np.full(len(idxs), np.nan)
    for k, i in enumerate(idxs):
        up = simulate_dir(C, i, +1); dn = simulate_dir(C, i, -1)
        if up is not None:
            native[k] = up
        if dn is not None:
            opposite[k] = dn
    stack = np.vstack([native, opposite])
    oracle = np.nanmax(stack, axis=0)
    oracle[np.all(np.isnan(stack), axis=0)] = np.nan       # both unresolved → NaN
    return {"native": native, "opposite": opposite, "oracle": oracle}


def _point(pnls, n_eligible):
    m = summarize(pnls, n_eligible=n_eligible)
    return {"n_entries": m.n_entries, "n_eligible": m.n_eligible, "entry_rate": m.entry_rate,
            "payoff": m.payoff, "total_pnl": m.total_pnl, "win_rate": m.win_rate,
            "pf": m.pf, "expectancy": m.expectancy, "max_dd": m.max_dd}


def ceiling_report(C) -> dict:
    """Champion baseline + the 'admit ALL dropped' extreme, box-native vs oracle, per stratum."""
    ed = eligible_dropped(C)
    n_elig = ed["n_eligible"]
    taken = cp.champion_taken_trades(C)
    champ_pnls = [t["pnl_points"] * C["pv"] for t in taken]

    def stratum(idxs):
        o = signal_outcomes(C, idxs)
        native_box = []
        for k, i in enumerate(idxs):
            s = int(np.sign(C["sig"][i - 1]))
            v = o["native"][k] if s >= 0 else o["opposite"][k]   # box direction: +1 sim vs -1 sim
            if not np.isnan(v):
                native_box.append(float(v))
        oracle = [float(v) for v in o["oracle"] if not np.isnan(v)]
        return {"n_dropped": len(idxs),
                "native": _point(champ_pnls + native_box, n_elig),
                "oracle": _point(champ_pnls + oracle, n_elig)}

    rep = {"champion": _point(champ_pnls, n_elig), "all": stratum(ed["idxs"])}
    for r, idxs in ed["by_reason"].items():
        rep[r] = stratum(idxs)
    return rep
