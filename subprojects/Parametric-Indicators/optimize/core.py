"""H.1 — timeframe-parametric, metrics-only backtest core.

This is the optimiser's fast path: it runs the SAME verified clone engine + the SAME volatility
gate + the SAME global-high-water-mark drawdown breaker as the dashboard's `strategy.build_payload`,
but (a) parameterised by the *decision-bar duration* (so any entry timeframe works — the only 4h
assumption removed is the hardcoded `+4h` 1m-window bound), and (b) returns only the summary metrics
+ the taken-trade list (no chart series), so thousands of trials run quickly.

Parity contract (locked by test_parity.py): with bar_duration = 4h and the winner params, this
reproduces `strategy.build_payload`'s summary bit-for-bit (+$7,735 / $3,670 maxDD / 66 trades).

Exits are unchanged — always resolved on the 1-minute frame inside the engine.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# the parent subproject modules use top-level imports (engine, box_lookup, ...)
_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import config  # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int  # noqa: E402
from optimize import signals as _sig  # noqa: E402


def backtest_metrics(
    df_dec: pd.DataFrame,
    df1: pd.DataFrame,
    box: pd.DataFrame,
    vf: np.ndarray,
    n_split: int,
    params: dict,
    bar_duration: pd.Timedelta,
    *,
    gate_ref_vf: np.ndarray | None = None,
    sig_int: np.ndarray | None = None,
    pv: float = config.NQ_POINT_VALUE,
) -> dict:
    """Run one backtest on an arbitrary decision timeframe; return summary metrics + trades.

    Args:
      df_dec:   decision-frame OHLCV (any timeframe); needs 'Date','Open','High','Low','Close'.
      df1:      1-minute OHLCV (exit resolution + realized vol). Unchanged across timeframes.
      box:      box-level frame indexed by normalized Date.
      vf:       HAR-RV forecast aligned 1:1 with df_dec rows.
      n_split:  index splitting the first calendar segment (e.g. 2025) from the rest; the gate
                threshold is frozen on vf[:n_split] (causal) unless gate_ref_vf is given.
      params:   {sl_soft, sl_hard, tp, gate_pct, dd_limit, cooldown, flip, window}.
      bar_duration: decision-bar length (e.g. pd.Timedelta(hours=4)); replaces the hardcoded +4h.
      gate_ref_vf:  optional explicit reference array for the gate percentile (walk-forward, H.6).
                    Defaults to vf[:n_split].

    Returns dict(pnl, pnl_2025, pnl_2026, max_dd, n_taken, n_candidates, n_skipped_breaker,
                 win, pf, n_locks, exposure, trades).
    """
    sl_soft = float(params["sl_soft"]); sl_hard = float(params["sl_hard"]); tp = float(params["tp"])
    gate_pct = float(params["gate_pct"]); dd_limit = float(params["dd_limit"])
    cooldown = int(params["cooldown"]); flip = bool(params["flip"])
    window = params.get("window", "full")

    N = len(df_dec)
    lo, hi = {"full": (0, N), "2025": (0, n_split), "2026": (n_split, N)}[window]
    d = df_dec.iloc[lo:hi].reset_index(drop=True)
    if d.empty:
        return _empty()
    t0 = d["Date"].iloc[0]
    t1 = d["Date"].iloc[-1] + bar_duration            # generalised: was hardcoded +4h
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    vfw = vf[lo:hi]

    # Volatility gate threshold frozen on the reference segment (causal); 0 => no gate.
    gate = None
    if gate_pct > 0:
        ref = gate_ref_vf if gate_ref_vf is not None else vf[:n_split]
        gthr = float(np.percentile(ref, gate_pct))
        gate = vfw <= gthr

    # WS-I.7 indicator layer (optional): fold veto + confirm into the gate as a per-bar mask.
    # gate_used = vol_gate ∧ ¬veto ∧ confirm≥K. Off/absent ⇒ gate unchanged (parity). The fast path
    # treats confirm/veto as an immediate-fill GATE; retrace/wait + live-carry stay in the exact
    # engine (dashboard). NSGA search over which indicators help runs on this gate.
    specs = params.get("indicators") or []
    if specs:
        from indicators import library, runner
        inds = library.from_specs(specs)
        if any(i.config.enabled for i in inds):
            base = gate if gate is not None else np.ones(len(d), dtype=bool)
            vmask = runner.veto_mask(d, box, inds)
            cmask = runner.confirm_mask(d, box, inds, int(params.get("k", 1)))
            gate = base & ~vmask & cmask

    # precomputed signals (param-independent) sliced to the window; else compute on the slice
    si = sig_int[lo:hi] if sig_int is not None else signals_to_int(_sig.decision_signals(d, box))
    cand = fast_backtest(
        d["Date"].to_numpy(), d["Close"].to_numpy(float), si, gate,
        d1["Date"].to_numpy(), d1["High"].to_numpy(float),
        d1["Low"].to_numpy(float), d1["Close"].to_numpy(float),
        sl_soft, sl_hard, tp, flip)
    # fast_backtest returns completed trades already in entry order (no OPEN trades)

    # Global-HWM drawdown breaker overlay (identical math to strategy.build_payload).
    use_brk = dd_limit > 0
    peak = eq = 0.0
    locked = False
    cd = 0
    skipped = 0
    n_locks = 0
    taken = []
    for t in cand:
        pnl = float(t["pnl_points"]) * pv
        if use_brk and locked:
            cd -= 1
            if cd <= 0:
                locked = False           # keep GLOBAL high-water mark (no peak reset)
            else:
                skipped += 1
                continue
        eq += pnl
        peak = max(peak, eq)
        dd = peak - eq
        taken.append({"pnl": pnl, "eq": eq, "dd": dd,
                      "year": pd.Timestamp(t["exit_time"]).year})
        if use_brk and dd >= dd_limit:
            locked = True
            cd = cooldown
            n_locks += 1

    if not taken:
        out = _empty(); out["n_candidates"] = len(cand); out["n_skipped_breaker"] = skipped
        return out

    pnl_arr = np.array([t["pnl"] for t in taken])
    yr = np.array([t["year"] for t in taken])
    eq_arr = np.array([t["eq"] for t in taken])
    uw = np.maximum.accumulate(eq_arr) - eq_arr
    wins = pnl_arr[pnl_arr > 0]; losses = pnl_arr[pnl_arr < 0]
    return dict(
        pnl=float(pnl_arr.sum()),
        pnl_2025=float(pnl_arr[yr == config.YEARS[0]].sum()),
        pnl_2026=float(pnl_arr[yr == config.YEARS[1]].sum()),
        max_dd=float(uw.max()),
        n_taken=len(taken), n_candidates=len(cand), n_skipped_breaker=skipped,
        exposure=round(100 * len(taken) / max(len(cand), 1), 1),
        win=round(100 * (pnl_arr > 0).mean(), 1),
        pf=(round(float(wins.sum() / abs(losses.sum())), 2)
            if len(losses) and losses.sum() != 0 else None),
        n_locks=n_locks,
        trades=taken,
    )


def _empty() -> dict:
    return dict(pnl=0.0, pnl_2025=0.0, pnl_2026=0.0, max_dd=0.0, n_taken=0, n_candidates=0,
                n_skipped_breaker=0, exposure=0.0, win=0.0, pf=None, n_locks=0, trades=[])
