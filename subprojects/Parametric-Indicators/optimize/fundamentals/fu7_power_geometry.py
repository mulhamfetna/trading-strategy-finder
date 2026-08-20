#!/usr/bin/env python3
"""FU-7 (#159) — power-scaled news-leg geometry. Implements docs/FU7-PREREGISTRATION.md.

Frozen arm (untouched constants) must reproduce the committed replay evidence to the cent;
scaled arm patches STOP_PCT/TP_PCT per event (r = pred_exp / causal within-series median,
clip [0.5,2]); falsifier = 20 within-series permutations of r. Pooled net-stressed delta,
event bootstrap, era halves on each leg's true span.

    WSH_16Y_ROOT=... python3 optimize/fundamentals/fu7_power_geometry.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PI_ROOT = HERE.parents[1]
REPO = PI_ROOT.parents[1]
for p_ in (str(PI_ROOT), str(HERE), str(REPO)):
    sys.path.insert(0, p_)

import src.deploy.release_executor as rex                          # noqa: E402
from src.deploy.release_executor import (COST_PER_LEG, PV, Leg,    # noqa: E402
                                         load_1s_windows, run_bracket, LEAD_S, EXIT_S)

LEGS = {"NQ": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
        "RTY": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
        "ES": ["Inflation Rate MoM"], "YM": ["Inflation Rate MoM"]}
CLIP_LO, CLIP_HI = 0.5, 2.0
N_PERM, N_BOOT, SEED = 20, 10000, 20260820
BARS_1S = "/home/dev/Mulham/data_2010_1s/{i}_Continuous_Data/{i}_1s.csv"


def leg_events(inst: str) -> pd.DataFrame:
    """Events + committed pred_exp from the frozen FU-9 dataset; r = within-series scaler."""
    d = pd.read_csv(HERE / f"fu9_event_state_{inst}.csv", parse_dates=["et"],
                    usecols=["et", "title", "pred_exp"])
    d = d[d.title.isin(LEGS[inst])].sort_values("et").reset_index(drop=True)
    r = np.ones(len(d))
    for _t, g in d.groupby("title"):
        v = g.pred_exp.to_numpy(float)
        for k, i in enumerate(g.index):
            prior = v[:k][np.isfinite(v[:k])]
            if np.isfinite(v[k]) and len(prior) >= 8:
                med = float(np.median(prior))
                if med > 0:
                    r[i] = float(np.clip(v[k] / med, CLIP_LO, CLIP_HI))
    d["r"] = r
    return d


def run_arm(bars, ev: pd.DataFrame, inst: str, r: np.ndarray) -> np.ndarray:
    """Net-stressed P&L per event for bracket scale r (1.0 = frozen). NaN where no fill."""
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    base_s, base_t = rex.STOP_PCT, rex.TP_PCT
    out = np.full(len(ev), np.nan)
    try:
        for i, row in ev.iterrows():
            rex.STOP_PCT = base_s * float(r[i])
            rex.TP_PCT = base_t * float(r[i])
            f = run_bracket(idx, op, hi, lo, cl, pd.Timestamp(row.et), Leg("long", 1),
                            PV[inst], row.title)
            if f is not None:
                out[i] = f.pnl_usd - COST_PER_LEG[inst]["stressed"]
    finally:
        rex.STOP_PCT, rex.TP_PCT = base_s, base_t
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    print(f"[FU-7] pre-reg docs/FU7-PREREGISTRATION.md · clip [{CLIP_LO},{CLIP_HI}] · "
          f"N_PERM={N_PERM} N_BOOT={N_BOOT} SEED={SEED}", flush=True)
    rng = np.random.default_rng(SEED)
    per_leg = {}
    pooled_diff = []          # per-event scaled − frozen (net; costs cancel)
    pooled_perm = [[] for _ in range(N_PERM)]
    for inst in LEGS:
        ev = leg_events(inst)
        windows = [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
                   for t in ev.et]
        bars = load_1s_windows(Path(BARS_1S.format(i=inst)), windows)
        frozen = run_arm(bars, ev, inst, np.ones(len(ev)))

        # parity gate: frozen arm vs the committed replay evidence, to the cent
        ref = pd.read_csv(HERE / f"wsescpi_replay_{inst}.csv", parse_dates=["et"])
        j = ref.merge(ev.assign(frozen=frozen + COST_PER_LEG[inst]["stressed"]),
                      on=["et", "title"], how="inner").dropna(subset=["frozen"])
        mx = (j.pnl_usd - j.frozen).abs().max() if len(j) else np.inf
        if not (len(j) and mx < 0.01):
            print(f"[FU-7] ABORT {inst}: frozen-arm parity broken (n={len(j)}, "
                  f"max|Δ| {mx})", flush=True)
            return 1

        scaled = run_arm(bars, ev, inst, ev.r.to_numpy())
        ok = np.isfinite(frozen) & np.isfinite(scaled)
        diff = scaled[ok] - frozen[ok]
        ets = ev.et.to_numpy()[ok]
        pooled_diff.append(pd.DataFrame({"et": ets, "diff": diff, "inst": inst}))

        for s in range(N_PERM):
            r2 = np.random.default_rng(SEED + 1 + s)
            rp = ev.r.to_numpy().copy()
            for _t, g in ev.groupby("title"):
                ii = g.index.to_numpy()
                rp[ii] = r2.permutation(rp[ii])
            sp = run_arm(bars, ev, inst, rp)
            okp = np.isfinite(frozen) & np.isfinite(sp)
            pooled_perm[s].append(float(np.nansum(sp[okp] - frozen[okp])))

        n_scaled = int((ev.r != 1.0).sum())
        per_leg[inst] = {
            "events": int(ok.sum()), "scaled_events": n_scaled,
            "parity_overlap": int(len(j)),
            "frozen_net": round(float(np.nansum(frozen)), 2),
            "scaled_net": round(float(np.nansum(scaled)), 2),
            "delta_net": round(float(diff.sum()), 2),
            "r_range": [round(float(ev.r.min()), 3), round(float(ev.r.max()), 3)],
        }
        L = per_leg[inst]
        print(f"[FU-7] {inst}: parity PASS ({L['parity_overlap']}ev to the cent) · "
              f"{L['events']}ev ({L['scaled_events']} scaled, r {L['r_range']}) · frozen "
              f"${L['frozen_net']:,.0f} → scaled ${L['scaled_net']:,.0f} "
              f"Δ {L['delta_net']:+,.0f}", flush=True)

    d = pd.concat(pooled_diff, ignore_index=True).sort_values("et").reset_index(drop=True)
    tot = float(d["diff"].sum())
    n = len(d)
    boots = np.array([d["diff"].to_numpy()[rng.integers(0, n, n)].sum()
                      for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))
    perm_tot = np.array([sum(x) for x in pooled_perm])
    mid = d.et.iloc[n // 2]
    eras = {"h1": round(float(d[d.et < mid]["diff"].sum()), 2),
            "h2": round(float(d[d.et >= mid]["diff"].sum()), 2),
            "split": str(pd.Timestamp(mid).date())}
    sd = float(d["diff"].std(ddof=1))
    mde = float(1.645 * sd * np.sqrt(n))
    placebo_med = float(np.median(perm_tot))
    if tot > 0 and ci[0] > 0 and placebo_med <= 0.5 * tot \
            and eras["h1"] >= 0 and eras["h2"] >= 0:
        verdict = "ADOPT-CANDIDATE"          # arms the full spec-change gate only
    elif ci[1] < 0:
        verdict = "CLOSED-NEGATIVE"
    else:
        verdict = "CLOSED-NULL"
    res = {"per_leg": per_leg,
           "pooled": {"delta_net": round(tot, 2), "n_events": n, "boot90_ci": ci,
                      "placebo_median": round(placebo_med, 2),
                      "placebo_p95": round(float(np.percentile(perm_tot, 95)), 2),
                      "eras": eras},
           "power": {"sd_event_diff": round(sd, 2), "mde_total": round(mde, 2)},
           "config": {"clip": [CLIP_LO, CLIP_HI], "scaler": "pred_exp / causal "
                      "within-series median (>=8 priors), else r=1"},
           "verdict": verdict}
    out = Path(a.out)
    (out / "fu7_result.json").write_text(json.dumps(res, indent=2))
    d.to_csv(out / "fu7_event_diff.csv", index=False)
    print(f"[FU-7] POOLED Δ {tot:+,.0f} over {n}ev CI90 [{ci[0]:,.0f},{ci[1]:,.0f}] "
          f"placebo median {placebo_med:+,.0f} eras {eras} MDE {mde:,.0f} "
          f"-> VERDICT {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
