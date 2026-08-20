"""FU-9 (#161) — build the event-state dataset per docs/FU9-DATASET-SPEC.md (frozen).

One row per (event, instrument): identity + M2 power context + the frozen ride outcome
(deployed executor primitive on 1s data) + the 165-indicator state vector at the last closed
1m bar before the rel−300s entry + (NQ) the FU-1 box-book state. Integrity gates C1–C4 run
inside the build; the dataset is only written when all pass.

    WSH_16Y_ROOT=... python3 optimize/fundamentals/fu9_build.py --instrument NQ \
        --bars-1s ~/Mulham/data_2010_1s/NQ_Continuous_Data/NQ_1s.csv
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PI_ROOT = HERE.parents[1]
REPO = PI_ROOT.parents[1]
sys.path.insert(0, str(PI_ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import p2_power_model as p2                       # noqa: E402
from p1_ride_through import load_tv_events        # noqa: E402
from extended_data import load_1m_extended        # noqa: E402
from indicators.library import REGISTRY, build    # noqa: E402
from indicators.base import IndicatorConfig       # noqa: E402
from indicators import runner as ind_runner       # noqa: E402
from src.deploy.release_executor import (COST_PER_LEG, PV, Leg, load_1s_windows,  # noqa: E402
                                         run_bracket, LEAD_S, EXIT_S)
from src.deploy.schedule import load as load_schedule, DEFAULT_SCHEDULE  # noqa: E402

WINDOW_BARS = 2000        # 1m context per event (max default warmup = 255)
STANCE_LAG_S = 360        # stance bar = last 1m bar with Date <= rel - 360s (closed at entry)
C2_SAMPLE, SEED = 25, 20260820
RETAIL = "Retail Sales MoM"
BOX_TFS = ("4h", "2h", "1h", "15m", "5m", "2m")


def event_table(inst: str) -> pd.DataFrame:
    """Confirmed schedule (CPI/NFP/FOMC, >=2016) + Retail from the TV calendar."""
    sched = load_schedule(DEFAULT_SCHEDULE)
    sc = sched[(sched.status == "confirmed") & (sched.et.dt.year >= 2016)][["et", "title"]]
    sc = sc.assign(source="schedule")
    tv = load_tv_events(inst)
    rt = tv[(tv.title == RETAIL) & (pd.to_datetime(tv.et).dt.year >= 2016)][["et", "title"]]
    rt = rt.assign(source="tv")
    ev = pd.concat([sc, rt], ignore_index=True)
    ev["et"] = pd.to_datetime(ev.et)
    ev = ev.drop_duplicates(["et", "title"]).sort_values("et").reset_index(drop=True)
    return ev


def power_context(inst: str, ev: pd.DataFrame, df1: pd.DataFrame) -> pd.DataFrame:
    """M2's own machinery over the FULL modeled-series history, joined onto our events."""
    raw = load_tv_events(inst)
    full = pd.concat([raw.reset_index(drop=True),
                      p2.realized_moves(df1, pd.DatetimeIndex(raw.et))], axis=1)
    full = full.dropna(subset=["jump_pct"]).sort_values("et").reset_index(drop=True)
    full["et"] = pd.to_datetime(full.et)
    full["pred_exp"] = p2.build_predictions(full, full.title, trailing=0)
    full["pred_t24"] = p2.build_predictions(full, full.title, trailing=24)
    full["n_priors"] = full.groupby(full.title).cumcount()
    return ev.merge(full[["et", "title", "jump_pct", "pred_exp", "pred_t24", "n_priors"]],
                    on=["et", "title"], how="left")


