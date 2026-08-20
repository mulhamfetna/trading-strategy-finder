#!/usr/bin/env python3
"""FU-5 (#157) — the state-gated ride. Implements docs/FU5-PREREGISTRATION.md (frozen).

Two pre-registered conditions (A overnight-trend agreement, B pre-release tape vol above
causal median) against the FROZEN FU-9 ride outcomes on the deployed legs. Primary = NQ
mean per-event net difference, event bootstrap; confirmations = 3 other legs' sign + era
halves; shuffle control. Reads exactly the two engineered features — no stance columns.

    WSH_16Y_ROOT=... python3 optimize/fundamentals/fu5_state_gate.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from extended_data import load_1m_extended     # noqa: E402

LEGS = {"NQ": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
        "RTY": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
        "ES": ["Inflation Rate MoM"], "YM": ["Inflation Rate MoM"]}
STANCE_LAG_S, TREND_H, VOL_MIN, VOL_PRIORS = 360, 12, 60, 20
N_BOOT, N_SHUF, SEED = 10000, 20, 20260820


def leg_frame(inst: str) -> pd.DataFrame:
    d = pd.read_csv(HERE / f"fu9_event_state_{inst}.csv", parse_dates=["et"],
                    usecols=["et", "title", "ride_net_stressed_usd"])
    d = d[d.title.isin(LEGS[inst])].dropna(subset=["ride_net_stressed_usd"])
    d = d.sort_values("et").reset_index(drop=True)
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    dts = df1["Date"].to_numpy()
    cl = df1["Close"].to_numpy(float)
    lr = np.diff(np.log(cl), prepend=np.nan)
    trend = np.full(len(d), np.nan)
    vol = np.full(len(d), np.nan)
    for i, et in enumerate(d.et):
        j = np.searchsorted(dts, np.datetime64(et - pd.Timedelta(seconds=STANCE_LAG_S)),
                            side="right")
        if j < VOL_MIN + 2:
            continue
        k = np.searchsorted(dts, np.datetime64(et - pd.Timedelta(hours=TREND_H)),
                            side="right")
        if 0 < k < j:
            trend[i] = np.sign(cl[j - 1] - cl[k - 1])
        w = lr[j - VOL_MIN:j]
        w = w[np.isfinite(w)]
        if len(w) >= VOL_MIN // 2:
            vol[i] = float(np.std(w, ddof=1))
    d["trend_pos"] = trend > 0
    d["trend_ok"] = np.isfinite(trend)
    # causal vol percentile among PRIOR events (>=VOL_PRIORS priors)
    hi = np.zeros(len(d), dtype=bool)
    ok = np.zeros(len(d), dtype=bool)
    for i in range(len(d)):
        prior = vol[:i][np.isfinite(vol[:i])]
        if np.isfinite(vol[i]) and len(prior) >= VOL_PRIORS:
            ok[i] = True
            hi[i] = vol[i] > float(np.median(prior))
    d["vol_hi"], d["vol_ok"] = hi, ok
    return d


def cond_stats(d: pd.DataFrame, flag: str, okcol: str, rng) -> dict:
    x = d[d[okcol]]
    a = x[x[flag]].ride_net_stressed_usd.to_numpy()
    b = x[~x[flag]].ride_net_stressed_usd.to_numpy()
    if len(a) < 10 or len(b) < 10:
        return {"n_true": int(len(a)), "n_false": int(len(b)), "insufficient": True}
    diff = float(a.mean() - b.mean())
    boots = []
    for _ in range(N_BOOT):
        boots.append(a[rng.integers(0, len(a), len(a))].mean()
                     - b[rng.integers(0, len(b), len(b))].mean())
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))
    return {"n_true": int(len(a)), "n_false": int(len(b)),
            "mean_true": round(float(a.mean()), 2), "mean_false": round(float(b.mean()), 2),
            "diff": round(diff, 2), "boot90_ci": [round(ci[0], 2), round(ci[1], 2)]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    print(f"[FU-5] pre-reg docs/FU5-PREREGISTRATION.md · A trend {TREND_H}h agree(+) · "
          f"B vol {VOL_MIN}m > causal median(+) · N_BOOT={N_BOOT} N_SHUF={N_SHUF} "
          f"SEED={SEED}", flush=True)
    rng = np.random.default_rng(SEED)
    frames = {i: leg_frame(i) for i in LEGS}
    res = {"conditions": {}}
    for cond, flag, okcol, pred in (("A_trend", "trend_pos", "trend_ok", "+"),
                                    ("B_vol", "vol_hi", "vol_ok", "+")):
        legs = {i: cond_stats(frames[i], flag, okcol, rng) for i in LEGS}
        nq = legs["NQ"]
        d = frames["NQ"]
        x = d[d[okcol]]
        mid = x.et.iloc[len(x) // 2]
        eras = {}
        for name, m in (("h1", x.et < mid), ("h2", x.et >= mid)):
            xx = x[m]
            aa = xx[xx[flag]].ride_net_stressed_usd
            bb = xx[~xx[flag]].ride_net_stressed_usd
            eras[name] = round(float(aa.mean() - bb.mean()), 2) \
                if len(aa) >= 5 and len(bb) >= 5 else None
        # shuffle control on NQ
        real = nq.get("diff", 0.0)
        shufs = []
        vals = x.ride_net_stressed_usd.to_numpy()
        fl = x[flag].to_numpy()
        for s in range(N_SHUF):
            r2 = np.random.default_rng(SEED + 1 + s)
            p = r2.permutation(fl)
            shufs.append(abs(float(vals[p].mean() - vals[~p].mean())))
        shuf95 = float(np.percentile(shufs, 95))
        others = [i for i in LEGS if i != "NQ"]
        agree = sum(1 for i in others
                    if legs[i].get("diff") is not None
                    and np.sign(legs[i].get("diff", 0)) == np.sign(real) and real != 0)
        ci = nq.get("boot90_ci", [0, 0])
        predicted_pos = real > 0
        ci_clear_pred = ci[0] > 0 if predicted_pos else False    # predicted direction is +
        ci_clear_opp = ci[1] < 0
        era_ok = all(v is not None and np.sign(v) == np.sign(real) for v in eras.values())
        if ci_clear_pred and agree >= 2 and era_ok and abs(real) > shuf95:
            verdict = "ARMED"
        elif ci_clear_opp and agree >= 2 and era_ok and abs(real) > shuf95:
            verdict = "CLOSED-CONTRARIAN"
        else:
            verdict = "CLOSED-NULL"
        sd = float(x.ride_net_stressed_usd.std(ddof=1))
        n1, n0 = nq.get("n_true", 0), nq.get("n_false", 0)
        mde = float(1.645 * sd * np.sqrt(1 / max(n1, 1) + 1 / max(n0, 1)))
        res["conditions"][cond] = {"predicted": pred, "legs": legs, "eras_nq": legs and eras,
                                   "shuffle_p95_abs": round(shuf95, 2),
                                   "cross_sign_agree": agree, "mde_diff": round(mde, 2),
                                   "verdict": verdict}
        print(f"[FU-5] {cond}: NQ diff {real:+,.0f} CI {ci} (n {n1}/{n0}) · others agree "
              f"{agree}/3 · eras {eras} · shuf95 {shuf95:,.0f} · MDE {mde:,.0f} "
              f"-> {verdict}", flush=True)
    out = Path(a.out)
    (out / "fu5_result.json").write_text(json.dumps(res, indent=2))
    feat = pd.concat([frames[i].assign(instrument=i) for i in LEGS], ignore_index=True)
    feat.to_csv(out / "fu5_features.csv", index=False)
    print(f"[FU-5] done -> fu5_result.json / fu5_features.csv "
          f"({len(feat)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
