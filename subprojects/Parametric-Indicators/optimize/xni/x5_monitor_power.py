#!/usr/bin/env python3
"""X-5 — monitor × compound power. Implements docs/X5-PREREGISTRATION.md (frozen).
Protective analysis on frozen data; no trigger changes regardless of verdict.

    python3 optimize/xni/x5_monitor_power.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FUND = HERE.parents[0] / "fundamentals"
EARN = HERE.parents[0] / "earnings" / "data"
N_BOOT, N_SHUF, SEED, WINDOW = 10000, 200, 20260820, 24
CPI = "Inflation Rate MoM"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()
    from scipy import stats
    rng = np.random.default_rng(SEED)
    print(f"[X-5] pre-reg docs/X5-PREREGISTRATION.md · window={WINDOW} N_SHUF={N_SHUF} "
          f"SEED={SEED}", flush=True)

    d = pd.read_csv(FUND / "fu9_event_state_NQ.csv", parse_dates=["et"],
                    usecols=["et", "title", "pred_exp", "ride_net_stressed_usd"])
    cpi = d[(d.title == CPI)].dropna(subset=["ride_net_stressed_usd"])
    cpi = cpi.sort_values("et").reset_index(drop=True)
    health = cpi.ride_net_stressed_usd.rolling(WINDOW).mean()
    earn = pd.read_csv(EARN / "ep1_events_NQ.csv", parse_dates=["event_et"])
    e_et = earn.event_et.to_numpy()
    e_pred = earn.pred.to_numpy(float)
    comp = np.full(len(cpi), np.nan)
    for i, r in cpi.iterrows():
        base = r.pred_exp if np.isfinite(r.pred_exp) else np.nan
        dh = np.abs((r.et.to_datetime64() - e_et) / np.timedelta64(1, "h"))
        near = e_pred[(dh <= 24.0) & np.isfinite(e_pred)]
        add = float(near.max()) if len(near) else 0.0
        comp[i] = (base + add) if np.isfinite(base) else np.nan
    ok = health.notna().to_numpy() & np.isfinite(comp)
    h = health.to_numpy()[ok]
    c = comp[ok]
    ets = cpi.et.to_numpy()[ok]
    n = int(ok.sum())
    rho, _ = stats.spearmanr(h, c)
    boots = []
    for _ in range(N_BOOT):
        ii = rng.integers(0, n, n)
        boots.append(stats.spearmanr(h[ii], c[ii])[0])
    ci = [round(float(np.percentile(boots, 5)), 4),
          round(float(np.percentile(boots, 95)), 4)]
    years = pd.DatetimeIndex(ets).year
    shufs = []
    for s in range(N_SHUF):
        r2 = np.random.default_rng(SEED + 1 + s)
        c2 = c.copy()
        for y in np.unique(years):
            m = years == y
            c2[m] = r2.permutation(c2[m])
        shufs.append(abs(float(stats.spearmanr(h, c2)[0])))
    p95 = float(np.percentile(shufs, 95))
    mid = ets[n // 2]
    r1, _ = stats.spearmanr(h[ets < mid], c[ets < mid])
    r2_, _ = stats.spearmanr(h[ets >= mid], c[ets >= mid])
    informative = ((ci[0] > 0 or ci[1] < 0) and abs(rho) > p95
                   and np.sign(r1) == np.sign(r2_) == np.sign(rho))
    verdict = "INFORMATIVE" if informative else "CLOSED-ORTHOGONAL"
    sd = float(np.std(boots, ddof=1))
    res = {"n": n, "spearman": round(float(rho), 4), "boot90_ci": ci,
           "shuffle_p95_abs": round(p95, 4),
           "eras": {"h1": round(float(r1), 4), "h2": round(float(r2_), 4),
                    "split": str(pd.Timestamp(mid).date())},
           "mde_rho": round(1.645 * sd, 4), "verdict": verdict}
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "x5_result.json").write_text(json.dumps(res, indent=2))
    print(f"[X-5] n={n} rho {rho:+.4f} CI {ci} shuf95 {p95:.4f} eras "
          f"{res['eras']} -> {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