def stance_rows(ev: pd.DataFrame, df1: pd.DataFrame,
                inds: dict) -> tuple[pd.DataFrame, dict, list]:
    """The 165-indicator state vector per event, plus per-indicator timing and the raw
    (window, stance_index) handles needed by the C2 falsifier."""
    d1 = df1.reset_index(drop=True)
    dts = d1["Date"].to_numpy()
    rows, handles = [], []
    timing = {k: 0.0 for k in inds}
    for _, r in ev.iterrows():
        cut = np.datetime64(r.et - pd.Timedelta(seconds=STANCE_LAG_S))
        j = np.searchsorted(dts, cut, side="right")  # rows [0, j) are usable; stance = j-1
        if j < 300:                                   # not enough history — keep NaN states
            rows.append({})
            handles.append(None)
            continue
        lo = max(0, j - WINDOW_BARS)
        win = d1.iloc[lo:j]
        ctx = ind_runner.market_context(win)
        last = len(win) - 1
        row = {}
        for k, ind in inds.items():
            t0 = time.time()
            try:
                cdir, vdir = ind.directions(ctx)
                w = int(ind.warmup_bars())
                if last < w:
                    row[f"cdir_{k}"], row[f"vdir_{k}"] = 0, 0
                else:
                    row[f"cdir_{k}"] = int(np.asarray(cdir)[last])
                    row[f"vdir_{k}"] = int(np.asarray(vdir)[last])
            except Exception as e:
                raise RuntimeError(f"indicator {k} failed at {r.et}: {e}") from e
            timing[k] += time.time() - t0
        rows.append(row)
        handles.append((lo, j))
    return pd.DataFrame(rows, index=ev.index), timing, handles


def c2_causality(ev: pd.DataFrame, df1: pd.DataFrame, states: pd.DataFrame,
                 handles: list, inds: dict) -> tuple[bool, str]:
    """Recompute a seeded sample with the window EXTENDED +1h past the release; the stance at
    the SAME bar must be unchanged (no indicator may repaint when future bars are appended)."""
    d1 = df1.reset_index(drop=True)
    dts = d1["Date"].to_numpy()
    ok_idx = [i for i, h in enumerate(handles) if h is not None]
    rng = np.random.default_rng(SEED)
    sample = rng.choice(ok_idx, size=min(C2_SAMPLE, len(ok_idx)), replace=False)
    for i in sample:
        lo, j = handles[i]
        fut = np.searchsorted(dts, np.datetime64(ev.et.iloc[i] + pd.Timedelta(hours=1)),
                              side="right")
        win = d1.iloc[lo:fut]
        ctx = ind_runner.market_context(win)
        pos = j - 1 - lo                              # the stance bar inside the extended window
        for k, ind in inds.items():
            cdir, vdir = ind.directions(ctx)
            w = int(ind.warmup_bars())
            exp_c = 0 if pos < w else int(np.asarray(cdir)[pos])
            exp_v = 0 if pos < w else int(np.asarray(vdir)[pos])
            if (exp_c != states.at[i, f"cdir_{k}"]) or (exp_v != states.at[i, f"vdir_{k}"]):
                return False, (f"REPAINT: {k} at {ev.et.iloc[i]} "
                               f"({states.at[i, f'cdir_{k}']},{states.at[i, f'vdir_{k}']}) "
                               f"-> ({exp_c},{exp_v}) with future bars appended")
    return True, f"{len(sample)} events x {len(inds)} indicators stance-stable under +1h future"


def ride_outcomes(inst: str, ev: pd.DataFrame, bars_1s: Path) -> pd.DataFrame:
    windows = [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
               for t in ev.et]
    bars = load_1s_windows(bars_1s, windows)
    print(f"[FU-9] {inst}: 1s bars loaded {len(bars):,}", flush=True)
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    out = []
    for _, r in ev.iterrows():
        f = run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("long", 1),
                        PV[inst], r.title)
        if f is None:
            out.append({"ride_outcome": None, "ride_exit_s": np.nan,
                        "ride_pnl_usd": np.nan, "ride_net_stressed_usd": np.nan})
        else:
            out.append({"ride_outcome": f.outcome, "ride_exit_s": f.exit_s_from_release,
                        "ride_pnl_usd": f.pnl_usd,
                        "ride_net_stressed_usd": f.pnl_usd - COST_PER_LEG[inst]["stressed"]})
    return pd.DataFrame(out, index=ev.index)


def box_state(ev: pd.DataFrame) -> pd.DataFrame:
    out = {}
    for tf in BOX_TFS:
        p = HERE / f"fu1_audit_{tf}.csv"
        t = pd.read_csv(p, parse_dates=["entry_time", "exit_time"])
        sgn = np.where(t.direction.astype(str).str.lower().eq("long"), 1, -1)
        col = np.zeros(len(ev), dtype=np.int8)
        for i, et in enumerate(ev.et):
            ts = et - pd.Timedelta(seconds=300)
            m = (t.entry_time <= ts) & (ts < t.exit_time)
            if m.any():
                col[i] = sgn[m.to_numpy()].max() if m.sum() == 1 else sgn[m.to_numpy()][0]
        out[f"box_{tf}"] = col
    return pd.DataFrame(out, index=ev.index)


