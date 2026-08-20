#!/usr/bin/env python3
"""FU-2 (#154) — the news-veto replay. Implements docs/FU2-PREREGISTRATION.md (frozen).

Per TF (NQ, 6 frames): ① baseline (must reproduce the committed FU-1 book — parity gate),
② the veto replay (entries blocked when the decision bar falls in [rel−5m, rel+15m] of any
Tier-1 minute — the engine's own gate, full path dependence), ③ the +3-day shifted-calendar
control (the seasonality-only veto). Decision statistic: pooled daily P&L diff (veto−base),
day bootstrap, 90% CI. Nothing in the engine changes; golden untouched.

    WSH_DATA_BASE=... python3 optimize/fundamentals/fu2_veto_replay.py [--tfs 4h,...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments, signals                    # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int     # noqa: E402
from perf._common import champion_preset                           # noqa: E402
from optimize.fundamentals.champion_params import champion_stops   # noqa: E402
from optimize.fundamentals.fu1_event_window_audit import (         # noqa: E402
    tier1_minutes, in_window, PRE_MIN, POST_MIN)

HERE = Path(__file__).resolve().parent
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
N_BOOT, SEED = 10000, 20260820
FLOOR = pd.Timestamp("2016-01-01")


def run_book(tf: str, rel_veto: np.ndarray | None) -> pd.DataFrame:
    """One engine replay; rel_veto=None -> baseline, else entries blocked in its windows."""
    df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
    p = champion_preset(tf)
    sl_soft, sl_hard, tp, flip = champion_stops(p)
    gate = vf <= float(np.percentile(vf[:n], float(p["gate_pct"])))
    if rel_veto is not None:
        gate = gate & ~in_window(df["Date"].to_numpy(), rel_veto)
    sig = signals_to_int(signals.decision_signals(df, box))
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float),
                      df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
                      sl_soft, sl_hard, tp, flip, m_open=df1["Open"].to_numpy(float))
    pv = instruments.point_value("NQ")
    t = pd.DataFrame([{k: x[k] for k in ("entry_time", "exit_time", "pnl_points")}
                      for x in F])
    t["entry_time"] = pd.to_datetime(t.entry_time)
    t["exit_time"] = pd.to_datetime(t.exit_time)
    t = t[t.entry_time >= FLOOR].reset_index(drop=True)
    t["pnl_usd"] = t.pnl_points * pv
    return t


def daily(t: pd.DataFrame, days: pd.DatetimeIndex) -> np.ndarray:
    s = t.groupby(t.exit_time.dt.normalize()).pnl_usd.sum()
    return s.reindex(days, fill_value=0.0).to_numpy()


def maxdd(daily_pnl: np.ndarray) -> float:
    c = np.cumsum(daily_pnl)
    return float(np.max(np.maximum.accumulate(c) - c))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tfs", default=",".join(TFS))
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    tfs = a.tfs.split(",")
    print(f"[FU-2] pre-reg docs/FU2-PREREGISTRATION.md · window [-{PRE_MIN}m,+{POST_MIN}m] "
          f"Tier-1 · N_BOOT={N_BOOT} SEED={SEED} · tfs={tfs}", flush=True)

    rel = tier1_minutes()
    rel_shift = rel + np.timedelta64(3, "D")
    days = pd.date_range(FLOOR, pd.Timestamp.now().normalize(), freq="D")

    per_tf = {}
    diff_real = np.zeros(len(days))
    diff_shift = np.zeros(len(days))
    for tf in tfs:
        base = run_book(tf, None)
        veto = run_book(tf, rel)
        shift = run_book(tf, rel_shift)

        # parity gate vs the committed FU-1 audit book
        ref = pd.read_csv(HERE / f"fu1_audit_{tf}.csv")
        par_ok = (len(base) == len(ref)
                  and abs(base.pnl_usd.sum() - ref.pnl_usd.sum()) < 0.01)
        db, dv, ds = daily(base, days), daily(veto, days), daily(shift, days)
        diff_real += dv - db
        diff_shift += ds - db
        per_tf[tf] = {
            "parity_vs_fu1": {"pass": bool(par_ok), "n": [int(len(base)), int(len(ref))],
                              "total": [round(float(base.pnl_usd.sum()), 2),
                                        round(float(ref.pnl_usd.sum()), 2)]},
            "base": {"n": int(len(base)), "net": round(float(base.pnl_usd.sum()), 2),
                     "maxdd": round(maxdd(db), 2)},
            "veto": {"n": int(len(veto)), "net": round(float(veto.pnl_usd.sum()), 2),
                     "maxdd": round(maxdd(dv), 2)},
            "shifted": {"n": int(len(shift)), "net": round(float(shift.pnl_usd.sum()), 2)},
            "delta_net": round(float(veto.pnl_usd.sum() - base.pnl_usd.sum()), 2),
            "delta_maxdd": round(maxdd(dv) - maxdd(db), 2),
            "delta_net_shifted": round(float(shift.pnl_usd.sum() - base.pnl_usd.sum()), 2),
        }
        r = per_tf[tf]
        print(f"[FU-2] {tf}: parity={'PASS' if par_ok else 'FAIL'} "
              f"base {r['base']['n']}tr ${r['base']['net']:,.0f} DD ${r['base']['maxdd']:,.0f} "
              f"| veto {r['veto']['n']}tr Δnet {r['delta_net']:+,.0f} ΔDD "
              f"{r['delta_maxdd']:+,.0f} | shifted Δnet {r['delta_net_shifted']:+,.0f}",
              flush=True)
        if not par_ok:
            print(f"[FU-2] ABORT: {tf} baseline does not reproduce the committed FU-1 book",
                  flush=True)
            return 1

    rng = np.random.default_rng(SEED)
    nd = len(days)
    boots = np.array([diff_real[rng.integers(0, nd, nd)].sum() for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))
    tot_real = float(diff_real.sum())
    tot_shift = float(diff_shift.sum())
    sd_daily = float(np.std(diff_real, ddof=1))
    mde = float(1.645 * sd_daily * np.sqrt(nd))     # detectable total at ~90% one-sided

    pooled_dd_delta = float(sum(v["delta_maxdd"] for v in per_tf.values()))
    if tot_real > 0 and ci[0] > 0 and pooled_dd_delta <= 0 and tot_real > tot_shift:
        verdict = "ADOPT-CANDIDATE"
    elif tot_real < 0 and ci[1] < 0:
        verdict = "CLOSED-NEGATIVE"
    else:
        verdict = "CLOSED-NULL"

    res = {"window_min": [PRE_MIN, POST_MIN], "tfs": tfs, "n_days": nd,
           "per_tf": per_tf,
           "pooled": {"delta_net": round(tot_real, 2), "boot90_ci": ci,
                      "delta_net_shifted": round(tot_shift, 2),
                      "sum_delta_maxdd": round(pooled_dd_delta, 2)},
           "power": {"sd_daily_diff": round(sd_daily, 2), "mde_total": round(mde, 2)},
           "verdict": verdict}
    out = Path(a.out)
    (out / "fu2_result.json").write_text(json.dumps(res, indent=2))
    pd.DataFrame({"day": days, "diff_real": diff_real, "diff_shifted": diff_shift}
                 ).to_csv(out / "fu2_daily_diff.csv", index=False)
    print(f"[FU-2] POOLED Δnet {tot_real:+,.0f} CI90 [{ci[0]:,.0f},{ci[1]:,.0f}] "
          f"shifted {tot_shift:+,.0f} ΣΔmaxDD {pooled_dd_delta:+,.0f} "
          f"MDE {mde:,.0f} -> VERDICT {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
