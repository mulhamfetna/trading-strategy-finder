#!/usr/bin/env python3
"""FU-3 Phase 2 (#155) — cross-instrument power sizing. docs/FU3P2-PREREGISTRATION.md.

ES/RTY/YM × 6 frames, L1+vol-gate books at deployed best_* champion box params (STRICT
extraction), the FROZEN FU-3 ramp on each instrument's OWN committed power file, equal
exposure. Pooled day-bootstrap CI + 1,000 permutations + true-span era halves.

    WSH_DATA_BASE=... python3 optimize/fundamentals/fu3p2_cross_sizing.py
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
from optimize.fundamentals.champion_params import champion_stops   # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parents[0] / "results"
INSTS = ["ES", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
N_BOOT, N_PERM, SEED, WARMUP = 10000, 1000, 20260820, 20


def champion_box(inst: str, tf: str) -> dict:
    return json.load(open(RESULTS / f"best_champions_full_{inst}.json"))[tf]["box"]


def run_book(inst: str, tf: str) -> pd.DataFrame:
    df, df1, box, vf, n = data.load_inputs(tf, instrument=inst)
    p = champion_box(inst, tf)
    sl_soft, sl_hard, tp, flip = champion_stops(p, tf=f"{inst}_{tf}")
    gate = vf <= float(np.percentile(vf[:n], float(p["gate_pct"])))
    sig = signals_to_int(signals.decision_signals(df, box))
    F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                      df1["Date"].to_numpy(), df1["High"].to_numpy(float),
                      df1["Low"].to_numpy(float), df1["Close"].to_numpy(float),
                      sl_soft, sl_hard, tp, flip, m_open=df1["Open"].to_numpy(float))
    pv = instruments.point_value(inst)
    t = pd.DataFrame([{k: x[k] for k in ("entry_time", "exit_time", "pnl_points")}
                      for x in F])
    if not len(t):
        return t
    t["entry_time"] = pd.to_datetime(t.entry_time)
    t["exit_time"] = pd.to_datetime(t.exit_time)
    t["pnl_usd"] = t.pnl_points * pv
    return t


def day_multipliers(inst: str) -> pd.Series:
    d = pd.read_csv(HERE / f"fu9_event_state_{inst}.csv", parse_dates=["et"],
                    usecols=["et", "title", "pred_exp"]).dropna(subset=["pred_exp"])
    p = d.groupby(d.et.dt.normalize()).pred_exp.max().sort_index()
    v = p.to_numpy(float)
    m = np.ones(len(v))
    for i in range(len(v)):
        if i >= WARMUP:
            m[i] = 0.5 + float(np.mean(v[:i] <= v[i]))
    return pd.Series(m, index=p.index)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    print(f"[FU-3P2] pre-reg docs/FU3P2-PREREGISTRATION.md · frozen FU-3 ramp · "
          f"insts {INSTS} · N_PERM={N_PERM} N_BOOT={N_BOOT} SEED={SEED}", flush=True)
    rng = np.random.default_rng(SEED)
    mults = {i: day_multipliers(i) for i in INSTS}
    books = {}
    per = {}
    for inst in INSTS:
        per[inst] = {}
        for tf in TFS:
            t = run_book(inst, tf)
            if not len(t):
                per[inst][tf] = {"n": 0}
                continue
            md = t.entry_time.dt.normalize().map(mults[inst]).fillna(1.0).to_numpy(float)
            md = md * (len(md) / md.sum())
            t = t.assign(mult=md, diff=t.pnl_usd * (md - 1.0))
            books[(inst, tf)] = t
            per[inst][tf] = {"n": int(len(t)),
                             "ramped": int((t.entry_time.dt.normalize()
                                            .isin(mults[inst].index)).sum()),
                             "flat_net": round(float(t.pnl_usd.sum()), 2),
                             "delta_net": round(float(t["diff"].sum()), 2),
                             "span": [str(t.entry_time.min().date()),
                                      str(t.entry_time.max().date())]}
            r = per[inst][tf]
            print(f"[FU-3P2] {inst} {tf}: n={r['n']} ramped={r['ramped']} flat "
                  f"${r['flat_net']:,.0f} Δ {r['delta_net']:+,.0f} span {r['span']}",
                  flush=True)

    all_t = pd.concat([b.assign(inst=i, tf=tf) for (i, tf), b in books.items()],
                      ignore_index=True)
    all_t["day"] = all_t.exit_time.dt.normalize()
    daily = all_t.groupby("day")["diff"].sum().sort_index()
    tot = float(daily.sum())
    days = daily.to_numpy()
    boots = np.array([days[rng.integers(0, len(days), len(days))].sum()
                      for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))

    per_inst = {i: round(float(all_t[all_t.inst == i]["diff"].sum()), 2) for i in INSTS}

    perm_tots = []
    for s in range(N_PERM):
        r2 = np.random.default_rng(SEED + 1 + s)
        pm = {i: pd.Series(r2.permutation(mults[i].to_numpy()), index=mults[i].index)
              for i in INSTS}
        tsum = 0.0
        for (i, tf), b in books.items():
            md = b.entry_time.dt.normalize().map(pm[i]).fillna(1.0).to_numpy(float)
            md = md * (len(md) / md.sum())
            tsum += float((b.pnl_usd * (md - 1.0)).sum())
        perm_tots.append(tsum)
    perm_tots = np.array(perm_tots)
    pct = float(np.mean(perm_tots < tot) * 100)

    mid = daily.index[len(daily) // 2]
    eras = {"h1": round(float(daily[daily.index < mid].sum()), 2),
            "h2": round(float(daily[daily.index >= mid].sum()), 2),
            "split": str(pd.Timestamp(mid).date())}
    sd = float(daily.std(ddof=1))
    mde = float(1.645 * sd * np.sqrt(len(days)))
    pos_insts = sum(1 for v in per_inst.values() if v > 0)
    if tot > 0 and ci[0] > 0 and pct >= 95 and pos_insts >= 2:
        verdict = "CONFIRMED"
    elif ci[1] < 0:
        verdict = "REFUTED"
    else:
        verdict = "CLOSED-NULL"

    p1 = json.load(open(HERE / "fu3_result.json"))
    combined = round(tot + p1["pooled"]["delta_net"], 2)
    res = {"per_book": per, "per_instrument": per_inst,
           "pooled": {"delta_net": round(tot, 2), "boot90_ci": ci,
                      "perm_percentile": pct,
                      "perm_median": round(float(np.median(perm_tots)), 2),
                      "eras": eras, "n_active_days": int(len(days))},
           "power": {"sd_daily_diff": round(sd, 2), "mde_total": round(mde, 2)},
           "secondary_combined_p1_p2_delta": combined,
           "verdict": verdict}
    (Path(a.out) / "fu3p2_result.json").write_text(json.dumps(res, indent=2))
    daily.rename("diff").reset_index().to_csv(Path(a.out) / "fu3p2_daily_diff.csv",
                                              index=False)
    print(f"[FU-3P2] per-inst {per_inst} · POOLED Δ {tot:+,.0f} CI90 "
          f"[{ci[0]:,.0f},{ci[1]:,.0f}] perm-pct {pct:.1f} eras {eras} MDE {mde:,.0f} "
          f"· combined P1+P2 {combined:+,.0f} -> VERDICT {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
