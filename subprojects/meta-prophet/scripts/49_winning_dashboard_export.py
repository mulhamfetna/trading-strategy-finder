"""WS-G — data exporter for the WINNING-STRATEGY dashboard (dashboard_winner/).

Runs the winning config (SL 30/40, TP 60, vol-gate@60, drawdown breaker $2,500/30) through the
verified single-contract CLONE, applies the causal drawdown breaker, and emits a rich embedded
`data.js` for a dedicated standalone dashboard. Exposes EVERYTHING the viewer needs to know what
happened, when and why:
  - candles + per-trade markers + ALL FOUR exit lines (soft SL, hard SL, soft TP, hard TP)
  - HAR-RV volatility forecast + the gate threshold
  - engine state timeline (1 = TRADING, 0 = LOCKED by the breaker)
  - equity curve + underwater drawdown (with −$2,500 breaker trigger and −$5,000 cap lines)
  - a VERBOSE chronological event log (entries / exits / gate context / breaker LOCK & UNLOCK)
  - a full per-trade table and summary stats

Main dashboard is NOT touched — this writes only into dashboard_winner/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path("/mnt/data/projects/trading"); ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ)); sys.path.insert(0, str(ROOT))
import importlib.util
spec = importlib.util.spec_from_file_location("bm", ROOT / "scripts" / "17_backtest_matrix.py")
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

NQ_PV = 20.0
# ----- WINNING CONFIG -----
SL_SOFT, SL_HARD, TP, GATE_PCT = 30.0, 40.0, 60.0, 60
DD_LIMIT, COOLDOWN, DD_CAP = 2000.0, 20, 5000.0
OUTDIR = ROOT / "dashboard_winner"; OUTDIR.mkdir(exist_ok=True)


def _ts(dt): return int(pd.Timestamp(dt).timestamp())


def main():
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum())
    vf = bm.har_rv_forecast(df4)
    gthr = float(np.percentile(vf[:n2025], GATE_PCT))
    gate = vf <= gthr

    p = bm.SimpleStrategyParams(sl_soft_points=SL_SOFT, sl_hard_points=SL_HARD, tp_soft_points=TP,
                                tp_hard_points=TP, data_path_4h="", data_path_1min="",
                                box_data_path="", flip_entry_direction=False)
    trades, _ = bm.SimpleStrategy(p).backtest(df4, df1, box, entry_gate=gate)
    cand = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    cand.sort(key=lambda t: pd.Timestamp(t["entry_time"]))

    # ---- breaker walk: classify taken vs locked-out, build events + equity + state ----
    peak = eq = 0.0; locked = False; cd = 0
    taken, events, state, eq_curve = [], [], [], []
    skipped_breaker = 0
    for t in cand:
        et, xt = _ts(t["entry_time"]), _ts(t["exit_time"])
        pnl_d = float(t["pnl_points"]) * NQ_PV
        if locked:
            cd -= 1
            if cd <= 0:
                # cooldown finished → unlock and TAKE this trade (matches scripts 46/47/48)
                locked = False  # FIX: keep GLOBAL high-water mark (no peak reset)
                events.append({"time": et, "type": "UNLOCK", "text":
                    f"UNLOCK — cooldown done; resume trading on this bar, drawdown global peak ${peak:,.0f} kept"})
            else:
                state.append({"time": et, "value": 0})
                skipped_breaker += 1
                events.append({"time": et, "type": "SKIP", "text":
                    f"LOCKED — skip {t['direction']} signal @ {t['entry_price']:.1f} "
                    f"(would-be P/L {pnl_d:+,.0f}); {cd} trades left in cooldown"})
                continue
        # take the trade
        state.append({"time": et, "value": 1})
        events.append({"time": et, "type": "ENTRY", "text":
            f"{t['direction'].upper()} entry @ {t['entry_price']:.1f}  | gate OK (vol {vf[int(t['entry_idx'])]:.0f} ≤ {gthr:.0f}) "
            f"| SLsoft {t['sl_soft_line']:.1f} / SLhard {t['sl_hard_line']:.1f} / TP {t['tp_hard_line']:.1f}"})
        eq += pnl_d; peak = max(peak, eq); dd = peak - eq
        events.append({"time": xt, "type": "WIN" if pnl_d > 0 else "LOSS", "text":
            f"exit @ {t['exit_price']:.1f} via {t['exit_reason']}  | P/L {pnl_d:+,.0f} "
            f"| equity ${eq:,.0f} | drawdown ${dd:,.0f}"})
        eq_curve.append({"time": xt, "value": round(eq, 2)})
        tk = {k: t[k] for k in ("entry_price", "exit_price", "direction", "exit_reason",
                                "sl_soft_line", "sl_hard_line", "tp_soft_line", "tp_hard_line")}
        tk.update(entry_time=et, exit_time=xt, pnl=round(pnl_d, 2),
                  equity=round(eq, 2), dd=round(dd, 2), year=pd.Timestamp(t["exit_time"]).year)
        taken.append(tk)
        if dd >= DD_LIMIT:
            locked = True; cd = COOLDOWN
            events.append({"time": xt, "type": "LOCK", "text":
                f"🔒 LOCK — drawdown ${dd:,.0f} ≥ ${DD_LIMIT:,.0f}; halt new entries for {COOLDOWN} trades"})

    # ---- series ----
    candles = [{"time": _ts(df4["Date"].iloc[i]), "open": float(df4["Open"].iloc[i]),
                "high": float(df4["High"].iloc[i]), "low": float(df4["Low"].iloc[i]),
                "close": float(df4["Close"].iloc[i])} for i in range(len(df4))]
    vol = [{"time": _ts(df4["Date"].iloc[i]), "value": round(float(vf[i]), 1)} for i in range(len(df4))]
    eqarr = np.array([e["value"] for e in eq_curve]) if eq_curve else np.array([0.0])
    peakarr = np.maximum.accumulate(eqarr); uw = peakarr - eqarr
    drawdown = [{"time": eq_curve[i]["time"], "value": -round(float(uw[i]), 2)} for i in range(len(eq_curve))]

    pnl = np.array([t["pnl"] for t in taken]); yr = np.array([t["year"] for t in taken])
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    mdf = pd.DataFrame({"x": [pd.Timestamp(t["exit_time"], unit="s") for t in taken], "p": pnl})
    mdf["ym"] = mdf["x"].dt.to_period("M").astype(str)
    monthly = [{"ym": k, "pnl": round(float(v), 0)} for k, v in mdf.groupby("ym")["p"].sum().items()]
    exitr = pd.Series([t["exit_reason"] for t in taken]).value_counts().to_dict()

    summary = dict(
        pnl=float(pnl.sum()), pnl_2025=float(pnl[yr == 2025].sum()), pnl_2026=float(pnl[yr == 2026].sum()),
        n_taken=len(taken), n_candidates=len(cand), n_skipped_breaker=skipped_breaker,
        exposure=round(100 * len(taken) / max(len(cand), 1), 1),
        win=round(100 * (pnl > 0).mean(), 1), pf=round(wins.sum() / abs(losses.sum()), 2) if len(losses) else None,
        avg_win=round(float(wins.mean()), 0) if len(wins) else 0, avg_loss=round(float(losses.mean()), 0) if len(losses) else 0,
        max_dd=round(float(uw.max()), 0), best=float(pnl.max()), worst=float(pnl.min()),
        n_locks=sum(1 for e in events if e["type"] == "LOCK"))

    params = dict(sl_soft=SL_SOFT, sl_hard=SL_HARD, tp=TP, gate_pct=GATE_PCT, gate_thr=round(gthr, 0),
                  dd_limit=DD_LIMIT, cooldown=COOLDOWN, dd_cap=DD_CAP, pv=NQ_PV)

    payload = dict(meta=dict(params=params, summary=summary, split_ts=_ts(df4.iloc[n2025]["Date"])),
                   candles=candles, vol=vol, gate_thr=gthr, state=state, trades=taken,
                   equity=eq_curve, drawdown=drawdown, monthly=monthly, exit_reasons=exitr,
                   events=sorted(events, key=lambda e: e["time"]))
    (OUTDIR / "data.js").write_text("window.WINNER_DATA = " + json.dumps(payload) + ";\n")
    print(f"wrote {OUTDIR/'data.js'} ({(OUTDIR/'data.js').stat().st_size//1024} KB)")
    print(f"  P/L ${summary['pnl']:,.0f} | maxDD ${summary['max_dd']:,.0f} | taken {summary['n_taken']}/{summary['n_candidates']} "
          f"| locks {summary['n_locks']} | breaker-skipped {summary['n_skipped_breaker']} | events {len(events)}")


if __name__ == "__main__":
    main()
