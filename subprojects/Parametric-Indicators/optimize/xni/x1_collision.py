#!/usr/bin/env python3
"""X-1 (#173) — the collision census + compound-power measurement.
Implements docs/X1-PREREGISTRATION.md (frozen). Census + MDE first; the n>=30 gate decides
mechanically which types ever compute an outcome.

    WSH_16Y_ROOT=... python3 optimize/xni/x1_collision.py --instrument NQ
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
EARN = PI_ROOT / "optimize" / "earnings" / "data"
for p_ in (str(PI_ROOT), str(FUND)):
    sys.path.insert(0, p_)

import p2_power_model as p2                    # noqa: E402
from p1_ride_through import load_tv_events     # noqa: E402
from extended_data import load_1m_extended     # noqa: E402

N_BOOT, N_SHUF, SEED, GATE_N = 10000, 200, 20260820, 30


def macro_events(inst: str) -> pd.DataFrame:
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    raw = load_tv_events(inst)
    ev = pd.concat([raw.reset_index(drop=True),
                    p2.realized_moves(df1, pd.DatetimeIndex(raw.et))], axis=1)
    ev = ev.dropna(subset=["jump_pct"]).sort_values("et").reset_index(drop=True)
    ev["et"] = pd.to_datetime(ev.et)
    return ev[ev.jump_pct > 0].reset_index(drop=True)


def run(inst: str, out_dir: Path) -> dict:
    print(f"[X-1] instrument={inst} · GATE n>={GATE_N} · N_SHUF={N_SHUF} SEED={SEED}",
          flush=True)
    mac = macro_events(inst)
    earn = pd.read_csv(EARN / f"ep1_events_{inst}.csv", parse_dates=["event_et"])
    e_et = earn.event_et.to_numpy()
    m_et = mac.et.to_numpy()

    def flag(lo_h: float, hi_h: float) -> np.ndarray:
        out = np.zeros(len(mac), dtype=bool)
        for i, t in enumerate(m_et):
            d = (t - e_et) / np.timedelta64(1, "h")
            out[i] = bool(np.any((d > lo_h) & (d <= hi_h)))
        return out

    t1 = flag(0.0, 18.0)                      # earnings 0-18h BEFORE the macro event
    t2 = flag(-24.0, 24.0)                    # earnings within +-24h
    # symmetric earnings-side census (no registered outcome)
    e_flag = np.zeros(len(earn), dtype=bool)
    for i, t in enumerate(e_et):
        d = (t - m_et) / np.timedelta64(1, "h")
        e_flag[i] = bool(np.any(np.abs(d) <= 24.0))

    res = {"instrument": inst, "n_macro": int(len(mac)), "n_earn": int(len(earn)),
           "census": {"T1": int(t1.sum()), "T2": int(t2.sum()),
                      "earnings_side_24h": int(e_flag.sum())},
           "types": {}}
    print(f"[X-1] census: macro={len(mac)} earn={len(earn)} · T1={t1.sum()} "
          f"T2={t2.sum()} · earnings-side {e_flag.sum()}", flush=True)

    lj = np.log(mac.jump_pct.to_numpy(float))
    rng = np.random.default_rng(SEED)
    for name, fl in (("T1", t1), ("T2", t2)):
        n = int(fl.sum())
        sd = float(np.std(lj, ddof=1))
        mde = float(1.645 * sd * np.sqrt(2.0 / max(n, 1)))
        entry = {"n": n, "mde_logjump": round(mde, 4)}
        if n < GATE_N:
            entry["verdict"] = "CLOSED-UNDERPOWERED"
            res["types"][name] = entry
            print(f"[X-1] {name}: n={n} < {GATE_N} -> CLOSED-UNDERPOWERED "
                  f"(MDE {mde:.3f})", flush=True)
            continue
        # matched controls: nearest-in-time non-collision same-series, no replacement
        diffs = []
        used = set()
        for i in np.where(fl)[0]:
            g = mac[(mac.title == mac.title.iloc[i]) & (~fl)]
            g = g[~g.index.isin(used)]
            if not len(g):
                continue
            j = (g.et - mac.et.iloc[i]).abs().idxmin()
            used.add(j)
            diffs.append(lj[i] - lj[j])   # RangeIndex: label == position
        diffs = np.array(diffs)
        m = float(np.mean(diffs))
        boots = np.array([diffs[rng.integers(0, len(diffs), len(diffs))].mean()
                          for _ in range(N_BOOT)])
        ci = [round(float(np.percentile(boots, 5)), 4),
              round(float(np.percentile(boots, 95)), 4)]
        shufs = []
        for s in range(N_SHUF):
            r2 = np.random.default_rng(SEED + 1 + s)
            fs = np.zeros(len(mac), dtype=bool)
            for _t, g in mac.groupby("title"):
                ii = g.index.to_numpy()
                k = int(fl[ii].sum())
                if k:
                    fs[r2.choice(ii, size=k, replace=False)] = True
            d2 = []
            u2 = set()
            for i in np.where(fs)[0]:
                g = mac[(mac.title == mac.title.iloc[i]) & (~fs)]
                g = g[~g.index.isin(u2)]
                if not len(g):
                    continue
                j = (g.et - mac.et.iloc[i]).abs().idxmin()
                u2.add(j)
                d2.append(lj[i] - lj[j])
            if d2:
                shufs.append(float(np.mean(d2)))
        p95 = float(np.percentile(shufs, 95))
        entry.update({"n_matched": int(len(diffs)), "mean_logjump_diff": round(m, 4),
                      "boot90_ci": ci, "shuffle_p95": round(p95, 4)})
        if m > 0 and ci[0] > 0 and m > p95:
            entry["verdict"] = "SUPER-ADDITIVE-CANDIDATE"   # needs the ES witness
        elif ci[1] < 0:
            entry["verdict"] = "CLOSED-CONTRARIAN-CANDIDATE"
        else:
            entry["verdict"] = "CLOSED-INDEPENDENT"
        res["types"][name] = entry
        print(f"[X-1] {name}: n={n} matched={len(diffs)} Δlog {m:+.4f} CI {ci} "
              f"shuf95 {p95:+.4f} -> {entry['verdict']}", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"x1_result_{inst}.json").write_text(json.dumps(res, indent=2))
    print(f"[X-1] done {inst} -> x1_result_{inst}.json", flush=True)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=["NQ", "ES"])
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()
    run(a.instrument, Path(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
