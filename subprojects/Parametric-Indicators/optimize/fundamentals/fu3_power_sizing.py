#!/usr/bin/env python3
"""FU-3 (#155) — power-aware box sizing. Implements docs/FU3-PREREGISTRATION.md (frozen).

Ramp trades entered on modeled-event days by the night-before predicted power (FU-9's
committed pred_exp; causal expanding percentile among prior event days; Exp2 shape
0.5+pct; non-event days 1.0), equal-exposure normalized (sum of multipliers = n trades).
Baselines re-use FU-2's engine replay and must reproduce the committed FU-1 books.

    WSH_DATA_BASE=... python3 optimize/fundamentals/fu3_power_sizing.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize.fundamentals.fu2_veto_replay import run_book, daily, maxdd, TFS  # noqa: E402

HERE = Path(__file__).resolve().parent
N_BOOT, N_PERM, SEED = 10000, 1000, 20260820
WARMUP_EVENT_DAYS = 20
ERA_SPLIT = pd.Timestamp("2021-01-01")
FLOOR = pd.Timestamp("2016-01-01")


def day_power() -> pd.Series:
    """P(d) = max committed night-before pred_exp over day d's scored events (FU-9 v1, NQ)."""
    d = pd.read_csv(HERE / "fu9_event_state_NQ.csv", parse_dates=["et"],
                    usecols=["et", "title", "pred_exp"])
    d = d.dropna(subset=["pred_exp"])
    return d.groupby(d.et.dt.normalize()).pred_exp.max().sort_index()


def day_multipliers(p: pd.Series) -> pd.Series:
    """Causal expanding percentile among PRIOR event days -> 0.5+pct; warmup 1.0."""
    vals = p.to_numpy(float)
    m = np.ones(len(vals))
    for i in range(len(vals)):
        if i >= WARMUP_EVENT_DAYS:
            m[i] = 0.5 + float(np.mean(vals[:i] <= vals[i]))
    return pd.Series(m, index=p.index)


def apply_ramp(t: pd.DataFrame, mult: pd.Series) -> tuple[np.ndarray, dict]:
    """Per-trade multipliers (entry day), equal-exposure normalized (sum m = n)."""
    md = t.entry_time.dt.normalize().map(mult).fillna(1.0).to_numpy(float)
    md = md * (len(md) / md.sum())
    return md, {"n_ramped": int((t.entry_time.dt.normalize().isin(mult.index)).sum()),
                "n": int(len(md))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tfs", default=",".join(TFS))
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    tfs = a.tfs.split(",")
    print(f"[FU-3] pre-reg docs/FU3-PREREGISTRATION.md · Exp2 shape 0.5+pct · warmup "
          f"{WARMUP_EVENT_DAYS} event days · N_PERM={N_PERM} N_BOOT={N_BOOT} SEED={SEED}",
          flush=True)

    p = day_power()
    mult = day_multipliers(p)
    print(f"[FU-3] event days with power: {len(p)} ({p.index.min().date()} .. "
          f"{p.index.max().date()}); multiplier range "
          f"[{mult.min():.2f}, {mult.max():.2f}]", flush=True)

    days = pd.date_range(FLOOR, pd.Timestamp.now().normalize(), freq="D")
    rng = np.random.default_rng(SEED)
    per_tf = {}
    diff_daily = np.zeros(len(days))
    books = {}
    for tf in tfs:
        t = run_book(tf, None)                     # baseline; FU-2 proved FU-1 parity
        ref = pd.read_csv(HERE / f"fu1_audit_{tf}.csv")
        par_ok = len(t) == len(ref) and abs(t.pnl_usd.sum() - ref.pnl_usd.sum()) < 0.01
        if not par_ok:
            print(f"[FU-3] ABORT: {tf} baseline != committed FU-1 book", flush=True)
            return 1
        m, meta = apply_ramp(t, mult)
        t = t.assign(pnl_ramp=t.pnl_usd * m)
        books[tf] = t
        d_flat = daily(t, days)
        d_ramp = daily(t.assign(pnl_usd=t.pnl_ramp), days)
        diff_daily += d_ramp - d_flat
        per_tf[tf] = {"parity_vs_fu1": bool(par_ok), **meta,
                      "flat_net": round(float(t.pnl_usd.sum()), 2),
                      "ramp_net": round(float(t.pnl_ramp.sum()), 2),
                      "delta_net": round(float(t.pnl_ramp.sum() - t.pnl_usd.sum()), 2),
                      "flat_maxdd": round(maxdd(d_flat), 2),
                      "ramp_maxdd": round(maxdd(d_ramp), 2)}
        r = per_tf[tf]
        print(f"[FU-3] {tf}: parity=PASS n={r['n']} ramped={r['n_ramped']} "
              f"flat ${r['flat_net']:,.0f} ramp ${r['ramp_net']:,.0f} "
              f"Δ {r['delta_net']:+,.0f} · DD {r['flat_maxdd']:,.0f}→{r['ramp_maxdd']:,.0f}",
              flush=True)

    tot = float(diff_daily.sum())

    # dumb control: permute event-day multipliers among event days, re-apply everywhere
    perm_tots = []
    ev_vals = mult.to_numpy().copy()
    for _ in range(N_PERM):
        pm = pd.Series(rng.permutation(ev_vals), index=mult.index)
        s = 0.0
        for tf in tfs:
            t = books[tf]
            md = t.entry_time.dt.normalize().map(pm).fillna(1.0).to_numpy(float)
            md = md * (len(md) / md.sum())
            s += float((t.pnl_usd * (md - 1.0)).sum())
        perm_tots.append(s)
    perm_tots = np.array(perm_tots)
    pct = float(np.mean(perm_tots < tot) * 100)

    boots = np.array([diff_daily[rng.integers(0, len(days), len(days))].sum()
                      for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))

    eras = {}
    for name, msk in (("2016_2020", days < ERA_SPLIT), ("2021_plus", days >= ERA_SPLIT)):
        eras[name] = round(float(diff_daily[msk].sum()), 2)

    sd = float(np.std(diff_daily, ddof=1))
    mde = float(1.645 * sd * np.sqrt(len(days)))

    if tot > 0 and ci[0] > 0 and pct >= 95 and all(v > 0 for v in eras.values()):
        verdict = "ADOPT-CANDIDATE"      # arms Phase-2 cross-instrument battery ONLY
    elif ci[1] < 0:
        verdict = "CLOSED-NEGATIVE"
    else:
        verdict = "CLOSED-NULL"

    res = {"per_tf": per_tf,
           "pooled": {"delta_net": round(tot, 2), "boot90_ci": ci,
                      "perm_percentile": pct,
                      "perm_median": round(float(np.median(perm_tots)), 2),
                      "eras": eras},
           "power": {"sd_daily_diff": round(sd, 2), "mde_total": round(mde, 2)},
           "config": {"warmup_event_days": WARMUP_EVENT_DAYS, "shape": "0.5+pct",
                      "n_event_days": int(len(p))},
           "verdict": verdict}
    out = Path(a.out)
    (out / "fu3_result.json").write_text(json.dumps(res, indent=2))
    pd.DataFrame({"day": days, "diff_ramp": diff_daily}).to_csv(
        out / "fu3_daily_diff.csv", index=False)
    print(f"[FU-3] POOLED Δ {tot:+,.0f} CI90 [{ci[0]:,.0f},{ci[1]:,.0f}] "
          f"perm-pct {pct:.1f} (median {np.median(perm_tots):+,.0f}) eras {eras} "
          f"MDE {mde:,.0f} -> VERDICT {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