def c1_parity(inst: str, df: pd.DataFrame) -> tuple[bool, str]:
    ref_p = HERE / f"wsescpi_replay_{inst}.csv"
    if not ref_p.exists():
        return True, "no committed replay evidence for this instrument (skip declared)"
    ref = pd.read_csv(ref_p, parse_dates=["et"])
    j = ref.merge(df[["et", "title", "ride_pnl_usd"]], on=["et", "title"], how="inner")
    if not len(j):
        return False, "ZERO overlap with the committed replay evidence"
    bad = (j.pnl_usd - j.ride_pnl_usd).abs() > 0.01
    return (not bad.any()), f"{len(j)} overlapping events, max |Δ| " \
                            f"{(j.pnl_usd - j.ride_pnl_usd).abs().max():.4f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=list(PV))
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    inst = a.instrument
    t0 = time.time()
    print(f"[FU-9] build {inst} · spec docs/FU9-DATASET-SPEC.md · WINDOW={WINDOW_BARS} "
          f"STANCE_LAG={STANCE_LAG_S}s SEED={SEED}", flush=True)

    ev = event_table(inst)
    print(f"[FU-9] events: {len(ev)} " +
          str(ev.groupby('title').size().to_dict()), flush=True)
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    ev = power_context(inst, ev, df1)

    inds = {k: build(k, IndicatorConfig(enabled=True)) for k in sorted(REGISTRY)}
    states, timing, handles = stance_rows(ev, df1, inds)
    top = sorted(timing.items(), key=lambda kv: -kv[1])[:10]
    print("[FU-9] top-10 indicator cost: " +
          ", ".join(f"{k} {v:.1f}s" for k, v in top), flush=True)

    rides = ride_outcomes(inst, ev, Path(a.bars_1s).expanduser())
    df = pd.concat([ev.assign(instrument=inst), rides, states], axis=1)
    if inst == "NQ":
        df = pd.concat([df, box_state(ev)], axis=1)

    gates = {}
    gates["C1_replay_parity"] = c1_parity(inst, df)
    gates["C2_causality"] = c2_causality(ev, df1, states, handles, inds)
    dup = df.duplicated(["instrument", "et", "title"]).sum()
    gates["C3_unique"] = (dup == 0, f"{dup} duplicates")
    cov = {}
    cov_ok = True
    span_lo = df1.Date.iloc[0]
    for ttl, g in ev.groupby("title"):
        expect = ((ev.title == ttl) & (ev.et >= span_lo)).sum()
        have = int(((df.title == ttl) & df.ride_pnl_usd.notna()).sum())
        cov[ttl] = f"{have}/{expect}"
        if expect and have < 0.9 * expect:
            cov_ok = False
    gates["C4_coverage"] = (cov_ok, json.dumps(cov))

    for g, (ok, msg) in gates.items():
        print(f"[FU-9] {g}: {'PASS' if ok else 'FAIL'} — {msg}", flush=True)
    all_ok = all(ok for ok, _ in gates.values())

    out = Path(a.out)
    if all_ok:
        dest = out / f"fu9_event_state_{inst}.csv"
        df.to_csv(dest, index=False)
        print(f"[FU-9] WRITTEN {dest} rows={len(df)} cols={len(df.columns)}", flush=True)
    else:
        print("[FU-9] GATES FAILED — dataset NOT written", flush=True)
    manifest = {"instrument": inst, "version": "v1", "rows": int(len(df)),
                "cols": int(len(df.columns)), "events_by_series": cov,
                "gates": {k: {"pass": bool(ok), "msg": m} for k, (ok, m) in gates.items()},
                "indicator_seconds_top10": {k: round(v, 2) for k, v in top},
                "wall_s": round(time.time() - t0, 1)}
    (out / f"fu9_manifest_{inst}.json").write_text(json.dumps(manifest, indent=2))
    print(f"[FU-9] done {inst} in {manifest['wall_s']}s -> "
          f"{'OK' if all_ok else 'GATES-FAILED'}", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
