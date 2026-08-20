#!/usr/bin/env python3
"""E-P1 (#169) — the earnings power model. Implements docs/EP1-PREREGISTRATION.md (frozen).

M2's machinery transplanted: P_hist per TICKER (expanding median of prior earnings-minute
|NQ move|%, shifted, >=8 priors) vs realized jump_pct. NQ primary; ES = full independent
replication. Gates: primary Fisher CI-lo>0 · V1 quintiles >=0.8 · V2 ES CI-lo>0 · V3 200
ticker-shuffles beat p95 · clean-minute control <= half the real rho.

    WSH_16Y_ROOT=... python3 optimize/earnings/ep1_power_model.py
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
FUND = PI_ROOT / "optimize" / "fundamentals"
for p_ in (str(PI_ROOT), str(FUND)):
    sys.path.insert(0, p_)

import p2_power_model as p2                    # noqa: E402
from extended_data import load_1m_extended     # noqa: E402
from scipy import stats                        # noqa: E402

TABLE = HERE / "data" / "earnings_timestamps_FINAL_16y.csv"
MIN_PRIOR, N_SHUF, SEED = 8, 200, 20260820
CTRL_OFFSETS = [3, 4, 5, 6, -3, -4, -5, -6]


def events() -> pd.DataFrame:
    d = pd.read_csv(TABLE, usecols=["ticker", "event_et", "session"])
    d["event_et"] = pd.to_datetime(d.event_et)
    return d.sort_values("event_et").reset_index(drop=True)


def score(inst: str, ev0: pd.DataFrame, rng) -> dict:
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    rm = p2.realized_moves(df1, pd.DatetimeIndex(ev0.event_et))
    ev = pd.concat([ev0.reset_index(drop=True), rm.reset_index(drop=True)], axis=1)
    n_all = len(ev)
    ev = ev.dropna(subset=["jump_pct"]).sort_values("event_et").reset_index(drop=True)
    print(f"[E-P1] {inst}: events with a bar {len(ev)}/{n_all}", flush=True)

    ev["pred"] = p2.build_predictions(ev, ev.ticker, trailing=0)
    m = ev.dropna(subset=["pred"]).reset_index(drop=True)
    r, p_ = stats.spearmanr(m.pred, m.jump_pct)
    lo, hi = p2.fisher_ci(float(r), len(m))
    out = {"n_scored": int(len(m)), "spearman": round(float(r), 4),
           "fisher_ci": [round(lo, 4), round(hi, 4)], "p": float(p_)}
    print(f"[E-P1] {inst}: primary rho {r:+.4f} CI [{lo:+.4f},{hi:+.4f}] n={len(m)}",
          flush=True)

    # V1 quintiles (NQ decides; reported for both)
    q = pd.qcut(m.pred, 5, labels=False, duplicates="drop")
    bm = m.groupby(q).jump_pct.mean()
    r_b, _ = stats.spearmanr(bm.index.to_numpy(), bm.to_numpy())
    out["v1_bucket_spearman"] = round(float(r_b), 4)
    out["v1_bucket_means"] = [round(float(x), 4) for x in bm.tolist()]

    # V3: 200 ticker-label shuffles, P_hist rebuilt each time
    shufs = []
    for s in range(N_SHUF):
        r2 = np.random.default_rng(SEED + 1 + s)
        lab = pd.Series(r2.permutation(ev.ticker.to_numpy()), index=ev.index)
        ps = p2.build_predictions(ev, lab, trailing=0)
        mm = pd.DataFrame({"p": ps, "j": ev.jump_pct}).dropna()
        shufs.append(float(stats.spearmanr(mm.p, mm.j)[0]))
    out["v3_shuffle"] = {"median": round(float(np.median(shufs)), 4),
                         "p95": round(float(np.percentile(shufs, 95)), 4)}

    # control: same clock minute, ±3–6 days, excluding any event day in the table
    ev_days = set(pd.to_datetime(ev0.event_et).dt.normalize())
    ctrl_stamps = []
    keep_idx = []
    for i, t in enumerate(m.event_et):
        for k in rng.permutation(len(CTRL_OFFSETS)):
            c = t + pd.Timedelta(days=int(CTRL_OFFSETS[k]))
            if c.normalize() not in ev_days:
                ctrl_stamps.append(c)
                keep_idx.append(i)
                break
    crm = p2.realized_moves(df1, pd.DatetimeIndex(ctrl_stamps))
    cj = crm.jump_pct.to_numpy()
    cp = m.pred.to_numpy()[keep_idx]
    okc = np.isfinite(cj)
    r_c, _ = stats.spearmanr(cp[okc], cj[okc])
    out["control"] = {"n": int(okc.sum()), "spearman": round(float(r_c), 4)}

    # jump gate context (stage-2 rhyme): event vs control mean |move|
    out["power_ratio_event_vs_control"] = round(
        float(np.nanmean(m.jump_pct.to_numpy()[keep_idx][okc]) / np.nanmean(cj[okc])), 2)
    m.to_csv(HERE / "data" / f"ep1_events_{inst}.csv", index=False)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()
    print(f"[E-P1] pre-reg docs/EP1-PREREGISTRATION.md · MIN_PRIOR={MIN_PRIOR} "
          f"N_SHUF={N_SHUF} SEED={SEED}", flush=True)
    rng = np.random.default_rng(SEED)
    ev0 = events()
    res = {"instruments": {}}
    for inst in ("NQ", "ES"):
        res["instruments"][inst] = score(inst, ev0, rng)

    nq = res["instruments"]["NQ"]
    es = res["instruments"]["ES"]
    g1 = nq["fisher_ci"][0] > 0
    g2 = nq["v1_bucket_spearman"] >= 0.8
    g3 = es["fisher_ci"][0] > 0
    g4 = nq["spearman"] > nq["v3_shuffle"]["p95"]
    g5 = abs(nq["control"]["spearman"]) <= 0.5 * abs(nq["spearman"])
    gates = {"1_primary_ci": g1, "2_v1_quintiles": g2, "3_es_confirm": g3,
             "4_shuffle_beat": g4, "5_control_weaker": g5}
    verdict = "PASS" if all(gates.values()) else "CLOSED-NEGATIVE"
    # power material (mandatory on a negative)
    n = nq["n_scored"]
    mdr = float(np.tanh(1.96 / np.sqrt(max(n - 3, 1))))   # min detectable rho at 95%
    res.update({"gates": gates, "verdict": verdict,
                "power": {"n_scored_nq": n, "min_detectable_rho": round(mdr, 4)}})
    (Path(a.out) / "ep1_result.json").write_text(json.dumps(res, indent=2))
    print(f"[E-P1] gates {gates} -> VERDICT {verdict} (min detectable rho {mdr:.3f})",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
