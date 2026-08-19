#!/usr/bin/env python3
"""FU-1 (#153) — the event-window interaction audit.

Implements `docs/FU1-PREREGISTRATION.md` (frozen definitions, filed before this ran).
What does the NQ champion book actually DO inside [release−5m, release+15m] windows of every
Tier-1 calendar minute? Five metrics per TF: time share, entry density, entry quality,
stop-out density, spanning give-up (era-0's B1, generalized).

    WSH_DATA_BASE=... python3 optimize/fundamentals/fu1_event_window_audit.py \
        [--tfs 4h,2h,1h,15m,5m,2m] [--n-boot 10000]

Outputs: fu1_audit_{tf}.csv · fu1_result.json (committed evidence).
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
import tv_calendar                                                 # noqa: E402

HERE = Path(__file__).resolve().parent
PRE_MIN, POST_MIN = 5, 15
FLOOR = np.datetime64("2016-01-01")
STOP_REASONS = {"STOP_LOSS_HARD", "STOP_LOSS_SOFT"}   # fast_engine.REASON_NAME


def tier1_minutes() -> np.ndarray:
    cal = tv_calendar.load()
    c = cal[(cal.importance == 1) & (cal.event_et >= "2016-01-01")]
    return np.sort(c.event_et.dt.floor("min").unique())


def in_window(ts: np.ndarray, rel: np.ndarray) -> np.ndarray:
    """bool per ts: falls inside [rel-PRE, rel+POST] of ANY release minute."""
    lo = rel - np.timedelta64(PRE_MIN, "m")
    i = np.searchsorted(lo, ts, side="right") - 1
    i = np.clip(i, 0, len(rel) - 1)
    out = np.zeros(len(ts), dtype=bool)
    for k in (0, 1):                       # the found interval and the one before (overlaps)
        j = np.clip(i - k, 0, len(rel) - 1)
        out |= (ts >= rel[j] - np.timedelta64(PRE_MIN, "m")) & \
               (ts <= rel[j] + np.timedelta64(POST_MIN, "m"))
    return out


def audit_tf(tf: str, rel: np.ndarray, n_boot: int, rng) -> tuple[dict, pd.DataFrame]:
    df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
    p = champion_preset(tf)
    sl_soft, sl_hard, tp, flip = champion_stops(p)
    gate = vf <= float(np.percentile(vf[:n], float(p["gate_pct"])))
    sig = signals_to_int(signals.decision_signals(df, box))
    MD = df1["Date"].to_numpy()
    MC = df1["Close"].to_numpy(float)
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      MD, df1["High"].to_numpy(float), df1["Low"].to_numpy(float), MC,
                      sl_soft, sl_hard, tp, flip, m_open=df1["Open"].to_numpy(float))
    pv = instruments.point_value("NQ")
    t = pd.DataFrame([{k: x[k] for k in
                       ("entry_time", "exit_time", "entry_price", "direction",
                        "exit_reason", "pnl_points")} for x in F])
    t["entry_time"] = pd.to_datetime(t.entry_time)
    t["exit_time"] = pd.to_datetime(t.exit_time)
    t = t[t.entry_time >= pd.Timestamp("2016-01-01")].reset_index(drop=True)
    t["pnl_usd"] = t.pnl_points * pv
    t["entry_in_win"] = in_window(t.entry_time.to_numpy(), rel)
    t["exit_in_win"] = in_window(t.exit_time.to_numpy(), rel)
    t["is_stop"] = t.exit_reason.isin(STOP_REASONS)

    # 1) time share from the 1-minute execution stream (>=2016)
    m16 = MD[MD >= FLOOR]
    time_share = float(in_window(m16, rel).mean())

    # 2/3) entry density + quality
    e_in = t[t.entry_in_win]
    e_out = t[~t.entry_in_win]
    diff = e_in.pnl_usd.mean() - e_out.pnl_usd.mean() if len(e_in) else np.nan
    ci = (np.nan, np.nan)
    if len(e_in) >= 5:
        sims = [rng.choice(e_in.pnl_usd, len(e_in)).mean()
                - rng.choice(e_out.pnl_usd, len(e_out)).mean() for _ in range(n_boot)]
        ci = (float(np.percentile(sims, 2.5)), float(np.percentile(sims, 97.5)))

    # 4) stop-out density
    stops = t[t.is_stop]
    stop_in_share = float(stops.exit_in_win.mean()) if len(stops) else np.nan

    # 5) spanning give-up (B1 generalized): first release strictly inside (entry, exit)
    give = []
    for _, r in t.iterrows():
        span = rel[(rel > np.datetime64(r.entry_time)) & (rel < np.datetime64(r.exit_time))]
        if not len(span):
            continue
        ri = int(np.searchsorted(MD, span[0], side="left"))
        if ri < 1 or ri >= len(MC):
            continue
        cb = float(MC[ri - 1])
        closed = (cb - r.entry_price) if r.direction == "long" else (r.entry_price - cb)
        give.append(float(r.pnl_points) - closed)
    give = np.array(give) * pv
    gu_p = np.nan
    if len(give) >= 5:
        sims = np.array([rng.choice(give, len(give)).mean() for _ in range(n_boot)])
        gu_p = float(min((sims <= 0).mean(), (sims >= 0).mean()) * 2)

    res = {"tf": tf, "n_trades": int(len(t)), "pv": pv,
           "time_share_pct": round(100 * time_share, 3),
           "entry_in_win": int(len(e_in)),
           "entry_in_win_pct": round(100 * len(e_in) / max(len(t), 1), 3),
           "entry_density_ratio": round(len(e_in) / max(len(t), 1) / max(time_share, 1e-9), 2),
           "pnl_in_mean": round(float(e_in.pnl_usd.mean()), 2) if len(e_in) else None,
           "pnl_out_mean": round(float(e_out.pnl_usd.mean()), 2),
           "pnl_diff": round(float(diff), 2) if np.isfinite(diff) else None,
           "pnl_diff_ci": [round(c, 2) if np.isfinite(c) else None for c in ci],
           "stop_exits": int(len(stops)),
           "stop_in_win_pct": round(100 * stop_in_share, 3) if np.isfinite(stop_in_share) else None,
           "stop_density_ratio": round(stop_in_share / max(time_share, 1e-9), 2)
           if np.isfinite(stop_in_share) else None,
           "spanning_trades": int(len(give)),
           "giveup_mean": round(float(give.mean()), 2) if len(give) else None,
           "giveup_sd": round(float(give.std(ddof=1)), 2) if len(give) > 1 else None,
           "giveup_p": round(gu_p, 4) if np.isfinite(gu_p) else None}
    return res, t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tfs", default="4h,2h,1h,15m,5m,2m")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    rel = tier1_minutes()
    print(f"FU-1 audit · Tier-1 minutes >=2016: {len(rel):,} · window [-{PRE_MIN}m, +{POST_MIN}m] "
          f"· pre-reg docs/FU1-PREREGISTRATION.md")
    results = []
    for tf in a.tfs.split(","):
        res, t = audit_tf(tf.strip(), rel, a.n_boot, rng)
        results.append(res)
        t.to_csv(Path(a.out_dir) / f"fu1_audit_{tf.strip()}.csv", index=False)
        print(f"  [{tf}] n={res['n_trades']} · time-share {res['time_share_pct']}% · "
              f"entries in-win {res['entry_in_win']} ({res['entry_in_win_pct']}%, "
              f"ratio {res['entry_density_ratio']}x) · pnl in/out "
              f"{res['pnl_in_mean']}/{res['pnl_out_mean']} · stops in-win "
              f"{res['stop_in_win_pct']}% (ratio {res['stop_density_ratio']}x) · "
              f"spanning {res['spanning_trades']} giveup {res['giveup_mean']} "
              f"(p={res['giveup_p']})")
    (Path(a.out_dir) / "fu1_result.json").write_text(json.dumps(
        {"prereg": "docs/FU1-PREREGISTRATION.md", "n_tier1_minutes": int(len(rel)),
         "window": [PRE_MIN, POST_MIN], "floor": "2016-01-01", "per_tf": results}, indent=2))
    print("wrote fu1_result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
