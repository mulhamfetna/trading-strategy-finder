"""Reusable backtest-to-payload builder for the interactive winning-strategy dashboard.

`build_payload(df4, df1, box, vf, n2025, params)` runs the verified single-contract CLONE with
the given parameters, applies the causal drawdown circuit-breaker overlay, and returns the full
dashboard payload (candles, vol, trades, events, equity, drawdown, state, summary). Used by both
the static exporter (scripts/49) and the live server (server.py).

params keys (all optional → sensible defaults = the winning config):
  sl_soft, sl_hard, tp, gate_pct (None/0 = no gate), dd_limit (None/0 = no breaker),
  cooldown, flip (bool), window ('full'|'2025'|'2026')
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

_PROJ = Path("/mnt/data/projects/trading")
_MP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJ)); sys.path.insert(0, str(_MP))
import importlib.util
_spec = importlib.util.spec_from_file_location("bm", _MP / "scripts" / "17_backtest_matrix.py")
bm = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(bm)

NQ_PV = 20.0
DEFAULTS = dict(sl_soft=30.0, sl_hard=40.0, tp=60.0, gate_pct=60.0,
                dd_limit=2500.0, cooldown=30, flip=False, window="full")


def _ts(dt): return int(pd.Timestamp(dt).timestamp())


def load_inputs():
    """Load 4h/1m/box once + the causal HAR-RV forecast. Returns (df4, df1, box, vf, n2025)."""
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum())
    vf = bm.har_rv_forecast(df4)
    return df4, df1, box, vf, n2025


def build_payload(df4, df1, box, vf, n2025, params=None):
    p = {**DEFAULTS, **(params or {})}
    sl_soft, sl_hard, tp = float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"])
    cooldown = int(p["cooldown"]); flip = bool(p["flip"])
    gate_pct = p["gate_pct"]; dd_limit = p["dd_limit"]
    window = p["window"] if p["window"] in ("full", "2025", "2026") else "full"

    # validate engine ordering constraints (clone requires hard >= soft, all > 0)
    sl_soft = max(1.0, sl_soft); sl_hard = max(sl_hard, sl_soft); tp = max(1.0, tp)

    N = len(df4)
    lo, hi = {"full": (0, N), "2025": (0, n2025), "2026": (n2025, N)}[window]
    d4 = df4.iloc[lo:hi].reset_index(drop=True)
    t0, t1 = d4["Date"].iloc[0], d4["Date"].iloc[-1] + pd.Timedelta(hours=4)
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    vfw = vf[lo:hi]

    # gate threshold frozen on 2025 (causal); None/0 => no gate
    gthr = None
    gate = None
    if gate_pct not in (None, 0, "", "none"):
        gthr = float(np.percentile(vf[:n2025], float(gate_pct)))
        gate = vfw <= gthr

    sp = bm.SimpleStrategyParams(sl_soft_points=sl_soft, sl_hard_points=sl_hard,
                                 tp_soft_points=tp, tp_hard_points=tp, data_path_4h="",
                                 data_path_1min="", box_data_path="", flip_entry_direction=flip)
    trades, _ = bm.SimpleStrategy(sp).backtest(d4, d1, box, entry_gate=gate)
    cand = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    cand.sort(key=lambda t: pd.Timestamp(t["entry_time"]))

    use_brk = dd_limit not in (None, 0, "", "none")
    dd_limit_f = float(dd_limit) if use_brk else 0.0
    peak = eq = 0.0; locked = False; cd = 0; skipped = 0
    taken, events, state, eq_curve = [], [], [], []
    for t in cand:
        et, xt = _ts(t["entry_time"]), _ts(t["exit_time"])
        pnl_d = float(t["pnl_points"]) * NQ_PV
        if use_brk and locked:
            cd -= 1
            if cd <= 0:
                locked = False; peak = eq
                events.append({"time": et, "type": "UNLOCK",
                               "text": f"UNLOCK — cooldown done; resume; peak reset to ${eq:,.0f}"})
            else:
                state.append({"time": et, "value": 0}); skipped += 1
                events.append({"time": et, "type": "SKIP",
                               "text": f"LOCKED — skip {t['direction']} @ {t['entry_price']:.1f} "
                                       f"(would-be {pnl_d:+,.0f}); {cd} left in cooldown"})
                continue
        state.append({"time": et, "value": 1})
        gtxt = "no gate" if gthr is None else f"gate OK (vol {vfw[int(t['entry_idx'])]:.0f} ≤ {gthr:.0f})"
        events.append({"time": et, "type": "ENTRY",
                       "text": f"{t['direction'].upper()} @ {t['entry_price']:.1f} | {gtxt} | "
                               f"SLsoft {t['sl_soft_line']:.1f}/SLhard {t['sl_hard_line']:.1f}/TP {t['tp_hard_line']:.1f}"})
        eq += pnl_d; peak = max(peak, eq); dd = peak - eq
        events.append({"time": xt, "type": "WIN" if pnl_d > 0 else "LOSS",
                       "text": f"exit @ {t['exit_price']:.1f} via {t['exit_reason']} | P/L {pnl_d:+,.0f} "
                               f"| equity ${eq:,.0f} | DD ${dd:,.0f}"})
        eq_curve.append({"time": xt, "value": round(eq, 2)})
        rec = {k: t[k] for k in ("entry_price", "exit_price", "direction", "exit_reason",
                                 "sl_soft_line", "sl_hard_line", "tp_soft_line", "tp_hard_line")}
        rec.update(entry_time=et, exit_time=xt, pnl=round(pnl_d, 2), equity=round(eq, 2),
                   dd=round(dd, 2), year=pd.Timestamp(t["exit_time"]).year)
        taken.append(rec)
        if use_brk and dd >= dd_limit_f:
            locked = True; cd = cooldown
            events.append({"time": xt, "type": "LOCK",
                           "text": f"🔒 LOCK — DD ${dd:,.0f} ≥ ${dd_limit_f:,.0f}; halt {cooldown} trades"})

    candles = [{"time": _ts(d4["Date"].iloc[i]), "open": float(d4["Open"].iloc[i]),
                "high": float(d4["High"].iloc[i]), "low": float(d4["Low"].iloc[i]),
                "close": float(d4["Close"].iloc[i])} for i in range(len(d4))]
    vol = [{"time": _ts(d4["Date"].iloc[i]), "value": round(float(vfw[i]), 1)} for i in range(len(d4))]
    eqarr = np.array([e["value"] for e in eq_curve]) if eq_curve else np.array([0.0])
    uw = np.maximum.accumulate(eqarr) - eqarr
    drawdown = [{"time": eq_curve[i]["time"], "value": -round(float(uw[i]), 2)} for i in range(len(eq_curve))]

    pnl = np.array([t["pnl"] for t in taken]) if taken else np.array([])
    yr = np.array([t["year"] for t in taken]) if taken else np.array([])
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    summary = dict(
        pnl=float(pnl.sum()) if len(pnl) else 0.0,
        pnl_2025=float(pnl[yr == 2025].sum()) if len(pnl) else 0.0,
        pnl_2026=float(pnl[yr == 2026].sum()) if len(pnl) else 0.0,
        n_taken=len(taken), n_candidates=len(cand), n_skipped_breaker=skipped,
        exposure=round(100 * len(taken) / max(len(cand), 1), 1),
        win=round(100 * (pnl > 0).mean(), 1) if len(pnl) else 0.0,
        pf=round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) and losses.sum() != 0 else None,
        avg_win=round(float(wins.mean()), 0) if len(wins) else 0,
        avg_loss=round(float(losses.mean()), 0) if len(losses) else 0,
        max_dd=round(float(uw.max()), 0) if len(eq_curve) else 0.0,
        best=float(pnl.max()) if len(pnl) else 0.0, worst=float(pnl.min()) if len(pnl) else 0.0,
        n_locks=sum(1 for e in events if e["type"] == "LOCK"))

    params_out = dict(sl_soft=sl_soft, sl_hard=sl_hard, tp=tp,
                      gate_pct=(None if gthr is None else float(gate_pct)),
                      gate_thr=(None if gthr is None else round(gthr, 0)),
                      dd_limit=(dd_limit_f if use_brk else None), cooldown=cooldown,
                      dd_cap=5000.0, pv=NQ_PV, flip=flip, window=window)
    return dict(meta=dict(params=params_out, summary=summary,
                          split_ts=_ts(df4.iloc[n2025]["Date"])),
                candles=candles, vol=vol, gate_thr=(gthr if gthr is not None else 0),
                state=state, trades=taken, equity=eq_curve, drawdown=drawdown,
                events=sorted(events, key=lambda e: e["time"]))
